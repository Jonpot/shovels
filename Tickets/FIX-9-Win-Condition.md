# FIX-9: Win Condition Detection

## Goal
Detect game end and display victory screen when one player remains.

## User Reports
- BUG-11: Game doesn't end when one player wins

## Prerequisites
- [CORE-5: Game Loop & Conditions](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/CORE-5-Game-Loop.md)

## Description
**Current Behavior:**
- Game continues even when only one player has living characters
- No victory detection or end screen

**Correct Behavior (per Official Rules):**
- Game ends immediately when only one player has any characters alive
- That player is declared the winner
- Display victory screen with:
  - Winner announcement
  - Final stats (optional: damage dealt, cards played, etc.)
  - Button to return to lobby

**Win Condition:**
- Player wins if all opponents have 0 living characters
- Living character = character with at least a face card (stack not empty)
- Check after every action that could kill a character:
  - Club attacks
  - Face strikes
  - Fatigue (losing character due to no valid actions)

## Technical Approach
**Engine (`shovels_engine/engine.py`):**

1. **Win Detection Function:**
   ```python
   def check_win_condition(game: GameState) -> Optional[str]:
       """Returns winner player_id if game is over, None otherwise"""
       living_players = []

       for player in game.players:
           has_living_character = any(
               len(char.stack) > 0 for char in player.characters
           )
           if has_living_character:
               living_players.append(player.id)

       if len(living_players) == 1:
           return living_players[0]
       elif len(living_players) == 0:
           return "DRAW"  # Edge case: simultaneous death
       return None
   ```

2. **Check After Damage Actions:**
   - After `resolve_suit_effect()` (club attacks)
   - After `apply_face_strike()`
   - After fatigue damage
   - If winner detected, set `game.winner = player_id` and `game.game_over = True`

3. **State Management:**
   - Add `game_over: bool = False` to GameState
   - Add `winner: Optional[str] = None` to GameState
   - Once game_over is True, reject all further actions

**Backend (`shovels_backend/main.py`):**
- After each action, check win condition
- If game over, broadcast final state with winner
- Preserve GameRoom for a grace period (30 seconds) for players to see result

**Frontend (`shovels_frontend/src/`):**

1. **Victory Screen Component:**
   - Create `VictoryScreen.jsx` component
   - Show when `game.game_over === true`
   - Display winner name (or "You Win!" if current player)
   - Show game stats (optional):
     - Total turns
     - Characters eliminated
     - Final coin count

2. **Return to Lobby:**
   - "Return to Lobby" button
   - Disconnects WebSocket and navigates to lobby browser
   - Could show rematch option (future enhancement)

3. **In-Game Detection:**
   - In `GameBoard.jsx`, check `game.game_over` after each state update
   - If true, render VictoryScreen overlay

## Definition of Done
- Game detects winner when only one player has living characters
- Victory screen displays winner and game stats
- "Return to Lobby" button works correctly
- No actions can be performed after game_over = true
- Unit tests for win detection in various scenarios
- Integration test for full game → character death → victory
