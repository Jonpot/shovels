# FIX-10: Phase 2 Deck Initialization

## Goal
Fix deck/discard pile setup when transitioning from Phase 1 to Phase 2.

## User Reports
- BUG-12: When Phase 2 starts, discard pile remains at ~52 cards and deck stays empty

## Description
**Current Behavior:**
- When Phase 2 starts, the deck remains empty
- The discard pile stays at ~52 cards
- Shop cards are drawn from an empty deck (unclear behavior)

**Correct Behavior (per Official Rules):**
1. When Phase 2 starts, the 20 cards set aside during setup should be added to the discard pile
2. The entire discard pile should then be shuffled
3. This shuffled pile becomes the new draw deck
4. 3 starting shop cards are drawn from this new deck

## Technical Approach
**Engine (`shovels_engine/engine.py` or `models.py`):**

1. **Locate Phase Transition Logic:**
   - Find where `game_state.phase` changes from 1 to 2
   - This likely occurs in `end_turn()` or a dedicated transition function

2. **Implement Deck Reset:**
   - Add the 20 set-aside cards (shop pile) to the discard pile
   - Shuffle the combined discard pile
   - Set this as the new deck
   - Clear the discard pile
   - Draw 3 cards for the initial shop

3. **State Updates:**
   - `game_state.deck` = shuffled discard + shop cards
   - `game_state.discard_pile` = []
   - `game_state.shop` = first 3 drawn cards

## Definition of Done
- When Phase 2 starts, discard pile is shuffled into a new deck
- The 20 set-aside shop cards are included in this shuffle
- Shop has 3 cards drawn from the new deck
- Discard pile is empty after transition
- Unit tests verify correct deck/discard counts at Phase 2 start
