import unittest
from shovels_engine.models import setup_game, Suit, Card
from shovels_engine.engine import (
    draw_cards, play_card, discard_card, 
    transition_to_phase_2
)

class TestPhase1Robust(unittest.TestCase):
    def setUp(self):
        self.player_ids = ["Alice", "Bob"]
        self.state = setup_game(self.player_ids)

    def test_draw_empty_deck_error(self):
        self.state.deck = []
        with self.assertRaisesRegex(ValueError, "Not enough cards in deck"):
            draw_cards(self.state, "Alice", ["DECK", "DECK"])

    def test_draw_face_cards_flag(self):
        # 1. Draw 1 face, 1 number -> flag False
        self.state.deck = [
            Card(rank=5, suit=Suit.HEARTS),
            Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="J")
        ]
        draw_cards(self.state, "Alice", ["DECK", "DECK"])
        self.assertFalse(self.state.players[0].can_discard_second_face)
        
        # Reset for next part
        self.state.players[0].hand = []
        self.state.turn_subphase = "DRAW"
        
        # 2. Draw 2 faces -> flag True
        self.state.deck = [
            Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="Q"),
            Card(rank=0, suit=Suit.SPADES, is_face=True, face_rank="K")
        ]
        draw_cards(self.state, "Alice", ["DECK", "DECK"])
        self.assertTrue(self.state.players[0].can_discard_second_face)

    def test_play_card_no_index_error(self):
        # Draw 1 face, 1 number
        self.state.deck = [
            Card(rank=5, suit=Suit.HEARTS),
            Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="J")
        ]
        draw_cards(self.state, "Alice", ["DECK", "DECK"])
        discard_card(self.state, "Alice", 0) # Discard number
        
        # Try to play without index -> Error because it's not the 2-face case
        with self.assertRaisesRegex(ValueError, "Character index required"):
            play_card(self.state, "Alice", 0, None)

    def test_play_card_second_face_discard(self):
        # Draw 2 faces
        self.state.deck = [
            Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="Q"),
            Card(rank=0, suit=Suit.SPADES, is_face=True, face_rank="K")
        ]
        draw_cards(self.state, "Alice", ["DECK", "DECK"])
        discard_card(self.state, "Alice", 0)
        
        # Valid: play_card with None index for the second face
        play_card(self.state, "Alice", 0, None)
        self.assertEqual(len(self.state.players[0].hand), 0)
        self.assertEqual(self.state.current_turn_index, 1)

    def test_create_new_character(self):
        # Draw face card
        self.state.deck = [
            Card(rank=5, suit=Suit.HEARTS),
            Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="J")
        ]
        draw_cards(self.state, "Alice", ["DECK", "DECK"])
        discard_card(self.state, "Alice", 1) # Discard face
        
        # Start with 3 characters. Max is 3. 
        # But wait, technical spec says "Initial Characters: 3 per player".
        # If max is 3, they can't create more. Let's test replacement.
        play_card(self.state, "Alice", 0, 0)
        self.assertEqual(len(self.state.players[0].characters), 3)

        # Test creating new character (if we temp increase max)
        self.state.max_characters = 4
        self.state.turn_subphase = "DRAW"
        self.state.deck = [
            Card(rank=5, suit=Suit.HEARTS),
            Card(rank=0, suit=Suit.SPADES, is_face=True, face_rank="K")
        ]
        draw_cards(self.state, "Alice", ["DECK", "DECK"])
        # Hand is [Face, Number] because deck.pop() takes the last item first.
        # Actually deck is [Number, Face]. Pop 1: Face. Pop 2: Number.
        # Hand: [Face, Number]
        discard_card(self.state, "Alice", 1) # Discard number, keep Face
        
        # Play face to index 3 (new)
        play_card(self.state, "Alice", 0, 3)
        self.assertEqual(len(self.state.players[0].characters), 4)
        self.assertEqual(self.state.players[0].characters[3].rank, "K")

    def test_create_new_character_limit_error(self):
        self.state.max_characters = 3 # Default
        self.state.players[0].hand = [Card(rank=0, suit=Suit.SPADES, is_face=True, face_rank="K")]
        self.state.turn_subphase = "PLAY"
        
        with self.assertRaisesRegex(ValueError, "too many characters"):
            play_card(self.state, "Alice", 0, 3)

    def test_tiebreaker_cancel_out_full(self):
        # Alice: Ace(11), 5
        # Bob: Ace(11), 8
        self.state.players[0].characters[0].stack.append(Card(rank=10, suit=Suit.SPADES, is_ace=True))
        self.state.players[0].characters[1].stack.append(Card(rank=5, suit=Suit.SPADES))
        
        self.state.players[1].characters[0].stack.append(Card(rank=10, suit=Suit.SPADES, is_ace=True))
        self.state.players[1].characters[1].stack.append(Card(rank=8, suit=Suit.SPADES))
        
        transition_to_phase_2(self.state)
        self.assertEqual(self.state.current_turn_index, 1) # Bob wins with 8

    def test_play_card_atomicity(self):
        """Verify that a card is not consumed if play_card raises a ValueError."""
        # 1. Number card to invalid new slot
        self.state.players[0].hand = [Card(rank=5, suit=Suit.HEARTS)]
        self.state.turn_subphase = "PLAY"
        
        with self.assertRaisesRegex(ValueError, "Cannot create new character with a number card"):
            play_card(self.state, "Alice", 0, 3) # Index 3 is new slot
        
        # Verify card is still in hand
        self.assertEqual(len(self.state.players[0].hand), 1)
        self.assertEqual(self.state.players[0].hand[0].rank, 5)

        # 2. Face card to invalid high index
        self.state.players[0].hand = [Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="K")]
        with self.assertRaisesRegex(ValueError, "too many characters"):
            play_card(self.state, "Alice", 0, 4) # Exceeds max (3) and next available (3)
            
        self.assertEqual(len(self.state.players[0].hand), 1)
        self.assertEqual(self.state.players[0].hand[0].face_rank, "K")

if __name__ == "__main__":
    unittest.main()
