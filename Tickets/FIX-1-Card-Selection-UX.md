# FIX-1: Card Selection UX Improvements

## Goal
Streamline card selection interactions and fix Phase 2 visual overlapping.

## User Reports
- BUG-1: Cumbersome character selection workflow
- BUG-9: Hand block overlaps Phase 2 UI elements

## Prerequisites
- [FE-4: Phase 2 UI](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/FE-4-Phase-2-UI.md)

## Description
**Auto-Select Character (BUG-1):**
- Clicking a card in a character's stack should automatically select that character as the action source
- This eliminates the need to click the character first in 90% of cases
- Tapping powers still requires explicit character selection first

**Stack Selection from Any Card (BUG-1):**
- Currently: Must select cards one-by-one from the top of the stack
- New behavior: Clicking any card in a stack selects that card AND all cards above it
- This allows quick multi-card selection without repeated clicks
- Maintains rule validation (cards must be contiguous from top)

**Hide Hand Block in Phase 2 (BUG-9):**
- Hand is not used in Phase 2, but the hand block still renders
- This causes the main game blocks to extend downward and get cut off
- Solution: Conditionally hide hand block when `game.phase === 2`

## Technical Approach
**Frontend (`shovels_frontend/src/`):**

1. **Auto-Select Character:**
   - In `GameBoard.jsx`, add click handler to cards in character stacks
   - When card clicked, automatically set `selectedCharacter` to that character's index
   - Preserve existing behavior for explicit character selection (for tapping)

2. **Range Selection:**
   - Modify card selection logic to detect which card was clicked
   - Calculate range from clicked card to top of stack
   - Select all cards in that range with visual feedback (blue glow)

3. **Conditional Hand Rendering:**
   - In `GameBoard.jsx`, wrap hand rendering in phase check:
     ```jsx
     {game.phase === 1 && <HandSection />}
     ```

## Definition of Done
- Clicking any card in a stack auto-selects that character and all cards above
- Hand block is hidden during Phase 2
- No visual overlap issues in Phase 2
- Selection behavior feels intuitive and quick
