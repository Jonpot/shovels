"""
Shared action execution logic.

Used by both ShovelsEnv and PolicyAgent to dispatch decoded actions to engine functions.
"""

from shovels_engine.models import GameState
from shovels_engine.engine import (
    draw_cards, discard_card, play_card,
    perform_action, apply_face_strike,
    tap_hero_power, buy_card, refresh_shop,
    select_gravedig_card, finish_gravedig,
    end_turn, resolve_defense_reaction,
)


def execute_action(decoded: dict, state: GameState, player_id: str):
    """Execute a decoded action dict against the game state."""
    action_type = decoded["type"]

    if action_type == "draw":
        draw_cards(state, player_id, decoded["sources"])
    elif action_type == "discard":
        discard_card(state, player_id, decoded["card_index"])
    elif action_type == "play":
        play_card(state, player_id, decoded["card_index"], decoded["character_index"])
    elif action_type == "perform":
        perform_action(
            state, player_id,
            decoded["char_index"], decoded["top_n_cards"],
            decoded["action_suit"],
            dug_indices=decoded.get("dug_indices"),
            target_info=decoded.get("target_info"),
        )
    elif action_type == "strike":
        apply_face_strike(
            state, player_id,
            decoded["char_index"],
            decoded["target_player_id"],
            decoded["target_char_index"],
            discard_all_cards=decoded["discard_all_cards"],
        )
    elif action_type == "tap":
        tap_hero_power(
            state, player_id,
            decoded["char_index"],
            target_info=decoded.get("target_info"),
        )
    elif action_type == "buy":
        buy_card(
            state, player_id,
            decoded["slot_index"], decoded["char_index"],
        )
    elif action_type == "refresh":
        refresh_shop(state, player_id)
    elif action_type == "gravedig_select":
        aci = state.active_character_index
        if aci is not None:
            select_gravedig_card(state, player_id, aci, decoded["card_index"])
    elif action_type == "gravedig_end":
        finish_gravedig(state, player_id)
    elif action_type == "end_turn":
        end_turn(state)
    elif action_type == "react_tap":
        resolve_defense_reaction(state, player_id, tap=True)
    elif action_type == "react_pass":
        resolve_defense_reaction(state, player_id, tap=False)
