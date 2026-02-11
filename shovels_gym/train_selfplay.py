"""
Self-play training script for Shovels RL agent.

Trains via MaskablePPO against a pool of historical checkpoints + RandomAgent.

Usage:
    python -m shovels_gym.train_selfplay --timesteps 2000000
    python -m shovels_gym.train_selfplay --resume models/shovels_selfplay.zip --timesteps 1000000
"""

import argparse
import os

from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from shovels_gym.envs.shovels_env import ShovelsEnv
from shovels_gym.self_play import OpponentPool, SelfPlayCallback


def mask_fn(env):
    return env.action_masks()


def main():
    parser = argparse.ArgumentParser(description="Self-play training for Shovels RL agent")
    parser.add_argument("--timesteps", type=int, default=2_000_000, help="Total training timesteps")
    parser.add_argument("--checkpoint-freq", type=int, default=50_000, help="Save checkpoint every N steps")
    parser.add_argument("--eval-freq", type=int, default=25_000, help="Evaluate every N steps")
    parser.add_argument("--eval-games", type=int, default=100, help="Games per evaluation")
    parser.add_argument("--pool-size", type=int, default=20, help="Max opponent pool size")
    parser.add_argument("--random-prob", type=float, default=0.2, help="Probability of playing vs RandomAgent")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate (default 1e-4, lower than standard for self-play stability)")
    parser.add_argument("--n-steps", type=int, default=4096, help="Steps per rollout (larger = more stable)")
    parser.add_argument("--batch-size", type=int, default=128, help="Minibatch size")
    parser.add_argument("--ent-coef", type=float, default=0.01, help="Entropy coefficient")
    parser.add_argument("--resume", type=str, default=None, help="Resume from model .zip file")
    parser.add_argument("--model-dir", type=str, default="models", help="Model save directory")
    parser.add_argument("--log-dir", type=str, default="logs/shovels_selfplay", help="TensorBoard log directory")
    args = parser.parse_args()

    os.makedirs(args.model_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)

    pool = OpponentPool(max_size=args.pool_size, random_prob=args.random_prob)

    env = ShovelsEnv(opponent_agent=pool.sample())
    env = ActionMasker(env, mask_fn)

    model_kwargs = dict(
        policy_kwargs=dict(net_arch=dict(pi=[256, 256], vf=[256, 256])),
        learning_rate=args.lr,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=10,
        gamma=0.99,
        ent_coef=args.ent_coef,
        verbose=1,
        tensorboard_log=args.log_dir,
    )

    if args.resume:
        print(f"Resuming from {args.resume}")
        # Create fresh model with desired hyperparams, then copy trained weights.
        # (Loading directly and changing n_steps/batch_size doesn't resize the
        # internal rollout buffer, causing overflow errors.)
        old_model = MaskablePPO.load(args.resume)
        model = MaskablePPO("MlpPolicy", env, **model_kwargs)
        model.policy.load_state_dict(old_model.policy.state_dict())
        del old_model
        # Seed the pool with the resumed model as first checkpoint
        pool.add_checkpoint(model, os.path.join(args.model_dir, "checkpoints"))
    else:
        model = MaskablePPO("MlpPolicy", env, **model_kwargs)

    callback = SelfPlayCallback(
        opponent_pool=pool,
        checkpoint_freq=args.checkpoint_freq,
        eval_freq=args.eval_freq,
        n_eval_games=args.eval_games,
        save_dir=os.path.join(args.model_dir, "checkpoints"),
        log_dir="logs/selfplay",
    )

    print(f"Self-play training for {args.timesteps} timesteps...")
    print(f"  LR: {args.lr}, n_steps: {args.n_steps}, batch: {args.batch_size}, ent: {args.ent_coef}")
    print(f"  Pool size: {args.pool_size}, Random prob: {args.random_prob}")
    print(f"  Checkpoint every {args.checkpoint_freq} steps, Eval every {args.eval_freq} steps")
    model.learn(total_timesteps=args.timesteps, callback=callback, progress_bar=True)

    model_path = os.path.join(args.model_dir, "shovels_selfplay")
    model.save(model_path)
    print(f"Model saved to {model_path}.zip")


if __name__ == "__main__":
    main()
