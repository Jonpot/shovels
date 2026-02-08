"""Training smoke tests for the Shovels Gymnasium environment."""

import os
import tempfile
import pytest

from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from shovels_gym.envs.shovels_env import ShovelsEnv


def _make_env():
    env = ShovelsEnv()
    return ActionMasker(env, lambda e: e.action_masks())


def test_training_smoke():
    """Train for 1000 steps without crashing."""
    env = _make_env()
    model = MaskablePPO(
        "MlpPolicy",
        env,
        n_steps=128,
        batch_size=32,
        n_epochs=2,
        verbose=0,
    )
    model.learn(total_timesteps=1000)


def test_model_save_load():
    """Save and reload a trained model."""
    env = _make_env()
    model = MaskablePPO(
        "MlpPolicy",
        env,
        n_steps=128,
        batch_size=32,
        n_epochs=2,
        verbose=0,
    )
    model.learn(total_timesteps=256)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_model")
        model.save(path)
        assert os.path.exists(path + ".zip")

        loaded = MaskablePPO.load(path)
        # Verify loaded model can predict
        obs, _ = ShovelsEnv().reset()
        action, _ = loaded.predict(obs, deterministic=True)
        assert 0 <= action < 240
