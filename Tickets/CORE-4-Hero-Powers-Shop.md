# CORE-4: Hero Powers & Shopping

## Goal
Implement character specialized powers and the shop system.

## Prerequisites
- [CORE-3: Phase 2 Actions](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/CORE-3-Phase-2-Actions.md)
- [Technical Specification §4 & §5](file:///c:/Users/jonat/Desktop/Personal/shovels/docs/TechnicalSpecification.md#4-hero-powers-tap-once-per-life)

## Description
- **Hero Powers:**
  - Implement "Tap Once per Life" logic.
  - Suits: Clubs (Burst Attack), Diamonds (Free Purchase), Spades (Gravedig), Hearts (Reaction Shield).
  - Reaction Shield must support out-of-turn execution (interruption logic).
- **Shopping:**
  - `buy_card(slot)`: Spend coins, move card to stack.
  - `refresh_shop()`: Spend 2 coins to wipe and refill.
  - Enforce upgrade rules (J -> Q -> K) and new stack limits.

## Definition of Done
- All Hero Powers implemented.
- Shopping system with coin management and upgrade validation.
- Tests for out-of-turn Hearts Reactor shield.
