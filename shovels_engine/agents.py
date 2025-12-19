import random
from shovels_engine.models import GameState, Suit
from shovels_engine.engine import (
    draw_cards, discard_card, play_card, 
    perform_action, apply_face_strike, 
    tap_hero_power, resolve_gravedig, buy_card,
    get_current_player, end_turn
)

class Agent:
    def act(self, state: GameState, player_id: str):
        raise NotImplementedError

class RandomAgent(Agent):
    def act(self, state: GameState, player_id: str):
        """Performs a random valid action based on the current subphase."""
        player = next(p for p in state.players if p.id == player_id)
        
        try:
            if state.phase == 1:
                if state.turn_subphase == "DRAW":
                    sources = []
                    temp_deck_count = len(state.deck)
                    temp_discard_count = len(state.discard_pile)
                    
                    for _ in range(2):
                        if temp_deck_count > 0:
                            sources.append("DECK")
                            temp_deck_count -= 1
                        elif temp_discard_count > 0:
                            sources.append("DISCARD")
                            temp_discard_count -= 1
                            
                    if len(sources) == 2:
                        # Enforce DISCARD first if drawing from both
                        if "DISCARD" in sources and "DECK" in sources:
                            sources = ["DISCARD", "DECK"]
                        draw_cards(state, player_id, sources)
                    else:
                        end_turn(state)
                elif state.turn_subphase == "DISCARD":
                    discard_card(state, player_id, 0)
                elif state.turn_subphase == "PLAY":
                    # Try to play a card on a valid character index
                    played = False
                    # Randomize order to avoid bias towards index 0
                    candidates = list(range(len(player.characters) + 1))
                    random.shuffle(candidates)
                    for c_idx in candidates:
                        target_idx = c_idx if c_idx < len(player.characters) else None
                        if target_idx is not None and target_idx >= state.max_characters:
                            target_idx = None
                        try:
                            play_card(state, player_id, 0, target_idx)
                            played = True
                            break
                        except ValueError:
                            continue
                    if not played:
                        end_turn(state)
            
            else:
                # Phase 2
                if state.turn_subphase == "BATTLE_ACTION":
                    if state.dug_cards:
                        # Recursive action using dug cards
                        suits = {c.suit for c in state.dug_cards}
                        suit = random.choice(list(suits))
                        indices = [i for i, c in enumerate(state.dug_cards) if c.suit == suit]
                        
                        target_info = None
                        if suit == Suit.CLUBS:
                            target_players = [p for p in state.players if p.is_alive and p.id != player_id]
                            if target_players:
                                target_p = random.choice(target_players)
                                target_c_idx = random.choice(range(len(target_p.characters)))
                                target_info = {'target_player_id': target_p.id, 'target_char_index': target_c_idx}
                        
                        perform_action(state, player_id, state.active_character_index, 0, suit, dug_indices=indices, target_info=target_info)
                        return

                    action_type = random.choice(["HAND", "TAP", "STRIKE"])
                    char_indices = [i for i, c in enumerate(player.characters)]
                    if not char_indices:
                        end_turn(state)
                        return
                        
                    char_idx = random.choice(char_indices)
                    char = player.characters[char_idx]
                    
                    if action_type == "TAP" and not char.is_tapped:
                        target_info = None
                        if char.suit == Suit.CLUBS:
                            target_info = {'targets': []}
                            for p in state.players:
                                if p.is_alive and p.id != player_id:
                                    for c_idx in range(len(p.characters)):
                                        target_info['targets'].append({'target_player_id': p.id, 'target_char_index': c_idx})
                            random.shuffle(target_info['targets'])
                            target_info['targets'] = target_info['targets'][:{"J": 1, "Q": 2, "K": 3}[char.rank]]
                        try:
                            tap_hero_power(state, player_id, char_idx, target_info)
                            return
                        except:
                            action_type = "HAND"
                    
                    if action_type == "STRIKE":
                        target_players = [p for p in state.players if p.is_alive and p.id != player_id]
                        if target_players:
                            target_p = random.choice(target_players)
                            target_c_idx = random.choice(range(len(target_p.characters)))
                            try:
                                apply_face_strike(state, player_id, char_idx, target_p.id, target_c_idx)
                                return
                            except:
                                action_type = "HAND"
                        else:
                            action_type = "HAND"
                    
                    if action_type == "HAND":
                        if not char.stack:
                            end_turn(state)
                            return
                            
                        num_cards = random.randint(1, len(char.stack))
                        suits = {c.suit for c in char.stack[-num_cards:]}
                        suit = random.choice(list(suits))
                        
                        target_info = None
                        if suit == Suit.CLUBS:
                            target_players = [p for p in state.players if p.is_alive and p.id != player_id]
                            if target_players:
                                target_p = random.choice(target_players)
                                target_c_idx = random.choice(range(len(target_p.characters)))
                                target_info = {'target_player_id': target_p.id, 'target_char_index': target_c_idx}
                            else:
                                end_turn(state)
                                return
                        
                        perform_action(state, player_id, char_idx, num_cards, suit, target_info=target_info)

                elif state.turn_subphase in ["SHOPPING", "SHOP_FREE_BUY"]:
                    valid_slots = [i for i, c in enumerate(state.shop_row) if c is not None]
                    played_in_shop = False
                    if valid_slots:
                        slot = random.choice(valid_slots)
                        char_idx = random.choice(range(len(player.characters)))
                        try:
                            buy_card(state, player_id, slot, char_idx)
                            played_in_shop = True
                        except:
                            pass
                    
                    if not played_in_shop or (player.coins < 3 and state.turn_subphase == "SHOPPING"):
                        end_turn(state)

                elif state.turn_subphase == "GRAVEDIGGING":
                    num_pool = len(state.gravedig_pool)
                    char = player.characters[state.active_character_index]
                    limit = {"J": 1, "Q": 2, "K": 3}[char.rank]
                    indices = random.sample(range(num_pool), min(limit, num_pool))
                    resolve_gravedig(state, player_id, state.active_character_index, indices)

        except Exception as e:
            # Fallback
            try:
                end_turn(state)
            except:
                pass
