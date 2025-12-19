import unittest
from shovels_engine.models import GameState, Card, Player, Character, Suit
from shovels_engine.engine import end_turn, can_player_act, check_win_condition

class TestGameLoop(unittest.TestCase):
    def test_can_player_act_with_stack(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[Card(rank=5, suit=Suit.CLUBS)])
        ])
        state = GameState(players=[p1], phase=2, current_turn_index=0)
        self.assertTrue(can_player_act(state, "p1"))

    def test_can_player_act_untapped(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[], is_tapped=False)
        ])
        state = GameState(players=[p1], phase=2, current_turn_index=0)
        self.assertTrue(can_player_act(state, "p1"))

    def test_cannot_player_act_tapped_empty(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[], is_tapped=True)
        ])
        # P2 exists so face strike is potentially possible, but P2 has stack
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="Q", suit=Suit.HEARTS, stack=[Card(rank=10, suit=Suit.HEARTS)])
        ])
        state = GameState(players=[p1, p2], phase=2, current_turn_index=0)
        self.assertFalse(can_player_act(state, "p1"))

    def test_can_player_act_face_strike(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[], is_tapped=True)
        ])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="Q", suit=Suit.HEARTS, stack=[]) # Exposed!
        ])
        state = GameState(players=[p1, p2], phase=2, current_turn_index=0)
        # Face strike is possible on P2
        self.assertTrue(can_player_act(state, "p1"))

    def test_fatigue_trigger(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[], is_tapped=True)
        ])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="K", suit=Suit.SPADES, stack=[Card(rank=10, suit=Suit.HEARTS)])
        ])
        state = GameState(players=[p1, p2], phase=2, current_turn_index=1) # P2's turn
        state.action_taken_this_turn = True # P2 acted, so it's fine
        
        # End P2's turn, transitions to P1
        end_turn(state)
        
        # P1 cannot act, so fatigue should trigger immediately in end_turn (which calls apply_fatigue)
        self.assertEqual(state.current_turn_index, 1) # Should be back to P2 if P1 died
        self.assertFalse(p1.is_alive)
        self.assertEqual(len(p1.characters), 0)
        self.assertEqual(state.winner_id, "p2")
        self.assertTrue(state.is_over)

    def test_win_condition_detection(self):
        p1 = Player(id="p1", name="P1", characters=[], is_alive=False)
        p2 = Player(id="p2", name="P2", characters=[Character(rank="J", suit=Suit.CLUBS)])
        state = GameState(players=[p1, p2], phase=2)
        check_win_condition(state)
        self.assertTrue(state.is_over)
        self.assertEqual(state.winner_id, "p2")

    def test_event_logging(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[Card(rank=5, suit=Suit.CLUBS)])
        ], hand=[Card(rank=2, suit=Suit.CLUBS)])
        state = GameState(players=[p1], phase=1, turn_subphase="PLAY")
        from shovels_engine.engine import play_card
        play_card(state, "p1", 0, 0)
        
        # Events: DRAW (implicitly maybe not?), DISCARD (no), PLAY_CARD, GAME_OVER (maybe not yet)
        # Let's check events
        event_types = [e['event_type'] for e in state.events]
        self.assertIn("PLAY_CARD", event_types)

if __name__ == '__main__':
    unittest.main()
