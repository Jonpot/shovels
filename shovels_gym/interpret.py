"""
Interpretability toolkit for Shovels MaskablePPO models.

Provides weight analysis, gradient saliency, scenario probing,
rollout statistics, and single-decision explanations.

Usage:
    python -m shovels_gym.interpret --model models/shovels_selfplay_2M.zip weights
    python -m shovels_gym.interpret --model models/shovels_selfplay_2M.zip saliency --n-games 100
    python -m shovels_gym.interpret --model models/shovels_selfplay_2M.zip probe
    python -m shovels_gym.interpret --model models/shovels_selfplay_2M.zip rollout --n-games 200
    python -m shovels_gym.interpret --model models/shovels_selfplay_2M.zip explain --seed 42
    python -m shovels_gym.interpret --model models/shovels_selfplay_2M.zip dashboard
"""

import argparse
import os
import random as py_random

import numpy as np
import torch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sb3_contrib import MaskablePPO
from tqdm import tqdm

from shovels_engine.models import GameState, Card, Character, Player, Suit, setup_game
from shovels_engine.agents import RandomAgent
from shovels_gym.obs_space import (
    OBS_SIZE, FEATURE_NAMES, FEATURE_GROUPS, FEATURE_SUPERGROUPS,
    encode_observation,
)
from shovels_gym.action_space import (
    ACTION_SPACE_SIZE, ACTION_NAMES, ACTION_CATEGORIES,
    action_masks as compute_action_masks,
    decode_action, PERFORM_START, STRIKE_START,
)
from shovels_gym.action_utils import execute_action
from shovels_gym.envs.shovels_env import ShovelsEnv, AGENT_ID, OPPONENT_ID


# ---------------------------------------------------------------------------
# Plot style
# ---------------------------------------------------------------------------

def _setup_style():
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "#f8f8f8",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "font.size": 10,
    })


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def load_model(path: str) -> MaskablePPO:
    return MaskablePPO.load(path)


def get_policy_layers(model: MaskablePPO) -> dict:
    """Extract Linear layers from the policy."""
    policy = model.policy
    layers = {}
    linear_idx = 0
    for layer in policy.mlp_extractor.policy_net:
        if isinstance(layer, torch.nn.Linear):
            layers[f"policy_net_{linear_idx}"] = layer
            linear_idx += 1
    linear_idx = 0
    for layer in policy.mlp_extractor.value_net:
        if isinstance(layer, torch.nn.Linear):
            layers[f"value_net_{linear_idx}"] = layer
            linear_idx += 1
    layers["action_net"] = policy.action_net
    layers["value_head"] = policy.value_net
    return layers


def forward_with_grad(model: MaskablePPO, obs: np.ndarray, mask: np.ndarray) -> dict:
    """Forward pass returning logits, probs, value, keeping grad graph."""
    policy = model.policy
    obs_t = torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0)
    obs_t.requires_grad_(True)

    features = policy.extract_features(obs_t, policy.pi_features_extractor)
    pi_latent, _ = policy.mlp_extractor(features)
    logits = policy.action_net(pi_latent)

    vf_features = policy.extract_features(obs_t, policy.vf_features_extractor)
    _, vf_latent = policy.mlp_extractor(vf_features)
    value = policy.value_net(vf_latent)

    mask_t = torch.as_tensor(mask, dtype=torch.bool)
    masked_logits = logits.clone()
    masked_logits[0, ~mask_t] = float("-inf")
    probs = torch.softmax(masked_logits, dim=-1)

    return {
        "obs_tensor": obs_t,
        "logits": logits,
        "masked_probs": probs.detach().numpy().squeeze(),
        "value": value.item(),
        "action": int(probs.argmax(dim=-1).item()),
        "probs_tensor": probs,
    }


def compute_saliency(
    model: MaskablePPO, obs: np.ndarray, mask: np.ndarray, target_action: int = None,
) -> np.ndarray:
    """Gradient * Input saliency: |d(log_prob)/d(input) * input|.

    Uses GradInput rather than raw gradient so features that are zero in the
    current observation (e.g. empty hand slots during Phase 2 combat) correctly
    produce zero saliency instead of reflecting static weight magnitudes.
    """
    result = forward_with_grad(model, obs, mask)
    action = target_action if target_action is not None else result["action"]
    log_prob = torch.log(result["probs_tensor"][0, action] + 1e-10)
    log_prob.backward()
    grad = result["obs_tensor"].grad.detach().numpy().squeeze()
    return np.abs(grad * obs)


def _group_importance(values: np.ndarray, groups: dict, mode: str = "mean") -> dict:
    """Aggregate values by feature group. mode='mean' or 'sum'."""
    result = {}
    for name, (start, end) in groups.items():
        segment = values[start:end]
        result[name] = float(segment.mean() if mode == "mean" else segment.sum())
    return result


def _supergroup_importance(group_imp: dict, supergroups: dict) -> dict:
    result = {}
    for sg_name, group_names in supergroups.items():
        vals = [group_imp[g] for g in group_names if g in group_imp]
        result[sg_name] = float(np.mean(vals)) if vals else 0.0
    return result


def _action_category(action_idx: int) -> str:
    for cat, (start, end) in ACTION_CATEGORIES.items():
        if start <= action_idx < end:
            return cat
    return "unknown"


def _perform_suit(action_idx: int) -> str:
    """For perform actions, return which suit."""
    if action_idx < PERFORM_START or action_idx >= STRIKE_START:
        return "N/A"
    idx = action_idx - PERFORM_START
    suit_target = idx % 6
    suits = ["diamonds", "hearts", "spades", "clubs", "clubs", "clubs"]
    return suits[suit_target]


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _collect_game_data(
    model: MaskablePPO,
    n_games: int,
    collect_saliency: bool = False,
    seed: int = None,
) -> list[dict]:
    """Play games and collect per-step data."""
    if seed is not None:
        py_random.seed(seed)
        np.random.seed(seed)

    env = ShovelsEnv()
    records = []

    for game_idx in tqdm(range(n_games), desc="Collecting games"):
        obs, info = env.reset()
        done = False
        step_in_game = 0
        while not done:
            mask = env.action_masks()
            result = forward_with_grad(model, obs, mask)
            action = result["action"]

            record = {
                "obs": obs.copy(),
                "mask": mask.copy(),
                "action": action,
                "action_probs": result["masked_probs"].copy(),
                "value": result["value"],
                "phase": info.get("phase", 1),
                "subphase": info.get("subphase", ""),
                "turn": info.get("turn_count", 0),
                "game_idx": game_idx,
                "step_in_game": step_in_game,
            }

            if collect_saliency:
                record["saliency"] = compute_saliency(model, obs, mask, action)

            records.append(record)

            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            step_in_game += 1

            record["reward"] = reward
            record["game_over"] = done
            record["won"] = info.get("winner_id") == AGENT_ID if done else None

    return records


# ---------------------------------------------------------------------------
# Analysis A: Weight importance
# ---------------------------------------------------------------------------

def analyze_weights(model: MaskablePPO, output_dir: str):
    """First-layer weight magnitude analysis."""
    _setup_style()
    out = os.path.join(output_dir, "weights")
    os.makedirs(out, exist_ok=True)

    layers = get_policy_layers(model)
    pi_w = layers["policy_net_0"].weight.detach().numpy()  # (256, 798)
    vf_w = layers["value_net_0"].weight.detach().numpy()

    pi_imp = np.abs(pi_w).mean(axis=0)  # (798,)
    vf_imp = np.abs(vf_w).mean(axis=0)

    # -- Top 30 features --
    top_idx = np.argsort(pi_imp)[-30:][::-1]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(range(30), pi_imp[top_idx][::-1], color="#4477AA")
    ax.set_yticks(range(30))
    ax.set_yticklabels([FEATURE_NAMES[i] for i in top_idx][::-1], fontsize=8)
    ax.set_xlabel("Mean |weight| in policy first layer")
    ax.set_title("Top 30 Features by Policy Network Weight Magnitude")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "weights_top30_features.png"), dpi=150)
    plt.close(fig)

    # -- Feature groups (policy vs value) --
    pi_groups = _group_importance(pi_imp, FEATURE_GROUPS)
    vf_groups = _group_importance(vf_imp, FEATURE_GROUPS)
    group_names = list(FEATURE_GROUPS.keys())
    x = np.arange(len(group_names))

    fig, ax = plt.subplots(figsize=(12, 6))
    w = 0.35
    ax.bar(x - w/2, [pi_groups[g] for g in group_names], w, label="Policy net", color="#4477AA")
    ax.bar(x + w/2, [vf_groups[g] for g in group_names], w, label="Value net", color="#CC6677")
    ax.set_xticks(x)
    ax.set_xticklabels(group_names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Mean |weight|")
    ax.set_title("Feature Group Importance: Policy vs Value Network")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "weights_feature_groups.png"), dpi=150)
    plt.close(fig)

    # -- Supergroups --
    pi_sg = _supergroup_importance(pi_groups, FEATURE_SUPERGROUPS)
    vf_sg = _supergroup_importance(vf_groups, FEATURE_SUPERGROUPS)
    sg_names = list(FEATURE_SUPERGROUPS.keys())
    x = np.arange(len(sg_names))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - w/2, [pi_sg[g] for g in sg_names], w, label="Policy net", color="#4477AA")
    ax.bar(x + w/2, [vf_sg[g] for g in sg_names], w, label="Value net", color="#CC6677")
    ax.set_xticks(x)
    ax.set_xticklabels(sg_names, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Mean |weight|")
    ax.set_title("Supergroup Importance: Policy vs Value Network")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "weights_supergroups.png"), dpi=150)
    plt.close(fig)

    # -- Policy vs Value scatter --
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(pi_imp, vf_imp, alpha=0.3, s=8, color="#228833")
    mx = max(pi_imp.max(), vf_imp.max()) * 1.1
    ax.plot([0, mx], [0, mx], "k--", alpha=0.3, linewidth=1)
    ax.set_xlabel("Policy net |weight|")
    ax.set_ylabel("Value net |weight|")
    ax.set_title("Feature Importance: Policy vs Value")
    # Annotate top outliers
    ratio = pi_imp / (vf_imp + 1e-8)
    for label, indices in [("Policy-heavy", np.argsort(ratio)[-5:]),
                           ("Value-heavy", np.argsort(ratio)[:5])]:
        for i in indices:
            ax.annotate(FEATURE_NAMES[i], (pi_imp[i], vf_imp[i]),
                        fontsize=6, alpha=0.8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "weights_policy_vs_value.png"), dpi=150)
    plt.close(fig)

    # -- Text report --
    with open(os.path.join(out, "weights_report.txt"), "w") as f:
        f.write("=== Weight Analysis Report ===\n\n")
        f.write("Top 30 features by policy net first-layer |weight|:\n")
        for rank, i in enumerate(top_idx, 1):
            f.write(f"  {rank:2d}. {FEATURE_NAMES[i]:40s}  pi={pi_imp[i]:.4f}  vf={vf_imp[i]:.4f}\n")
        f.write("\nFeature group importance (policy net):\n")
        for g in sorted(pi_groups.keys(), key=lambda k: pi_groups[k], reverse=True):
            f.write(f"  {g:25s}  {pi_groups[g]:.4f}\n")
        f.write("\nSupergroup importance (policy net):\n")
        for g in sorted(pi_sg.keys(), key=lambda k: pi_sg[k], reverse=True):
            f.write(f"  {g:20s}  {pi_sg[g]:.4f}\n")

    print(f"Weight analysis saved to {out}/")


# ---------------------------------------------------------------------------
# Analysis B: Gradient saliency
# ---------------------------------------------------------------------------

def analyze_saliency(model: MaskablePPO, n_games: int, output_dir: str):
    """Gradient-based saliency aggregated over many games."""
    _setup_style()
    out = os.path.join(output_dir, "saliency")
    os.makedirs(out, exist_ok=True)

    records = _collect_game_data(model, n_games, collect_saliency=True)
    print(f"Collected {len(records)} decision points from {n_games} games")

    all_sal = np.array([r["saliency"] for r in records])  # (N, 798)
    avg_sal = all_sal.mean(axis=0)

    # -- Average saliency by group --
    group_sal = _group_importance(avg_sal, FEATURE_GROUPS)
    group_names = sorted(group_sal.keys(), key=lambda k: group_sal[k], reverse=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(range(len(group_names)), [group_sal[g] for g in group_names][::-1], color="#4477AA")
    ax.set_yticks(range(len(group_names)))
    ax.set_yticklabels(group_names[::-1], fontsize=8)
    ax.set_xlabel("Mean |gradient * input|")
    ax.set_title(f"Average Saliency by Feature Group ({n_games} games)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "saliency_avg_by_group.png"), dpi=150)
    plt.close(fig)

    # -- Saliency by action type (heatmap) --
    cat_names = list(ACTION_CATEGORIES.keys())
    sg_names = list(FEATURE_SUPERGROUPS.keys())
    heatmap = np.zeros((len(cat_names), len(sg_names)))

    for ci, cat in enumerate(cat_names):
        cat_mask = np.array([_action_category(r["action"]) == cat for r in records])
        if cat_mask.sum() == 0:
            continue
        cat_sal = all_sal[cat_mask].mean(axis=0)
        sg_imp = _supergroup_importance(
            _group_importance(cat_sal, FEATURE_GROUPS), FEATURE_SUPERGROUPS
        )
        for si, sg in enumerate(sg_names):
            heatmap[ci, si] = sg_imp.get(sg, 0)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(heatmap, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(sg_names)))
    ax.set_xticklabels(sg_names, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(cat_names)))
    ax.set_yticklabels(cat_names, fontsize=9)
    ax.set_title("Saliency: Action Type vs Feature Supergroup")
    fig.colorbar(im, ax=ax, label="Mean |gradient * input|")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "saliency_by_action_type.png"), dpi=150)
    plt.close(fig)

    # -- Phase 1 vs Phase 2 --
    p1_mask = np.array([r["phase"] == 1 for r in records])
    p2_mask = np.array([r["phase"] == 2 for r in records])

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    for ax, phase_mask, title in [(axes[0], p1_mask, "Phase 1"),
                                   (axes[1], p2_mask, "Phase 2")]:
        if phase_mask.sum() == 0:
            ax.set_title(f"{title} (no data)")
            continue
        phase_sal = all_sal[phase_mask].mean(axis=0)
        sg_imp = _supergroup_importance(
            _group_importance(phase_sal, FEATURE_GROUPS), FEATURE_SUPERGROUPS
        )
        vals = [sg_imp[sg] for sg in sg_names]
        ax.barh(range(len(sg_names)), vals, color="#4477AA")
        ax.set_yticks(range(len(sg_names)))
        ax.set_yticklabels(sg_names, fontsize=8)
        ax.set_xlabel("Mean |gradient * input|")
        ax.set_title(title)
    fig.suptitle("Saliency by Phase", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "saliency_by_phase.png"), dpi=150)
    plt.close(fig)

    # -- Top 30 features in Phase 2 --
    if p2_mask.sum() > 0:
        p2_sal = all_sal[p2_mask].mean(axis=0)
        top_idx = np.argsort(p2_sal)[-30:][::-1]
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(range(30), p2_sal[top_idx][::-1], color="#EE6677")
        ax.set_yticks(range(30))
        ax.set_yticklabels([FEATURE_NAMES[i] for i in top_idx][::-1], fontsize=8)
        ax.set_xlabel("Mean |gradient * input| (Phase 2)")
        ax.set_title("Top 30 Features by Saliency in Phase 2")
        fig.tight_layout()
        fig.savefig(os.path.join(out, "saliency_top30_phase2.png"), dpi=150)
        plt.close(fig)

    print(f"Saliency analysis saved to {out}/")


# ---------------------------------------------------------------------------
# Analysis C: Scenario probing
# ---------------------------------------------------------------------------

def _make_card(rank: int, suit: Suit, is_ace: bool = False) -> Card:
    return Card(rank=rank, suit=suit, is_ace=is_ace)


def _make_char(face_rank: str, suit: Suit, stack_cards: list[Card]) -> Character:
    return Character(rank=face_rank, suit=suit, stack=stack_cards)


def _base_phase2_state() -> GameState:
    """Create a minimal valid Phase 2 state."""
    state = setup_game([AGENT_ID, OPPONENT_ID])
    state.phase = 2
    state.turn_subphase = "BATTLE_ACTION"
    state.current_turn_index = 0  # agent's turn
    state.action_taken_this_turn = False
    state.cards_removed_this_turn = False
    state.character_tapped_this_turn = False
    state.active_character_index = None
    return state


def _set_characters(state: GameState, player_id: str, chars: list[Character]):
    player = next(p for p in state.players if p.id == player_id)
    player.characters = chars


SCENARIOS = {}


def _register(name):
    def decorator(fn):
        SCENARIOS[name] = fn
        return fn
    return decorator


@_register("opponent_undefended")
def _scenario_opponent_undefended() -> tuple[GameState, str]:
    """Opponent has no hearts - maximally vulnerable."""
    state = _base_phase2_state()
    _set_characters(state, AGENT_ID, [
        _make_char("J", Suit.CLUBS, [
            _make_card(5, Suit.HEARTS), _make_card(7, Suit.CLUBS), _make_card(8, Suit.CLUBS),
        ]),
        _make_char("Q", Suit.DIAMONDS, [
            _make_card(3, Suit.HEARTS), _make_card(6, Suit.DIAMONDS), _make_card(9, Suit.DIAMONDS),
        ]),
        _make_char("K", Suit.SPADES, [
            _make_card(4, Suit.HEARTS), _make_card(5, Suit.SPADES), _make_card(7, Suit.CLUBS),
        ]),
    ])
    _set_characters(state, OPPONENT_ID, [
        _make_char("J", Suit.HEARTS, [
            _make_card(3, Suit.CLUBS), _make_card(6, Suit.CLUBS), _make_card(8, Suit.SPADES),
        ]),
        _make_char("Q", Suit.CLUBS, [
            _make_card(4, Suit.DIAMONDS), _make_card(7, Suit.SPADES), _make_card(9, Suit.CLUBS),
        ]),
        _make_char("K", Suit.DIAMONDS, [
            _make_card(5, Suit.CLUBS), _make_card(6, Suit.SPADES), _make_card(10, Suit.DIAMONDS),
        ]),
    ])
    return state, "Opponent has zero hearts on any character"


@_register("high_diamonds_shop")
def _scenario_high_diamonds_shop() -> tuple[GameState, str]:
    """Shop full of diamonds, player has coins, SHOPPING subphase."""
    state = _base_phase2_state()
    state.turn_subphase = "SHOPPING"
    player = next(p for p in state.players if p.id == AGENT_ID)
    player.coins = 12
    state.shop_row = [
        _make_card(9, Suit.DIAMONDS), _make_card(10, Suit.DIAMONDS), _make_card(8, Suit.DIAMONDS),
    ]
    _set_characters(state, AGENT_ID, [
        _make_char("J", Suit.CLUBS, [_make_card(5, Suit.HEARTS), _make_card(7, Suit.CLUBS)]),
        _make_char("Q", Suit.DIAMONDS, [_make_card(4, Suit.HEARTS), _make_card(6, Suit.DIAMONDS)]),
        _make_char("K", Suit.SPADES, [_make_card(3, Suit.HEARTS), _make_card(8, Suit.SPADES)]),
    ])
    _set_characters(state, OPPONENT_ID, [
        _make_char("J", Suit.HEARTS, [_make_card(5, Suit.CLUBS), _make_card(6, Suit.HEARTS)]),
        _make_char("Q", Suit.CLUBS, [_make_card(4, Suit.DIAMONDS), _make_card(7, Suit.HEARTS)]),
        _make_char("K", Suit.DIAMONDS, [_make_card(3, Suit.CLUBS), _make_card(8, Suit.HEARTS)]),
    ])
    return state, "Shop has high diamonds, player has 12 coins"


@_register("early_phase2")
def _scenario_early_phase2() -> tuple[GameState, str]:
    """Phase 2 just started, full stacks on both sides."""
    state = _base_phase2_state()
    _set_characters(state, AGENT_ID, [
        _make_char("J", Suit.CLUBS, [
            _make_card(3, Suit.DIAMONDS), _make_card(5, Suit.HEARTS), _make_card(7, Suit.CLUBS),
            _make_card(8, Suit.CLUBS), _make_card(9, Suit.HEARTS), _make_card(10, Suit.CLUBS),
        ]),
        _make_char("Q", Suit.DIAMONDS, [
            _make_card(4, Suit.HEARTS), _make_card(6, Suit.DIAMONDS), _make_card(8, Suit.DIAMONDS),
            _make_card(9, Suit.CLUBS), _make_card(10, Suit.HEARTS),
        ]),
        _make_char("K", Suit.SPADES, [
            _make_card(2, Suit.HEARTS), _make_card(4, Suit.SPADES), _make_card(6, Suit.SPADES),
            _make_card(7, Suit.HEARTS), _make_card(8, Suit.SPADES),
        ]),
    ])
    _set_characters(state, OPPONENT_ID, [
        _make_char("K", Suit.CLUBS, [
            _make_card(3, Suit.HEARTS), _make_card(5, Suit.CLUBS), _make_card(7, Suit.CLUBS),
            _make_card(8, Suit.HEARTS), _make_card(9, Suit.CLUBS), _make_card(10, Suit.SPADES),
        ]),
        _make_char("Q", Suit.HEARTS, [
            _make_card(4, Suit.HEARTS), _make_card(6, Suit.HEARTS), _make_card(8, Suit.CLUBS),
            _make_card(9, Suit.DIAMONDS), _make_card(10, Suit.HEARTS),
        ]),
        _make_char("J", Suit.DIAMONDS, [
            _make_card(2, Suit.DIAMONDS), _make_card(4, Suit.CLUBS), _make_card(6, Suit.DIAMONDS),
            _make_card(7, Suit.SPADES), _make_card(8, Suit.DIAMONDS),
        ]),
    ])
    return state, "Early Phase 2: full stacks, all characters alive"


@_register("late_losing")
def _scenario_late_losing() -> tuple[GameState, str]:
    """Player down to 1 character, opponent has 3."""
    state = _base_phase2_state()
    _set_characters(state, AGENT_ID, [
        _make_char("K", Suit.CLUBS, [
            _make_card(5, Suit.HEARTS), _make_card(7, Suit.CLUBS), _make_card(9, Suit.CLUBS),
        ]),
        _make_char("Q", Suit.DIAMONDS, []),  # dead
        _make_char("J", Suit.SPADES, []),    # dead
    ])
    state.players[0].characters[1].is_dead = True
    state.players[0].characters[2].is_dead = True
    _set_characters(state, OPPONENT_ID, [
        _make_char("J", Suit.HEARTS, [
            _make_card(3, Suit.CLUBS), _make_card(6, Suit.HEARTS), _make_card(8, Suit.CLUBS),
        ]),
        _make_char("Q", Suit.CLUBS, [
            _make_card(4, Suit.HEARTS), _make_card(7, Suit.CLUBS), _make_card(9, Suit.SPADES),
        ]),
        _make_char("K", Suit.DIAMONDS, [
            _make_card(5, Suit.HEARTS), _make_card(6, Suit.DIAMONDS), _make_card(10, Suit.CLUBS),
        ]),
    ])
    return state, "Losing: 1 alive vs 3"


@_register("late_winning")
def _scenario_late_winning() -> tuple[GameState, str]:
    """Player has 3 characters, opponent down to 1."""
    state = _base_phase2_state()
    _set_characters(state, AGENT_ID, [
        _make_char("J", Suit.CLUBS, [
            _make_card(5, Suit.HEARTS), _make_card(7, Suit.CLUBS), _make_card(8, Suit.CLUBS),
        ]),
        _make_char("Q", Suit.DIAMONDS, [
            _make_card(3, Suit.HEARTS), _make_card(6, Suit.DIAMONDS),
        ]),
        _make_char("K", Suit.SPADES, [
            _make_card(4, Suit.HEARTS), _make_card(5, Suit.SPADES),
        ]),
    ])
    opp_chars = [
        _make_char("K", Suit.CLUBS, [
            _make_card(6, Suit.HEARTS), _make_card(8, Suit.CLUBS), _make_card(10, Suit.CLUBS),
        ]),
        _make_char("Q", Suit.HEARTS, []),
        _make_char("J", Suit.DIAMONDS, []),
    ]
    opp_chars[1].is_dead = True
    opp_chars[2].is_dead = True
    _set_characters(state, OPPONENT_ID, opp_chars)
    return state, "Winning: 3 alive vs 1"


@_register("clubs_on_top")
def _scenario_clubs_on_top() -> tuple[GameState, str]:
    """Player has clubs on top of all stacks - attack ready."""
    state = _base_phase2_state()
    _set_characters(state, AGENT_ID, [
        _make_char("J", Suit.CLUBS, [
            _make_card(3, Suit.DIAMONDS), _make_card(5, Suit.HEARTS), _make_card(9, Suit.CLUBS),
        ]),
        _make_char("Q", Suit.DIAMONDS, [
            _make_card(4, Suit.HEARTS), _make_card(6, Suit.DIAMONDS), _make_card(8, Suit.CLUBS),
        ]),
        _make_char("K", Suit.SPADES, [
            _make_card(2, Suit.HEARTS), _make_card(7, Suit.SPADES), _make_card(10, Suit.CLUBS),
        ]),
    ])
    _set_characters(state, OPPONENT_ID, [
        _make_char("J", Suit.HEARTS, [
            _make_card(3, Suit.CLUBS), _make_card(5, Suit.HEARTS), _make_card(7, Suit.HEARTS),
        ]),
        _make_char("Q", Suit.CLUBS, [
            _make_card(4, Suit.DIAMONDS), _make_card(6, Suit.HEARTS), _make_card(8, Suit.HEARTS),
        ]),
        _make_char("K", Suit.DIAMONDS, [
            _make_card(5, Suit.SPADES), _make_card(7, Suit.HEARTS), _make_card(9, Suit.HEARTS),
        ]),
    ])
    return state, "All player stacks have clubs on top (attack-ready)"


@_register("hearts_defense")
def _scenario_hearts_defense() -> tuple[GameState, str]:
    """Player has strong hearts protection everywhere."""
    state = _base_phase2_state()
    _set_characters(state, AGENT_ID, [
        _make_char("J", Suit.CLUBS, [
            _make_card(3, Suit.CLUBS), _make_card(5, Suit.CLUBS), _make_card(10, Suit.HEARTS),
        ]),
        _make_char("Q", Suit.DIAMONDS, [
            _make_card(4, Suit.DIAMONDS), _make_card(6, Suit.CLUBS), _make_card(9, Suit.HEARTS),
        ]),
        _make_char("K", Suit.SPADES, [
            _make_card(2, Suit.SPADES), _make_card(7, Suit.CLUBS), _make_card(8, Suit.HEARTS),
        ]),
    ])
    _set_characters(state, OPPONENT_ID, [
        _make_char("K", Suit.CLUBS, [
            _make_card(3, Suit.HEARTS), _make_card(5, Suit.CLUBS), _make_card(9, Suit.CLUBS),
            _make_card(10, Suit.CLUBS),
        ]),
        _make_char("Q", Suit.CLUBS, [
            _make_card(4, Suit.HEARTS), _make_card(7, Suit.CLUBS), _make_card(8, Suit.CLUBS),
        ]),
        _make_char("J", Suit.HEARTS, [
            _make_card(6, Suit.CLUBS), _make_card(8, Suit.CLUBS),
        ]),
    ])
    return state, "Player has strong hearts on top; opponent has clubs-heavy stacks"


@_register("moonshot_stack")
def _scenario_moonshot() -> tuple[GameState, str]:
    """One character has a massive 10-card stack, others are minimal."""
    state = _base_phase2_state()
    _set_characters(state, AGENT_ID, [
        _make_char("K", Suit.CLUBS, [
            _make_card(3, Suit.DIAMONDS), _make_card(4, Suit.HEARTS), _make_card(5, Suit.CLUBS),
            _make_card(6, Suit.CLUBS), _make_card(7, Suit.HEARTS), _make_card(8, Suit.CLUBS),
            _make_card(9, Suit.CLUBS), _make_card(10, Suit.HEARTS), _make_card(10, Suit.CLUBS),
            _make_card(9, Suit.DIAMONDS),
        ]),
        _make_char("Q", Suit.DIAMONDS, [_make_card(3, Suit.HEARTS)]),
        _make_char("J", Suit.SPADES, [_make_card(2, Suit.SPADES)]),
    ])
    _set_characters(state, OPPONENT_ID, [
        _make_char("J", Suit.HEARTS, [
            _make_card(5, Suit.HEARTS), _make_card(7, Suit.CLUBS), _make_card(8, Suit.CLUBS),
        ]),
        _make_char("Q", Suit.CLUBS, [
            _make_card(4, Suit.HEARTS), _make_card(6, Suit.CLUBS), _make_card(9, Suit.SPADES),
        ]),
        _make_char("K", Suit.DIAMONDS, [
            _make_card(3, Suit.HEARTS), _make_card(7, Suit.DIAMONDS), _make_card(10, Suit.CLUBS),
        ]),
    ])
    return state, "Moonshot: char 0 has 10-card stack, others minimal"


def _probe_state(model: MaskablePPO, state: GameState) -> dict:
    """Run model on a game state and return analysis."""
    obs = encode_observation(state, AGENT_ID)
    mask = compute_action_masks(state, AGENT_ID)

    if not mask.any():
        return {"error": "No valid actions"}

    result = forward_with_grad(model, obs, mask)
    saliency = compute_saliency(model, obs, mask, result["action"])

    # Top actions
    probs = result["masked_probs"]
    valid_indices = np.where(mask)[0]
    sorted_valid = sorted(valid_indices, key=lambda i: probs[i], reverse=True)
    top_actions = [(int(i), ACTION_NAMES[i], float(probs[i])) for i in sorted_valid[:10]]

    # Top salient features
    top_sal_idx = np.argsort(saliency)[-15:][::-1]
    top_features = [(FEATURE_NAMES[i], float(saliency[i]), float(obs[i])) for i in top_sal_idx]

    return {
        "value": result["value"],
        "top_actions": top_actions,
        "top_features": top_features,
        "group_saliency": _group_importance(saliency, FEATURE_GROUPS),
        "n_valid_actions": int(mask.sum()),
    }


def analyze_probes(model: MaskablePPO, output_dir: str):
    """Run all probe scenarios."""
    _setup_style()
    out = os.path.join(output_dir, "probes")
    os.makedirs(out, exist_ok=True)

    results = {}
    for name, builder in SCENARIOS.items():
        state, description = builder()
        analysis = _probe_state(model, state)
        analysis["description"] = description
        results[name] = analysis

        # Text report per scenario
        with open(os.path.join(out, f"probe_{name}.txt"), "w") as f:
            f.write(f"=== Scenario: {name} ===\n")
            f.write(f"Description: {description}\n")
            f.write(f"Value estimate: {analysis['value']:.4f}\n")
            f.write(f"Valid actions: {analysis['n_valid_actions']}\n\n")
            f.write("Top 10 actions:\n")
            for idx, aname, prob in analysis["top_actions"]:
                f.write(f"  [{idx:3d}] {aname:45s}  {prob:.4f}\n")
            f.write("\nTop 15 salient features:\n")
            for fname, sal, val in analysis["top_features"]:
                f.write(f"  {fname:45s}  saliency={sal:.5f}  value={val:.3f}\n")

    # -- Value comparison bar chart --
    scenario_names = list(results.keys())
    values = [results[n]["value"] for n in scenario_names]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#CC6677" if v < 0 else "#228833" for v in values]
    ax.barh(range(len(scenario_names)), values, color=colors)
    ax.set_yticks(range(len(scenario_names)))
    ax.set_yticklabels(scenario_names, fontsize=9)
    ax.axvline(x=0, color="black", linewidth=0.8)
    ax.set_xlabel("Value Estimate (>0 = thinks it's winning)")
    ax.set_title("Value Estimates Across Scenarios")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "probe_values_comparison.png"), dpi=150)
    plt.close(fig)

    # -- Action distribution multi-panel --
    n_scenarios = len(scenario_names)
    fig, axes = plt.subplots(2, (n_scenarios + 1) // 2, figsize=(16, 10))
    axes = axes.flatten()
    for i, name in enumerate(scenario_names):
        ax = axes[i]
        top = results[name]["top_actions"][:7]
        names_short = [a[1][:30] for a in top]
        probs = [a[2] for a in top]
        ax.barh(range(len(top)), probs[::-1], color="#4477AA")
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(names_short[::-1], fontsize=6)
        ax.set_title(name, fontsize=9)
        ax.set_xlim(0, 1)
    for i in range(n_scenarios, len(axes)):
        axes[i].set_visible(False)
    fig.suptitle("Top Actions per Scenario", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "probe_action_distributions.png"), dpi=150)
    plt.close(fig)

    print(f"Probe analysis saved to {out}/")


# ---------------------------------------------------------------------------
# Analysis D: Rollout statistics
# ---------------------------------------------------------------------------

def _compute_phase_positions(records: list[dict]) -> None:
    """Compute normalized position within each phase for each record.

    Phase 1 steps get position 0→1 within Phase 1; Phase 2 steps get
    position 0→1 within Phase 2. This avoids mixing the two very different
    game halves together.
    """
    # Group step indices by (game_idx, phase)
    from collections import defaultdict
    phase_steps: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        phase_steps[(r["game_idx"], r["phase"])].append(i)

    for (game_idx, phase), indices in phase_steps.items():
        n = len(indices)
        for rank, idx in enumerate(indices):
            records[idx]["phase_position"] = rank / max(n - 1, 1)


def _rollout_phase_charts(
    records: list[dict],
    phase: int,
    n_games: int,
    out: str,
    suffix: str,
    n_buckets: int = 20,
):
    """Generate entropy, value, and action-type charts for a single phase."""
    phase_records = [r for r in records if r["phase"] == phase]
    if not phase_records:
        return

    phase_label = f"Phase {phase}"
    x = np.linspace(0, 1, n_buckets)

    # -- Entropy --
    bucket_entropy = [[] for _ in range(n_buckets)]
    for r in phase_records:
        b = min(int(r["phase_position"] * n_buckets), n_buckets - 1)
        bucket_entropy[b].append(r["entropy"])

    fig, ax = plt.subplots(figsize=(10, 5))
    means = [np.mean(b) if b else 0 for b in bucket_entropy]
    ax.plot(x, means, "b-o", markersize=4)
    ax.set_xlabel(f"{phase_label} progression (0=start, 1=end)")
    ax.set_ylabel("Policy entropy (nats)")
    ax.set_title(f"Policy Entropy: {phase_label} ({n_games} games, {len(phase_records)} decisions)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"entropy_{suffix}.png"), dpi=150)
    plt.close(fig)

    # -- Value trajectory: wins vs losses --
    bucket_val_win = [[] for _ in range(n_buckets)]
    bucket_val_loss = [[] for _ in range(n_buckets)]
    for r in phase_records:
        b = min(int(r["phase_position"] * n_buckets), n_buckets - 1)
        if r["game_won"] is True:
            bucket_val_win[b].append(r["value"])
        elif r["game_won"] is False:
            bucket_val_loss[b].append(r["value"])

    fig, ax = plt.subplots(figsize=(10, 5))
    win_means = [np.mean(b) if b else float("nan") for b in bucket_val_win]
    loss_means = [np.mean(b) if b else float("nan") for b in bucket_val_loss]
    ax.plot(x, win_means, "g-o", markersize=4, label="Wins")
    ax.plot(x, loss_means, "r-s", markersize=4, label="Losses")
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel(f"{phase_label} progression")
    ax.set_ylabel("Value estimate")
    ax.set_title(f"Value Trajectory: {phase_label} (Wins vs Losses)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"value_{suffix}.png"), dpi=150)
    plt.close(fig)

    # -- Action type frequency --
    cat_names = list(ACTION_CATEGORIES.keys())
    cat_buckets = np.zeros((n_buckets, len(cat_names)))
    for r in phase_records:
        b = min(int(r["phase_position"] * n_buckets), n_buckets - 1)
        ci = cat_names.index(r["action_cat"]) if r["action_cat"] in cat_names else -1
        if ci >= 0:
            cat_buckets[b, ci] += 1
    # Remove action categories that never occur in this phase
    used_cats = [ci for ci, cat in enumerate(cat_names) if cat_buckets[:, ci].sum() > 0]
    # Normalize rows
    row_sums = cat_buckets.sum(axis=1, keepdims=True)
    cat_buckets = np.divide(cat_buckets, row_sums, where=row_sums > 0, out=cat_buckets)

    fig, ax = plt.subplots(figsize=(12, 6))
    bottom = np.zeros(n_buckets)
    all_colors = plt.cm.tab10(np.linspace(0, 1, len(cat_names)))
    for ci in used_cats:
        ax.bar(x, cat_buckets[:, ci], width=0.04, bottom=bottom,
               label=cat_names[ci], color=all_colors[ci])
        bottom += cat_buckets[:, ci]
    ax.set_xlabel(f"{phase_label} progression")
    ax.set_ylabel("Action type frequency")
    ax.set_title(f"Action Distribution: {phase_label}")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"actions_{suffix}.png"), dpi=150)
    plt.close(fig)


def analyze_rollouts(model: MaskablePPO, n_games: int, output_dir: str):
    """Policy behavior analysis over many games, split by phase."""
    _setup_style()
    out = os.path.join(output_dir, "rollouts")
    os.makedirs(out, exist_ok=True)

    records = _collect_game_data(model, n_games, collect_saliency=False)
    print(f"Collected {len(records)} decision points from {n_games} games")

    # Tag each record with game outcome
    game_outcomes = {}
    for r in records:
        if r["game_over"] and r["won"] is not None:
            game_outcomes[r["game_idx"]] = r["won"]
    for r in records:
        r["game_won"] = game_outcomes.get(r["game_idx"])

    # Compute per-record stats
    for r in records:
        probs = r["action_probs"]
        valid = probs > 0
        if valid.sum() > 0:
            p = probs[valid]
            r["entropy"] = float(-np.sum(p * np.log(p + 1e-10)))
        else:
            r["entropy"] = 0.0
        r["action_cat"] = _action_category(r["action"])

    # Compute per-phase position (0→1 within each phase separately)
    _compute_phase_positions(records)

    # Generate separate charts for each phase
    p1_count = sum(1 for r in records if r["phase"] == 1)
    p2_count = sum(1 for r in records if r["phase"] == 2)
    print(f"  Phase 1: {p1_count} decisions | Phase 2: {p2_count} decisions")

    _rollout_phase_charts(records, phase=1, n_games=n_games, out=out, suffix="phase1")
    _rollout_phase_charts(records, phase=2, n_games=n_games, out=out, suffix="phase2")

    # -- Perform suit breakdown (Phase 2 only) --
    perform_records = [r for r in records if r["action_cat"] == "perform"]
    if perform_records:
        suit_counts = {"clubs": 0, "diamonds": 0, "hearts": 0, "spades": 0}
        for r in perform_records:
            s = _perform_suit(r["action"])
            if s in suit_counts:
                suit_counts[s] += 1

        fig, ax = plt.subplots(figsize=(7, 7))
        suit_names = list(suit_counts.keys())
        suit_vals = [suit_counts[s] for s in suit_names]
        suit_colors = ["#444444", "#4477AA", "#CC6677", "#228833"]
        ax.pie(suit_vals, labels=suit_names, colors=suit_colors, autopct="%1.1f%%",
               startangle=90)
        ax.set_title(f"Perform Action Suit Breakdown ({len(perform_records)} actions)")
        fig.tight_layout()
        fig.savefig(os.path.join(out, "perform_suit_breakdown.png"), dpi=150)
        plt.close(fig)

    # -- Phase 2: tap vs perform vs strike breakdown over time --
    p2_records = [r for r in records if r["phase"] == 2]
    if p2_records:
        combat_cats = ["perform", "strike", "tap", "buy", "end_turn"]
        n_buckets = 20
        x = np.linspace(0, 1, n_buckets)
        combat_buckets = np.zeros((n_buckets, len(combat_cats)))
        for r in p2_records:
            b = min(int(r["phase_position"] * n_buckets), n_buckets - 1)
            if r["action_cat"] in combat_cats:
                ci = combat_cats.index(r["action_cat"])
                combat_buckets[b, ci] += 1
        row_sums = combat_buckets.sum(axis=1, keepdims=True)
        combat_buckets = np.divide(combat_buckets, row_sums, where=row_sums > 0, out=combat_buckets)

        fig, ax = plt.subplots(figsize=(12, 6))
        bottom = np.zeros(n_buckets)
        combat_colors = ["#CC6677", "#882255", "#AA4499", "#4477AA", "#88CCEE"]
        for ci, cat in enumerate(combat_cats):
            if combat_buckets[:, ci].sum() > 0:
                ax.bar(x, combat_buckets[:, ci], width=0.04, bottom=bottom,
                       label=cat, color=combat_colors[ci])
                bottom += combat_buckets[:, ci]
        ax.set_xlabel("Phase 2 progression")
        ax.set_ylabel("Action frequency")
        ax.set_title("Phase 2 Combat Action Breakdown Over Time")
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "combat_actions_phase2.png"), dpi=150)
        plt.close(fig)

    print(f"Rollout analysis saved to {out}/")


# ---------------------------------------------------------------------------
# Analysis E: Decision explainer
# ---------------------------------------------------------------------------

def explain_decision(model: MaskablePPO, seed: int = None, output_dir: str = "logs/interpret"):
    """Deep dive on a single Phase 2 decision."""
    _setup_style()
    out = os.path.join(output_dir, "explain")
    os.makedirs(out, exist_ok=True)

    if seed is not None:
        py_random.seed(seed)
        np.random.seed(seed)

    # Play a game until a Phase 2 decision point
    env = ShovelsEnv()
    obs, info = env.reset()
    target_step = None
    steps = 0
    while True:
        mask = env.action_masks()
        action, _ = model.predict(obs, deterministic=True, action_masks=mask)
        if info.get("phase") == 2 and steps > 5:
            # Use this state
            target_step = steps
            break
        obs, reward, terminated, truncated, info = env.step(int(action))
        steps += 1
        if terminated or truncated:
            # Game ended before Phase 2 - try again
            obs, info = env.reset()
            steps = 0

    # Now analyze this decision point
    result = forward_with_grad(model, obs, mask)
    saliency = compute_saliency(model, obs, mask, result["action"])

    probs = result["masked_probs"]
    valid_indices = np.where(mask)[0]
    sorted_valid = sorted(valid_indices, key=lambda i: probs[i], reverse=True)
    top_actions = [(int(i), ACTION_NAMES[i], float(probs[i])) for i in sorted_valid[:15]]

    top_sal_idx = np.argsort(saliency)[-15:][::-1]
    top_features = [(FEATURE_NAMES[i], float(saliency[i]), float(obs[i])) for i in top_sal_idx]

    group_sal = _group_importance(saliency, FEATURE_GROUPS)

    # -- Text report --
    with open(os.path.join(out, "explain_decision.txt"), "w") as f:
        f.write(f"=== Decision Explanation (step {target_step}) ===\n")
        f.write(f"Phase: {info.get('phase')}  Subphase: {info.get('subphase')}\n")
        f.write(f"Turn: {info.get('turn_count')}  Seed: {seed}\n\n")
        f.write(f"Value estimate: {result['value']:.4f}\n")
        interpretation = "winning" if result["value"] > 0 else "losing"
        f.write(f"  (model thinks it's {interpretation})\n\n")
        f.write(f"Valid actions: {int(mask.sum())}\n\n")
        f.write("Top 15 actions by probability:\n")
        for idx, aname, prob in top_actions:
            marker = " <-- CHOSEN" if idx == result["action"] else ""
            f.write(f"  [{idx:3d}] {aname:45s}  {prob:.4f}{marker}\n")
        f.write("\nTop 15 salient features:\n")
        for fname, sal, val in top_features:
            f.write(f"  {fname:45s}  saliency={sal:.5f}  value={val:.3f}\n")
        f.write("\nFeature group saliency:\n")
        for g in sorted(group_sal.keys(), key=lambda k: group_sal[k], reverse=True):
            f.write(f"  {g:25s}  {group_sal[g]:.5f}\n")

    # -- 3-panel figure --
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 8))

    # Panel 1: Top action probabilities
    top10 = top_actions[:10]
    ax1.barh(range(len(top10)), [a[2] for a in top10][::-1], color="#4477AA")
    ax1.set_yticks(range(len(top10)))
    ax1.set_yticklabels([a[1][:35] for a in top10][::-1], fontsize=7)
    ax1.set_xlabel("Probability")
    ax1.set_title("Top 10 Action Probabilities")

    # Panel 2: Top salient features
    top10f = top_features[:10]
    ax2.barh(range(len(top10f)), [f[1] for f in top10f][::-1], color="#EE6677")
    ax2.set_yticks(range(len(top10f)))
    ax2.set_yticklabels([f[0] for f in top10f][::-1], fontsize=7)
    ax2.set_xlabel("|Gradient * Input|")
    ax2.set_title("Top 10 Salient Features")

    # Panel 3: Group saliency
    gnames = sorted(group_sal.keys(), key=lambda k: group_sal[k], reverse=True)
    ax3.barh(range(len(gnames)), [group_sal[g] for g in gnames][::-1], color="#228833")
    ax3.set_yticks(range(len(gnames)))
    ax3.set_yticklabels(gnames[::-1], fontsize=7)
    ax3.set_xlabel("Mean |gradient * input|")
    ax3.set_title("Feature Group Saliency")

    fig.suptitle(f"Decision Explanation (step {target_step}, value={result['value']:.3f})", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "explain_decision.png"), dpi=150)
    plt.close(fig)

    print(f"Decision explanation saved to {out}/")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def run_dashboard(model: MaskablePPO, n_games: int, output_dir: str):
    """Run all analyses."""
    print("=" * 60)
    print("Running full interpretability dashboard")
    print("=" * 60)

    print("\n[1/5] Weight analysis...")
    analyze_weights(model, output_dir)

    print("\n[2/5] Saliency analysis...")
    analyze_saliency(model, n_games, output_dir)

    print("\n[3/5] Scenario probing...")
    analyze_probes(model, output_dir)

    print("\n[4/5] Rollout analysis...")
    analyze_rollouts(model, n_games, output_dir)

    print("\n[5/5] Decision explanation...")
    for seed in [42, 123, 777]:
        explain_decision(model, seed=seed, output_dir=output_dir)

    print(f"\nDashboard complete! All outputs in {output_dir}/")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Shovels RL Interpretability Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model", type=str, required=True, help="Path to MaskablePPO .zip")
    parser.add_argument("--output-dir", type=str, default="logs/interpret", help="Output directory")
    parser.add_argument("--n-games", type=int, default=200, help="Games for data collection")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("weights", help="Weight-based feature importance")
    subparsers.add_parser("saliency", help="Gradient saliency maps")
    subparsers.add_parser("probe", help="Scenario probing")
    subparsers.add_parser("rollout", help="Policy distribution analysis")
    subparsers.add_parser("explain", help="Single-state decision explainer")
    subparsers.add_parser("dashboard", help="Run all analyses")

    args = parser.parse_args()
    model = load_model(args.model)

    if args.command == "weights":
        analyze_weights(model, args.output_dir)
    elif args.command == "saliency":
        analyze_saliency(model, args.n_games, args.output_dir)
    elif args.command == "probe":
        analyze_probes(model, args.output_dir)
    elif args.command == "rollout":
        analyze_rollouts(model, args.n_games, args.output_dir)
    elif args.command == "explain":
        explain_decision(model, seed=args.seed, output_dir=args.output_dir)
    elif args.command == "dashboard":
        run_dashboard(model, args.n_games, args.output_dir)


if __name__ == "__main__":
    main()
