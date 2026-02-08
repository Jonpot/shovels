"""
Evaluate a trained Shovels model against RandomAgent.

Usage:
    python -m shovels_gym.evaluate --model models/shovels_ppo.zip --games 1000
"""

import argparse
import os
from tqdm import tqdm

import time
import numpy as np
from sb3_contrib import MaskablePPO

from shovels_gym.envs.shovels_env import ShovelsEnv
from shovels_gym.playback import save_game_log


def evaluate(model_path: str, n_games: int = 1000, verbose: bool = True,
             log_dir: str = "logs/game_replays"):
    """Evaluate model vs RandomAgent. Returns (win_rate, stats_dict)."""
    model = MaskablePPO.load(model_path)
    env = ShovelsEnv()

    wins = 0
    losses = 0
    draws = 0
    total_reward = 0.0
    total_length = 0
    rewards_list = []
    saved_win = False
    saved_loss = False

    for game_idx in tqdm(range(n_games)):
        obs, info = env.reset()
        done = False
        ep_reward = 0.0
        ep_length = 0
        start_time = time.time()

        while not done:
            mask = env.action_masks()
            action, _ = model.predict(obs, deterministic=True, action_masks=mask)
            obs, reward, terminated, truncated, info = env.step(int(action))
            ep_reward += reward
            ep_length += 1
            done = terminated or truncated

            if time.time() - start_time > 1.0:
                print(f"Warning: Game {game_idx + 1} taking too long ({ep_length} steps, {ep_reward:.2f} reward)")

                print("Reward:", reward
                      , "Terminated:", terminated
                      , "Truncated:", truncated
                      , "Info:", info)

                break

        winner = info.get("winner_id")
        if winner == "agent":
            wins += 1
            if not saved_win:
                save_game_log(env.state, os.path.join(log_dir, "replay_win.txt"))
                saved_win = True
                if verbose:
                    print(f"  Saved win replay (game {game_idx + 1})")
        elif winner == "opponent":
            losses += 1
            if not saved_loss:
                save_game_log(env.state, os.path.join(log_dir, "replay_loss.txt"))
                saved_loss = True
                if verbose:
                    print(f"  Saved loss replay (game {game_idx + 1})")
        else:
            draws += 1

        total_reward += ep_reward
        total_length += ep_length
        rewards_list.append(ep_reward)

        if verbose and (game_idx + 1) % 100 == 0:
            print(f"  Game {game_idx + 1}/{n_games}: "
                  f"W={wins} L={losses} D={draws} "
                  f"WR={wins / (game_idx + 1):.2%}")

    win_rate = wins / n_games
    stats = {
        "n_games": n_games,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate,
        "avg_reward": total_reward / n_games,
        "avg_length": total_length / n_games,
        "reward_std": float(np.std(rewards_list)),
    }

    if verbose:
        print(f"\n{'=' * 50}")
        print(f"Evaluation Results ({n_games} games)")
        print(f"{'=' * 50}")
        print(f"Win rate:     {win_rate:.2%}")
        print(f"Wins:         {wins}")
        print(f"Losses:       {losses}")
        print(f"Draws:        {draws}")
        print(f"Avg reward:   {stats['avg_reward']:.3f} +/- {stats['reward_std']:.3f}")
        print(f"Avg length:   {stats['avg_length']:.1f} steps")
        if saved_win or saved_loss:
            print(f"\nGame replays saved to {log_dir}/")
            if saved_win:
                print(f"  Win:  {os.path.join(log_dir, 'replay_win.txt')}")
            if saved_loss:
                print(f"  Loss: {os.path.join(log_dir, 'replay_loss.txt')}")

    return win_rate, stats


def save_eval_plot(stats: dict, output_dir: str = "logs/training_plots"):
    """Save a summary bar chart of evaluation results."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping plot")
        return

    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5))
    categories = ["Wins", "Losses", "Draws"]
    values = [stats["wins"], stats["losses"], stats["draws"]]
    colors = ["#2ecc71", "#e74c3c", "#95a5a6"]
    ax.bar(categories, values, color=colors)
    ax.set_ylabel("Count")
    ax.set_title(f"Evaluation: {stats['n_games']} games (WR: {stats['win_rate']:.1%})")
    for i, v in enumerate(values):
        ax.text(i, v + max(values) * 0.02, str(v), ha="center", fontweight="bold")
    fig.savefig(os.path.join(output_dir, "eval_results.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to {output_dir}/eval_results.png")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Shovels RL agent")
    parser.add_argument("--model", type=str, required=True, help="Path to model .zip file")
    parser.add_argument("--games", type=int, default=1000, help="Number of evaluation games")
    args = parser.parse_args()

    win_rate, stats = evaluate(args.model, args.games)
    save_eval_plot(stats)


if __name__ == "__main__":
    main()
