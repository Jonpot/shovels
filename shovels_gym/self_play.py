"""
Self-play training infrastructure for Shovels RL.

Provides:
- PolicyAgent: Wraps a MaskablePPO model as an Agent for opponent play
- OpponentPool: Manages a pool of historical checkpoints + RandomAgent
- SelfPlayCallback: SB3 callback that manages checkpoint rotation during training
"""

import os
import random

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback
from sb3_contrib import MaskablePPO

from shovels_engine.agents import Agent, RandomAgent
from shovels_engine.engine import end_turn
from shovels_engine.models import GameState
from shovels_gym.action_space import action_masks as compute_action_masks, decode_action
from shovels_gym.action_utils import execute_action
from shovels_gym.obs_space import encode_observation


class PolicyAgent(Agent):
    """Wraps a MaskablePPO model to implement the Agent interface."""

    def __init__(self, model: MaskablePPO, deterministic: bool = False):
        self.model = model
        self.deterministic = deterministic

    def act(self, state: GameState, player_id: str):
        obs = encode_observation(state, player_id)
        mask = compute_action_masks(state, player_id)
        action, _ = self.model.predict(obs, deterministic=self.deterministic, action_masks=mask)
        decoded = decode_action(int(action), state, player_id)
        execute_action(decoded, state, player_id)


class OpponentPool:
    """Manages a pool of opponent policies for self-play training."""

    def __init__(self, max_size: int = 20, random_prob: float = 0.2):
        self.checkpoints: list[str] = []
        self.max_size = max_size
        self.random_prob = random_prob
        self._random_agent = RandomAgent()

    def sample(self) -> Agent:
        """Sample an opponent from the pool."""
        if not self.checkpoints or random.random() < self.random_prob:
            return self._random_agent
        # Weighted toward recent checkpoints (exponential decay)
        weights = [2 ** i for i in range(len(self.checkpoints))]
        path = random.choices(self.checkpoints, weights=weights, k=1)[0]
        model = MaskablePPO.load(path)
        return PolicyAgent(model, deterministic=False)

    def add_checkpoint(self, model: MaskablePPO, save_dir: str):
        """Save current model as a new checkpoint in the pool."""
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"checkpoint_{len(self.checkpoints)}")
        model.save(path)
        self.checkpoints.append(path)
        if len(self.checkpoints) > self.max_size:
            # Keep first (earliest baseline) and most recent, evict second oldest
            self.checkpoints.pop(1)


class SelfPlayCallback(BaseCallback):
    """SB3 callback that manages opponent pool and evaluation during self-play training."""

    def __init__(
        self,
        opponent_pool: OpponentPool,
        checkpoint_freq: int = 50_000,
        eval_freq: int = 25_000,
        n_eval_games: int = 100,
        milestone_freq: int = 500_000,
        save_dir: str = "models/checkpoints",
        log_dir: str = "logs/selfplay",
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.opponent_pool = opponent_pool
        self.checkpoint_freq = checkpoint_freq
        self.eval_freq = eval_freq
        self.n_eval_games = n_eval_games
        self.milestone_freq = milestone_freq
        self.save_dir = save_dir
        self.log_dir = log_dir

        # Tracking
        self.random_win_rates: list[float] = []
        self.selfplay_win_rates: list[float] = []
        self.timesteps_log: list[int] = []

        # Milestone tracking: label -> path
        self.milestones: dict[str, str] = {}
        # Win rates per milestone: label -> list of win rates
        self.milestone_win_rates: dict[str, list[float]] = {}
        self._next_milestone = milestone_freq

    def register_base_model(self, path: str, label: str = "0M"):
        """Register the base model (post random-agent training) as milestone 0M."""
        self.milestones[label] = path
        self.milestone_win_rates[label] = []

    def _on_step(self) -> bool:
        if self.num_timesteps % self.checkpoint_freq == 0 and self.num_timesteps > 0:
            self.opponent_pool.add_checkpoint(self.model, self.save_dir)
            if self.verbose:
                print(f"[{self.num_timesteps}] Checkpoint saved "
                      f"(pool size: {len(self.opponent_pool.checkpoints)})")

        # Save milestone checkpoints (separate from opponent pool)
        if self.num_timesteps >= self._next_milestone:
            label = f"{self._next_milestone / 1_000_000:.1f}M"
            milestone_dir = os.path.join(self.save_dir, "milestones")
            os.makedirs(milestone_dir, exist_ok=True)
            milestone_path = os.path.join(milestone_dir, f"milestone_{label}")
            self.model.save(milestone_path)
            self.milestones[label] = milestone_path
            self.milestone_win_rates[label] = []
            self._next_milestone += self.milestone_freq
            if self.verbose:
                print(f"[{self.num_timesteps}] Milestone saved: {label}")

        if self.num_timesteps % self.eval_freq == 0 and self.num_timesteps > 0:
            self._evaluate()

        return True

    def _on_rollout_start(self) -> None:
        """Sample a new opponent at the start of each rollout."""
        opponent = self.opponent_pool.sample()
        env = self.training_env.envs[0]
        # Unwrap to get the underlying ShovelsEnv
        while hasattr(env, "env"):
            env = env.env
        env.set_opponent(opponent)

    def _on_training_end(self) -> None:
        self._save_plots()

    def _evaluate(self):
        """Evaluate against RandomAgent, latest checkpoint, and all milestones."""
        from shovels_gym.envs.shovels_env import ShovelsEnv

        random_wr = self._play_games(ShovelsEnv(), self.n_eval_games)

        selfplay_wr = None
        if self.opponent_pool.checkpoints:
            latest = MaskablePPO.load(self.opponent_pool.checkpoints[-1])
            opponent = PolicyAgent(latest, deterministic=True)
            selfplay_wr = self._play_games(
                ShovelsEnv(opponent_agent=opponent), self.n_eval_games
            )

        self.random_win_rates.append(random_wr)
        self.selfplay_win_rates.append(selfplay_wr if selfplay_wr is not None else 0.0)
        self.timesteps_log.append(self.num_timesteps)

        if self.verbose:
            sp_str = f"{selfplay_wr:.2%}" if selfplay_wr is not None else "N/A"
            print(f"[{self.num_timesteps}] vs Random: {random_wr:.2%} | "
                  f"vs Latest Checkpoint: {sp_str}")

        # Evaluate against each milestone
        for label, path in self.milestones.items():
            try:
                opp_model = MaskablePPO.load(path)
                opp = PolicyAgent(opp_model, deterministic=True)
                wr = self._play_games(ShovelsEnv(opponent_agent=opp), self.n_eval_games)
                self.milestone_win_rates[label].append(wr)
                if self.verbose:
                    print(f"  vs {label}: {wr:.2%}")
                if self.logger:
                    self.logger.record(f"selfplay/wr_vs_{label}", wr)
            except Exception as e:
                if self.verbose:
                    print(f"  vs {label}: ERROR ({e})")
                self.milestone_win_rates[label].append(0.0)

        if self.logger:
            self.logger.record("selfplay/wr_vs_random", random_wr)
            if selfplay_wr is not None:
                self.logger.record("selfplay/wr_vs_checkpoint", selfplay_wr)

    def _play_games(self, env, n_games: int) -> float:
        """Play n_games and return win rate."""
        wins = 0
        for _ in range(n_games):
            obs, info = env.reset()
            done = False
            while not done:
                mask = env.action_masks()
                action, _ = self.model.predict(obs, deterministic=True, action_masks=mask)
                obs, reward, terminated, truncated, info = env.step(int(action))
                done = terminated or truncated
            if info.get("winner_id") == "agent":
                wins += 1
        return wins / n_games

    def _save_plots(self):
        """Generate training curve plots."""
        if not self.timesteps_log:
            return

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not available, skipping plots")
            return

        os.makedirs(self.log_dir, exist_ok=True)

        fig, ax = plt.subplots(figsize=(12, 7))
        ax.plot(self.timesteps_log, self.random_win_rates, "b-o", markersize=3, label="vs Random")
        ax.plot(self.timesteps_log, self.selfplay_win_rates, "r-s", markersize=3, label="vs Latest Checkpoint")

        # Plot milestone win rates
        colors = plt.cm.viridis(np.linspace(0.2, 0.8, max(len(self.milestones), 1)))
        for i, (label, wrs) in enumerate(self.milestone_win_rates.items()):
            if wrs:
                # Milestone evals only start after the milestone is created,
                # so align x-axis to the tail of timesteps_log
                n = len(wrs)
                ts = self.timesteps_log[-n:]
                ax.plot(ts, wrs, "--", color=colors[i % len(colors)], markersize=2,
                        alpha=0.7, label=f"vs {label}")

        ax.set_xlabel("Timesteps")
        ax.set_ylabel("Win Rate")
        ax.set_title("Self-Play Training: Win Rates")
        ax.set_ylim(0, 1)
        ax.axhline(y=0.5, color="gray", linestyle="--", alpha=0.5)
        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.savefig(os.path.join(self.log_dir, "selfplay_win_rates.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

        if self.verbose:
            print(f"Self-play plots saved to {self.log_dir}/")
