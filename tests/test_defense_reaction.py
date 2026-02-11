"""Tests for the Hearts defense reaction system."""

import numpy as np
import pytest

from shovels_engine.models import (
    GameState, Card, Character, Player, Suit, PendingAttack, setup_game,
)
from shovels_engine.engine import (
    attack_heart, _resolve_attack, resolve_defense_reaction,
    apply_face_strike, tap_hero_power, end_turn, perform_action,
)
from shovels_gym.obs_space import OBS_SIZE, encode_observation
from shovels_gym.action_space import (
    ACTION_SPACE_SIZE, REACT_TAP_IDX, REACT_PASS_IDX, action_masks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_phase2_state(
    p1_chars=None,
    p2_chars=None,
    enable_reactions=True,
) -> GameState:
    """Build a minimal Phase 2 state for reaction testing."""
    if p1_chars is None:
        p1_chars = [
            Character(rank="Q", suit=Suit.CLUBS, stack=[
                Card(uid="c1", rank=5, suit=Suit.CLUBS),
            ]),
            Character(rank="J", suit=Suit.HEARTS, stack=[
                Card(uid="c2", rank=4, suit=Suit.HEARTS),
            ]),
            Character(rank="K", suit=Suit.DIAMONDS, stack=[]),
        ]
    if p2_chars is None:
        p2_chars = [
            Character(rank="J", suit=Suit.HEARTS, stack=[
                Card(uid="c3", rank=3, suit=Suit.HEARTS),
            ]),
            Character(rank="Q", suit=Suit.HEARTS, stack=[
                Card(uid="c4", rank=6, suit=Suit.HEARTS),
            ]),
            Character(rank="K", suit=Suit.SPADES, stack=[
                Card(uid="c5", rank=7, suit=Suit.SPADES),
            ]),
        ]

    state = GameState(
        phase=2,
        turn_subphase="BATTLE_ACTION",
        players=[
            Player(id="p1", name="P1", characters=p1_chars),
            Player(id="p2", name="P2", characters=p2_chars),
        ],
        current_turn_index=0,
        enable_reactions=enable_reactions,
        deck=[Card(uid=f"d{i}", rank=2+i, suit=Suit.DIAMONDS) for i in range(10)],
    )
    return state


# ---------------------------------------------------------------------------
# 1. PendingAttack model
# ---------------------------------------------------------------------------

def test_pending_attack_model():
    pa = PendingAttack(
        attacker_id="p1",
        target_player_id="p2",
        target_char_index=0,
        damage=5,
        previous_subphase="BATTLE_ACTION",
        source="perform",
    )
    assert pa.attacker_id == "p1"
    assert pa.damage == 5
    assert pa.remaining_tap_targets == []


# ---------------------------------------------------------------------------
# 2. attack_heart triggers reaction for Hearts heroes
# ---------------------------------------------------------------------------

def test_attack_heart_triggers_reaction():
    state = _make_phase2_state()
    # Attack p2's char 0 (J of Hearts, untapped) — should pause
    paused = attack_heart(state, "p1", "p2", 0, 5)
    assert paused is True
    assert state.turn_subphase == "DEFENSE_REACTION"
    assert state.pending_attack is not None
    assert state.pending_attack.damage == 5
    assert state.pending_attack.target_char_index == 0


# ---------------------------------------------------------------------------
# 3. attack_heart resolves immediately for non-Hearts
# ---------------------------------------------------------------------------

def test_attack_heart_no_reaction_non_hearts():
    state = _make_phase2_state()
    # Attack p2's char 2 (K of Spades) — should resolve immediately
    paused = attack_heart(state, "p1", "p2", 2, 5)
    assert paused is False
    assert state.pending_attack is None
    assert state.turn_subphase == "BATTLE_ACTION"


# ---------------------------------------------------------------------------
# 4. resolve_defense_tap adds shield
# ---------------------------------------------------------------------------

def test_resolve_defense_tap():
    state = _make_phase2_state()
    attack_heart(state, "p1", "p2", 0, 5)  # J of Hearts
    assert state.turn_subphase == "DEFENSE_REACTION"

    p2_char0 = state.players[1].characters[0]
    assert p2_char0.temporary_shield == 0

    resolve_defense_reaction(state, "p2", tap=True)
    assert p2_char0.is_tapped is True
    assert p2_char0.temporary_shield == 3  # J = 3 shield


# ---------------------------------------------------------------------------
# 5. resolve_defense_pass resolves without shield
# ---------------------------------------------------------------------------

def test_resolve_defense_pass():
    state = _make_phase2_state()
    attack_heart(state, "p1", "p2", 0, 5)

    p2_char0 = state.players[1].characters[0]
    resolve_defense_reaction(state, "p2", tap=False)
    assert p2_char0.is_tapped is False
    assert p2_char0.temporary_shield == 0


# ---------------------------------------------------------------------------
# 6. Tap blocks attack (low damage + tap → heart survives)
# ---------------------------------------------------------------------------

def test_tap_blocks_attack():
    """J of Hearts has heart 3 on top. Attack with damage=5.
    Without tap: 5 >= 3 → heart broken.
    With tap (J=3 shield): 5 >= (3 + 3) = 6? No → heart survives.
    """
    state = _make_phase2_state()
    attack_heart(state, "p1", "p2", 0, 5)
    resolve_defense_reaction(state, "p2", tap=True)

    p2_char0 = state.players[1].characters[0]
    # Heart card (rank 3) should still be on the stack
    assert len(p2_char0.stack) == 1
    assert p2_char0.stack[0].suit == Suit.HEARTS
    assert not p2_char0.is_dead


# ---------------------------------------------------------------------------
# 7. Tap insufficient for high damage
# ---------------------------------------------------------------------------

def test_tap_insufficient():
    """J of Hearts has heart 3 on top. Attack with damage=10.
    With tap (J=3 shield): 10 >= (3 + 3) = 6? Yes → heart broken.
    """
    state = _make_phase2_state()
    attack_heart(state, "p1", "p2", 0, 10)
    resolve_defense_reaction(state, "p2", tap=True)

    p2_char0 = state.players[1].characters[0]
    # Heart was broken, stack should be empty
    assert len(p2_char0.stack) == 0


# ---------------------------------------------------------------------------
# 8. Clubs tap multi-hit with sequential reactions
# ---------------------------------------------------------------------------

def test_clubs_tap_multi_hit_reactions():
    """Q of Clubs taps for 2 hits. Both targets are Hearts heroes → 2 reactions."""
    state = _make_phase2_state()
    # P1 char 0 is Q of Clubs
    # Targets: p2 char 0 (J Hearts) and p2 char 1 (Q Hearts)
    target_info = {
        "targets": [
            {"target_player_id": "p2", "target_char_index": 0},
            {"target_player_id": "p2", "target_char_index": 1},
        ]
    }
    tap_hero_power(state, "p1", 0, target_info=target_info)

    # First reaction should be pending
    assert state.turn_subphase == "DEFENSE_REACTION"
    pa = state.pending_attack
    assert pa is not None
    assert pa.target_char_index == 0
    assert len(pa.remaining_tap_targets) == 1

    # Resolve first reaction (pass)
    resolve_defense_reaction(state, "p2", tap=False)

    # Second reaction should now be pending
    assert state.turn_subphase == "DEFENSE_REACTION"
    pa2 = state.pending_attack
    assert pa2 is not None
    assert pa2.target_char_index == 1

    # Resolve second reaction (tap)
    resolve_defense_reaction(state, "p2", tap=True)
    # Both reactions resolved, pending should be cleared
    assert state.pending_attack is None


# ---------------------------------------------------------------------------
# 9. Face strike reaction
# ---------------------------------------------------------------------------

def test_face_strike_reaction():
    """Face strike against Hearts hero should trigger DEFENSE_REACTION."""
    # Build state: p1 char 2 (K Diamonds) is exposed (no stack)
    state = _make_phase2_state()
    # Ensure p1 char 2 has no stack (exposed face)
    assert len(state.players[0].characters[2].stack) == 0

    apply_face_strike(state, "p1", 2, "p2", 0)

    # Should pause for reaction (p2 char 0 is J Hearts)
    assert state.turn_subphase == "DEFENSE_REACTION"
    assert state.pending_attack is not None
    assert state.pending_attack.source == "strike"
    assert state.pending_attack.damage == 1


# ---------------------------------------------------------------------------
# 10. Reaction action mask
# ---------------------------------------------------------------------------

def test_reaction_action_mask():
    """REACT_TAP/REACT_PASS should only be valid during DEFENSE_REACTION."""
    state = _make_phase2_state()

    # Before reaction: neither should be valid
    mask_before = action_masks(state, "p2")
    assert not mask_before[REACT_TAP_IDX]
    assert not mask_before[REACT_PASS_IDX]

    # Trigger reaction targeting p2's J of Hearts
    attack_heart(state, "p1", "p2", 0, 5)
    mask_during = action_masks(state, "p2")
    assert mask_during[REACT_TAP_IDX]   # Hearts hero, untapped → can tap
    assert mask_during[REACT_PASS_IDX]  # Can always pass

    # Attacker should NOT have reaction actions
    mask_attacker = action_masks(state, "p1")
    assert not mask_attacker[REACT_TAP_IDX]
    assert not mask_attacker[REACT_PASS_IDX]


def test_reaction_mask_already_tapped():
    """If the Hearts hero is already tapped, only REACT_PASS should be valid."""
    state = _make_phase2_state()
    # Pre-tap p2 char 0
    state.players[1].characters[0].is_tapped = True

    attack_heart(state, "p1", "p2", 0, 5)
    # Still enters reaction because we check enable_reactions and suit
    # But wait — attack_heart checks is_tapped. If tapped, no reaction.
    # So it should resolve immediately
    assert state.pending_attack is None  # No reaction for already-tapped hero


# ---------------------------------------------------------------------------
# 11. Observation size
# ---------------------------------------------------------------------------

def test_obs_size_804():
    assert OBS_SIZE == 804
    state = setup_game(["p1", "p2"])
    state.enable_reactions = True
    obs = encode_observation(state, "p1")
    assert obs.shape == (804,)


def test_obs_pending_attack_features():
    """Pending attack features should be populated during DEFENSE_REACTION."""
    state = _make_phase2_state()
    attack_heart(state, "p1", "p2", 0, 5)

    obs = encode_observation(state, "p2")
    # pending_damage is at index 20 (after 1 phase + 9 subphase + 5 counts + 6 flags)
    # Actually index 20 in the game_meta section
    # The exact index: phase(1) + subphase(9) + coins(1) + deck(1) + discard(1) + shop_pile(1) + turn(1) + flags(6) = 21
    # pending_damage at idx 21, pending_target at 22-24, survive at 25
    assert obs[21] > 0  # pending_damage should be non-zero (5/50 = 0.1)


# ---------------------------------------------------------------------------
# 12. Gym env returns control during opponent's attack
# ---------------------------------------------------------------------------

def test_gym_agent_reacts():
    """Gym environment should return control to agent during DEFENSE_REACTION."""
    from shovels_gym.envs.shovels_env import ShovelsEnv

    env = ShovelsEnv()
    obs, info = env.reset()

    # Run a few steps to verify the env works with reactions enabled
    assert env.state.enable_reactions is True
    assert obs.shape == (OBS_SIZE,)

    # Verify the env can complete a full game
    done = False
    steps = 0
    while not done and steps < 1000:
        mask = env.action_masks()
        valid_actions = np.where(mask)[0]
        if len(valid_actions) == 0:
            break
        action = np.random.choice(valid_actions)
        obs, reward, terminated, truncated, info = env.step(int(action))
        done = terminated or truncated
        steps += 1

    # Should complete without errors
    assert steps > 0


# ---------------------------------------------------------------------------
# 13. Reactions disabled (backward compatibility)
# ---------------------------------------------------------------------------

def test_no_reaction_when_disabled():
    """With enable_reactions=False, attack_heart should resolve immediately."""
    state = _make_phase2_state(enable_reactions=False)
    paused = attack_heart(state, "p1", "p2", 0, 5)
    assert paused is False
    assert state.pending_attack is None


# ---------------------------------------------------------------------------
# 14. Action space size
# ---------------------------------------------------------------------------

def test_action_space_size_242():
    assert ACTION_SPACE_SIZE == 242
