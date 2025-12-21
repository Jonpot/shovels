from enum import Enum
from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field
import random

class Suit(str, Enum):
    CLUBS = "CLUBS"
    DIAMONDS = "DIAMONDS"
    HEARTS = "HEARTS"
    SPADES = "SPADES"

class Card(BaseModel):
    uid: str
    rank: int  # 2-10
    suit: Suit
    is_face: bool = False
    face_rank: Optional[str] = None  # "J", "Q", "K"
    is_ace: bool = False

    @property
    def price(self) -> int:
        if self.is_face:
            return {"J": 3, "Q": 4, "K": 5}[self.face_rank]
        return 10 if self.is_ace else self.rank

class Character(BaseModel):
    uid: str
    rank: str  # J, Q, K
    suit: Suit
    stack: List[Card] = Field(default_factory=list)
    is_tapped: bool = False
    shield: int = 0

class Player(BaseModel):
    id: str
    name: str
    characters: List[Character] = Field(default_factory=list)
    hand: List[Card] = Field(default_factory=list)
    coins: int = 0
    can_discard_second_face: bool = False
    is_alive: bool = True

class GameState(BaseModel):
    deck: List[Card] = Field(default_factory=list)
    shop_pile: List[Card] = Field(default_factory=list)
    shop_row: List[Card] = Field(default_factory=list)
    discard_pile: List[Card] = Field(default_factory=list)
    players: List[Player] = Field(default_factory=list)
    current_turn_index: int = 0
    turn_count: int = 0
    phase: int = 1
    turn_subphase: str = "DRAW"  # DRAW, DISCARD, PLAY, BATTLE_ACTION
    max_characters: int = 3
    action_taken_this_turn: bool = False
    cards_removed_this_turn: bool = False
    character_tapped_this_turn: bool = False
    dug_cards: List[Card] = Field(default_factory=list)
    active_character_index: Optional[int] = None
    gravedig_pool: List[Card] = Field(default_factory=list)
    free_buys_remaining: int = 0
    events: List[Dict] = Field(default_factory=list)
    winner_id: Optional[str] = None
    is_over: bool = False

def initialize_full_pool() -> List[Card]:
    """Creates the full 104-card pool (2 standard 52-card decks)."""
    pool = []
    card_id = 0
    for _ in range(2):
        for suit in Suit:
            # Number cards 2-10
            for r in range(2, 11):
                pool.append(Card(uid=f"card_{card_id}", rank=r, suit=suit, is_face=False))
                card_id += 1
            # Ace (Value 10, but distinct from 10)
            pool.append(Card(uid=f"card_{card_id}", rank=10, suit=suit, is_face=False, is_ace=True))
            card_id += 1
            # Face cards
            for f in ["J", "Q", "K"]:
                pool.append(Card(uid=f"card_{card_id}", rank=0, suit=suit, is_face=True, face_rank=f))
                card_id += 1
    return pool

def setup_game(player_ids: List[str], player_names: Optional[Dict[str, str]] = None) -> GameState:
    """Initializes a new game according to the rules."""
    pool = initialize_full_pool()
    random.shuffle(pool)
    
    # Extract all face cards for character dealing
    face_cards = [c for c in pool if c.is_face]
    remaining_deck = [c for c in pool if not c.is_face]
    
    random.shuffle(face_cards)
    
    players = []
    for pid in player_ids:
        # Deal 3 face-down characters
        p_chars = []
        for _ in range(3):
            fc = face_cards.pop()
            p_chars.append(Character(uid=fc.uid, rank=fc.face_rank, suit=fc.suit))
        
        # Use real name if provided, else fallback to generic ID-based name
        p_name = player_names.get(pid, f"Player {pid}") if player_names else f"Player {pid}"
        players.append(Player(id=pid, name=p_name, characters=p_chars))
    
    # Return remaining face cards to deck
    remaining_deck.extend(face_cards)
    random.shuffle(remaining_deck)
    
    # Create Shop Pile (20 cards)
    shop_pile = [remaining_deck.pop() for _ in range(20)]
    
    return GameState(
        deck=remaining_deck,
        shop_pile=shop_pile,
        players=players
    )
