from typing import List, Optional, Tuple, Dict
from .models import GameState, Card, Character, Player, Suit
import collections

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
    card = player.hand.pop(card_index)
    
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

def buy_card(state: GameState, player_id: str, slot_index: int, char_index: int):
    """
    Phase 2: Spend coins to buy a card from the shop.
    """
    if state.phase != 2:
        raise ValueError("Must be in Phase 2")
    
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    if slot_index >= len(state.shop_row):
        raise ValueError("Invalid shop slot")
    
    card = state.shop_row[slot_index]
    
    # Calculate price
    if card.is_face:
        prices = {"J": 3, "Q": 4, "K": 5}
        price = prices[card.face_rank]
    else:
        price = 10 if card.is_ace else card.rank
        
    if player.coins < price:
        raise ValueError("Not enough coins")
    
    # Enforce upgrade rules
    char = player.characters[char_index]
    if card.is_face:
        # Face upgrade: J < Q < K
        rank_values = {"J": 1, "Q": 2, "K": 3}
        if rank_values[card.face_rank] <= rank_values[char.rank]:
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
    
    # Refill shop
    if state.shop_pile:
        state.shop_row[slot_index] = state.shop_pile.pop()
    else:
        state.shop_row.pop(slot_index) # Just empty the slot if pile is empty
        
    state.action_taken_this_turn = True

def refresh_shop(state: GameState, player_id: str):
    """
    Phase 2: Spend 2 coins to refresh the shop.
    """
    if state.phase != 2:
        raise ValueError("Must be in Phase 2")
    
    player = next((p for p in state.players if p.id == player_id), None)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    
    if player.coins < 2:
        raise ValueError("Not enough coins to refresh shop")
    
    player.coins -= 2
    
    # Wipe and refill
    for card in state.shop_row:
        state.discard_pile.append(card)
    
    state.shop_row = []
    for _ in range(3):
        if state.shop_pile:
            state.shop_row.append(state.shop_pile.pop())
            
    state.action_taken_this_turn = True

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
    
    if char.suit == Suit.CLUBS:
        if not target_info:
            raise ValueError("Target info required for Clubs power")
        targets = target_info.get('targets', []) # List of {'target_player_id': ..., 'target_char_index': ...}
        
        num_strikes = {"J": 1, "Q": 2, "K": 3}[char.rank]
        if len(targets) > num_strikes:
            raise ValueError(f"{char.rank} of Clubs can only hit {num_strikes} targets")
            
        for target in targets:
            attack_heart(state, player_id, target['target_player_id'], target['target_char_index'], 10)
            
    elif char.suit == Suit.DIAMONDS:
        # Free purchases
        if not target_info:
            raise ValueError("Target info required for Diamonds power")
        slots = target_info.get('slots', []) # List of shop slot indices
        
        num_free = {"J": 1, "Q": 2, "K": 3}[char.rank]
        if len(slots) > num_free:
            raise ValueError(f"{char.rank} of Diamonds can only buy {num_free} cards")
            
        # Temporarily give player enough coins to buy for free
        original_coins = player.coins
        for slot in slots:
            card = state.shop_row[slot]
            if card.is_face:
                price = {"J": 3, "Q": 4, "K": 5}[card.face_rank]
            else:
                price = 10 if card.is_ace else card.rank
            
            player.coins = price
            buy_card(state, player_id, slot, char_index)
        player.coins = original_coins # Restore coins
        
    elif char.suit == Suit.SPADES:
        # Gravedig: Draw 5 from discard, keep N
        if not target_info:
            raise ValueError("Target info required for Spades power")
        indices = target_info.get('indices', []) # Indices in discard pile (from the top 5)
        
        num_keep = {"J": 1, "Q": 2, "K": 3}[char.rank]
        if len(indices) > num_keep:
            raise ValueError(f"{char.rank} of Spades can only keep {num_keep} cards")
        
        # Take up to 5 cards from top of discard
        available = []
        for _ in range(min(5, len(state.discard_pile))):
            available.append(state.discard_pile.pop())
        
        # Keep selected
        for idx in sorted(indices, reverse=True):
            if idx < len(available):
                char.stack.append(available.pop(idx))
        
        # Return rest to discard
        state.discard_pile.extend(reversed(available))
        
    elif char.suit == Suit.HEARTS:
        shield_values = {"J": 3, "Q": 5, "K": 10}
        char.shield += shield_values[char.rank]
        
    if is_turn and not state.dug_cards:
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
    
    resolve_suit_effect(state, player_id, char_index, action_suit, total_rank, target_info)
    
    if not state.dug_cards:
        end_turn(state)

def resolve_suit_effect(state: GameState, player_id: str, char_index: Optional[int], suit: Suit, total_rank: int, target_info: Optional[Dict] = None):
    if suit == Suit.CLUBS:
        if not target_info:
            raise ValueError("Target info required for Clubs")
        attack_heart(state, player_id, target_info['target_player_id'], target_info['target_char_index'], total_rank)
    elif suit == Suit.DIAMONDS:
        player = next(p for p in state.players if p.id == player_id)
        player.coins += total_rank
    elif suit == Suit.HEARTS:
        pass
    elif suit == Suit.SPADES:
        if char_index is None:
            raise ValueError("Spade actions require character context")
        char = next(p for p in state.players if p.id == player_id).characters[char_index]
        dig_count = min(total_rank, len(char.stack))
        for _ in range(dig_count):
            state.dug_cards.append(char.stack.pop())
            state.cards_removed_this_turn = True
        return # Recursion

def apply_face_strike(state: GameState, player_id: str, char_index: int, target_player_id: str, target_char_index: int):
    if state.phase != 2:
        raise ValueError("Must be in Phase 2")
    
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
    
    removed = False
    if not target_char.stack:
        target_player.characters.pop(target_char_index)
        state.cards_removed_this_turn = True
        removed = True
        if not target_player.characters:
            target_player.is_alive = False
    else:
        # Heart protection scenario
        pass

    state.action_taken_this_turn = True
    state.active_character_index = char_index
    
    if not removed and not state.cards_removed_this_turn and not state.character_tapped_this_turn:
        player.characters.pop(char_index)
        state.cards_removed_this_turn = True
        if not player.characters:
            player.is_alive = False

    if not state.dug_cards:
        end_turn(state)

def attack_heart(state: GameState, player_id: str, target_player_id: str, target_char_index: int, damage: int):
    target_player = next(p for p in state.players if p.id == target_player_id)
    target_char = target_player.characters[target_char_index]
    
    if not target_char.stack:
        if damage >= 1:
            target_player.characters.pop(target_char_index)
            state.cards_removed_this_turn = True
            if not target_player.characters:
                target_player.is_alive = False
        return

    for i in range(len(target_char.stack) - 1, -1, -1):
        card = target_char.stack[i]
        if card.suit == Suit.HEARTS:
            if damage >= (card.rank + target_char.shield):
                num_to_remove = len(target_char.stack) - i
                for _ in range(num_to_remove):
                    state.discard_pile.append(target_char.stack.pop())
                state.cards_removed_this_turn = True
                break

def end_turn(state: GameState):
    player = get_current_player(state)
    
    if state.phase == 2:
        if not state.action_taken_this_turn and not state.cards_removed_this_turn and not state.character_tapped_this_turn:
            if player.characters:
                player.characters.pop()
                if not player.characters:
                    player.is_alive = False
    
    player.can_discard_second_face = False
    state.action_taken_this_turn = False
    state.cards_removed_this_turn = False
    state.character_tapped_this_turn = False
    state.dug_cards = []
    state.active_character_index = None
    
    state.turn_count += 1
    
    num_players = len(state.players)
    for _ in range(num_players):
        state.current_turn_index = (state.current_turn_index + 1) % num_players
        if state.players[state.current_turn_index].is_alive:
            break
            
    state.turn_subphase = "DRAW" if state.phase == 1 else "BATTLE_ACTION"
    
    if state.phase == 1 and not state.deck:
        if state.turn_count % len(state.players) == 0:
            transition_to_phase_2(state)

def transition_to_phase_2(state: GameState):
    """
    Reveal stacks and determine first player for Phase 2.
    Highest unique Spade rank wins. (Ace > 10...2). Ties cancel out.
    """
    state.phase = 2
    state.turn_subphase = "BATTLE_ACTION"
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
