# FIX-13: Spades Hero Power Hand Not Visible

## Goal
Fix the hand display for Spades face card hero powers so drawn cards are visible.

## User Reports
- BUG-15: Spades Hero power doesn't work - supposed to draw 5 cards from discard, but no hand appears. Discard pile decreases (cards are drawn) but hand is not rendered. Suspected cause: Hand element hidden during Phase 2 to avoid covering other elements.

## Description
**Current Behavior:**
- Tapping Spades face card (J/Q/K) triggers hero power
- Cards are correctly drawn from discard pile (count decreases)
- Hand is NOT visible to the player
- Player cannot select 1/2/3 cards to play to the tapped character
- Hand element appears to be hidden during Phase 2

**Correct Behavior (per Official Rules):**
- **Jack of Spades:** Draw 5 from discard, play 1 to this character
- **Queen of Spades:** Draw 5 from discard, play 2 to this character
- **King of Spades:** Draw 5 from discard, play 3 to this character
- Hand should be visible and allow card selection
- Selected cards are played to the tapped spades character

## Technical Approach
**Frontend (`shovels_frontend/src/views/GameBoard.jsx`):**

1. **Investigate Hand Visibility:**
   - Find where hand rendering is controlled
   - Check if there's a Phase 2 condition hiding the hand
   - Identify CSS/conditional rendering that hides hand

2. **Fix Hand Display:**
   - Hand should be visible when `player.hand.length > 0` regardless of phase
   - May need to reposition hand during Phase 2 to avoid overlapping
   - Consider a modal/overlay approach for hero power hand selection

3. **Possible Solutions:**
   - **Option A:** Reposition hand element to non-overlapping location in Phase 2
   - **Option B:** Use a modal/dialog for hero power card selection
   - **Option C:** Use absolute positioning with higher z-index
   - **Option D:** Collapse other elements when hand is active

4. **Add Selection UI:**
   - Show visual indicator for how many cards must be selected (1/2/3)
   - Add "Confirm Selection" button
   - Validate correct number of cards selected

## Definition of Done
- Spades hero power draws cards and displays them visibly
- Player can see and select from drawn cards
- J/Q/K correctly require 1/2/3 card selections respectively
- Selected cards are played to the tapped spades character
- Hand display doesn't permanently obstruct other game elements
- Works correctly for all three spades face cards
