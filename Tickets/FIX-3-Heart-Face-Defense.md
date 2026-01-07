# FIX-3: Heart Face Defense Reactions

## Goal
Implement reactive tapping of Heart Face cards to defend against incoming attacks.

## User Reports
- BUG-3: Cannot tap Heart Face cards to defend when attacked

## Prerequisites
- [CORE-3: Phase 2 Actions](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/CORE-3-Phase-2-Actions.md)
- [FIX-2: Club Face Multi-Attack](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/FIX-2-Club-Face-Multi-Attack.md)

## Description
**Current Behavior:**
- When attacked, defender cannot react by tapping Heart Face cards
- Attacks resolve using only passive Heart card protection

**Correct Behavior (per Official Rules):**
- When a character is attacked, the defending player gets a chance to react
- Defender can tap untapped Heart Face cards (J♥, Q♥, K♥) on that character
- Tapped Heart Faces add shield value: J♥=11, Q♥=12, K♥=13
- Shield is temporary and only applies to this specific attack
- After reaction window, attack resolves normally with added shield

**Example:**
1. Attacker plays 8♣ + 5♣ = 13 damage to opponent's character
2. Defender's character has 4♥ on stack (base shield = 4)
3. Defender taps J♥ on that character (adds 11 shield)
4. Total shield = 4 + 11 = 15, so attack fails to break the heart

## Technical Approach
This requires implementing a **reactive interrupt system**.

**Engine (`shovels_engine/engine.py`):**

1. **Attack Resolution Refactor:**
   - Before applying damage, enter DEFENSE_REACTION subphase
   - Set `pending_attack` in GameState with attacker, target, damage
   - Switch active player to defender temporarily
   - Wait for defender's reaction (tap heart faces or pass)

2. **Reaction Handling:**
   - Add `react_to_attack(defender_id, character_index, tap_faces: bool)`
   - If tapping, validate hearts are untapped on target character
   - Calculate temporary shield bonus
   - Add shield to character for this attack only

3. **Resume Attack:**
   - After reaction (or timeout), switch back to attacker
   - Resolve attack with accumulated shield
   - Clear temporary shield immediately after

4. **State Management:**
   - Add `pending_attack: Optional[PendingAttack]` to GameState
   - Add `temporary_shield: int` to Character
   - Add DEFENSE_REACTION to Subphase enum

**Backend (`shovels_backend/main.py`):**
- Broadcast state change when entering DEFENSE_REACTION
- Add WebSocket route for `react_to_attack` action
- Handle timeout if defender doesn't respond (auto-pass)

**Frontend (`shovels_frontend/src/`):**
- Show modal/overlay when in DEFENSE_REACTION subphase
- Highlight attacked character and available Heart Faces
- Provide "Tap to Defend" and "Pass" buttons
- Display pending attack details (damage, attacker)

## Definition of Done
- Defender can tap Heart Faces during attack resolution
- Tapped Heart Faces add temporary shield to attack
- Shield clears after attack resolves
- Frontend shows clear reaction UI
- Unit tests cover reaction timing and shield calculation
- Integration test for full attack-reaction-resolution flow
