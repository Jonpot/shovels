# FIX-8: Face Strike Implementation

## Goal
Fix face striking to properly deal 1 damage and end turn.

## User Reports
- BUG-7: Face striking doesn't deal damage or end turn

## Prerequisites
- [CORE-3: Phase 2 Actions](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/CORE-3-Phase-2-Actions.md)

## Description
**Current Behavior:**
- Face striking does nothing (no damage, turn doesn't end)

**Correct Behavior (per Official Rules):**
- Face strike is a special action available when character has no cards above face
- Deals exactly **1 damage** to target opponent character
- Can be blocked by any Heart card (since damage = 1)
- Can be defended by tapping Heart Face (adds shield)
- **Ends attacker's turn** after resolution

**When Available:**
- Character's stack is empty except for face card (no cards to discard)
- OR after Spade gravedigging exposes the face card

**Rule Rationale:**
- Face strike is a weak but guaranteed action
- Prevents total stall when you have no cards to discard
- Only useful for finishing off unprotected characters

## Technical Approach
**Engine (`shovels_engine/engine.py`):**

1. **Update `apply_face_strike()`:**
   - Validate: Selected character has only face card (or face is exposed via gravedigging)
   - Apply 1 damage to target character
   - Check shield: if target has any Heart card, attack fails (shield >= 1)
   - If shield < 1, remove top card from target stack

2. **Heart Protection:**
   - Heart cards should block 1 damage face strikes
   - Reuse existing heart-breaking logic from `resolve_suit_effect()`
   - If damage breaks heart, remove heart card and cards above it

3. **End Turn After Face Strike:**
   - After `apply_face_strike()` resolves, call `end_turn()`
   - This is different from other actions which allow continued play

4. **Availability Check:**
   ```python
   def can_face_strike(character: Character) -> bool:
       """Face strike available when only face card remains"""
       return len(character.stack) == 1  # Only face card
       # OR during gravedigging if all cards are dug
   ```

**Integration with Defense Reactions:**
- Face strike should trigger defense reaction window (from FIX-3)
- Defender can tap Heart Face to add shield against the 1 damage
- This makes face strikes blockable even without heart cards

**Backend (`shovels_backend/main.py`):**
- Ensure face_strike action calls `end_turn()` after resolution
- Broadcast turn change to all players

**Frontend (`shovels_frontend/src/`):**
- Show "Face Strike" button when character is empty
- Display targeting UI (similar to club attacks)
- Show damage = 1 in UI feedback

## Definition of Done
- Face strike deals exactly 1 damage to target
- Can be blocked by any Heart card
- Turn ends automatically after face strike
- Available when character is empty or fully dug
- Unit tests for face strike damage and blocking
- Integration test for face strike → defense reaction → turn end
