"""
End-to-end training pipeline for Shovels RL agent.

Phase 1: Train 500k steps vs RandomAgent → base model
Phase 2: Train 5M steps self-play from base → milestone checkpoints every 500k
Phase 3: Run interpretability analysis on final model

Usage:
    python -m shovels_gym.train_pipeline
    python -m shovels_gym.train_pipeline --phase1-steps 500000 --phase2-steps 5000000
    python -m shovels_gym.train_pipeline --skip-phase1 --base-model models/shovels_ppo_500k.zip
"""

import argparse
import os
import time

from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from shovels_gym.envs.shovels_env import ShovelsEnv
from shovels_gym.self_play import OpponentPool, SelfPlayCallback


def mask_fn(env):
    return env.action_masks()


def phase1_random_training(
    timesteps: int,
    model_dir: str,
    log_dir: str,
    lr: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
) -> str:
    """Phase 1: Train against RandomAgent."""
    print("=" * 60)
    print(f"PHASE 1: Training {timesteps:,} steps vs RandomAgent")
    print("=" * 60)

    env = ShovelsEnv()
    env = ActionMasker(env, mask_fn)

    model = MaskablePPO(
        "MlpPolicy",
        env,
        policy_kwargs=dict(net_arch=dict(pi=[256, 256], vf=[256, 256])),
        learning_rate=lr,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.01,
        verbose=1,
        tensorboard_log=os.path.join(log_dir, "phase1"),
    )

    start = time.time()
    model.learn(total_timesteps=timesteps, progress_bar=True)
    elapsed = time.time() - start
    print(f"Phase 1 complete in {elapsed/60:.1f} minutes")

    base_path = os.path.join(model_dir, "shovels_ppo_base")
    model.save(base_path)
    print(f"Base model saved to {base_path}.zip")

    return base_path


def phase2_selfplay_training(
    base_model_path: str,
    timesteps: int,
    model_dir: str,
    log_dir: str,
    milestone_freq: int = 500_000,
    checkpoint_freq: int = 50_000,
    eval_freq: int = 50_000,
    eval_games: int = 100,
    pool_size: int = 20,
    random_prob: float = 0.2,
    lr: float = 1e-4,
    n_steps: int = 4096,
    batch_size: int = 128,
) -> str:
    """Phase 2: Self-play training from base model."""
    print("=" * 60)
    print(f"PHASE 2: Self-play training {timesteps:,} steps")
    print(f"  Base model: {base_model_path}")
    print(f"  Milestones every {milestone_freq:,} steps")
    print("=" * 60)

    pool = OpponentPool(max_size=pool_size, random_prob=random_prob)

    env = ShovelsEnv(opponent_agent=pool.sample())
    env = ActionMasker(env, mask_fn)

    model_kwargs = dict(
        policy_kwargs=dict(net_arch=dict(pi=[256, 256], vf=[256, 256])),
        learning_rate=lr,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.01,
        verbose=1,
        tensorboard_log=os.path.join(log_dir, "phase2"),
    )

    # Load base model weights into fresh model (to get correct buffer sizes)
    old_model = MaskablePPO.load(base_model_path)
    model = MaskablePPO("MlpPolicy", env, **model_kwargs)
    model.policy.load_state_dict(old_model.policy.state_dict())
    del old_model

    # Seed pool with base model
    checkpoint_dir = os.path.join(model_dir, "checkpoints")
    pool.add_checkpoint(model, checkpoint_dir)

    callback = SelfPlayCallback(
        opponent_pool=pool,
        checkpoint_freq=checkpoint_freq,
        eval_freq=eval_freq,
        n_eval_games=eval_games,
        milestone_freq=milestone_freq,
        save_dir=checkpoint_dir,
        log_dir=os.path.join(log_dir, "selfplay"),
    )

    # Register base model as the 0M milestone
    callback.register_base_model(base_model_path, label="0M")

    start = time.time()
    print(f"  LR: {lr}, n_steps: {n_steps}, batch: {batch_size}")
    print(f"  Pool size: {pool_size}, Random prob: {random_prob}")
    model.learn(total_timesteps=timesteps, callback=callback, progress_bar=True)
    elapsed = time.time() - start
    print(f"Phase 2 complete in {elapsed/3600:.1f} hours")

    final_path = os.path.join(model_dir, "shovels_selfplay_final")
    model.save(final_path)
    print(f"Final model saved to {final_path}.zip")

    return final_path


def phase3_interpretability(model_path: str, log_dir: str):
    """Phase 3: Run interpretability analysis."""
    print("=" * 60)
    print("PHASE 3: Interpretability analysis")
    print("=" * 60)

    import subprocess
    import sys

    interpret_dir = os.path.join(log_dir, "interpret")
    os.makedirs(interpret_dir, exist_ok=True)

    commands = ["weights", "saliency", "probe", "rollout"]
    for cmd in commands:
        print(f"\nRunning: {cmd}")
        try:
            subprocess.run(
                [
                    sys.executable, "-m", "shovels_gym.interpret",
                    "--model", f"{model_path}.zip",
                    "--output-dir", interpret_dir,
                    cmd,
                ],
                check=True,
                timeout=1800,  # 30 min timeout per command
            )
        except subprocess.TimeoutExpired:
            print(f"  {cmd} timed out after 30 minutes, skipping")
        except subprocess.CalledProcessError as e:
            print(f"  {cmd} failed: {e}")

    print(f"\nInterpretability results saved to {interpret_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Full Shovels RL training pipeline")
    parser.add_argument("--phase1-steps", type=int, default=500_000)
    parser.add_argument("--phase2-steps", type=int, default=5_000_000)
    parser.add_argument("--milestone-freq", type=int, default=500_000)
    parser.add_argument("--skip-phase1", action="store_true",
                        help="Skip phase 1 and use existing base model")
    parser.add_argument("--base-model", type=str, default=None,
                        help="Path to base model (without .zip) for --skip-phase1")
    parser.add_argument("--skip-interpret", action="store_true",
                        help="Skip interpretability analysis")
    parser.add_argument("--model-dir", type=str, default="models")
    parser.add_argument("--log-dir", type=str, default="logs")
    args = parser.parse_args()

    os.makedirs(args.model_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)

    pipeline_start = time.time()

    # Phase 1
    if args.skip_phase1:
        if not args.base_model:
            base_path = os.path.join(args.model_dir, "shovels_ppo_base")
        else:
            base_path = args.base_model
        print(f"Skipping Phase 1, using base model: {base_path}")
    else:
        base_path = phase1_random_training(
            timesteps=args.phase1_steps,
            model_dir=args.model_dir,
            log_dir=args.log_dir,
        )

    # Phase 2
    final_path = phase2_selfplay_training(
        base_model_path=base_path,
        timesteps=args.phase2_steps,
        model_dir=args.model_dir,
        log_dir=args.log_dir,
        milestone_freq=args.milestone_freq,
    )

    # Phase 3
    if not args.skip_interpret:
        phase3_interpretability(final_path, args.log_dir)

    total = time.time() - pipeline_start
    print("=" * 60)
    print(f"PIPELINE COMPLETE in {total/3600:.1f} hours")
    print(f"  Base model: {base_path}.zip")
    print(f"  Final model: {final_path}.zip")
    print("=" * 60)


if __name__ == "__main__":
    main()
