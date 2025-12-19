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
