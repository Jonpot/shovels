"""Tests for the interpretability toolkit."""

import numpy as np
import pytest

from shovels_gym.obs_space import (
    OBS_SIZE, FEATURE_NAMES, FEATURE_GROUPS, FEATURE_SUPERGROUPS,
    encode_observation,
)
from shovels_gym.action_space import (
    ACTION_SPACE_SIZE, ACTION_NAMES, ACTION_CATEGORIES,
    action_masks as compute_action_masks,
)
from shovels_engine.models import setup_game


def test_feature_names_length():
    assert len(FEATURE_NAMES) == OBS_SIZE


def test_feature_names_unique():
    assert len(set(FEATURE_NAMES)) == len(FEATURE_NAMES), "Duplicate feature names found"


def test_feature_names_nonempty():
    for i, name in enumerate(FEATURE_NAMES):
        assert name, f"Feature {i} has empty name"


def test_feature_groups_cover_all():
    """Groups must cover all 798 indices with no gaps or overlaps."""
    covered = set()
    for name, (start, end) in FEATURE_GROUPS.items():
        assert start < end, f"Group {name} has invalid range ({start}, {end})"
        for i in range(start, end):
            assert i not in covered, f"Index {i} covered by multiple groups"
            covered.add(i)
    assert covered == set(range(OBS_SIZE)), f"Missing indices: {set(range(OBS_SIZE)) - covered}"


def test_feature_supergroups_reference_valid_groups():
    for sg, groups in FEATURE_SUPERGROUPS.items():
        for g in groups:
            assert g in FEATURE_GROUPS, f"Supergroup {sg} references unknown group {g}"


def test_action_names_length():
    assert len(ACTION_NAMES) == ACTION_SPACE_SIZE


def test_action_names_nonempty():
    for i, name in enumerate(ACTION_NAMES):
        assert name, f"Action {i} has empty name"


def test_action_categories_cover_all():
    covered = set()
    for name, (start, end) in ACTION_CATEGORIES.items():
        for i in range(start, end):
            assert i not in covered, f"Action {i} covered by multiple categories"
            covered.add(i)
    assert covered == set(range(ACTION_SPACE_SIZE))


def _make_model():
    """Create a tiny MaskablePPO for testing (untrained)."""
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker
    from shovels_gym.envs.shovels_env import ShovelsEnv

    env = ShovelsEnv()
    env = ActionMasker(env, lambda e: e.action_masks())
    model = MaskablePPO(
        "MlpPolicy", env,
        policy_kwargs=dict(net_arch=dict(pi=[32, 32], vf=[32, 32])),
        n_steps=64, batch_size=32, verbose=0,
    )
    return model


def test_get_policy_layers():
    from shovels_gym.interpret import get_policy_layers

    model = _make_model()
    layers = get_policy_layers(model)
    assert "policy_net_0" in layers
    assert "policy_net_1" in layers
    assert "value_net_0" in layers
    assert "value_net_1" in layers
    assert "action_net" in layers
    assert "value_head" in layers


def test_forward_with_grad():
    from shovels_gym.interpret import forward_with_grad

    model = _make_model()
    state = setup_game(["agent", "opponent"])
    obs = encode_observation(state, "agent")
    mask = compute_action_masks(state, "agent")

    result = forward_with_grad(model, obs, mask)
    assert result["masked_probs"].shape == (ACTION_SPACE_SIZE,)
    assert isinstance(result["value"], float)
    assert 0 <= result["action"] < ACTION_SPACE_SIZE
    assert abs(result["masked_probs"].sum() - 1.0) < 1e-5


def test_compute_saliency_shape():
    from shovels_gym.interpret import compute_saliency

    model = _make_model()
    state = setup_game(["agent", "opponent"])
    obs = encode_observation(state, "agent")
    mask = compute_action_masks(state, "agent")

    sal = compute_saliency(model, obs, mask)
    assert sal.shape == (OBS_SIZE,)
    assert (sal >= 0).all()


def test_scenario_states_valid():
    """Each probe scenario produces a valid state with valid action masks."""
    from shovels_gym.interpret import SCENARIOS

    for name, builder in SCENARIOS.items():
        state, description = builder()
        assert isinstance(description, str)
        obs = encode_observation(state, "agent")
        assert obs.shape == (OBS_SIZE,)
        mask = compute_action_masks(state, "agent")
        assert mask.any(), f"Scenario {name} has no valid actions"


def test_probe_state():
    from shovels_gym.interpret import SCENARIOS, _probe_state

    model = _make_model()
    state, _ = SCENARIOS["early_phase2"]()
    result = _probe_state(model, state)
    assert "value" in result
    assert "top_actions" in result
    assert len(result["top_actions"]) > 0
    assert "group_saliency" in result
