"""
Action encoding/decoding and masking for the Shovels Gymnasium environment.

Flat Discrete(240) action space with boolean masking for MaskablePPO.

Action Encoding Table (240 total):
| Section | Actions | Indices   | Subphase            | Description                              |
|---------|---------|-----------|---------------------|------------------------------------------|
| A: Draw | 3       | 0-2       | DRAW                | [DECK,DECK],[DISCARD,DECK],[DISCARD,DISC]|
| B: Discard | 2    | 3-4       | DISCARD             | Discard hand[0] or hand[1]               |
| C: Play | 8       | 5-12      | PLAY                | hand[0..1] x char[0..2] + discard-face   |
| D: Perform | 180   | 13-192    | BATTLE_ACTION/DIG   | char(3)xtop_n(1..10)xsuit_target(6)      |
| E: Strike | 18     | 193-210   | BATTLE_ACTION/DIG   | char(3)xtarget_char(3)xdiscard_all(2)    |
| F: Tap Hero | 12   | 211-222   | BATTLE_ACTION       | non-clubs(3)+clubs char(3)xtarget(3)     |
| G: Shop Buy | 9    | 223-231   | SHOPPING/FREE_BUY   | slot(3)xchar(3)                          |
| H: Shop Refresh | 1| 232       | SHOPPING            | Refresh shop (2 coins)                   |
| I: Gravedig Sel | 5| 233-237   | GRAVEDIGGING        | Select pool card index 0-4               |
| J: Gravedig End | 1| 238       | GRAVEDIGGING        | Finish early                             |
| K: End Turn | 1    | 239       | Multiple            | End current turn/subphase                |
"""

import numpy as np
from shovels_engine.models import GameState, Suit, Card

ACTION_SPACE_SIZE = 240

# Section boundaries
DRAW_START = 0       # 3 actions: 0-2
DISCARD_START = 3    # 2 actions: 3-4
PLAY_START = 5       # 8 actions: 5-12
PERFORM_START = 13   # 180 actions: 13-192
STRIKE_START = 193   # 18 actions: 193-210
TAP_START = 211      # 12 actions: 211-222
BUY_START = 223      # 9 actions: 223-231
REFRESH_IDX = 232    # 1 action
GRAVEDIG_SEL_START = 233  # 5 actions: 233-237
GRAVEDIG_END_IDX = 238    # 1 action
END_TURN_IDX = 239        # 1 action

# Suit target encoding for Section D
SUIT_TARGETS = [Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES,
                Suit.CLUBS, Suit.CLUBS, Suit.CLUBS]
# Indices 0-2: non-clubs suits (target_info=None)
# Indices 3-5: clubs with target_char 0, 1, 2


def decode_action(action: int, state: GameState, player_id: str) -> dict:
    """Decode a flat action index into engine function call parameters.

    Returns a dict with:
      - 'type': one of 'draw', 'discard', 'play', 'perform', 'strike',
                'tap', 'buy', 'refresh', 'gravedig_select', 'gravedig_end', 'end_turn'
      - Additional keys depending on type.
    """
    player = next(p for p in state.players if p.id == player_id)
    opponent = next(p for p in state.players if p.id != player_id)

    if DRAW_START <= action <= 2:
        # Section A: Draw
        sources_map = {0: ["DECK", "DECK"], 1: ["DISCARD", "DECK"], 2: ["DISCARD", "DISCARD"]}
        return {"type": "draw", "sources": sources_map[action]}

    elif DISCARD_START <= action <= 4:
        # Section B: Discard
        return {"type": "discard", "card_index": action - DISCARD_START}

    elif PLAY_START <= action <= 12:
        # Section C: Play
        idx = action - PLAY_START
        if idx < 6:
            # hand[0..1] x char[0..2]
            hand_idx = idx // 3
            char_idx = idx % 3
            return {"type": "play", "card_index": hand_idx, "character_index": char_idx}
        elif idx == 6:
            # Discard 2nd face (hand[0], no character_index)
            return {"type": "play", "card_index": 0, "character_index": None}
        else:
            # Discard 2nd face (hand[1], no character_index)
            return {"type": "play", "card_index": 1, "character_index": None}

    elif PERFORM_START <= action <= 192:
        # Section D: Perform Action
        idx = action - PERFORM_START
        char_idx = idx // 60
        remainder = idx % 60
        top_n = (remainder // 6) + 1
        suit_target = remainder % 6

        suit = SUIT_TARGETS[suit_target]
        target_info = None
        if suit == Suit.CLUBS:
            opp_char_idx = suit_target - 3
            target_info = {"target_player_id": opponent.id, "target_char_index": opp_char_idx}

        # For SPADE_DIG: select dug_cards matching the suit
        dug_indices = None
        if state.turn_subphase == "SPADE_DIG" and state.active_character_index is not None:
            char = player.characters[state.active_character_index]
            char_idx = state.active_character_index
            dug_indices = [i for i, c in enumerate(char.dug_cards) if c.suit == suit]
            if suit == Suit.CLUBS and not dug_indices:
                # All dug cards for clubs action
                dug_indices = list(range(len(char.dug_cards)))
            top_n = 0  # Not used in dug mode

        return {
            "type": "perform",
            "char_index": char_idx,
            "top_n_cards": top_n,
            "action_suit": suit,
            "target_info": target_info,
            "dug_indices": dug_indices,
        }

    elif STRIKE_START <= action <= 210:
        # Section E: Face Strike
        idx = action - STRIKE_START
        char_idx = idx // 6
        remainder = idx % 6
        target_char_idx = remainder // 2
        discard_all = bool(remainder % 2)
        return {
            "type": "strike",
            "char_index": char_idx,
            "target_player_id": opponent.id,
            "target_char_index": target_char_idx,
            "discard_all_cards": discard_all,
        }

    elif TAP_START <= action <= 222:
        # Section F: Tap Hero Power
        idx = action - TAP_START
        if idx < 3:
            # Non-clubs tap: char[0..2]
            return {"type": "tap", "char_index": idx, "target_info": None}
        else:
            # Clubs tap: char(3) x primary_target(3)
            clubs_idx = idx - 3
            char_idx = clubs_idx // 3
            primary_target = clubs_idx % 3
            # Build target list based on character rank
            char = player.characters[char_idx] if char_idx < len(player.characters) else None
            num_strikes = {"J": 1, "Q": 2, "K": 3}.get(char.rank, 1) if char else 1
            targets = []
            # Primary target first
            living_opp = [i for i, c in enumerate(opponent.characters) if not c.is_dead]
            if primary_target in living_opp:
                targets.append({"target_player_id": opponent.id, "target_char_index": primary_target})
            # Fill remaining strikes by cycling through other living opponent chars
            for opp_idx in living_opp:
                if len(targets) >= num_strikes:
                    break
                if opp_idx != primary_target:
                    targets.append({"target_player_id": opponent.id, "target_char_index": opp_idx})
            return {"type": "tap", "char_index": char_idx, "target_info": {"targets": targets}}

    elif BUY_START <= action <= 231:
        # Section G: Shop Buy
        idx = action - BUY_START
        slot_idx = idx // 3
        char_idx = idx % 3
        return {"type": "buy", "slot_index": slot_idx, "char_index": char_idx}

    elif action == REFRESH_IDX:
        return {"type": "refresh"}

    elif GRAVEDIG_SEL_START <= action <= 237:
        return {"type": "gravedig_select", "card_index": action - GRAVEDIG_SEL_START}

    elif action == GRAVEDIG_END_IDX:
        return {"type": "gravedig_end"}

    elif action == END_TURN_IDX:
        return {"type": "end_turn"}

    raise ValueError(f"Invalid action index: {action}")


def action_masks(state: GameState, player_id: str) -> np.ndarray:
    """Compute boolean mask over all 240 actions. True = valid."""
    mask = np.zeros(ACTION_SPACE_SIZE, dtype=bool)

    player = next(p for p in state.players if p.id == player_id)
    opponent = next(p for p in state.players if p.id != player_id)

    if state.is_over:
        # No valid actions when game is over
        return mask

    subphase = state.turn_subphase

    # ---- Section A: Draw (Phase 1, DRAW subphase) ----
    if state.phase == 1 and subphase == "DRAW":
        deck_n = len(state.deck)
        discard_n = len(state.discard_pile)
        # 0: [DECK, DECK] - need 2 in deck
        if deck_n >= 2:
            mask[0] = True
        # 1: [DISCARD, DECK] - need 1 discard + 1 deck
        if discard_n >= 1 and deck_n >= 1:
            mask[1] = True
        # 2: [DISCARD, DISCARD] - need 2 in discard
        if discard_n >= 2:
            mask[2] = True

    # ---- Section B: Discard (Phase 1, DISCARD subphase) ----
    if state.phase == 1 and subphase == "DISCARD":
        for i in range(min(2, len(player.hand))):
            mask[DISCARD_START + i] = True

    # ---- Section C: Play (Phase 1, PLAY subphase) ----
    if state.phase == 1 and subphase == "PLAY":
        for hand_idx in range(min(2, len(player.hand))):
            card = player.hand[hand_idx]
            for char_idx in range(3):
                action_idx = PLAY_START + hand_idx * 3 + char_idx
                if not card.is_face:
                    # Number card: must go to existing character
                    if char_idx < len(player.characters):
                        mask[action_idx] = True
                else:
                    # Face card: can replace existing or create new (if under max)
                    if char_idx < len(player.characters):
                        mask[action_idx] = True
                    elif char_idx == len(player.characters) and char_idx < state.max_characters:
                        mask[action_idx] = True
            # Discard 2nd face option
            if player.can_discard_second_face and card.is_face:
                discard_idx = PLAY_START + 6 + hand_idx
                mask[discard_idx] = True

    # ---- Section D: Perform Action (Phase 2, BATTLE_ACTION or SPADE_DIG) ----
    if state.phase == 2 and subphase in ("BATTLE_ACTION", "SPADE_DIG"):
        if subphase == "SPADE_DIG":
            # In SPADE_DIG, only the active character can act, using dug_cards
            aci = state.active_character_index
            if aci is not None and aci < len(player.characters):
                char = player.characters[aci]
                if char.dug_cards:
                    dug_suits = {c.suit for c in char.dug_cards}
                    for suit_target_idx in range(6):
                        suit = SUIT_TARGETS[suit_target_idx]
                        if suit not in dug_suits:
                            continue
                        if suit == Suit.CLUBS:
                            opp_char_idx = suit_target_idx - 3
                            if opp_char_idx < len(opponent.characters) and not opponent.characters[opp_char_idx].is_dead:
                                # top_n=1 encodes the "use dug cards" action; actual top_n ignored for dug
                                mask[PERFORM_START + aci * 60 + 0 * 6 + suit_target_idx] = True
                        else:
                            mask[PERFORM_START + aci * 60 + 0 * 6 + suit_target_idx] = True
        else:
            # BATTLE_ACTION: normal perform from stack
            for char_idx in range(min(3, len(player.characters))):
                char = player.characters[char_idx]
                if char.is_dead or not char.stack:
                    continue
                # Recursive action constraint
                if state.active_character_index is not None and char_idx != state.active_character_index:
                    continue
                stack_len = len(char.stack)
                for top_n in range(1, min(11, stack_len + 1)):
                    top_cards = char.stack[-top_n:]
                    suits_in_top = {c.suit for c in top_cards}
                    for suit_target_idx in range(6):
                        suit = SUIT_TARGETS[suit_target_idx]
                        if suit not in suits_in_top:
                            continue
                        if suit == Suit.CLUBS:
                            opp_char_idx = suit_target_idx - 3
                            if opp_char_idx < len(opponent.characters) and not opponent.characters[opp_char_idx].is_dead:
                                mask[PERFORM_START + char_idx * 60 + (top_n - 1) * 6 + suit_target_idx] = True
                        else:
                            mask[PERFORM_START + char_idx * 60 + (top_n - 1) * 6 + suit_target_idx] = True

    # ---- Section E: Face Strike (Phase 2, BATTLE_ACTION or SPADE_DIG) ----
    if state.phase == 2 and subphase in ("BATTLE_ACTION", "SPADE_DIG"):
        for char_idx in range(min(3, len(player.characters))):
            char = player.characters[char_idx]
            if char.is_dead:
                continue
            # Recursive action constraint
            if state.active_character_index is not None and char_idx != state.active_character_index:
                continue

            is_dug = len(char.dug_cards) > 0
            is_exposed = len(char.stack) == 0

            for target_char_idx in range(min(3, len(opponent.characters))):
                if opponent.characters[target_char_idx].is_dead:
                    continue
                # discard_all=False: char must be exposed or digging
                if is_exposed or is_dug:
                    mask[STRIKE_START + char_idx * 6 + target_char_idx * 2 + 0] = True
                # discard_all=True: char must have cards on stack
                if len(char.stack) > 0:
                    mask[STRIKE_START + char_idx * 6 + target_char_idx * 2 + 1] = True

    # ---- Section F: Tap Hero Power (Phase 2, BATTLE_ACTION) ----
    if state.phase == 2 and subphase == "BATTLE_ACTION":
        for char_idx in range(min(3, len(player.characters))):
            char = player.characters[char_idx]
            if char.is_dead or char.is_tapped:
                continue
            if char.suit != Suit.CLUBS:
                # Non-clubs: simple tap
                mask[TAP_START + char_idx] = True
            else:
                # Clubs: need living targets
                living_opp = [i for i, c in enumerate(opponent.characters) if not c.is_dead]
                for primary_target in living_opp:
                    if primary_target < 3:
                        mask[TAP_START + 3 + char_idx * 3 + primary_target] = True

    # ---- Section G: Shop Buy (Phase 2, SHOPPING or SHOP_FREE_BUY) ----
    if state.phase == 2 and subphase in ("SHOPPING", "SHOP_FREE_BUY"):
        for slot_idx in range(min(3, len(state.shop_row))):
            card = state.shop_row[slot_idx]
            if card is None:
                continue
            effective_free = state.free_buys_remaining > 0
            price = 0 if effective_free else card.price
            if player.coins < price:
                continue
            for char_idx in range(min(3, len(player.characters))):
                char = player.characters[char_idx]
                if not card.is_face:
                    # Number card: can't add to dead character
                    if not char.is_dead:
                        mask[BUY_START + slot_idx * 3 + char_idx] = True
                else:
                    # Face card: upgrade rules
                    rank_values = {"J": 1, "Q": 2, "K": 3}
                    card_val = rank_values.get(card.face_rank, 0)
                    if char.is_dead:
                        # Only Jack revives
                        if card.face_rank == "J":
                            mask[BUY_START + slot_idx * 3 + char_idx] = True
                    else:
                        char_val = rank_values.get(char.rank, 0)
                        if card_val > char_val:
                            mask[BUY_START + slot_idx * 3 + char_idx] = True
                        elif effective_free:
                            # Free buys allow invalid upgrades (card gets discarded)
                            mask[BUY_START + slot_idx * 3 + char_idx] = True

    # ---- Section H: Shop Refresh ----
    if state.phase == 2 and subphase == "SHOPPING":
        if player.coins >= 2:
            mask[REFRESH_IDX] = True

    # ---- Section I: Gravedig Select ----
    if state.phase == 2 and subphase == "GRAVEDIGGING":
        aci = state.active_character_index
        if aci is not None and aci < len(player.characters):
            char = player.characters[aci]
            num_keep = {"J": 1, "Q": 2, "K": 3}.get(char.rank, 1)
            cards_taken = state.gravedig_cards_taken
            if cards_taken < num_keep:
                for i in range(min(5, len(state.gravedig_pool))):
                    card = state.gravedig_pool[i]
                    if _can_take_gravedig(card, char):
                        mask[GRAVEDIG_SEL_START + i] = True

    # ---- Section J: Gravedig Finish ----
    if state.phase == 2 and subphase == "GRAVEDIGGING":
        mask[GRAVEDIG_END_IDX] = True

    # ---- Section K: End Turn ----
    if state.phase == 2 and subphase in ("BATTLE_ACTION", "SHOPPING", "SHOP_FREE_BUY", "SPADE_DIG"):
        mask[END_TURN_IDX] = True
    # Phase 1: can't voluntarily end turn (actions are mandatory per subphase)

    # Ensure at least one action is valid (fallback to end_turn)
    if not mask.any():
        mask[END_TURN_IDX] = True

    return mask


def _can_take_gravedig(card: Card, char) -> bool:
    """Check if a gravedig pool card can be taken by this character."""
    if not card.is_face:
        return True
    if card.face_rank == "J":
        return False
    rank_values = {"J": 1, "Q": 2, "K": 3}
    card_val = rank_values.get(card.face_rank, 0)
    char_val = rank_values.get(char.rank, 0)
    return card_val > char_val
