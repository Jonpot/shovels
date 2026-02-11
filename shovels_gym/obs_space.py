"""
Observation encoding helpers for the Shovels Gymnasium environment.

Flat Box(low=0, high=1, shape=(804,)) with all values normalized to [0,1].

Layout (804 floats):
| Component               | Size | Description                                  |
|-------------------------|------|----------------------------------------------|
| Game metadata           | 26   | phase, subphase(9), coins, sizes, flags,     |
|                         |      | pending_attack(5)                            |
| Own chars (x3)          | 273  | Per char: 11 meta + 10 stack cards x 8       |
| Opp chars (x3)          | 273  | Same structure                               |
| Hand (x2)               | 16   | Phase 1 hand cards, 8 each                   |
| Shop row (x3)           | 24   | 3 shop slots, 8 each                         |
| Gravedig pool (x5)      | 40   | 5 pool cards, 8 each                         |
| Dug cards (x10)         | 80   | Active char's dug cards, 8 each              |
| Strategic features (x6) | 66   | Per char: stack composition + defense info    |
| Cross-player features   | 6    | Alive counts, attack totals, weakest hearts   |

Card encoding (8 floats):
  [exists, rank/10, is_ace, face_rank_norm, suit_clubs, suit_diamonds, suit_hearts, suit_spades]

Character meta (11 floats):
  [exists, is_dead, rank_J, rank_Q, rank_K, suit_clubs, suit_diamonds, suit_hearts, suit_spades, is_tapped, shield/10]

Strategic features per character (11 floats):
  [stack_depth, clubs_rank_sum, diamonds_rank_sum, hearts_rank_sum, spades_rank_sum,
   topmost_heart_rank, topmost_heart_depth, top_suit_clubs, top_suit_diamonds, top_suit_hearts, top_suit_spades]

Pending attack features (5 floats):
  [pending_damage, pending_target_0, pending_target_1, pending_target_2, pending_survive_with_tap]

Cross-player features (6 floats):
  [own_alive, opp_alive, own_total_attack, opp_total_attack, own_weakest_heart, opp_weakest_heart]
"""

import numpy as np
from shovels_engine.models import GameState, Suit, Card, Character

OBS_SIZE = 804

# Subphase encoding (one-hot over 9 values)
SUBPHASES = ["DRAW", "DISCARD", "PLAY", "BATTLE_ACTION", "SHOPPING", "SHOP_FREE_BUY", "SPADE_DIG", "GRAVEDIGGING", "DEFENSE_REACTION"]
SUBPHASE_MAP = {s: i for i, s in enumerate(SUBPHASES)}

MAX_STACK_CARDS = 10
MAX_DUG_CARDS = 10
MAX_GRAVEDIG_POOL = 5


def encode_card(card) -> np.ndarray:
    """Encode a single card as 8 floats in [0,1]."""
    if card is None:
        return np.zeros(8, dtype=np.float32)

    suit_onehot = [0.0, 0.0, 0.0, 0.0]
    suit_idx = {Suit.CLUBS: 0, Suit.DIAMONDS: 1, Suit.HEARTS: 2, Suit.SPADES: 3}
    suit_onehot[suit_idx[card.suit]] = 1.0

    face_rank_norm = 0.0
    if card.is_face and card.face_rank:
        face_rank_norm = {"J": 0.33, "Q": 0.67, "K": 1.0}[card.face_rank]

    return np.array([
        1.0,                              # exists
        card.rank / 10.0,                 # rank normalized
        1.0 if card.is_ace else 0.0,      # is_ace
        face_rank_norm,                   # face rank normalized
        suit_onehot[0],                   # clubs
        suit_onehot[1],                   # diamonds
        suit_onehot[2],                   # hearts
        suit_onehot[3],                   # spades
    ], dtype=np.float32)


def encode_character(char: Character) -> np.ndarray:
    """Encode a character: 11 meta + 10 stack cards x 8 = 91 floats."""
    result = np.zeros(91, dtype=np.float32)

    if char is None:
        return result

    # Meta (11 floats)
    result[0] = 1.0                                     # exists
    result[1] = 1.0 if char.is_dead else 0.0           # is_dead
    result[2] = 1.0 if char.rank == "J" else 0.0       # rank_J
    result[3] = 1.0 if char.rank == "Q" else 0.0       # rank_Q
    result[4] = 1.0 if char.rank == "K" else 0.0       # rank_K
    suit_idx = {Suit.CLUBS: 5, Suit.DIAMONDS: 6, Suit.HEARTS: 7, Suit.SPADES: 8}
    if char.suit in suit_idx:
        result[suit_idx[char.suit]] = 1.0
    result[9] = 1.0 if char.is_tapped else 0.0         # is_tapped
    result[10] = min(char.temporary_shield / 10.0, 1.0) # shield normalized

    # Stack cards (up to 10, from bottom to top)
    offset = 11
    for i in range(min(MAX_STACK_CARDS, len(char.stack))):
        result[offset + i * 8: offset + (i + 1) * 8] = encode_card(char.stack[i])

    return result


SUIT_MAP = {Suit.CLUBS: 0, Suit.DIAMONDS: 1, Suit.HEARTS: 2, Suit.SPADES: 3}


def encode_char_strategic(char: Character) -> np.ndarray:
    """Encode strategic features for one character (11 floats)."""
    result = np.zeros(11, dtype=np.float32)
    if char is None or char.is_dead:
        return result

    stack = char.stack
    result[0] = min(len(stack) / 10.0, 1.0)  # stack_depth

    # Suit rank sums
    suit_sums = [0.0, 0.0, 0.0, 0.0]  # clubs, diamonds, hearts, spades
    for c in stack:
        suit_sums[SUIT_MAP[c.suit]] += c.rank

    result[1] = min(suit_sums[0] / 50.0, 1.0)  # clubs_rank_sum
    result[2] = min(suit_sums[1] / 50.0, 1.0)  # diamonds_rank_sum
    result[3] = min(suit_sums[2] / 50.0, 1.0)  # hearts_rank_sum
    result[4] = min(suit_sums[3] / 50.0, 1.0)  # spades_rank_sum

    # Topmost heart: scan from top of stack (last element) down
    heart_rank = 0.0
    heart_depth = 1.0  # 1.0 = no heart found
    for i, c in enumerate(reversed(stack)):
        if c.suit == Suit.HEARTS:
            heart_rank = c.rank / 10.0
            heart_depth = i / 10.0  # 0.0 = top card, higher = deeper
            break
    result[5] = heart_rank
    result[6] = heart_depth

    # Top card suit (one-hot)
    if stack:
        top_suit = SUIT_MAP[stack[-1].suit]
        result[7 + top_suit] = 1.0

    return result


def encode_observation(state: GameState, player_id: str) -> np.ndarray:
    """Encode the full game state as a flat observation vector."""
    obs = np.zeros(OBS_SIZE, dtype=np.float32)
    idx = 0

    player = next(p for p in state.players if p.id == player_id)
    opponent = next(p for p in state.players if p.id != player_id)

    # ---- Game metadata (26 floats) ----
    # Phase (1 float): 0.0 for phase 1, 1.0 for phase 2
    obs[idx] = 1.0 if state.phase == 2 else 0.0
    idx += 1

    # Subphase one-hot (9 floats)
    sp_idx = SUBPHASE_MAP.get(state.turn_subphase, 0)
    obs[idx + sp_idx] = 1.0
    idx += 9

    # Coins (1 float, normalized)
    obs[idx] = min(player.coins / 20.0, 1.0)
    idx += 1

    # Deck size (1 float, normalized)
    obs[idx] = min(len(state.deck) / 80.0, 1.0)
    idx += 1

    # Discard pile size (1 float)
    obs[idx] = min(len(state.discard_pile) / 80.0, 1.0)
    idx += 1

    # Shop pile size (1 float)
    obs[idx] = min(len(state.shop_pile) / 20.0, 1.0)
    idx += 1

    # Turn count (1 float, normalized)
    obs[idx] = min(state.turn_count / 100.0, 1.0)
    idx += 1

    # Flags (6 floats)
    obs[idx] = 1.0 if state.action_taken_this_turn else 0.0
    idx += 1
    obs[idx] = 1.0 if state.cards_removed_this_turn else 0.0
    idx += 1
    obs[idx] = 1.0 if state.character_tapped_this_turn else 0.0
    idx += 1
    obs[idx] = min(state.free_buys_remaining / 3.0, 1.0)
    idx += 1
    obs[idx] = 1.0 if player.can_discard_second_face else 0.0
    idx += 1
    obs[idx] = min(state.gravedig_cards_taken / 3.0, 1.0)
    idx += 1

    # Pending attack features (5 floats)
    pa = state.pending_attack
    if pa is not None and pa.target_player_id == player_id:
        obs[idx] = min(pa.damage / 50.0, 1.0)  # pending_damage
        idx += 1
        for ci in range(3):
            obs[idx] = 1.0 if pa.target_char_index == ci else 0.0
            idx += 1
        # Would survive with tap?
        survive = 0.0
        if pa.target_char_index < len(player.characters):
            tc = player.characters[pa.target_char_index]
            if not tc.is_dead and tc.suit == Suit.HEARTS:
                shield_add = {"J": 3, "Q": 5, "K": 10}.get(tc.rank, 0)
                for c in reversed(tc.stack):
                    if c.suit == Suit.HEARTS:
                        if pa.damage < (c.rank + tc.temporary_shield + shield_add):
                            survive = 1.0
                        break
        obs[idx] = survive
        idx += 1
    else:
        idx += 5  # Skip pending attack features

    # ---- Own characters (3 x 91 = 273 floats) ----
    for i in range(3):
        if i < len(player.characters):
            obs[idx: idx + 91] = encode_character(player.characters[i])
        idx += 91

    # ---- Opponent characters (3 x 91 = 273 floats) ----
    for i in range(3):
        if i < len(opponent.characters):
            obs[idx: idx + 91] = encode_character(opponent.characters[i])
        idx += 91

    # ---- Hand (2 x 8 = 16 floats) ----
    for i in range(2):
        if i < len(player.hand):
            obs[idx: idx + 8] = encode_card(player.hand[i])
        idx += 8

    # ---- Shop row (3 x 8 = 24 floats) ----
    for i in range(3):
        if i < len(state.shop_row) and state.shop_row[i] is not None:
            obs[idx: idx + 8] = encode_card(state.shop_row[i])
        idx += 8

    # ---- Gravedig pool (5 x 8 = 40 floats) ----
    for i in range(MAX_GRAVEDIG_POOL):
        if i < len(state.gravedig_pool):
            obs[idx: idx + 8] = encode_card(state.gravedig_pool[i])
        idx += 8

    # ---- Dug cards (10 x 8 = 80 floats) ----
    dug = []
    if state.active_character_index is not None:
        aci = state.active_character_index
        if aci < len(player.characters):
            dug = player.characters[aci].dug_cards
    for i in range(MAX_DUG_CARDS):
        if i < len(dug):
            obs[idx: idx + 8] = encode_card(dug[i])
        idx += 8

    # ---- Strategic features per character (6 x 11 = 66 floats) ----
    all_chars = []
    for i in range(3):
        char = player.characters[i] if i < len(player.characters) else None
        obs[idx: idx + 11] = encode_char_strategic(char)
        all_chars.append((char, "own"))
        idx += 11
    for i in range(3):
        char = opponent.characters[i] if i < len(opponent.characters) else None
        obs[idx: idx + 11] = encode_char_strategic(char)
        all_chars.append((char, "opp"))
        idx += 11

    # ---- Cross-player strategic features (6 floats) ----
    own_alive = sum(1 for c in player.characters if not c.is_dead)
    opp_alive = sum(1 for c in opponent.characters if not c.is_dead)
    obs[idx] = own_alive / 3.0
    idx += 1
    obs[idx] = opp_alive / 3.0
    idx += 1

    # Total clubs attack potential
    own_attack = sum(
        sum(c.rank for c in ch.stack if c.suit == Suit.CLUBS)
        for ch in player.characters if not ch.is_dead
    )
    opp_attack = sum(
        sum(c.rank for c in ch.stack if c.suit == Suit.CLUBS)
        for ch in opponent.characters if not ch.is_dead
    )
    obs[idx] = min(own_attack / 100.0, 1.0)
    idx += 1
    obs[idx] = min(opp_attack / 100.0, 1.0)
    idx += 1

    # Weakest topmost heart (best target / own vulnerability)
    def weakest_topmost_heart(chars):
        """Find the lowest topmost-heart rank among alive characters (0 = no hearts)."""
        heart_ranks = []
        for ch in chars:
            if ch.is_dead:
                continue
            for c in reversed(ch.stack):
                if c.suit == Suit.HEARTS:
                    heart_ranks.append(c.rank)
                    break
            else:
                # No heart at all - maximally vulnerable
                heart_ranks.append(0)
        return min(heart_ranks) if heart_ranks else 0

    obs[idx] = weakest_topmost_heart(player.characters) / 10.0
    idx += 1
    obs[idx] = weakest_topmost_heart(opponent.characters) / 10.0
    idx += 1

    assert idx == OBS_SIZE, f"Observation size mismatch: {idx} != {OBS_SIZE}"
    return obs


# ---------------------------------------------------------------------------
# Human-readable feature names and groups (for interpretability)
# ---------------------------------------------------------------------------

_CARD_FIELDS = ["exists", "rank", "is_ace", "face_rank", "clubs", "diamonds", "hearts", "spades"]
_CHAR_META_FIELDS = [
    "exists", "is_dead", "rank_J", "rank_Q", "rank_K",
    "suit_clubs", "suit_diamonds", "suit_hearts", "suit_spades",
    "is_tapped", "shield",
]
_STRAT_FIELDS = [
    "stack_depth", "clubs_sum", "diamonds_sum", "hearts_sum", "spades_sum",
    "top_heart_rank", "top_heart_depth",
    "top_clubs", "top_diamonds", "top_hearts", "top_spades",
]


def _build_feature_names() -> list[str]:
    names: list[str] = []

    # Game metadata (26)
    names.append("phase")
    for sp in SUBPHASES:
        names.append(f"subphase_{sp.lower()}")
    names.append("coins")
    names.append("deck_size")
    names.append("discard_size")
    names.append("shop_pile_size")
    names.append("turn_count")
    names.append("action_taken")
    names.append("cards_removed")
    names.append("char_tapped")
    names.append("free_buys")
    names.append("can_discard_2nd_face")
    names.append("gravedig_taken")
    names.extend(["pending_damage", "pending_target_0", "pending_target_1",
                   "pending_target_2", "pending_survive_with_tap"])

    # Own + Opponent characters (6 x 91)
    for side in ("own", "opp"):
        for ci in range(3):
            prefix = f"{side}_char{ci}"
            for mf in _CHAR_META_FIELDS:
                names.append(f"{prefix}_{mf}")
            for si in range(MAX_STACK_CARDS):
                for cf in _CARD_FIELDS:
                    names.append(f"{prefix}_s{si}_{cf}")

    # Hand (2 x 8)
    for hi in range(2):
        for cf in _CARD_FIELDS:
            names.append(f"hand{hi}_{cf}")

    # Shop (3 x 8)
    for si in range(3):
        for cf in _CARD_FIELDS:
            names.append(f"shop{si}_{cf}")

    # Gravedig pool (5 x 8)
    for gi in range(MAX_GRAVEDIG_POOL):
        for cf in _CARD_FIELDS:
            names.append(f"gpool{gi}_{cf}")

    # Dug cards (10 x 8)
    for di in range(MAX_DUG_CARDS):
        for cf in _CARD_FIELDS:
            names.append(f"dug{di}_{cf}")

    # Strategic features (6 x 11)
    for side in ("own", "opp"):
        for ci in range(3):
            prefix = f"strat_{side}_char{ci}"
            for sf in _STRAT_FIELDS:
                names.append(f"{prefix}_{sf}")

    # Cross-player (6)
    names.extend([
        "cross_own_alive", "cross_opp_alive",
        "cross_own_attack", "cross_opp_attack",
        "cross_own_weakest_heart", "cross_opp_weakest_heart",
    ])

    return names


FEATURE_NAMES: list[str] = _build_feature_names()
assert len(FEATURE_NAMES) == OBS_SIZE, f"FEATURE_NAMES length {len(FEATURE_NAMES)} != {OBS_SIZE}"

FEATURE_GROUPS: dict[str, tuple[int, int]] = {
    "game_meta": (0, 26),
    "own_char_0": (26, 117),
    "own_char_1": (117, 208),
    "own_char_2": (208, 299),
    "opp_char_0": (299, 390),
    "opp_char_1": (390, 481),
    "opp_char_2": (481, 572),
    "hand": (572, 588),
    "shop": (588, 612),
    "gravedig_pool": (612, 652),
    "dug_cards": (652, 732),
    "strat_own_char_0": (732, 743),
    "strat_own_char_1": (743, 754),
    "strat_own_char_2": (754, 765),
    "strat_opp_char_0": (765, 776),
    "strat_opp_char_1": (776, 787),
    "strat_opp_char_2": (787, 798),
    "cross_player": (798, 804),
}

FEATURE_SUPERGROUPS: dict[str, list[str]] = {
    "game_state": ["game_meta"],
    "own_characters": ["own_char_0", "own_char_1", "own_char_2"],
    "opp_characters": ["opp_char_0", "opp_char_1", "opp_char_2"],
    "hand": ["hand"],
    "shop": ["shop"],
    "dig_zone": ["gravedig_pool", "dug_cards"],
    "own_strategy": ["strat_own_char_0", "strat_own_char_1", "strat_own_char_2"],
    "opp_strategy": ["strat_opp_char_0", "strat_opp_char_1", "strat_opp_char_2"],
    "cross_player": ["cross_player"],
}
