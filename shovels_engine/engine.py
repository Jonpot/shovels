from typing import List, Optional, Tuple, Dict
from .models import GameState, Card, Character, Player, Suit
import collections
import random

def log_event(state: GameState, event_type: str, data: Dict):
    """Logs an event to the game state history."""
    # Safety check for players list
    if not state.players:
        return
        
    p = state.players[state.current_turn_index]
    event = {
        "event_type": event_type,
        "player_id": p.id,
        "turn_count": state.turn_count,
        "phase": state.phase,
        "subphase": state.turn_subphase,
        "data": data
    }
    state.events.append(event)

def get_current_player(state: GameState) -> Player:
    return state.players[state.current_turn_index]

def draw_cards(state: GameState, player_id: str, sources: List[str]):
    """
    Phase 1: Draw 2 cards.
    sources: List of "DECK" or "DISCARD" of length 2.
    Constraint: If drawing from both deck and discard, the discard card must be drawn first.
    """
    if state.turn_subphase != "DRAW":
        raise ValueError("Must be in DRAW subphase")
    
    if len(sources) != 2:
        raise ValueError("Must draw exactly 2 cards")
    
    # Enforce constraint: If sources are ["DECK", "DISCARD"], it's invalid.
    if sources == ["DECK", "DISCARD"]:
        raise ValueError("If drawing from both deck and discard, the discard card must be drawn first.")

    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    # Reset flag at start of draw
    player.can_discard_second_face = False
    drawn_cards = []
    
    for source in sources:
        if source == "DISCARD":
            if not state.discard_pile:
                raise ValueError("Discard pile is empty")
            card = state.discard_pile.pop()
        elif source == "DECK":
            if not state.deck:
                raise ValueError("Deck is empty. Players must draw from discard pile if possible.")
            card = state.deck.pop()
        else:
            raise ValueError(f"Invalid source: {source}")
        
        player.hand.append(card)
        drawn_cards.append(card)
    
    # Flag is true iff both drawn cards are face cards
    if all(c.is_face for c in drawn_cards):
        player.can_discard_second_face = True
        
    state.turn_subphase = "DISCARD"
    log_event(state, "DRAW", {"sources": sources, "drawn": [c.model_dump() for c in drawn_cards]})

def discard_card(state: GameState, player_id: str, card_index: int):
    """
    Phase 1: Discard 1.
    """
    if state.turn_subphase != "DISCARD":
        raise ValueError("Must be in DISCARD subphase")
        
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    if card_index >= len(player.hand):
        raise ValueError("Invalid card index")
    
    card = player.hand.pop(card_index)
    state.discard_pile.append(card)
    
    state.turn_subphase = "PLAY"
    log_event(state, "DISCARD_HAND", {"card": card.model_dump()})

def play_card(state: GameState, player_id: str, card_index: int, character_index: Optional[int] = None):
    """
    Phase 1: Play the remaining card.
    - Number card -> Character stack.
    - Face card -> Replace character (reset is_tapped) OR create new character (if under max).
    - If character_index is None and player.can_discard_second_face is True, discard the second face card.
    """
    if state.turn_subphase != "PLAY":
        raise ValueError("Must be in PLAY subphase")
        
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    if card_index >= len(player.hand):
        raise ValueError("Invalid card index")
    
    card = player.hand[card_index] # Peek
    
    # Handle discarding second face card
    if character_index is None:
        if player.can_discard_second_face and card.is_face:
            # Valid: discard the second face card
            player.hand.pop(card_index)
            state.discard_pile.append(card)
            end_turn(state)
            return
        else:
            raise ValueError("Character index required for playing cards in Phase 1 (unless discarding a second face card)")

    # Play logic
    player.hand.pop(card_index)
    log_event(state, "PLAY_CARD", {"card": card.model_dump(), "character_index": character_index})
    
    if not card.is_face:
        if character_index >= len(player.characters):
            raise ValueError("Cannot create new character with a number card")
        player.characters[character_index].stack.append(card)
    else:
        # Replacement or New Character
        if character_index < len(player.characters):
            # Replace existing
            old_char = player.characters[character_index]
            old_face = Card(rank=0, suit=old_char.suit, is_face=True, face_rank=old_char.rank)
            state.discard_pile.append(old_face)
            player.characters[character_index].rank = card.face_rank
            player.characters[character_index].suit = card.suit
            player.characters[character_index].is_tapped = False
        elif character_index == len(player.characters) and character_index < state.max_characters:
            # Create new character
            new_char = Character(rank=card.face_rank, suit=card.suit, stack=[])
            player.characters.append(new_char)
        else:
            raise ValueError(f"Invalid character index or too many characters (max {state.max_characters})")
    
    end_turn(state)

def buy_card(state: GameState, player_id: str, slot_index: int, char_index: int, is_free: bool = False):
    """
    Phase 2/SHOPPING: Buy a card from the shop.
    """
    if state.phase != 2:
        raise ValueError("Must be in Phase 2")
    
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    if state.turn_subphase not in ["SHOPPING", "SHOP_FREE_BUY"]:
        raise ValueError(f"Cannot buy card in {state.turn_subphase} subphase")
        
    if slot_index >= len(state.shop_row) or state.shop_row[slot_index] is None:
        raise ValueError("Invalid shop slot")
    
    card = state.shop_row[slot_index]
    
    # Calculate effective price
    effective_is_free = is_free or state.free_buys_remaining > 0
    price = 0 if effective_is_free else card.price
        
    if player.coins < price:
        raise ValueError("Not enough coins")
    
    # Enforce upgrade rules
    char = player.characters[char_index]
    if card.is_face:
        # Face upgrade: J < Q < K
        rank_values = {"J": 1, "Q": 2, "K": 3}
        if rank_values[card.face_rank] <= rank_values[char.rank]:
            if effective_is_free:
                # Discard invalid free buy
                state.discard_pile.append(card)
                state.shop_row[slot_index] = None
                if state.free_buys_remaining > 0:
                    state.free_buys_remaining -= 1
                return
            else:
                raise ValueError(f"Cannot upgrade {char.rank} with {card.face_rank}")
        
        # Replace face
        old_face = Card(rank=0, suit=char.suit, is_face=True, face_rank=char.rank)
        state.discard_pile.append(old_face)
        char.rank = card.face_rank
        char.suit = card.suit
        char.is_tapped = False
    else:
        # Number card to stack
        char.stack.append(card)
        
    player.coins -= price
    if state.free_buys_remaining > 0:
        state.free_buys_remaining -= 1
        
    # Mark slot as empty (refilled at end of turn or refresh)
    state.shop_row[slot_index] = None
    log_event(state, "BUY_CARD", {"card": card.model_dump(), "slot_index": slot_index, "char_index": char_index, "price": price})

def refresh_shop(state: GameState, player_id: str):
    """
    Phase 2: Spend 2 coins to refresh the shop.
    Wipe row and refill.
    """
    if state.phase != 2:
        raise ValueError("Must be in Phase 2")
    
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    if player.coins < 2:
        raise ValueError("Not enough coins to refresh shop")
    
    player.coins -= 2
    
    # Wipe current row
    for card in state.shop_row:
        if card:
            state.discard_pile.append(card)
    
    state.shop_row = [None, None, None]
    refill_shop_row(state)

def refill_shop_row(state: GameState):
    """Internal helper to fill empty shop slots."""
    for i in range(len(state.shop_row)):
        if state.shop_row[i] is None:
            if not state.shop_pile and state.discard_pile:
                # Refill shop pile from discard
                state.shop_pile = state.discard_pile[:]
                state.discard_pile = []
                random.shuffle(state.shop_pile)
            
            if state.shop_pile:
                state.shop_row[i] = state.shop_pile.pop()

def tap_hero_power(state: GameState, player_id: str, char_index: int, target_info: Optional[Dict] = None):
    """
    Phase 2: Use a character's specialized power.
    """
    if state.phase != 2:
        raise ValueError("Must be in Phase 2")
    
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    # Heart Reactor (Out-of-turn)
    is_turn = get_current_player(state).id == player_id
    char = player.characters[char_index]
    
    if not is_turn and char.suit != Suit.HEARTS:
        raise ValueError("Can only use Heart powers out-of-turn")
    
    if char.is_tapped:
        raise ValueError("Character already tapped")
    
    char.is_tapped = True
    state.character_tapped_this_turn = True
    log_event(state, "TAP_HERO", {"char_index": char_index, "suit": char.suit, "rank": char.rank})
    
    if char.suit == Suit.CLUBS:
        if not target_info:
            raise ValueError("Target info required for Clubs power")
        targets = target_info.get('targets', []) # List of {'target_player_id': ..., 'target_char_index': ...}
        
        num_strikes = {"J": 1, "Q": 2, "K": 3}[char.rank]
        if len(targets) > num_strikes:
            raise ValueError(f"{char.rank} of Clubs can only hit {num_strikes} targets")
            
        # Group targets by player and process them in descending order of character index
        # to prevent index-shifting bugs.
        from collections import defaultdict
        player_targets = defaultdict(list)
        for t in targets:
            player_targets[t['target_player_id']].append(t['target_char_index'])
            
        for target_p_id, char_indices in player_targets.items():
            # Process each unique slot in descending order to prevent shifting other slots
            unique_slots = sorted(list(set(char_indices)), reverse=True)
            for slot_idx in unique_slots:
                hits = char_indices.count(slot_idx)
                for _ in range(hits):
                    # Re-check existence before each hit on this slot
                    target_p = next(p for p in state.players if p.id == target_p_id)
                    if slot_idx < len(target_p.characters):
                        attack_heart(state, player_id, target_p_id, slot_idx, 10)
                    else:
                        break # Slot already removed
    
    elif char.suit == Suit.DIAMONDS:
        # Free purchases: Set counter and transition to subphase
        num_free = {"J": 1, "Q": 2, "K": 3}[char.rank]
        state.free_buys_remaining = num_free
        state.turn_subphase = "SHOP_FREE_BUY"
        return # subphase remains
        
    elif char.suit == Suit.SPADES:
        # Gravedig: Transition to subphase and deal 5 cards to pool
        # Shuffle discard pile
        temp_deck = state.discard_pile[:]
        state.discard_pile = []
        random.shuffle(temp_deck)
        
        # Deal up to 5 cards to gravedig pool
        state.gravedig_pool = []
        for _ in range(min(5, len(temp_deck))):
            state.gravedig_pool.append(temp_deck.pop())
        
        # Remaining discard pile
        state.discard_pile.extend(temp_deck)
        state.turn_subphase = "GRAVEDIGGING"
        state.active_character_index = char_index
        return # subphase remains
        
    elif char.suit == Suit.HEARTS:
        shield_values = {"J": 3, "Q": 5, "K": 10}
        char.shield += shield_values[char.rank]
    
    if is_turn and not state.dug_cards and state.turn_subphase not in ["SHOPPING", "SHOP_FREE_BUY", "GRAVEDIGGING"]:
        end_turn(state)

def resolve_gravedig(state: GameState, player_id: str, char_index: int, indices: List[int]):
    """
    Complete the Spades power: choose indices from gravedig_pool to keep.
    """
    if state.turn_subphase != "GRAVEDIGGING":
        raise ValueError("Must be in GRAVEDIGGING subphase")
    
    player = next((p for p in state.players if p.id == player_id), None)
    char = player.characters[char_index]
    
    num_keep = {"J": 1, "Q": 2, "K": 3}[char.rank]
    if len(indices) > num_keep:
        raise ValueError(f"{char.rank} of Spades can only keep {num_keep} cards")
        
    # Keep selected indices
    # We must sort reverse to avoid shifting indices while popping
    for idx in sorted(indices, reverse=True):
        if idx < len(state.gravedig_pool):
            char.stack.append(state.gravedig_pool.pop(idx))
            
    # Return rest to discard
    state.discard_pile.extend(state.gravedig_pool)
    state.gravedig_pool = []
    
    state.turn_subphase = "BATTLE_ACTION"
    if not state.dug_cards:
        end_turn(state)

def perform_action(state: GameState, player_id: str, char_index: Optional[int], top_n_cards: int, action_suit: Suit, dug_indices: Optional[List[int]] = None, target_info: Optional[Dict] = None):
    """
    Phase 2: Perform an action.
    """
    if state.phase != 2:
        raise ValueError("Must be in Phase 2")
    
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    if get_current_player(state).id != player_id:
        raise ValueError("Not your turn")
        
    if state.turn_subphase != "BATTLE_ACTION":
        raise ValueError(f"Cannot perform action in {state.turn_subphase} subphase")

    # Restriction: If in a sub-turn (digging), must use the same character
    if state.active_character_index is not None:
        if char_index is not None and char_index != state.active_character_index:
            raise ValueError("Recursive actions must use the same character")
        char_index = state.active_character_index

    action_cards = []
    
    if dug_indices is not None:
        # Use from dug pool
        for idx in sorted(dug_indices, reverse=True):
            action_cards.append(state.dug_cards.pop(idx))
    else:
        # Use from character stack
        if char_index is None:
            raise ValueError("char_index required")
        char = player.characters[char_index]
        for _ in range(top_n_cards):
            c = char.stack.pop()
            action_cards.append(c)
            state.discard_pile.append(c)
            state.cards_removed_this_turn = True

    suits_present = {c.suit for c in action_cards}
    if action_suit not in suits_present:
        raise ValueError(f"Suit {action_suit} not present")

    total_rank = sum(10 if c.is_ace else c.rank for c in action_cards if c.suit == action_suit)
    state.action_taken_this_turn = True
    state.active_character_index = char_index # Set this as the active character for this turn
    
    log_event(state, "ACTION", {
        "action_suit": action_suit, 
        "total_rank": total_rank, 
        "top_n_cards": top_n_cards,
        "is_recursive": len(dug_indices) > 0 if dug_indices else False
    })
    resolve_suit_effect(state, player_id, char_index, action_suit, total_rank, target_info)
    
    if not state.dug_cards and state.turn_subphase not in ["SHOPPING", "SHOP_FREE_BUY", "GRAVEDIGGING"]:
        end_turn(state)

def resolve_suit_effect(state: GameState, player_id: str, char_index: Optional[int], suit: Suit, total_rank: int, target_info: Optional[Dict] = None):
    if suit == Suit.CLUBS:
        if not target_info:
            raise ValueError("Target info required for Clubs")
        attack_heart(state, player_id, target_info['target_player_id'], target_info['target_char_index'], total_rank)
    elif suit == Suit.DIAMONDS:
        player = next(p for p in state.players if p.id == player_id)
        player.coins += total_rank
        state.turn_subphase = "SHOPPING"
        return # Don't end turn, stay in shopping
    elif suit == Suit.HEARTS:
        pass
    elif suit == Suit.SPADES:
        if char_index is None:
            raise ValueError("Spade actions require character context")
        char = next(p for p in state.players if p.id == player_id).characters[char_index]
        dig_count = min(total_rank, len(char.stack))
        dug = []
        for _ in range(dig_count):
            card = char.stack.pop()
            state.dug_cards.append(card)
            dug.append(card)
            state.cards_removed_this_turn = True
        log_event(state, "DIG_ACTION", {"dig_count": dig_count, "dug_cards": [c.model_dump() for c in dug]})
        return # Recursion

def apply_face_strike(state: GameState, player_id: str, char_index: int, target_player_id: str, target_char_index: int):
    if state.phase != 2:
        raise ValueError("Must be in Phase 2")
        
    if state.turn_subphase != "BATTLE_ACTION":
        raise ValueError(f"Cannot strike in {state.turn_subphase} subphase")
    
    player = next(p for p in state.players if p.id == player_id)
    
    # Consistency check
    if state.active_character_index is not None and char_index != state.active_character_index:
        raise ValueError("Recursive actions must use the same character")
    
    char = player.characters[char_index]
    
    is_dug = len(state.dug_cards) > 0
    if len(char.stack) > 0 and not is_dug:
        raise ValueError("Character must be exposed to strike (unless digging)")
    
    target_player = next(p for p in state.players if p.id == target_player_id)
    target_char = target_player.characters[target_char_index]
    
    log_event(state, "FACE_STRIKE", {"target_player_id": target_player_id, "target_char_index": target_char_index})
    
    removed = False
    if not target_char.stack:
        log_event(state, "CHARACTER_DEATH", {
            "player_id": target_player_id, 
            "character_index": target_char_index, 
            "reason": "STRIKE",
            "rank": target_char.rank,
            "suit": target_char.suit
        })
        target_player.characters.pop(target_char_index)
        state.cards_removed_this_turn = True
        removed = True
        if not target_player.characters:
            target_player.is_alive = False
            log_event(state, "PLAYER_DEAD", {"player_id": target_player_id, "reason": "STRIKE"})
    else:
        # Heart protection or other logic
        pass

    state.action_taken_this_turn = True
    state.active_character_index = char_index
    
    if not removed and not state.cards_removed_this_turn and not state.character_tapped_this_turn:
        log_event(state, "CHARACTER_DEATH", {
            "player_id": player_id, 
            "character_index": char_index, 
            "reason": "SUICIDE_STRIKE",
            "rank": char.rank,
            "suit": char.suit
        })
        player.characters.pop(char_index)
        state.cards_removed_this_turn = True
        if not player.characters:
            player.is_alive = False
            log_event(state, "PLAYER_DEAD", {"player_id": player_id, "reason": "SUICIDE_STRIKE"})

    if not state.dug_cards:
        end_turn(state)

def attack_heart(state: GameState, player_id: str, target_player_id: str, target_char_index: int, damage: int):
    target_player = next(p for p in state.players if p.id == target_player_id)
    target_char = target_player.characters[target_char_index]
    
    if not target_char.stack:
        if damage >= 1:
            log_event(state, "CHARACTER_DEATH", {
                "player_id": target_player_id, 
                "character_index": target_char_index, 
                "reason": "HEART_OVERWHELM",
                "rank": target_char.rank,
                "suit": target_char.suit
            })
            target_player.characters.pop(target_char_index)
            state.cards_removed_this_turn = True
            if not target_player.characters:
                target_player.is_alive = False
                log_event(state, "PLAYER_DEAD", {"player_id": target_player_id, "reason": "HEART_OVERWHELM"})
        return

    for i in range(len(target_char.stack) - 1, -1, -1):
        card = target_char.stack[i]
        if card.suit == Suit.HEARTS:
            if damage >= (card.rank + target_char.shield):
                num_to_remove = len(target_char.stack) - i
                for _ in range(num_to_remove):
                    state.discard_pile.append(target_char.stack.pop())
                state.cards_removed_this_turn = True
                log_event(state, "HEART_BROKEN", {"target_player_id": target_player_id, "target_char_index": target_char_index, "damage": damage, "shield": target_char.shield})
                break

def end_turn(state: GameState):
    player = get_current_player(state)
    
    # Reset subphase and handle post-turn fatigue
    if state.turn_subphase in ["SHOPPING", "SHOP_FREE_BUY"]:
        log_event(state, "SHOPPING_END", {"coins_remaining": player.coins})
    elif state.turn_subphase == "GRAVEDIGGING":
        log_event(state, "GRAVEDIGGING_END", {})

    if state.phase == 2 and not state.is_over:
        if not (state.action_taken_this_turn or state.cards_removed_this_turn or state.character_tapped_this_turn):
            apply_fatigue(state, player.id, end_turn_after=False)
            if state.is_over:
                return

    player.can_discard_second_face = False
    player.coins = 0
    state.action_taken_this_turn = False
    state.cards_removed_this_turn = False
    state.character_tapped_this_turn = False
    state.dug_cards = []
    state.active_character_index = None
    state.gravedig_pool = []
    state.free_buys_remaining = 0
    
    # Refill Shop Row at end of turn
    refill_shop_row(state)
    
    check_win_condition(state)
    if state.is_over:
        return
    
    state.turn_count += 1
    
    # Advance to next living player
    num_players = len(state.players)
    for _ in range(num_players):
        state.current_turn_index = (state.current_turn_index + 1) % num_players
        if state.players[state.current_turn_index].is_alive:
            break
            
    state.turn_subphase = "DRAW" if state.phase == 1 else "BATTLE_ACTION"
    
    if state.phase == 1 and not state.deck:
        if state.turn_count % len(state.players) == 0:
            transition_to_phase_2(state)
    
    # Re-check win condition after transition (rare edge case)
    check_win_condition(state)
    if state.is_over:
        return

    # Log turn start BEFORE fatigue check so fatigue outcomes are associated with the new turn
    log_event(state, "TURN_START", {"player_id": state.players[state.current_turn_index].id, "subphase": state.turn_subphase})

    # Phase 2 Start-of-turn Fatigue Check
    if state.phase == 2:
        next_player = state.players[state.current_turn_index]
        if not can_player_act(state, next_player.id):
            apply_fatigue(state, next_player.id, end_turn_after=True)
            return
    
def check_win_condition(state: GameState):
    """Detects when only one player (or one player's team) remains."""
    if state.is_over:
        return
        
    alive_players = [p for p in state.players if p.is_alive]
    if len(alive_players) <= 1:
        state.is_over = True
        if len(alive_players) == 1:
            state.winner_id = alive_players[0].id
            log_event(state, "GAME_OVER", {"winner_id": state.winner_id})
        else:
            state.winner_id = "DRAW"
            log_event(state, "GAME_OVER", {"winner_id": "DRAW"})

def can_player_act(state: GameState, player_id: str) -> bool:
    """Every turn you must either discard a card, tap a hero power, or face-strike."""
    player = next((p for p in state.players if p.id == player_id), None)
    if not player or not player.is_alive or not player.characters:
        return False
    
    for char in player.characters:
        # Can discard? (Has any cards in stack)
        if char.stack:
            return True
        # Can tap hero power?
        if not char.is_tapped:
            return True
        # Can face-strike that kills?
        # A face card can strike if it has NO cards on top.
        # It must kill at least one opposing card.
        if not char.stack:
            for other_player in state.players:
                if other_player.id == player_id or not other_player.is_alive:
                    continue
                for other_char_idx, other_char in enumerate(other_player.characters):
                    # If target is an exposed face (no cards on top), it's a legal strike target.
                    # It will either die or be forced to tap for shield.
                    if not other_char.stack:
                        return True
                    
                    # If it has hearts, check if 1 damage would kill it.
                    top_card = other_char.stack[-1]
                    if top_card.suit == Suit.HEARTS and (1 >= (top_card.rank + other_char.shield)):
                        return True
                        
    return False

def apply_fatigue(state: GameState, player_id: str, end_turn_after: bool = False):
    """Discard one of your own face cards — that character dies."""
    player = next((p for p in state.players if p.id == player_id), None)
    if not player or not player.is_alive:
        return
        
    if player.characters:
        char_idx = len(player.characters) - 1
        dead_char = player.characters.pop()
        log_event(state, "CHARACTER_DEATH", {
            "player_id": player_id, 
            "character_index": char_idx, 
            "reason": "FATIGUE", 
            "rank": dead_char.rank, 
            "suit": dead_char.suit
        })
        if not player.characters:
            player.is_alive = False
            log_event(state, "PLAYER_DEAD", {"player_id": player_id, "reason": "FATIGUE"})
    
    # After fatigue, check win condition
    check_win_condition(state)
    
    if not state.is_over:
        if end_turn_after:
            end_turn(state)
    else:
        # Game is over, ensure index points to the winner
        alive_players = [p for p in state.players if p.is_alive]
        if alive_players:
            for i, p in enumerate(state.players):
                if p.id == alive_players[0].id:
                    state.current_turn_index = i
                    break

def transition_to_phase_2(state: GameState):
    """
    Reveal stacks and determine first player for Phase 2.
    Highest unique Spade rank wins. (Ace > 10...2). Ties cancel out.
    """
    state.phase = 2
    state.turn_subphase = "BATTLE_ACTION"
    
    # Initialize Shop Row
    state.shop_row = []
    for _ in range(3):
        if state.shop_pile:
            state.shop_row.append(state.shop_pile.pop())
            
    spade_ranks: Dict[int, List[int]] = collections.defaultdict(list)
    for p_idx, player in enumerate(state.players):
        for char in player.characters:
            for card in char.stack:
                if card.suit == Suit.SPADES:
                    val = 11 if card.is_ace else card.rank
                    spade_ranks[val].append(p_idx)
    sorted_ranks = sorted(spade_ranks.keys(), reverse=True)
    found_player = None
    for rank in sorted_ranks:
        owners = spade_ranks[rank]
        if len(owners) == 1:
            found_player = owners[0]
            break
        # else: tie, cancels out
    
    if found_player is not None:
        state.current_turn_index = found_player
    else:
        state.current_turn_index = 0
        
    log_event(state, "PHASE_TRANSITION", {
        "new_phase": 2, 
        "first_player_id": state.players[state.current_turn_index].id,
        "spade_tiebreaker": {str(k): [state.players[pid].id for pid in v] for k, v in spade_ranks.items()}
    })
