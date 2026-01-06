# CORE-5: Game Loop & Conditions

## Goal
Finalize the game flow, turns, and win/loss conditions.

## Prerequisites
- [CORE-4: Hero Powers & Shopping](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/CORE-4-Hero-Powers-Shop.md)
- [Technical Specification §3.2 (Must-Act Rule)](file:///c:/Users/jonat/Desktop/Personal/shovels/docs/TechnicalSpecification.md#32-phase-2-battle)

## Description
- **Turn Management:** Refill shop at end of turn. Advance to next player.
- **Fatigue (Must-Act):** Check at start of turn if a player has legal moves. If not, trigger character death (Fatigue).
- **Win Condition:** Detect when only one player (or one player's team) remains.
- **Logging:** Implement a formal Event log for playback and debugging.

## Definition of Done
- Complete game loop from Phase 1 start to Phase 2 win.
- Unit tests for "Fatigue" scenarios.
- Integration test for a full automated game (random moves).
