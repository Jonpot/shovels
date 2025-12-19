import unittest
from shovels_engine.models import setup_game, Card, Suit
from shovels_engine.agents import RandomAgent

class TestAgentDraw(unittest.TestCase):
    def setUp(self):
        self.state = setup_game(["p1", "p2"])
        self.agent = RandomAgent()
        self.state.turn_subphase = "DRAW"

    def test_agent_handles_one_card_deck(self):
        """
        If deck has 1 card, agent should NOT ask for 2 DECK cards.
        """
        self.state.deck = [Card(rank=5, suit=Suit.HEARTS)]
        self.state.discard_pile = [Card(rank=2, suit=Suit.CLUBS), Card(rank=3, suit=Suit.CLUBS)]
        
        # This should NOT rasie ValueError
        self.agent.act(self.state, "p1")
        
        self.assertEqual(self.state.turn_subphase, "DISCARD")
        self.assertEqual(len(self.state.players[0].hand), 2)
        # Verify it didn't crash
        
    def test_agent_handles_empty_deck(self):
        """
        If deck is empty, agent should draw from discard pile.
        """
        self.state.deck = []
        self.state.discard_pile = [Card(rank=2, suit=Suit.CLUBS), Card(rank=3, suit=Suit.CLUBS)]
        
        self.agent.act(self.state, "p1")
        
        self.assertEqual(self.state.turn_subphase, "DISCARD")
        self.assertEqual(len(self.state.players[0].hand), 2)

if __name__ == "__main__":
    unittest.main()
