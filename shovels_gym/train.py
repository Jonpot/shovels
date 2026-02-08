"""
SB3 MaskablePPO training script for Shovels.

Usage:
    python -m shovels_gym.train --timesteps 500000
"""

import argparse
import os

from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from shovels_gym.envs.shovels_env import ShovelsEnv
from shovels_gym.callbacks import WinRateCallback


def mask_fn(env):
    return env.action_masks()


def make_env():
    env = ShovelsEnv()
    env = ActionMasker(env, mask_fn)
    return env


def main():
    parser = argparse.ArgumentParser(description="Train Shovels RL agent")
    parser.add_argument("--timesteps", type=int, default=500_000, help="Total training timesteps")
    parser.add_argument("--eval-freq", type=int, default=10_000, help="Evaluate every N steps")
    parser.add_argument("--eval-games", type=int, default=100, help="Games per evaluation")
    parser.add_argument("--model-dir", type=str, default="models", help="Model save directory")
    parser.add_argument("--log-dir", type=str, default="logs/shovels_ppo", help="TensorBoard log directory")
    args = parser.parse_args()

    os.makedirs(args.model_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)

    env = make_env()

    model = MaskablePPO(
        "MlpPolicy",
        env,
        policy_kwargs=dict(net_arch=dict(pi=[256, 256], vf=[256, 256])),
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.01,
        verbose=1,
        tensorboard_log=args.log_dir,
    )

    callback = WinRateCallback(
        eval_freq=args.eval_freq,
        n_eval_games=args.eval_games,
        log_dir="logs/training_plots",
    )

    print(f"Training for {args.timesteps} timesteps...")
    model.learn(total_timesteps=args.timesteps, callback=callback, progress_bar=True)

    model_path = os.path.join(args.model_dir, "shovels_ppo")
    model.save(model_path)
    print(f"Model saved to {model_path}.zip")


if __name__ == "__main__":
    main()
