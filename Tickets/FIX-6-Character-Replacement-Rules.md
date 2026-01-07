# FIX-6: Character Replacement Rules

## Goal
Enforce correct Phase 2 character replacement rules and allow playing Jacks to empty slots.

## User Reports
- BUG-6: Phase 2 replacement rules incorrect, cannot play Jack to empty slot

## Prerequisites
- [CORE-2: Phase 1](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/CORE-2-Phase-1.md)
- [CORE-3: Phase 2 Actions](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/CORE-3-Phase-2-Actions.md)

## Description
**Current Behavior:**
- Can "sidegrade" (replace Jack with Jack, Queen with Queen)
- Can downgrade (replace King with Queen, Queen with Jack)
- Cannot select empty character slot to play cards

**Correct Behavior (per Official Rules):**

**Phase 1 Replacement:**
- Any face card can replace any other face card (correctly implemented)

**Phase 2 Replacement (UPGRADE ONLY):**
- **Jack → Queen or King ONLY**
- **Queen → King ONLY**
- **King → Cannot be replaced**
- No sidegrades (J→J, Q→Q)
- No downgrades (K→Q, K→J, Q→J)

**Dead Character Replacement:**
- When a character dies (stack completely removed), slot becomes empty
- Player can play **Jack ONLY** to empty slot to create new character
- This is the only way to recover from losing a character

## Technical Approach
**Engine (`shovels_engine/engine.py`):**

1. **Update `play_card()` Validation:**
   - Add phase check for replacement rules
   - Phase 1: Allow any face-to-face replacement (current behavior)
   - Phase 2: Validate upgrade-only rule

2. **Phase 2 Upgrade Logic:**
   ```python
   def can_replace_character(current_face: Card, new_face: Card, phase: int) -> bool:
       if phase == 1:
           return True  # Any replacement allowed

       # Phase 2: Upgrade only
       face_hierarchy = {'J': 0, 'Q': 1, 'K': 2}
       current_rank = face_hierarchy[current_face.rank]
       new_rank = face_hierarchy[new_face.rank]
       return new_rank > current_rank
   ```

3. **Empty Slot Handling:**
   - Character with empty stack is represented as `Character(stack=[], is_dead=True)`
   - Add UI affordance to select dead character slots
   - Validate only Jacks can be played to dead slots
   - Create new Character with Jack as face card

4. **Validation in `play_card()`:**
   - Check if target character is dead → only allow Jack
   - Check if target character exists → apply phase-specific replacement rules
   - Reject invalid replacements with clear error message

**Frontend (`shovels_frontend/src/`):**

1. **Dead Character Slots:**
   - Render empty character slot as placeholder with "Empty" or skull icon
   - Make slot clickable when holding a Jack
   - Show visual feedback that Jack can be played here

2. **Replacement Validation:**
   - Before allowing card play, check Phase 2 upgrade rules
   - Show error message if trying invalid replacement
   - Highlight valid targets in green when holding replacement face

## Definition of Done
- Phase 2 replacement only allows upgrades (J→Q/K, Q→K)
- King cannot be replaced in Phase 2
- Dead character slots are selectable
- Only Jacks can be played to empty slots
- Frontend shows clear visual feedback for valid/invalid placements
- Unit tests cover all replacement scenarios
- Integration test for character death and Jack replacement
