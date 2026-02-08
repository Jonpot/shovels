"""
Game playback log formatter.

Converts engine event logs into human-readable game replays.
"""

import os
from io import StringIO
from shovels_engine.models import GameState, Suit


def _card_str(card_data: dict) -> str:
    """Format a card dict from model_dump() into a short string."""
    if card_data.get("is_face"):
        return f"{card_data['face_rank']}{card_data['suit'][0]}"
    rank = "A" if card_data.get("is_ace") else str(card_data["rank"])
    return f"{rank}{card_data['suit'][0]}"


def _char_summary(char) -> str:
    """One-line character summary."""
    if char.is_dead:
        return "(DEAD)"
    face = f"{char.rank}{char.suit.value[0]}"
    stack_cards = ", ".join(
        f"{'A' if c.is_ace else c.rank}{c.suit.value[0]}" if not c.is_face
        else f"{c.face_rank}{c.suit.value[0]}"
        for c in char.stack
    )
    tapped = " TAPPED" if char.is_tapped else ""
    shield = f" +{char.temporary_shield}sh" if char.temporary_shield else ""
    return f"{face}[{stack_cards}]{tapped}{shield}"


def _board_snapshot(state: GameState) -> str:
    """Compact board state snapshot."""
    lines = []
    for p in state.players:
        alive = "" if p.is_alive else " DEAD"
        chars = " | ".join(_char_summary(c) for c in p.characters)
        coins_str = f" ${p.coins}" if p.coins else ""
        lines.append(f"  {p.id}{alive}{coins_str}: {chars}")

    shop_cards = []
    for i, c in enumerate(state.shop_row):
        if c:
            r = "A" if c.is_ace else (c.face_rank if c.is_face else str(c.rank))
            shop_cards.append(f"{r}{c.suit.value[0]}")
        else:
            shop_cards.append("--")
    lines.append(f"  Shop: [{', '.join(shop_cards)}]  Deck: {len(state.deck)}")
    return "\n".join(lines)


def format_game_log(state: GameState) -> str:
    """Format a completed game's event log into a readable replay."""
    out = StringIO()

    out.write("=" * 60 + "\n")
    winner = state.winner_id or "NONE"
    out.write(f"GAME REPLAY  |  Winner: {winner}  |  Turns: {state.turn_count}\n")
    out.write("=" * 60 + "\n\n")

    # Show final board state (initial setup is visible through Phase 1 plays)
    out.write("--- FINAL BOARD STATE ---\n")
    out.write(_board_snapshot(state))
    out.write("\n\n")

    current_turn = -1
    current_phase = 0

    for event in state.events:
        etype = event["event_type"]
        pid = event["player_id"]
        turn = event["turn_count"]
        phase = event["phase"]
        subphase = event["subphase"]
        data = event["data"]

        # Phase transition
        if phase != current_phase:
            current_phase = phase
            if etype == "PHASE_TRANSITION":
                out.write(f"\n{'#' * 60}\n")
                out.write(f"### PHASE 2 BEGINS  |  First player: {data['first_player_id']}\n")
                out.write(f"{'#' * 60}\n")
                board = data.get("board")
                if board:
                    out.write("\n")
                    for pid_key, chars in board.items():
                        char_strs = []
                        for c in chars:
                            if c["is_dead"]:
                                char_strs.append("(DEAD)")
                                continue
                            face = f"{c['rank']}{c['suit'][0]}"
                            stack = ", ".join(
                                _card_str(card) for card in c["stack"]
                            )
                            tapped = " TAPPED" if c["is_tapped"] else ""
                            char_strs.append(f"{face}[{stack}]{tapped}")
                        out.write(f"  {pid_key}: {' | '.join(char_strs)}\n")
                out.write("\n")
                continue

        # Turn header
        if turn != current_turn:
            current_turn = turn
            out.write(f"\n--- Turn {turn} | Phase {phase} | {pid}'s turn ---\n")

        # Format events
        if etype == "TURN_START":
            continue  # Redundant with turn header

        elif etype == "DRAW":
            sources = data["sources"]
            drawn = [_card_str(c) for c in data["drawn"]]
            out.write(f"  [{pid}] Draw: {', '.join(drawn)} (from {', '.join(sources)})\n")

        elif etype == "DISCARD_HAND":
            out.write(f"  [{pid}] Discard: {_card_str(data['card'])}\n")

        elif etype == "PLAY_CARD":
            card = data["card"]
            card_s = _card_str(card)
            ci = data["character_index"]
            if ci is not None:
                out.write(f"  [{pid}] Play {card_s} -> Character {ci}\n")
            else:
                out.write(f"  [{pid}] Discard 2nd face: {card_s}\n")

        elif etype == "ACTION":
            suit = str(data["action_suit"]).replace("Suit.", "")
            rank = data["total_rank"]
            ci = data.get("char_index", "?")
            recursive = " (recursive)" if data.get("is_recursive") else ""
            cards = data.get("cards", [])
            cards_str = ", ".join(_card_str(c) for c in cards) if cards else ""
            target = data.get("target_info")
            target_str = ""
            if target:
                target_str = f" -> {target['target_player_id']} char {target['target_char_index']}"
            out.write(f"  [{pid}] Action: char {ci} plays [{cards_str}] {suit} rank={rank}{target_str}{recursive}\n")

        elif etype == "DIG_ACTION":
            count = data["dig_count"]
            out.write(f"  [{pid}] Dig: {count} cards flagged\n")

        elif etype == "TAP_HERO":
            out.write(f"  [{pid}] Tap Hero: {data['rank']}{data['suit'][0]}\n")

        elif etype == "FACE_STRIKE":
            tp = data["target_player_id"]
            tc = data["target_char_index"]
            out.write(f"  [{pid}] Face Strike -> {tp} char {tc}\n")

        elif etype == "BUY_CARD":
            card_s = _card_str(data["card"])
            price = data["price"]
            ci = data["char_index"]
            cost_str = f"${price}" if price > 0 else "FREE"
            out.write(f"  [{pid}] Buy {card_s} ({cost_str}) -> char {ci}\n")

        elif etype == "HEART_BROKEN":
            tp = data["target_player_id"]
            tc = data["target_char_index"]
            dmg = data["damage"]
            hr = data.get("heart_rank", "?")
            sh = data.get("shield", 0)
            out.write(f"  Heart broken: {hr}H on {tp} char {tc} (dmg={dmg} >= rank={hr}+shield={sh})\n")

        elif etype == "CHARACTER_DEATH":
            dp = data["player_id"]
            dc = data["character_index"]
            rank = data.get("rank", "?")
            suit = data.get("suit", "?")
            reason = data["reason"]
            suit_c = suit[0] if isinstance(suit, str) and len(suit) > 0 else "?"
            out.write(f"  ** {dp} char {dc} ({rank}{suit_c}) DIES: {reason} **\n")

        elif etype == "PLAYER_DEAD":
            dp = data["player_id"]
            reason = data["reason"]
            out.write(f"  *** PLAYER {dp} ELIMINATED ({reason}) ***\n")

        elif etype == "GAME_OVER":
            out.write(f"\n{'=' * 60}\n")
            out.write(f"GAME OVER  |  Winner: {data['winner_id']}\n")
            out.write(f"{'=' * 60}\n")

        elif etype == "SHOPPING_END":
            coins = data.get("coins_remaining", 0)
            out.write(f"  [{pid}] Shopping ends (${coins} unspent)\n")

        elif etype == "GRAVEDIG_SELECT":
            card_s = _card_str(data["card"])
            taken = data["cards_taken"]
            limit = data["limit"]
            out.write(f"  [{pid}] Gravedig take: {card_s} ({taken}/{limit})\n")

        elif etype == "GRAVEDIG_UPGRADE":
            old = data.get("old_rank", "?")
            new = data.get("new_rank", "?")
            out.write(f"  [{pid}] Gravedig upgrade: {old} -> {new}\n")

        elif etype == "GRAVEDIG_SKIP":
            out.write(f"  [{pid}] Gravedig skipped: {data.get('reason', '')}\n")

        else:
            out.write(f"  [{pid}] {etype}: {data}\n")

    return out.getvalue()


def save_game_log(state: GameState, filepath: str):
    """Format and write a game replay log to file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    log = format_game_log(state)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(log)
