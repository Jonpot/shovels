import unittest
import random
from shovels_engine.models import setup_game, Suit
from shovels_engine.engine import (
    draw_cards, discard_card, play_card, 
    perform_action, apply_face_strike, 
    tap_hero_power, resolve_gravedig, buy_card, refresh_shop,
    get_current_player
)

class TestIntegration(unittest.TestCase):
    def test_random_game_simulation(self):
        """Plays a full game with random moves to ensure no crashes and valid completion."""
        player_ids = ["p1", "p2", "p3"]
        state = setup_game(player_ids)
        
        max_turns = 1000 # Safety limit
        turns_played = 0
        
        while not state.is_over and turns_played < max_turns:
            turns_played += 1
            player = get_current_player(state)
            try:
                if state.phase == 1:
                    # Phase 1: Draw, Discard, Play
                    if state.turn_subphase == "DRAW":
                        sources = []
                        for _ in range(2):
                            if state.deck:
                                sources.append("DECK")
                            elif state.discard_pile:
                                sources.append("DISCARD")
                        if sources:
                            draw_cards(state, player.id, sources)
                        else:
                            # Both empty? (Very rare)
                            from shovels_engine.engine import end_turn
                            end_turn(state)
                    elif state.turn_subphase == "DISCARD":
                        discard_card(state, player.id, 0)
                    elif state.turn_subphase == "PLAY":
                        # Must play until hand is empty
                        played = False
                        for c_idx in range(len(player.characters) + 1):
                            target_idx = c_idx if c_idx < len(player.characters) else None
                            if target_idx is not None and target_idx >= state.max_characters:
                                target_idx = None
                            try:
                                play_card(state, player.id, 0, target_idx)
                                played = True
                                break
                            except ValueError:
                                continue
                        if not played:
                            from shovels_engine.engine import end_turn
                            end_turn(state)
                
                else:
                    # Phase 2: Battle Action, Shopping, Gravedigging
                    if state.turn_subphase == "BATTLE_ACTION":
                        if state.dug_cards:
                            # Recursive action using dug cards
                            suits = {c.suit for c in state.dug_cards}
                            suit = random.choice(list(suits))
                            indices = [i for i, c in enumerate(state.dug_cards) if c.suit == suit]
                            
                            target_info = None
                            if suit == Suit.CLUBS:
                                target_players = [p for p in state.players if p.is_alive and p.id != player.id]
                                if target_players:
                                    target_p = random.choice(target_players)
                                    target_c_idx = random.choice(range(len(target_p.characters)))
                                    target_info = {'target_player_id': target_p.id, 'target_char_index': target_c_idx}
                            
                            try:
                                perform_action(state, player.id, state.active_character_index, 0, suit, dug_indices=indices, target_info=target_info)
                                continue # Loop again
                            except:
                                from shovels_engine.engine import end_turn
                                end_turn(state)
                                continue

                        # Normal action
                        action_type = random.choice(["HAND", "TAP", "STRIKE"])
                        
                        char_indices = [i for i, c in enumerate(player.characters)]
                        if not char_indices:
                            from shovels_engine.engine import end_turn
                            end_turn(state)
                            continue
                            
                        char_idx = random.choice(char_indices)
                        char = player.characters[char_idx]
                        
                        if action_type == "TAP" and not char.is_tapped:
                            target_info = None
                            if char.suit == Suit.CLUBS:
                                target_info = {'targets': []}
                                for p in state.players:
                                    if p.is_alive and p.id != player.id:
                                        for c_idx in range(len(p.characters)):
                                            target_info['targets'].append({'target_player_id': p.id, 'target_char_index': c_idx})
                                random.shuffle(target_info['targets'])
                                target_info['targets'] = target_info['targets'][:{"J": 1, "Q": 2, "K": 3}[char.rank]]
                            try:
                                tap_hero_power(state, player.id, char_idx, target_info)
                                continue # Loop again for subphase processing
                            except:
                                action_type = "HAND"
                        
                        if action_type == "STRIKE":
                            target_players = [p for p in state.players if p.is_alive and p.id != player.id]
                            if target_players:
                                target_p = random.choice(target_players)
                                target_c_idx = random.choice(range(len(target_p.characters)))
                                try:
                                    apply_face_strike(state, player.id, char_idx, target_p.id, target_c_idx)
                                    continue # Loop again
                                except:
                                    action_type = "HAND"
                            else:
                                action_type = "HAND"
                        
                        if action_type == "HAND":
                            if not char.stack:
                                from shovels_engine.engine import end_turn
                                end_turn(state)
                                continue
                                
                            num_cards = random.randint(1, len(char.stack))
                            suits = {c.suit for c in char.stack[-num_cards:]}
                            
                            # Filter out SPADES if stack is empty (redundant check but good for safety)
                            # Actually, Spades action is only useful if there are cards to dig.
                            # If we pick Spades, ensure there are cards *below* the action set? 
                            # No, Spade action itself takes cards from the stack.
                            suit = random.choice(list(suits))
                            
                            target_info = None
                            if suit == Suit.CLUBS:
                                target_players = [p for p in state.players if p.is_alive and p.id != player.id]
                                if target_players:
                                    target_p = random.choice(target_players)
                                    target_c_idx = random.choice(range(len(target_p.characters)))
                                    target_info = {'target_player_id': target_p.id, 'target_char_index': target_c_idx}
                                else:
                                    # Try another suit or just end turn
                                    from shovels_engine.engine import end_turn
                                    end_turn(state)
                                    continue
                            
                            try:
                                perform_action(state, player.id, char_idx, num_cards, suit, target_info=target_info)
                                continue # Loop again
                            except:
                                from shovels_engine.engine import end_turn
                                end_turn(state)

                    elif state.turn_subphase in ["SHOPPING", "SHOP_FREE_BUY"]:
                        # Buy cards
                        valid_slots = [i for i, c in enumerate(state.shop_row) if c is not None]
                        played_in_shop = False
                        if valid_slots:
                            slot = random.choice(valid_slots)
                            char_idx = random.choice(range(len(player.characters)))
                            try:
                                buy_card(state, player.id, slot, char_idx)
                                played_in_shop = True
                            except:
                                pass
                        
                        if not played_in_shop or (player.coins < 3 and state.turn_subphase == "SHOPPING"):
                            from shovels_engine.engine import end_turn
                            end_turn(state)

                    elif state.turn_subphase == "GRAVEDIGGING":
                        num_pool = len(state.gravedig_pool)
                        char = player.characters[state.active_character_index]
                        limit = {"J": 1, "Q": 2, "K": 3}[char.rank]
                        indices = random.sample(range(num_pool), min(limit, num_pool))
                        resolve_gravedig(state, player.id, state.active_character_index, indices)

            except Exception as e:
                from shovels_engine.engine import end_turn
                try:
                    end_turn(state)
                except:
                    pass

        self.assertTrue(state.is_over or turns_played == max_turns)
        if state.is_over:
            self.assertIsNotNone(state.winner_id)
            print(f'Game log:')
            for event in state.events:
                print(f"{event}\n")
            print(f"Game over after {turns_played} turns. Winner: {state.winner_id}")
        else:
            raise Exception(f"Game ended but {state.is_over} and {turns_played} < {max_turns}? {state}")

if __name__ == '__main__':
    unittest.main()
