import unittest
from shovels_engine.models import GameState, Card, Player, Character, Suit
from shovels_engine.engine import buy_card, refresh_shop

class TestShop(unittest.TestCase):
    def test_buy_number_card(self):
        p1 = Player(id="p1", name="P1", coins=10, characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[])
        ])
        state = GameState(
            players=[p1],
            phase=2,
            shop_row=[Card(rank=5, suit=Suit.DIAMONDS)],
            shop_pile=[Card(rank=2, suit=Suit.HEARTS)]
        )
        buy_card(state, "p1", 0, 0)
        self.assertEqual(p1.coins, 5)
        self.assertEqual(len(p1.characters[0].stack), 1)
        self.assertEqual(p1.characters[0].stack[0].rank, 5)
        self.assertEqual(state.shop_row[0].rank, 2)
        self.assertTrue(state.action_taken_this_turn)

    def test_buy_face_upgrade(self):
        p1 = Player(id="p1", name="P1", coins=10, characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[])
        ])
        state = GameState(
            players=[p1],
            phase=2,
            shop_row=[Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="Q")],
            shop_pile=[]
        )
        buy_card(state, "p1", 0, 0)
        self.assertEqual(p1.coins, 6) # 10 - 4
        self.assertEqual(p1.characters[0].rank, "Q")
        self.assertEqual(p1.characters[0].suit, Suit.HEARTS)
        self.assertEqual(len(state.shop_row), 0)

    def test_buy_invalid_upgrade(self):
        p1 = Player(id="p1", name="P1", coins=10, characters=[
            Character(rank="Q", suit=Suit.CLUBS, stack=[])
        ])
        state = GameState(
            players=[p1],
            phase=2,
            shop_row=[Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="J")]
        )
        with self.assertRaisesRegex(ValueError, "Cannot upgrade Q with J"):
            buy_card(state, "p1", 0, 0)

    def test_refresh_shop(self):
        p1 = Player(id="p1", name="P1", coins=5)
        state = GameState(
            players=[p1],
            phase=2,
            shop_row=[Card(rank=2, suit=Suit.CLUBS)],
            shop_pile=[Card(rank=5, suit=Suit.DIAMONDS)]
        )
        refresh_shop(state, "p1")
        self.assertEqual(p1.coins, 3)
        self.assertEqual(state.shop_row[0].rank, 5)
        self.assertEqual(state.discard_pile[0].rank, 2)

if __name__ == '__main__':
    unittest.main()
