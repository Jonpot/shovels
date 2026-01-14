# FIX-11: Gravedigging Error After Face Strike

## Goal
Fix erroneous "Gravedigging" error dialog appearing after performing a face strike.

## User Reports
- BUG-13: After using spades action to dig up to face card and perform a face strike, an error box appears saying "Gravedigging" "ERROR: No character selected in GRAVEDIGGING"

## Description
**Current Behavior:**
- Player performs a spades action
- Digs cards up to their face card
- Performs a face strike with the dug cards
- Error dialog appears: "Gravedigging - ERROR: No character selected in GRAVEDIGGING"
- User is not gravedigging at all

**Correct Behavior:**
- After a face strike completes, the turn/action should resolve normally
- No gravedigging prompt should appear unless the player specifically triggered gravedigging
- The subphase should transition correctly after face strike resolution

## Technical Approach
**Engine (`shovels_engine/engine.py`):**

1. **Investigate Subphase Transitions:**
   - Find where `GRAVEDIGGING` subphase is entered
   - Check `apply_face_strike()` and surrounding logic
   - Identify what triggers the incorrect subphase transition

2. **Fix Subphase Flow:**
   - After face strike resolution, ensure subphase returns to `BATTLE_ACTION` or appropriate state
   - Only enter `GRAVEDIGGING` when explicitly triggered by gravedigging action

**Frontend (`shovels_frontend/src/views/GameBoard.jsx`):**
- Check how the frontend responds to subphase state
- Ensure error handling doesn't show false positives

## Definition of Done
- Face strike completes without triggering gravedigging error
- Subphase correctly transitions after face strike
- Gravedigging subphase only activates for actual gravedigging actions
- No erroneous error dialogs appear
