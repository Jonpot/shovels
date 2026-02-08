"""
Training callbacks for Shovels RL training.

WinRateCallback evaluates the model against RandomAgent periodically
and generates training curves.
"""

import os
import numpy as np
from stable_baselines3.common.callbacks import BaseCallback


class WinRateCallback(BaseCallback):
    """Evaluate model vs RandomAgent periodically during training."""

    def __init__(self, eval_freq=10000, n_eval_games=100, log_dir="./logs/training_plots", verbose=1):
        super().__init__(verbose)
        self.eval_freq = eval_freq
        self.n_eval_games = n_eval_games
        self.log_dir = log_dir

        self.win_rates = []
        self.avg_rewards = []
        self.avg_lengths = []
        self.timesteps_log = []

    def _on_step(self) -> bool:
        if self.num_timesteps % self.eval_freq == 0:
            self._evaluate()
        return True

    def _on_training_end(self) -> None:
        self._save_plots()

    def _evaluate(self):
        """Play n_eval_games and record stats."""
        from shovels_gym.envs.shovels_env import ShovelsEnv

        env = ShovelsEnv()
        wins = 0
        total_reward = 0.0
        total_length = 0

        for _ in range(self.n_eval_games):
            obs, info = env.reset()
            done = False
            ep_reward = 0.0
            ep_length = 0

            while not done:
                mask = env.action_masks()
                action, _ = self.model.predict(obs, deterministic=True, action_masks=mask)
                obs, reward, terminated, truncated, info = env.step(int(action))
                ep_reward += reward
                ep_length += 1
                done = terminated or truncated

            if info.get("winner_id") == "agent":
                wins += 1
            total_reward += ep_reward
            total_length += ep_length

        win_rate = wins / self.n_eval_games
        avg_reward = total_reward / self.n_eval_games
        avg_length = total_length / self.n_eval_games

        self.win_rates.append(win_rate)
        self.avg_rewards.append(avg_reward)
        self.avg_lengths.append(avg_length)
        self.timesteps_log.append(self.num_timesteps)

        if self.verbose:
            print(f"[{self.num_timesteps}] Win rate: {win_rate:.2%} | "
                  f"Avg reward: {avg_reward:.3f} | Avg length: {avg_length:.1f}")

        # Log to tensorboard if available
        if self.logger:
            self.logger.record("eval/win_rate", win_rate)
            self.logger.record("eval/avg_reward", avg_reward)
            self.logger.record("eval/avg_length", avg_length)

    def _save_plots(self):
        """Generate and save training curve plots."""
        if not self.timesteps_log:
            return

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not available, skipping plot generation")
            return

        os.makedirs(self.log_dir, exist_ok=True)

        # Win rate plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(self.timesteps_log, self.win_rates, "b-o", markersize=3)
        ax.set_xlabel("Timesteps")
        ax.set_ylabel("Win Rate")
        ax.set_title("Win Rate vs Random Agent")
        ax.set_ylim(0, 1)
        ax.axhline(y=0.5, color="r", linestyle="--", alpha=0.5, label="50% baseline")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.savefig(os.path.join(self.log_dir, "win_rate.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

        # Average reward plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(self.timesteps_log, self.avg_rewards, "g-o", markersize=3)
        ax.set_xlabel("Timesteps")
        ax.set_ylabel("Average Reward")
        ax.set_title("Average Episode Reward")
        ax.grid(True, alpha=0.3)
        fig.savefig(os.path.join(self.log_dir, "avg_reward.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

        # Average game length plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(self.timesteps_log, self.avg_lengths, "m-o", markersize=3)
        ax.set_xlabel("Timesteps")
        ax.set_ylabel("Average Game Length (steps)")
        ax.set_title("Average Game Length")
        ax.grid(True, alpha=0.3)
        fig.savefig(os.path.join(self.log_dir, "avg_length.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

        if self.verbose:
            print(f"Training plots saved to {self.log_dir}/")
