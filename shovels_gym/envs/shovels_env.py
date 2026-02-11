"""
Gymnasium environment for the Shovels card game.

Agent is always player index 0. Opponent is configurable (defaults to RandomAgent).
"""

import random as py_random

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from shovels_engine.models import setup_game, GameState
from shovels_engine.agents import RandomAgent
from shovels_engine.engine import end_turn
from shovels_gym.action_space import (
    ACTION_SPACE_SIZE, action_masks, decode_action,
)
from shovels_gym.action_utils import execute_action
from shovels_gym.obs_space import OBS_SIZE, encode_observation


AGENT_ID = "agent"
OPPONENT_ID = "opponent"


class ShovelsEnv(gym.Env):
    """Shovels card game as a Gymnasium environment with action masking."""

    metadata = {"render_modes": []}

    def __init__(self, max_steps=500, opponent_agent=None, **kwargs):
        super().__init__()
        self.max_steps = max_steps

        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBS_SIZE,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(ACTION_SPACE_SIZE)

        self.state: GameState = None  # type: ignore
        self.opponent_agent = opponent_agent or RandomAgent()
        self.step_count = 0

    def set_opponent(self, agent):
        """Swap the opponent agent (used by self-play callback between episodes)."""
        self.opponent_agent = agent

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        # Seed Python's random module for determinism (engine uses random internally)
        if seed is not None:
            py_random.seed(seed)
        self.state = setup_game([AGENT_ID, OPPONENT_ID])
        self.state.enable_reactions = True
        self.step_count = 0

        # If opponent goes first, run their turns
        self._run_opponent_turns()

        obs = encode_observation(self.state, AGENT_ID)
        info = self._get_info()
        return obs, info

    def step(self, action: int):
        assert not self.state.is_over, "Game is already over"

        mask = self.action_masks()
        if not mask[action]:
            # Invalid action - penalize and skip
            obs = encode_observation(self.state, AGENT_ID)
            return obs, -0.1, False, False, self._get_info()

        # Snapshot for reward calculation
        opp_alive_before = sum(1 for c in self._get_opponent().characters if not c.is_dead)
        own_alive_before = sum(1 for c in self._get_player().characters if not c.is_dead)

        # Execute action
        try:
            self._execute_action(action)
        except (ValueError, AssertionError, IndexError, StopIteration):
            # Engine rejected the action - small penalty, don't end game
            obs = encode_observation(self.state, AGENT_ID)
            return obs, -0.01, False, False, self._get_info()

        # Run opponent turns if it's their turn
        if not self.state.is_over:
            self._run_opponent_turns()

        self.step_count += 1

        # Calculate reward
        reward = self._calculate_reward(opp_alive_before, own_alive_before)

        terminated = self.state.is_over
        truncated = self.step_count >= self.max_steps

        obs = encode_observation(self.state, AGENT_ID)
        info = self._get_info()

        return obs, reward, terminated, truncated, info

    def action_masks(self) -> np.ndarray:
        """Return boolean mask over action space."""
        return action_masks(self.state, AGENT_ID)

    def _execute_action(self, action: int):
        """Decode and execute a single action."""
        decoded = decode_action(action, self.state, AGENT_ID)
        execute_action(decoded, self.state, AGENT_ID)

    def _run_opponent_turns(self):
        """Run opponent turns until it's the agent's turn or game over.

        Handles DEFENSE_REACTION: if agent needs to react, returns control.
        If opponent needs to react, handles it automatically.
        """
        safety = 0
        while not self.state.is_over and safety < 200:
            # Check for defense reaction first
            if self.state.turn_subphase == "DEFENSE_REACTION":
                pa = self.state.pending_attack
                if pa and pa.target_player_id == AGENT_ID:
                    break  # Agent needs to react — return control
                elif pa and pa.target_player_id == OPPONENT_ID:
                    # Opponent reacts automatically
                    try:
                        self.opponent_agent.act(self.state, OPPONENT_ID)
                    except Exception:
                        # Auto-pass on error
                        from shovels_engine.engine import resolve_defense_reaction
                        try:
                            resolve_defense_reaction(self.state, OPPONENT_ID, tap=False)
                        except Exception:
                            break
                    safety += 1
                    continue

            current_id = self.state.players[self.state.current_turn_index].id
            if current_id != OPPONENT_ID:
                break  # Agent's turn

            try:
                self.opponent_agent.act(self.state, OPPONENT_ID)
            except Exception:
                try:
                    end_turn(self.state)
                except Exception:
                    break
            safety += 1

    def _calculate_reward(self, opp_alive_before: int, own_alive_before: int) -> float:
        """Calculate shaped reward from state diff."""
        reward = -0.005  # step penalty

        if self.state.is_over:
            if self.state.winner_id == AGENT_ID:
                reward += 1.0
            elif self.state.winner_id == OPPONENT_ID:
                reward -= 1.0
            # Draw: no bonus/penalty
            return reward

        # Character kills/losses
        opp_alive_after = sum(1 for c in self._get_opponent().characters if not c.is_dead)
        own_alive_after = sum(1 for c in self._get_player().characters if not c.is_dead)

        opp_killed = opp_alive_before - opp_alive_after
        own_lost = own_alive_before - own_alive_after

        reward += opp_killed * 0.1
        reward -= own_lost * 0.1

        return reward

    def _get_player(self):
        return next(p for p in self.state.players if p.id == AGENT_ID)

    def _get_opponent(self):
        return next(p for p in self.state.players if p.id == OPPONENT_ID)

    def _get_info(self) -> dict:
        return {
            "phase": self.state.phase,
            "subphase": self.state.turn_subphase,
            "turn_count": self.state.turn_count,
            "is_over": self.state.is_over,
            "winner_id": self.state.winner_id,
        }
