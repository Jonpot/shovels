"""
Observation encoding helpers for the Shovels Gymnasium environment.

Flat Box(low=0, high=1, shape=(726,)) with all values normalized to [0,1].

Layout (726 floats):
| Component          | Size | Description                                  |
|--------------------|------|----------------------------------------------|
| Game metadata      | 20   | phase, subphase(8), coins, sizes, flags      |
| Own chars (x3)     | 273  | Per char: 11 meta + 10 stack cards x 8       |
| Opp chars (x3)     | 273  | Same structure                               |
| Hand (x2)          | 16   | Phase 1 hand cards, 8 each                   |
| Shop row (x3)      | 24   | 3 shop slots, 8 each                         |
| Gravedig pool (x5) | 40   | 5 pool cards, 8 each                         |
| Dug cards (x10)    | 80   | Active char's dug cards, 8 each              |

Card encoding (8 floats):
  [exists, rank/10, is_ace, face_rank_norm, suit_clubs, suit_diamonds, suit_hearts, suit_spades]

Character meta (11 floats):
  [exists, is_dead, rank_J, rank_Q, rank_K, suit_clubs, suit_diamonds, suit_hearts, suit_spades, is_tapped, shield/10]
"""

import numpy as np
from shovels_engine.models import GameState, Suit, Card, Character

OBS_SIZE = 726

# Subphase encoding (one-hot over 8 values)
SUBPHASES = ["DRAW", "DISCARD", "PLAY", "BATTLE_ACTION", "SHOPPING", "SHOP_FREE_BUY", "SPADE_DIG", "GRAVEDIGGING"]
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


def encode_observation(state: GameState, player_id: str) -> np.ndarray:
    """Encode the full game state as a flat observation vector."""
    obs = np.zeros(OBS_SIZE, dtype=np.float32)
    idx = 0

    player = next(p for p in state.players if p.id == player_id)
    opponent = next(p for p in state.players if p.id != player_id)

    # ---- Game metadata (22 floats) ----
    # Phase (1 float): 0.0 for phase 1, 1.0 for phase 2
    obs[idx] = 1.0 if state.phase == 2 else 0.0
    idx += 1

    # Subphase one-hot (8 floats)
    sp_idx = SUBPHASE_MAP.get(state.turn_subphase, 0)
    obs[idx + sp_idx] = 1.0
    idx += 8

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

    assert idx == OBS_SIZE, f"Observation size mismatch: {idx} != {OBS_SIZE}"
    return obs
