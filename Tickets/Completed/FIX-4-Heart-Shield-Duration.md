# FIX-4: Heart Shield Duration Fix

## Goal
Fix Heart Face tapping on your own turn to grant temporary (not permanent) shield.

## User Reports
- BUG-10: Tapping Heart Face on your own turn gives permanent shield

## Prerequisites
- [CORE-4: Hero Powers & Shop](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/CORE-4-Hero-Powers-Shop.md)

## Description
**Current Behavior:**
- Tapping a Heart Face (J♥, Q♥, K♥) on your own turn grants permanent shield
- This shield persists across turns indefinitely

**Correct Behavior (per Official Rules):**
- Tapping Heart Face on your own turn is allowed (it's a valid stall action)
- The shield granted should be **temporary** and last only until end of current turn
- This makes self-tapping Hearts effectively a no-op (just burns your turn)
- Shield should immediately clear when turn ends

**Rule Rationale:**
- Heart Face tapping is primarily a defensive **reaction** to attacks
- Self-tapping is permitted but provides no lasting benefit
- This prevents abuse of Heart Face powers for permanent defense

## Technical Approach
**Engine (`shovels_engine/engine.py`):**

1. **Distinguish Shield Sources:**
   - Currently `character.shield` is a single integer
   - Need to track: `base_shield` (from stacked hearts) vs `temporary_shield`
   - Or add `temporary_shield_expires_turn: Optional[int]` field

2. **Update `tap_hero_power()` for Hearts:**
   - When tapping J♥/Q♥/K♥, add shield value to `temporary_shield`
   - Set `shield_expires_turn = current_turn_number`

3. **Clear Temporary Shield in `end_turn()`:**
   - Check all characters for expired shields
   - Clear `temporary_shield` where `shield_expires_turn == current_turn`
   - This ensures self-tapped shields only last for that turn

4. **Shield Calculation:**
   - Update damage calculation to sum `base_shield + temporary_shield`
   - When heart breaks, subtract from combined shield pool

**Models (`shovels_engine/models.py`):**
- Add `temporary_shield: int = 0` to Character
- Add `shield_expires_turn: Optional[int] = None` to Character
- Update `total_shield` property to return `base_shield + temporary_shield`

## Definition of Done
- Tapping Heart Face on your own turn grants shield only until end of turn
- Shield is cleared automatically when turn ends
- Base shield from stacked hearts remains unchanged
- Unit tests verify shield expiration timing
- Integration test shows self-tapped hearts don't provide lasting benefit
