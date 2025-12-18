import unittest
from shovels_engine.models import GameState, Card, Player, Character, Suit
from shovels_engine.engine import perform_action, apply_face_strike, end_turn, transition_to_phase_2

class TestPhase2(unittest.TestCase):
    def test_action_hand_suit_selection(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[
                Card(rank=5, suit=Suit.CLUBS),
                Card(rank=3, suit=Suit.DIAMONDS),
                Card(rank=2, suit=Suit.CLUBS)
            ])
        ])
        state = GameState(players=[p1], phase=2, turn_subphase="BATTLE_ACTION")
        # Use DIAMONDS to avoid target_info requirement for now
        perform_action(state, "p1", 0, 2, Suit.DIAMONDS)
        self.assertEqual(len(p1.characters[0].stack), 1)
        self.assertEqual(p1.coins, 3)

    def test_clubs_heart_removal(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[Card(rank=10, suit=Suit.CLUBS)])
        ])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="Q", suit=Suit.HEARTS, stack=[
                Card(rank=5, suit=Suit.HEARTS),
                Card(rank=2, suit=Suit.DIAMONDS)
            ])
        ])
        state = GameState(players=[p1, p2], phase=2, turn_subphase="BATTLE_ACTION", current_turn_index=0)
        perform_action(state, "p1", 0, 1, Suit.CLUBS, target_info={
            'target_player_id': "p2",
            'target_char_index': 0
        })
        # Heart removed, but character should still be there (stack empty)
        self.assertEqual(len(p2.characters), 1)
        self.assertEqual(len(p2.characters[0].stack), 0)

    def test_spade_dig_recursion(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="K", suit=Suit.SPADES, stack=[
                Card(rank=5, suit=Suit.DIAMONDS),
                Card(rank=2, suit=Suit.SPADES)
            ])
        ])
        state = GameState(players=[p1], phase=2, turn_subphase="BATTLE_ACTION")
        perform_action(state, "p1", 0, 1, Suit.SPADES)
        self.assertEqual(len(state.dug_cards), 1)
        self.assertEqual(state.dug_cards[0].rank, 5)
        self.assertEqual(state.current_turn_index, 0)
        perform_action(state, "p1", None, 0, Suit.DIAMONDS, dug_indices=[0])
        self.assertEqual(p1.coins, 5)
        self.assertEqual(len(state.dug_cards), 0)

    def test_face_strike_suicide(self):
        p1 = Player(id="p1", name="P1", characters=[Character(rank="J", suit=Suit.CLUBS, stack=[])])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="Q", suit=Suit.HEARTS, stack=[Card(rank=10, suit=Suit.HEARTS)])
        ])
        state = GameState(players=[p1, p2], phase=2, turn_subphase="BATTLE_ACTION", current_turn_index=0)
        apply_face_strike(state, "p1", 0, "p2", 0)
        self.assertEqual(len(p1.characters), 0)
        self.assertFalse(p1.is_alive)

    def test_must_act_rule(self):
        p1 = Player(id="p1", name="P1", characters=[Character(rank="J", suit=Suit.CLUBS, stack=[])])
        state = GameState(players=[p1], phase=2, turn_subphase="BATTLE_ACTION", current_turn_index=0)
        end_turn(state)
        self.assertEqual(len(p1.characters), 0)
        self.assertFalse(p1.is_alive)

    def test_spade_dig_character_consistency(self):
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[
                Card(rank=5, suit=Suit.HEARTS), # To be dug
                Card(rank=10, suit=Suit.DIAMONDS), # To be dug
                Card(rank=2, suit=Suit.SPADES) # The action card
            ]),
            Character(rank="Q", suit=Suit.DIAMONDS, stack=[Card(rank=5, suit=Suit.DIAMONDS)])
        ])
        state = GameState(players=[p1], phase=2, turn_subphase="BATTLE_ACTION")
        
        # Dig with character 0
        perform_action(state, "p1", 0, 1, Suit.SPADES)
        self.assertEqual(state.active_character_index, 0)
        self.assertEqual(len(state.dug_cards), 2)
        
        # Try to use character 1 for next action -> Should fail
        with self.assertRaisesRegex(ValueError, "Recursive actions must use the same character"):
            perform_action(state, "p1", 1, 0, Suit.DIAMONDS, dug_indices=[0])
        
        # Correctly use character 0 (or None)
        # Use a Diamond in the hand for the second action
        state.dug_cards = [Card(rank=5, suit=Suit.DIAMONDS)]
        perform_action(state, "p1", 0, 0, Suit.DIAMONDS, dug_indices=[0])
        self.assertEqual(p1.coins, 5)

    def test_clubs_direct_face_kill(self):
        """Clubs attack on an exposed face card should kill the character."""
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[Card(rank=10, suit=Suit.CLUBS)])
        ])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="Q", suit=Suit.HEARTS, stack=[]) # Exposed
        ])
        state = GameState(players=[p1, p2], phase=2, turn_subphase="BATTLE_ACTION", current_turn_index=0)
        
        # Damage >= 1 kills exposed face
        perform_action(state, "p1", 0, 1, Suit.CLUBS, target_info={
            'target_player_id': "p2",
            'target_char_index': 0
        })
        
        self.assertEqual(len(p2.characters), 0)
        self.assertFalse(p2.is_alive)

    def test_spade_dig_to_face_strike(self):
        """Digging to the face card allows an unexposed Face Strike."""
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[
                Card(rank=5, suit=Suit.HEARTS), # To be dug
                Card(rank=2, suit=Suit.SPADES) # The action card
            ])
        ])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="Q", suit=Suit.HEARTS, stack=[])
        ])
        state = GameState(players=[p1, p2], phase=2, turn_subphase="BATTLE_ACTION")
        
        # Dig with Spade
        perform_action(state, "p1", 0, 1, Suit.SPADES)
        # Card(2, Spades) was popped for action. Card(5, Hearts) was dug. Stack is now empty.
        self.assertEqual(len(p1.characters[0].stack), 0)
        
        # Now apply face strike (allowed because we are digging)
        apply_face_strike(state, "p1", 0, "p2", 0)
        self.assertEqual(len(p2.characters), 0)

    def test_face_strike_suicide_prevention(self):
        """Failed Face Strike doesn't suicide if cards were removed by digging earlier."""
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[
                Card(rank=5, suit=Suit.HEARTS), 
                Card(rank=2, suit=Suit.SPADES)
            ])
        ])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="Q", suit=Suit.HEARTS, stack=[Card(rank=10, suit=Suit.HEARTS)]) # Protection
        ])
        state = GameState(players=[p1, p2], phase=2, turn_subphase="BATTLE_ACTION")
        
        # Digging counts as removing cards (from stack to dug pool)
        perform_action(state, "p1", 0, 1, Suit.SPADES)
        self.assertTrue(state.cards_removed_this_turn)
        
        # Failed face strike
        apply_face_strike(state, "p1", 0, "p2", 0)
        
        # Should NOT suicide because cards_removed_this_turn is True
        self.assertEqual(len(p1.characters), 1)
        self.assertTrue(p1.is_alive)

    def test_must_act_with_tap(self):
        """Tapping a character prevents the Must-Act penalty."""
        p1 = Player(id="p1", name="P1", characters=[Character(rank="J", suit=Suit.CLUBS, stack=[])])
        state = GameState(players=[p1], phase=2, turn_subphase="BATTLE_ACTION")
        
        state.character_tapped_this_turn = True
        end_turn(state)
        
        self.assertEqual(len(p1.characters), 1)
        self.assertTrue(p1.is_alive)

    def test_phase2_tiebreaker(self):
        """Highest unique Spade rank wins. Ties cancel out."""
        p1 = Player(id="p1", name="P1", characters=[
            Character(rank="J", suit=Suit.CLUBS, stack=[Card(rank=10, suit=Suit.SPADES, is_ace=True)])
        ])
        p2 = Player(id="p2", name="P2", characters=[
            Character(rank="Q", suit=Suit.CLUBS, stack=[Card(rank=10, suit=Suit.SPADES, is_ace=True)])
        ])
        p3 = Player(id="p3", name="P3", characters=[
            Character(rank="K", suit=Suit.CLUBS, stack=[Card(rank=8, suit=Suit.SPADES)])
        ])
        
        state = GameState(players=[p1, p2, p3], phase=1)
        transition_to_phase_2(state)
        
        # Aces (rank 11) tie between P1 and P2, so P3 wins with rank 8
        self.assertEqual(state.current_turn_index, 2)

    def test_turn_skip_dead_player(self):
        """Turn progression should skip players with no characters."""
        p1 = Player(id="p1", name="P1", characters=[Character(rank="J", suit=Suit.CLUBS, stack=[])])
        p2 = Player(id="p2", name="P2", characters=[], is_alive=False)
        p3 = Player(id="p3", name="P3", characters=[Character(rank="K", suit=Suit.CLUBS, stack=[])])
        
        state = GameState(players=[p1, p2, p3], phase=2, current_turn_index=0)
        state.action_taken_this_turn = True # To avoid Must-Act
        
        end_turn(state)
        
        # Should skip P2 and go to P3
        self.assertEqual(state.current_turn_index, 2)

if __name__ == '__main__':
    unittest.main()
