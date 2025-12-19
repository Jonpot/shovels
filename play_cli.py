import sys
import json
from shovels_engine.models import setup_game, Suit
from shovels_engine.engine import (
    draw_cards, discard_card, play_card, 
    perform_action, apply_face_strike, 
    tap_hero_power, resolve_gravedig, buy_card,
    get_current_player, end_turn
)
from shovels_engine.cli_utils import print_state, print_banner, print_bot_summary
from shovels_engine.agents import RandomAgent

def get_input(prompt="> "):
    return input(prompt).strip().lower()

def play_cli():
    print("Welcome to SHOVELS CLI!")
    try:
        num_players = int(input("Number of players (2-4): ") or "2")
    except:
        num_players = 2
    
    player_ids = [f"p{i+1}" for i in range(num_players)]
    human_ids = []
    for pid in player_ids:
        choice = input(f"Is {pid} human? (y/n, default n): ").lower()
        if choice == 'y':
            human_ids.append(pid)
    
    state = setup_game(player_ids)
    bot = RandomAgent()
    last_phase = state.phase

    while not state.is_over:
        if state.phase != last_phase:
            print_banner(f"PHASE {state.phase} START")
            last_phase = state.phase
            input("Press Enter to continue...")

        current_player = get_current_player(state)
        print_state(state)
        
        if current_player.id in human_ids:
            print(f"\nYOUR TURN ({current_player.id})")
            cmd_line = get_input()
            if not cmd_line:
                continue
                
            parts = cmd_line.split()
            base = parts[0]
            
            try:
                if base == "quit":
                    sys.exit(0)
                elif base == "help":
                    print("\nCommands:")
                    print("  draw [deck/discard] [deck/discard] - e.g. draw deck deck")
                    print("  discard <hand_idx>")
                    print("  play <hand_idx> [char_idx/none]")
                    print("  action <char_idx> <num_cards> <suit> - e.g. action 0 2 clubs")
                    print("  strike <char_idx> <target_p_id> <target_char_idx>")
                    print("  tap <char_idx> - Follow prompts for targets")
                    print("  buy <slot_idx> <char_idx>")
                    print("  gravedig <idx1> <idx2>... - Indices from pool")
                    print("  end - End turn")
                    print("  logs - Show events")
                    input("\nPress Enter to continue...")
                    continue
                
                elif base == "logs":
                    print("\nRecent Events:")
                    for e in state.events[-10:]:
                        print(f"  {e['event_type']}: {e['data']}")
                    input("\nPress Enter to continue...")
                    continue

                elif base == "draw":
                    sources = [s.upper() for s in parts[1:]] if len(parts) > 1 else ["DECK", "DECK"]
                    draw_cards(state, current_player.id, sources)
                
                elif base == "discard":
                    idx = int(parts[1])
                    discard_card(state, current_player.id, idx)
                
                elif base == "play":
                    if len(parts) == 2:
                        # Shortcut: play <char_idx> -> play 0 <char_idx>
                        h_idx = 0
                        c_idx = int(parts[1])
                    elif len(parts) > 2:
                        h_idx = int(parts[1])
                        c_idx = int(parts[2]) if parts[2] != 'none' else None
                    else:
                        print("Usage: play <char_idx> OR play <hand_idx> <char_idx>")
                        continue
                    play_card(state, current_player.id, h_idx, c_idx)
                
                elif base == "action":
                    c_idx = int(parts[1])
                    num = int(parts[2])
                    suit = Suit[parts[3].upper()]
                    target_info = None
                    if suit == Suit.CLUBS:
                        t_p = input("Target Player ID: ")
                        t_c = int(input("Target Character Index: "))
                        target_info = {"target_player_id": t_p, "target_char_index": t_c}
                    
                    # Check for recursion
                    dug_indices = None
                    if state.dug_cards:
                        print(f"Dug Cards: {[str(c) for c in state.dug_cards]}")
                        indices_str = input("Indices to use from DUG (comma separated): ")
                        dug_indices = [int(i.strip()) for i in indices_str.split(",")] if indices_str else []
                    
                    perform_action(state, current_player.id, c_idx, num, suit, target_info=target_info, dug_indices=dug_indices)
                
                elif base == "strike":
                    c_idx = int(parts[1])
                    t_p = parts[2]
                    t_c = int(parts[3])
                    apply_face_strike(state, current_player.id, c_idx, t_p, t_c)
                
                elif base == "tap":
                    c_idx = int(parts[1])
                    char = current_player.characters[c_idx]
                    target_info = None
                    if char.suit == Suit.CLUBS:
                        limit = {"J": 1, "Q": 2, "K": 3}[char.rank]
                        print(f"Clubs Burst! Choose up to {limit} targets.")
                        targets = []
                        for _ in range(limit):
                            inp = input(f"Target {len(targets)+1} (p_id char_idx) or 'done': ")
                            if inp.lower() == 'done': break
                            tp, tc = inp.split()
                            targets.append({"target_player_id": tp, "target_char_index": int(tc)})
                        target_info = {"targets": targets}
                    tap_hero_power(state, current_player.id, c_idx, target_info)
                
                elif base == "buy":
                    slot = int(parts[1])
                    c_idx = int(parts[2])
                    buy_card(state, current_player.id, slot, c_idx)
                
                elif base == "gravedig":
                    indices = [int(i) for i in parts[1:]]
                    resolve_gravedig(state, current_player.id, state.active_character_index, indices)
                
                elif base == "end":
                    end_turn(state)
                
                else:
                    print("Unknown command. Type 'help' for info.")
            
            except Exception as e:
                print(f"ERROR: {e}")
                input("\nPress Enter to try again...")
        
        else:
            print(f"Bot {current_player.id} is thinking...")
            bot.act(state, current_player.id)
            print_bot_summary(state, current_player.id)
            input("\nPress Enter to continue...")
    
    print_state(state)
    print(f"\nGAME OVER! Winner: {state.winner_id}")

if __name__ == "__main__":
    play_cli()
