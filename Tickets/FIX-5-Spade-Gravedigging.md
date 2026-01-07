# FIX-5: Spade Gravedigging System

## Goal
Fix Spade actions to properly implement the gravedigging mechanic.

## User Reports
- BUG-8: Spade actions delete cards instead of flagging them for selection

## Prerequisites
- [CORE-3: Phase 2 Actions](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/CORE-3-Phase-2-Actions.md)

## Description
**Current Behavior:**
- Using Spade action deletes entire character stack up to face card
- Cards disappear from the game entirely (not even discarded)

**Correct Behavior (per Official Rules):**
1. Calculate Spade action value (sum of ranks of all spades played/discarded)
2. Count that many cards from the TOP of target character's stack
3. Flag those cards as "dug up" / available for next action
4. Player effectively repeats their turn, but can now:
   - Select ANY combination of flagged cards (not just from top)
   - Discard them for another action (including another Spade action)
5. If Spade value exceeds stack size, all cards are flagged
6. If you dig to the face card, you can perform a face strike

**Example:**
- Character stack: [J♠, 9♣, 7♥, 5♦, K♥ (face)]
- Play 6♠ + 3♠ = 9 spade value
- All 4 cards above face are flagged: [J♠, 9♣, 7♥, 5♦]
- Player can now discard any combination of those cards for next action
- E.g., discard 9♣ alone for an attack, or 7♥+5♦ for coins, etc.

## Technical Approach
**Engine (`shovels_engine/engine.py`):**

1. **Gravedigging State:**
   - Add `dug_cards: List[Card]` to Character
   - Add GRAVEDIGGING to Subphase enum
   - When Spade action resolves, flag top N cards and enter GRAVEDIGGING

2. **Card Selection During Gravedigging:**
   - Allow selecting ANY cards from `dug_cards` (not just contiguous from top)
   - Validate selection is subset of `dug_cards`
   - After action, remove discarded cards from stack AND `dug_cards`
   - Exit GRAVEDIGGING and return to BATTLE_ACTION

3. **Recursive Spades:**
   - If player performs another Spade action during gravedigging
   - Re-calculate flagged cards from current stack state
   - Update `dug_cards` to new flagged set

4. **Face Strike Accessibility:**
   - If `len(dug_cards) == len(character.stack) - 1`, face is exposed
   - Allow face strike as valid action

**Backend (`shovels_backend/main.py`):**
- Update action routing to handle GRAVEDIGGING subphase
- Broadcast updated `dug_cards` state to all players

**Frontend (`shovels_frontend/src/`):**

1. **Visual Indicator:**
   - Add green glowing border to cards in `dug_cards` list
   - This is distinct from blue border (currently selected)
   - Shows which cards are available for selection

2. **Selection Logic:**
   - Allow clicking any green-bordered card individually
   - Don't require contiguous selection from top
   - Selected cards get both green (available) and blue (selected) borders

3. **UI Feedback:**
   - Show message: "Gravedigging: Select from flagged cards"
   - Display count of available cards

## Definition of Done
- Spade actions flag cards instead of deleting them
- Flagged cards shown with green border in frontend
- Player can select any combination of flagged cards
- Recursive Spade actions work correctly
- Face strike becomes available when fully dug
- Cards are properly discarded after gravedigging action
- Unit tests cover gravedigging flow and edge cases
- Integration test for multi-level Spade chains
