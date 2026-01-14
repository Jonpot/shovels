# FIX-12: Card Selection Disabled in Inappropriate States

## Goal
Restrict card selection to only valid game states where selection is meaningful.

## User Reports
- BUG-14: Cards can be selected when they shouldn't be - during opponent's turn, when selecting characters for shop cards, during attacks, etc.

## Description
**Current Behavior:**
- Cards can be selected at any time regardless of game state
- Selection is enabled during opponent's turn
- Selection is enabled while in SHOPPING subphase (selecting characters)
- Selection is enabled during attack resolution

**Correct Behavior:**
Cards should ONLY be selectable in these scenarios:
1. **Start of own turn in Phase 2** - to select cards for an action
2. **After performing a Spades action** - to select dug cards for continued play
3. **During GRAVEDIGGING subphase** - when specifically choosing cards from grave

Cards should NOT be selectable:
- During opponent's turn
- While in SHOPPING subphase (selecting target characters)
- During attack resolution
- During any other player's action

## Technical Approach
**Frontend (`shovels_frontend/src/views/GameBoard.jsx`):**

1. **Create Selection State Logic:**
   - Add a computed/derived state: `canSelectCards`
   - Base this on: `isMyTurn`, `currentSubphase`, `gamePhase`

2. **Conditions for `canSelectCards = true`:**
   ```javascript
   const canSelectCards =
     isMyTurn &&
     gameState.phase === 2 &&
     (subphase === 'BATTLE_ACTION' ||
      subphase === 'GRAVEDIGGING' ||
      subphase === 'DIG_SELECTION');
   ```

3. **Apply to Card Components:**
   - Pass `canSelectCards` to card rendering components
   - Disable click/selection handlers when false
   - Optionally add visual feedback (dimmed appearance) when not selectable

4. **Stack Component Updates:**
   - Ensure character stack cards respect selection state
   - Disable hover/click interactions appropriately

## Definition of Done
- Cards cannot be selected during opponent's turn
- Cards cannot be selected during SHOPPING subphase
- Cards cannot be selected during attack resolution
- Cards CAN be selected at start of turn in Phase 2
- Cards CAN be selected after spades actions for dig selection
- Visual feedback indicates when cards are not selectable
