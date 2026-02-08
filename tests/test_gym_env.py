"""Tests for the Shovels Gymnasium environment."""

import numpy as np
import pytest
import gymnasium as gym

from shovels_gym.envs.shovels_env import ShovelsEnv
from shovels_gym.obs_space import OBS_SIZE
from shovels_gym.action_space import ACTION_SPACE_SIZE


@pytest.fixture
def env():
    return ShovelsEnv()


def test_check_env():
    """Run gymnasium's built-in environment checker."""
    from gymnasium.utils.env_checker import check_env
    env = ShovelsEnv()
    # check_env will raise if something is wrong
    check_env(env, skip_render_check=True)


def test_reset_returns_valid_obs(env):
    """reset() returns observation with correct shape and bounds."""
    obs, info = env.reset()
    assert obs.shape == (OBS_SIZE,)
    assert obs.dtype == np.float32
    assert np.all(obs >= 0.0)
    assert np.all(obs <= 1.0)
    assert isinstance(info, dict)


def test_action_masks_shape(env):
    """action_masks() returns correct shape."""
    env.reset()
    mask = env.action_masks()
    assert mask.shape == (ACTION_SPACE_SIZE,)
    assert mask.dtype == bool


def test_action_masks_always_has_valid(env):
    """At least one action is valid at every step."""
    env.reset()
    for _ in range(50):
        mask = env.action_masks()
        assert mask.any(), "No valid actions available"
        valid_actions = np.where(mask)[0]
        action = np.random.choice(valid_actions)
        obs, reward, terminated, truncated, info = env.step(int(action))
        if terminated or truncated:
            break


def test_full_random_game(env):
    """Play a full game using random masked actions."""
    obs, info = env.reset()
    done = False
    steps = 0
    max_steps = 1000

    while not done and steps < max_steps:
        mask = env.action_masks()
        valid_actions = np.where(mask)[0]
        assert len(valid_actions) > 0, f"No valid actions at step {steps}"
        action = np.random.choice(valid_actions)
        obs, reward, terminated, truncated, info = env.step(int(action))
        done = terminated or truncated
        steps += 1

    assert done, f"Game did not complete in {max_steps} steps"


def test_observation_bounds(env):
    """All observation values stay in [0, 1] throughout a game."""
    obs, _ = env.reset()
    assert np.all(obs >= 0.0) and np.all(obs <= 1.0), "Initial obs out of bounds"

    for _ in range(100):
        mask = env.action_masks()
        valid_actions = np.where(mask)[0]
        action = np.random.choice(valid_actions)
        obs, reward, terminated, truncated, info = env.step(int(action))
        assert np.all(obs >= 0.0) and np.all(obs <= 1.0), "Obs out of bounds during game"
        if terminated or truncated:
            break


def test_reward_on_win_loss(env):
    """Terminal rewards should be +1 for win, -1 for loss."""
    # Play many games and check terminal rewards
    for _ in range(20):
        obs, _ = env.reset()
        done = False
        last_reward = 0.0
        steps = 0

        while not done and steps < 1000:
            mask = env.action_masks()
            valid_actions = np.where(mask)[0]
            action = np.random.choice(valid_actions)
            obs, reward, terminated, truncated, info = env.step(int(action))
            last_reward = reward
            done = terminated or truncated
            steps += 1

        if info.get("winner_id") == "agent":
            # Win reward should include +1.0
            assert last_reward > 0.5, f"Expected positive terminal reward on win, got {last_reward}"
        elif info.get("winner_id") == "opponent":
            # Loss reward should include -1.0
            assert last_reward < -0.5, f"Expected negative terminal reward on loss, got {last_reward}"


def test_multiple_games(env):
    """Run 10 full games, all should complete without error."""
    completed = 0
    for _ in range(10):
        obs, _ = env.reset()
        done = False
        steps = 0

        while not done and steps < 1000:
            mask = env.action_masks()
            valid_actions = np.where(mask)[0]
            action = np.random.choice(valid_actions)
            obs, reward, terminated, truncated, info = env.step(int(action))
            done = terminated or truncated
            steps += 1

        if done:
            completed += 1

    assert completed == 10, f"Only {completed}/10 games completed"


def test_env_registration():
    """Environment can be created via gymnasium.make()."""
    import shovels_gym  # noqa: F401 - triggers registration
    env = gym.make("Shovels-v0")
    obs, info = env.reset()
    assert obs.shape == (OBS_SIZE,)
    env.close()
