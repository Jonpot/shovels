# CORE-2: Phase 1 Logic

## Goal
Implement the "Character Creation" phase logic.

## Prerequisites
- [CORE-1: Game State and Entities](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/CORE-1-Game-State.md)
- [Technical Specification §3](file:///c:/Users/jonat/Desktop/Personal/shovels/docs/TechnicalSpecification.md#3-phase-mechanics)

## Description
Implement the logic for Phase 1 in `shovels_engine/engine.py`:

- **Setup:** Distribute 3 face-down characters to each player. Initialize the Shop pile (20 cards).
- **Turn Sequence:**
  - `draw_cards(source)`: Draw from deck or top of discard.
  - `play_card(card, target_stack)`: If number card, add to stack. If face card, replace character.
  - `discard_card(card)`: Send to discard pile.
- **Cycle Control:** Ensure clockwise turn order and check for deck depletion.
- **Transition:** logic to reveal stacks and determine the first active player for Phase 2 (highest Spade rank).

## Definition of Done
- Phase 1 logic fully implemented.
- Unit tests for drawing, playing, and discarding logic.
- Tests for the transition to Phase 2.
