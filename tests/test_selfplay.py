"""Tests for self-play training infrastructure."""

import os
import tempfile
import numpy as np
import pytest

from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from shovels_engine.agents import RandomAgent
from shovels_gym.envs.shovels_env import ShovelsEnv
from shovels_gym.self_play import PolicyAgent, OpponentPool, SelfPlayCallback


def _make_model():
    """Create a minimal MaskablePPO model for testing."""
    env = ShovelsEnv()
    env = ActionMasker(env, lambda e: e.action_masks())
    model = MaskablePPO(
        "MlpPolicy", env, n_steps=128, batch_size=32, n_epochs=2, verbose=0,
    )
    model.learn(total_timesteps=256)
    return model


def test_policy_agent_acts():
    """PolicyAgent can complete a full game without error."""
    model = _make_model()
    agent = PolicyAgent(model, deterministic=True)
    env = ShovelsEnv(opponent_agent=agent)
    obs, info = env.reset()
    done = False
    steps = 0
    while not done and steps < 500:
        mask = env.action_masks()
        valid = np.where(mask)[0]
        action = np.random.choice(valid)
        obs, reward, terminated, truncated, info = env.step(int(action))
        done = terminated or truncated
        steps += 1
    # Game should complete (not hang)
    assert steps < 500 or info["is_over"]


def test_opponent_pool_empty_returns_random():
    """Empty pool always returns RandomAgent."""
    pool = OpponentPool(random_prob=0.0)
    agent = pool.sample()
    assert isinstance(agent, RandomAgent)


def test_opponent_pool_with_checkpoints():
    """Pool with checkpoints returns PolicyAgent when not selecting random."""
    pool = OpponentPool(random_prob=0.0)
    model = _make_model()
    with tempfile.TemporaryDirectory() as tmpdir:
        pool.add_checkpoint(model, tmpdir)
        agent = pool.sample()
        assert isinstance(agent, PolicyAgent)


def test_opponent_pool_random_prob():
    """Pool respects random_prob=1.0 to always return RandomAgent."""
    pool = OpponentPool(random_prob=1.0)
    model = _make_model()
    with tempfile.TemporaryDirectory() as tmpdir:
        pool.add_checkpoint(model, tmpdir)
        # With random_prob=1.0, should always get RandomAgent
        for _ in range(10):
            assert isinstance(pool.sample(), RandomAgent)


def test_opponent_pool_max_size():
    """Pool evicts old checkpoints when exceeding max_size."""
    pool = OpponentPool(max_size=3)
    model = _make_model()
    with tempfile.TemporaryDirectory() as tmpdir:
        for _ in range(5):
            pool.add_checkpoint(model, tmpdir)
        assert len(pool.checkpoints) == 3


def test_selfplay_env_accepts_opponent():
    """ShovelsEnv works with PolicyAgent as opponent."""
    model = _make_model()
    agent = PolicyAgent(model)
    env = ShovelsEnv(opponent_agent=agent)
    obs, info = env.reset()
    assert obs.shape == env.observation_space.shape


def test_set_opponent_swaps():
    """set_opponent changes the opponent used in subsequent games."""
    env = ShovelsEnv()
    assert isinstance(env.opponent_agent, RandomAgent)

    model = _make_model()
    policy = PolicyAgent(model)
    env.set_opponent(policy)
    assert isinstance(env.opponent_agent, PolicyAgent)

    # Should still work after swap
    obs, info = env.reset()
    assert obs.shape == env.observation_space.shape


def test_selfplay_training_smoke():
    """Train 1000 steps with self-play callback, no crash."""
    pool = OpponentPool(random_prob=1.0)  # Start with only random
    env = ShovelsEnv(opponent_agent=pool.sample())
    env = ActionMasker(env, lambda e: e.action_masks())

    model = MaskablePPO(
        "MlpPolicy", env, n_steps=128, batch_size=32, n_epochs=2, verbose=0,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        callback = SelfPlayCallback(
            opponent_pool=pool,
            checkpoint_freq=500,
            eval_freq=500,
            n_eval_games=5,
            save_dir=os.path.join(tmpdir, "checkpoints"),
            log_dir=os.path.join(tmpdir, "plots"),
            verbose=0,
        )
        model.learn(total_timesteps=1000, callback=callback)

    # Pool should have gained checkpoints
    assert len(pool.checkpoints) >= 1
