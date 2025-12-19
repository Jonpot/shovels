import unittest
from shovels_engine.models import setup_game, Card, Suit
from shovels_engine.engine import draw_cards

class TestDrawAtomicity(unittest.TestCase):
    def setUp(self):
        self.state = setup_game(["p1", "p2"])
        # Clear piles
        self.state.deck = []
        self.state.discard_pile = []
        self.state.turn_subphase = "DRAW"

    def test_draw_deck_depletion_atomicity(self):
        """
        If deck has 1 card and player tries to draw 2 from deck,
        it should raise ValueError and NOT add any cards to hand.
        """
        self.state.deck = [Card(rank=5, suit=Suit.HEARTS)]
        p1 = self.state.players[0]
        initial_hand_size = len(p1.hand) # Should be 0 after setup_game if we cleared it, but setup_game gives 3 chars not hand.
        p1.hand = []
        
        with self.assertRaisesRegex(ValueError, "Not enough cards in deck"):
            draw_cards(self.state, "p1", ["DECK", "DECK"])
            
        self.assertEqual(len(p1.hand), 0)
        self.assertEqual(len(self.state.deck), 1)
        self.assertEqual(self.state.turn_subphase, "DRAW")

    def test_draw_mixed_atomicity_fail_second(self):
        """
        Draw DISCARD then DECK. Deck is empty.
        Should fail and NOT remove the card from discard pile.
        """
        self.state.discard_pile = [Card(rank=10, suit=Suit.SPADES)]
        self.state.deck = [] # Empty
        p1 = self.state.players[0]
        p1.hand = []
        
        with self.assertRaisesRegex(ValueError, "Not enough cards in deck"):
            draw_cards(self.state, "p1", ["DISCARD", "DECK"])
            
        self.assertEqual(len(p1.hand), 0)
        self.assertEqual(len(self.state.discard_pile), 1)

if __name__ == "__main__":
    unittest.main()
