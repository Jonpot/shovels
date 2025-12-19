from shovels_engine.models import GameState, Suit, Card, Character, Player

def card_to_str(card: Card) -> str:
    if card.is_face:
        return f"[{card.face_rank}{card.suit.value[0]}]"
    rank_str = str(card.rank) if not card.is_ace else "A"
    return f"{rank_str}{card.suit.value[0]}"

def char_to_str(char: Character) -> str:
    face = f"{char.rank}{char.suit.value[0]}"
    stack_str = ", ".join(card_to_str(c) for c in char.stack)
    status = "TAPPED" if char.is_tapped else "READY"
    return f"[{face} | {stack_str}] ({status})"

def print_state(state: GameState):
    print("\n" + "="*50)
    print(f"TURN {state.turn_count} | PHASE {state.phase} | SUBPHASE: {state.turn_subphase}")
    print(f"Deck: {len(state.deck)} cards")
    if state.discard_pile:
        top_3 = state.discard_pile[-3:]
        discard_str = ", ".join(card_to_str(c) for c in reversed(top_3))
        print(f"Discard Pile ({len(state.discard_pile)} cards): [{discard_str}]")
    else:
        print("Discard Pile: EMPTY")
    print("="*50)

    print("\nSHOP ROW:")
    for i, c in enumerate(state.shop_row):
        card_str = card_to_str(c) if c else "EMPTY"
        print(f"  Slot {i}: {card_str}")

    print("\nPLAYERS:")
    for i, p in enumerate(state.players):
        active = ">> " if state.current_turn_index == i else "   "
        dead = " (DEAD)" if not p.is_alive else ""
        print(f"{active}Player {p.id} ({p.name}){dead}")
        print(f"     Coins: {p.coins}")
        hand_str = ", ".join(card_to_str(c) for c in p.hand)
        print(f"     Hand: [{hand_str}]")
        print(f"     Characters ({len(p.characters)}/{state.max_characters}):")
        for j, c in enumerate(p.characters):
            print(f"       {j}: {char_to_str(c)}")
    
    if state.dug_cards:
        dug_str = ", ".join(card_to_str(c) for c in state.dug_cards)
        print(f"\nDUG CARDS (RECURSIVE POOL): [{dug_str}]")

    if state.gravedig_pool:
        pool_str = ", ".join(card_to_str(c) for c in state.gravedig_pool)
        print(f"\nGRAVEDIG POOL: [{pool_str}]")
    
    print("="*50)

def print_banner(text: str):
    print("\n" + "#"*60)
    print(f"## {text.center(54)} ##")
    print("#"*60 + "\n")

def print_bot_summary(state: GameState, player_id: str):
    # Find events since the last TURN_START or the start of the list
    relevant_events = []
    # Find the last TURN_START for this specific bot
    start_idx = -1
    for i in range(len(state.events) - 1, -1, -1):
        e = state.events[i]
        if e['event_type'] == "TURN_START" and e['player_id'] == player_id:
            start_idx = i
            break
    
    if start_idx == -1:
        # Fallback to last 5 events
        relevant_events = [e for e in state.events[-5:] if e.get('player_id') == player_id]
    else:
        relevant_events = [e for e in state.events[start_idx:] if e.get('player_id') == player_id]
    
    if not relevant_events:
        return

    print(f"\n[BOT {player_id} ACTION SUMMARY]:")
    for e in relevant_events:
        etype = e['event_type']
        data = e['data']
        if etype == "TURN_START": continue # Skip the start log
        
        if etype == "DRAW":
            print(f"  - Drew {len(data['drawn'])} cards.")
        elif etype == "DISCARD_HAND":
            c = data['card']
            print(f"  - Discarded {c['rank']}{c['suit'][0]}.")
        elif etype == "PLAY_CARD":
            c = data['card']
            target = f"Character {data['character_index']}" if data['character_index'] is not None else "NEW SLOT"
            print(f"  - Played {c['rank'] if not c['is_face'] else c['face_rank']}{c['suit'][0]} to {target}.")
        elif etype == "ACTION":
            print(f"  - Performed {data['action_suit']} Action with rank {data['total_rank']}.")
        elif etype == "DIG_ACTION":
            print(f"  - Dug up {data['dig_count']} cards.")
        elif etype == "TAP_HERO":
            print(f"  - Tapped {data['rank']}{data['suit'][0]} Hero Power.")
        elif etype == "BUY_CARD":
            print(f"  - Bought {data['card']['rank'] if not data['card']['is_face'] else data['card']['face_rank']}{data['card']['suit'][0]} for {data['price']} coins.")
        elif etype == "CHARACTER_DEATH":
            print(f"  - Character Died: {data['rank']}{data['suit'][0]} (Reason: {data['reason']})")
        elif etype == "FACE_STRIKE":
            print(f"  - Face Struck Player {data['target_player_id']} Character {data['target_char_index']}.")
        elif etype == "PLAYER_DEAD":
            print(f"  - PLAYER ELIMINATED: {data['player_id']} (Reason: {data['reason']})")
        else:
            print(f"  - {etype}: {data}")
