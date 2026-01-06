# CORE-3: Phase 2 Actions

## Goal
Implement the core Battle actions (Clubs, Diamonds, Hearts, Spades).

## Prerequisites
- [CORE-2: Phase 1 Logic](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/CORE-2-Phase-1.md)
- [Technical Specification §3.2](file:///c:/Users/jonat/Desktop/Personal/shovels/docs/TechnicalSpecification.md#32-phase-2-battle)

## Description
Implement the "Action Hand" logic and suit effects:

- `form_action_hand(character, cards)`: Validate cards are from top of stack.
- `resolve_action(suit, total_rank)`:
  - **Clubs (Attack):** Damage calculation vs target Heart rank. Nested removal of cards above.
  - **Diamonds (Coins):** Return coin count for current turn.
  - **Hearts (Stall):** Passive action.
  - **Spades (Shovels):** Logic to extract sub-stack and trigger a new action hand.
- `apply_face_strike(character, target)`: Free 1-damage logic with "must-remove-card" constraint.

## Definition of Done
- Action resolution logic implemented.
- Robust unit tests for combat (Hearts removal, character death).
- Tests for Shovel/Digging chains.
