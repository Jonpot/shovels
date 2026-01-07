# FIX-2: Club Face Multi-Attack

## Goal
Fix Queen and King of Clubs to allow multiple attacks per tap.

## User Reports
- BUG-2: Queen/King of Clubs only allows single 10-damage attack

## Prerequisites
- [CORE-4: Hero Powers & Shop](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/CORE-4-Hero-Powers-Shop.md)

## Description
**Current Behavior:**
- Tapping Queen of Clubs allows only 1 attack of 10 damage
- Tapping King of Clubs allows only 1 attack of 10 damage

**Correct Behavior (per Official Rules):**
- **Queen of Clubs:** 2 attacks of 10 damage each (different targets)
- **King of Clubs:** 3 attacks of 10 damage each (different targets)
- Each attack must target a different opponent character
- All attacks happen in a single action

**Rule Constraint:**
- Each attack within a multi-attack must target a different character
- If there aren't enough valid targets, only perform as many attacks as possible
- Example: Queen vs 1 opponent with 1 character = only 1 attack

## Technical Approach
**Engine (`shovels_engine/engine.py`):**

1. **Update `tap_hero_power()` for Clubs:**
   - When tapping Q♣ or K♣, set a counter for remaining attacks
   - Enter a multi-attack subphase or loop
   - Track which characters have already been targeted this turn

2. **Target Validation:**
   - After each attack, mark target as "hit this multi-attack"
   - Validate subsequent targets are different characters
   - Auto-complete if no more valid targets exist

3. **State Management:**
   - Add `multi_attack_remaining: int` to GameState
   - Add `multi_attack_targets_hit: List[tuple]` to track (player_id, char_index)
   - Clear after all attacks or turn end

**Backend (`shovels_backend/main.py`):**
- Update WebSocket handler to support multi-attack flow
- Broadcast state after each individual attack

## Definition of Done
- Queen of Clubs allows 2 attacks of 10 damage each
- King of Clubs allows 3 attacks of 10 damage each
- Each attack must target a different character
- All attacks complete in a single action
- Unit tests cover multi-attack scenarios and edge cases
