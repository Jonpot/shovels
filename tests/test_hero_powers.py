import unittest
from shovels_engine.models import GameState, Card, Player, Character, Suit
from shovels_engine.engine import tap_hero_power, buy_card, resolve_gravedig

class TestHeroPowers(unittest.TestCase):
    def test_clubs_burst(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="K", suit=Suit.CLUBS)
        ])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="J", suit=Suit.HEARTS, stack=[Card(rank=5, suit=Suit.HEARTS)]),
            Character(rank="K", suit=Suit.DIAMONDS, stack=[])
        ])
        state = GameState(players=[p1, p2], phase=2, current_turn_index=0)
        
        # Strike 1: kills K of Diamonds (char 1).
        # Strike 2: removes J of Hearts stack (char 0).
        # Strike 3: kills J of Hearts (char 0).
        tap_hero_power(state, "p1", 0, target_info={
            'targets': [
                {'target_player_id': 'p2', 'target_char_index': 1},
                {'target_player_id': 'p2', 'target_char_index': 0},
                {'target_player_id': 'p2', 'target_char_index': 0}
            ]
        })
        
        self.assertTrue(p1.characters[0].is_tapped)
        self.assertEqual(len(p2.characters), 0) # Both should be dead
        self.assertFalse(p2.is_alive)

    def test_diamonds_free_buy(self):
        p1 = Player(id="p1", name="P1", coins=0, characters=[
            Character(rank="J", suit=Suit.DIAMONDS)
        ])
        state = GameState(
            players=[p1],
            phase=2,
            shop_row=[Card(rank=10, suit=Suit.CLUBS, is_ace=True)],
            shop_pile=[Card(rank=2, suit=Suit.DIAMONDS)]
        )
        tap_hero_power(state, "p1", 0) 
        self.assertEqual(state.turn_subphase, "SHOP_FREE_BUY")
        self.assertEqual(state.free_buys_remaining, 1)
        
        # Now buy for free
        buy_card(state, "p1", 0, 0)
        self.assertEqual(len(p1.characters[0].stack), 1)
        self.assertEqual(state.free_buys_remaining, 0)
        self.assertIsNone(state.shop_row[0])

    def test_spades_gravedig(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.SPADES)
        ])
        state = GameState(
            players=[p1],
            phase=2,
            discard_pile=[
                Card(rank=2, suit=Suit.CLUBS),
                Card(rank=3, suit=Suit.CLUBS),
                Card(rank=4, suit=Suit.CLUBS),
                Card(rank=5, suit=Suit.CLUBS),
                Card(rank=6, suit=Suit.CLUBS)
            ]
        )
        # Spades power now deals 5 cards to a pool
        tap_hero_power(state, "p1", 0) 
        self.assertEqual(state.turn_subphase, "GRAVEDIGGING")
        self.assertEqual(len(state.gravedig_pool), 5)
        
        # Resolve gravedig
        resolve_gravedig(state, "p1", 0, [0])
        self.assertEqual(len(p1.characters[0].stack), 1)
        self.assertEqual(len(state.discard_pile), 4)
        self.assertEqual(state.turn_subphase, "BATTLE_ACTION")

    def test_hearts_shield_out_of_turn(self):
        p1 = Player(id="p1", name="P1", characters=[Character(rank="J", suit=Suit.CLUBS)])
        p2 = Player(id="p2", name="P2", characters=[Character(rank="J", suit=Suit.HEARTS)])
        state = GameState(players=[p1, p2], phase=2, current_turn_index=0)
        
        # P2 uses power out of turn
        tap_hero_power(state, "p2", 0)
        self.assertEqual(p2.characters[0].shield, 3)
        self.assertTrue(p2.characters[0].is_tapped)
        self.assertEqual(state.current_turn_index, 0) # Still P1's turn

    def test_shield_protection(self):
        p1 = Player(id="p1", name="P1", characters=[Character(rank="J", suit=Suit.CLUBS)])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="J", suit=Suit.HEARTS, stack=[Card(rank=8, suit=Suit.HEARTS)], shield=3)
        ])
        state = GameState(players=[p1, p2], phase=2, current_turn_index=0)
        
        from shovels_engine.engine import attack_heart
        # 10 damage vs (8 rank + 3 shield = 11 threshold) -> Should fail
        attack_heart(state, "p1", "p2", 0, 10)
        self.assertEqual(len(p2.characters[0].stack), 1)
        
        # 11 damage should succeed
        attack_heart(state, "p1", "p2", 0, 11)
        self.assertEqual(len(p2.characters[0].stack), 0)

if __name__ == '__main__':
    unittest.main()
