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
            turn_subphase="SHOPPING",
            shop_row=[Card(rank=5, suit=Suit.DIAMONDS)],
            deck=[Card(rank=2, suit=Suit.HEARTS)]  # In Phase 2, shop refills from deck
        )
        buy_card(state, "p1", 0, 0)
        self.assertEqual(p1.coins, 5)
        self.assertEqual(len(p1.characters[0].stack), 1)
        self.assertEqual(p1.characters[0].stack[0].rank, 5)
        # Shop row doesn't refill immediately
        self.assertIsNone(state.shop_row[0])

    def test_buy_face_upgrade(self):
        p1 = Player(id="p1", name="P1", coins=10, characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[])
        ])
        state = GameState(
            players=[p1],
            phase=2,
            turn_subphase="SHOPPING",
            shop_row=[Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="Q")],
            deck=[]  # In Phase 2, shop_pile should be empty (merged into deck at transition)
        )
        buy_card(state, "p1", 0, 0)
        self.assertEqual(p1.coins, 6) # 10 - 4
        self.assertEqual(p1.characters[0].rank, "Q")
        self.assertEqual(p1.characters[0].suit, Suit.HEARTS)
        # Slot is now None
        self.assertIsNone(state.shop_row[0])
        self.assertEqual(len(state.shop_row), 1) # Wait, my buy_card does pop if pile is empty? 
        # No, my buy_card does state.shop_row[slot_index] = None

    def test_buy_invalid_upgrade(self):
        p1 = Player(id="p1", name="P1", coins=10, characters=[
            Character(rank="Q", suit=Suit.CLUBS, stack=[])
        ])
        state = GameState(
            players=[p1],
            phase=2,
            turn_subphase="SHOPPING",
            shop_row=[Card(rank=0, suit=Suit.HEARTS, is_face=True, face_rank="J")]
        )
        with self.assertRaisesRegex(ValueError, "Cannot upgrade Q with J"):
            buy_card(state, "p1", 0, 0)

    def test_refresh_shop(self):
        p1 = Player(id="p1", name="P1", coins=5)
        state = GameState(
            players=[p1],
            phase=2,
            turn_subphase="BATTLE_ACTION",
            shop_row=[Card(rank=2, suit=Suit.CLUBS)],
            deck=[Card(rank=5, suit=Suit.DIAMONDS)]  # In Phase 2, shop draws from deck
        )
        refresh_shop(state, "p1")
        self.assertEqual(state.players[0].coins, 3)
        self.assertIsNotNone(state.shop_row[0])
        self.assertEqual(state.shop_row[0].rank, 5)  # type: ignore[union-attr]
        # Deck is now empty after refill
        self.assertEqual(len(state.deck), 0)

    def test_refresh_shop_refill(self):
        p1 = Player(id="p1", name="P1", coins=2)
        state = GameState(
            players=[p1],
            phase=2,
            turn_subphase="BATTLE_ACTION",
            shop_row=[Card(rank=2, suit=Suit.CLUBS)],
            deck=[], # Empty deck
            discard_pile=[Card(rank=5, suit=Suit.DIAMONDS)]
        )
        refresh_shop(state, "p1")
        # should have 3 slots, filled from discard (shuffled into deck) then drawn
        self.assertEqual(state.players[0].coins, 0)
        self.assertEqual(len(state.shop_row), 3)
        self.assertEqual(len(state.discard_pile), 0)

if __name__ == '__main__':
    unittest.main()
