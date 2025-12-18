from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field
import random

class Suit(str, Enum):
    CLUBS = "CLUBS"
    DIAMONDS = "DIAMONDS"
    HEARTS = "HEARTS"
    SPADES = "SPADES"

class Card(BaseModel):
    rank: int  # 2-10
    suit: Suit
    is_face: bool = False
    face_rank: Optional[str] = None  # "J", "Q", "K"
    is_ace: bool = False

class Character(BaseModel):
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

def initialize_full_pool() -> List[Card]:
    """Creates the full 104-card pool (2 standard 52-card decks)."""
    pool = []
    for _ in range(2):
        for suit in Suit:
            # Number cards 2-10
            for r in range(2, 11):
                pool.append(Card(rank=r, suit=suit, is_face=False))
            # Ace (Value 10, but distinct from 10)
            pool.append(Card(rank=10, suit=suit, is_face=False, is_ace=True))
            # Face cards
            for f in ["J", "Q", "K"]:
                pool.append(Card(rank=0, suit=suit, is_face=True, face_rank=f))
    return pool

def setup_game(player_ids: List[str]) -> GameState:
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
            p_chars.append(Character(rank=fc.face_rank, suit=fc.suit))
        players.append(Player(id=pid, name=f"Player {pid}", characters=p_chars))
    
    # Return remaining face cards to deck
    remaining_deck.extend(face_cards)
    random.shuffle(remaining_deck)
    
    # Create Shop Pile (20 cards)
    shop_pile = [remaining_deck.pop() for _ in range(20)]
    
    # Create Shop Row (3 cards)
    shop_row = [remaining_deck.pop() for _ in range(3)]
    
    return GameState(
        deck=remaining_deck,
        shop_pile=shop_pile,
        shop_row=shop_row,
        players=players
    )
