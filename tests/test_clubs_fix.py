import unittest
from shovels_engine.models import setup_game, Card, Suit, Character
from shovels_engine.engine import attack_heart

class TestClubsFix(unittest.TestCase):
    def setUp(self):
        self.state = setup_game(["p1", "p2"])
        # Clear out characters to have a clean state
        self.state.players[0].characters = []
        self.state.players[1].characters = []

    def test_clubs_attack_no_hearts_in_stack(self):
        """
        Verify that a character with a non-empty stack containing NO Hearts
        is still removed by a Clubs attack (damage >= 1).
        """
        p2 = self.state.players[1]
        # Give p2 a character with a stack of Diamonds/Clubs, but NO Hearts
        stack = [
            Card(rank=5, suit=Suit.DIAMONDS),
            Card(rank=2, suit=Suit.CLUBS)
        ]
        target_char = Character(rank="KC", suit=Suit.CLUBS, stack=stack)
        p2.characters.append(target_char)
        
        # p1 attacks p2's ONLY character
        # Damage 7 (greater than 1)
        attack_heart(self.state, "p1", "p2", 0, 7)
        
        # Verify character 0 is removed
        self.assertEqual(len(p2.characters), 0)
        self.assertFalse(p2.is_alive)
        
        # Verify events
        death_events = [e for e in self.state.events if e['event_type'] == "CHARACTER_DEATH"]
        self.assertEqual(len(death_events), 1)
        self.assertEqual(death_events[0]['data']['reason'], "HEART_OVERWHELM")

    def test_clubs_attack_with_hearts(self):
        """
        Verify that a character with a Heart in their stack ONLY loses cards above/at the Heart.
        """
        p2 = self.state.players[1]
        # Stack: [2D, 5H (Heart!), 8C]
        # Index 0: 2D
        # Index 1: 5H
        # Index 2: 8C
        stack = [
            Card(rank=2, suit=Suit.DIAMONDS),
            Card(rank=5, suit=Suit.HEARTS),
            Card(rank=8, suit=Suit.CLUBS)
        ]
        target_char = Character(rank="KC", suit=Suit.CLUBS, stack=stack)
        p2.characters.append(target_char)
        
        # p1 attacks with Damage 7
        # 5H (rank 5) should absorb 7 damage because 7 >= 5
        attack_heart(self.state, "p1", "p2", 0, 7)
        
        # Character should still exist
        self.assertEqual(len(p2.characters), 1)
        self.assertTrue(p2.is_alive)
        # Stack should only have [2D] remaining
        self.assertEqual(len(p2.characters[0].stack), 1)
        self.assertEqual(p2.characters[0].stack[0].suit, Suit.DIAMONDS)

if __name__ == "__main__":
    unittest.main()
