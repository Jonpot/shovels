import unittest
import json
from shovels_engine.models import Suit, Card, Character, Player, GameState, initialize_full_pool, setup_game

class TestModels(unittest.TestCase):
    def test_deck_initialization(self):
        pool = initialize_full_pool()
        self.assertEqual(len(pool), 104)
        
        # Check suits
        for suit in Suit:
            suit_cards = [c for c in pool if c.suit == suit]
            self.assertEqual(len(suit_cards), 26) # 13 * 2
            
        # Check face cards
        face_cards = [c for c in pool if c.is_face]
        self.assertEqual(len(face_cards), 24) # (J, Q, K) * 4 * 2

    def test_game_setup(self):
        player_ids = ["p1", "p2"]
        state = setup_game(player_ids)
        
        self.assertEqual(len(state.players), 2)
        for p in state.players:
            self.assertEqual(len(p.characters), 3)
            
        self.assertEqual(len(state.shop_pile), 20)
        self.assertEqual(len(state.deck), 78)

    def test_serialization(self):
        player_ids = ["p1"]
        state = setup_game(player_ids)
        
        # Serialize
        json_data = state.model_dump_json()
        self.assertIsInstance(json_data, str)
        
        # Deserialize
        new_state = GameState.model_validate_json(json_data)
        self.assertEqual(new_state.players[0].id, "p1")
        self.assertEqual(len(new_state.players[0].characters), 3)
        self.assertEqual(len(new_state.deck), 104 - 3 - 20)

if __name__ == "__main__":
    unittest.main()
