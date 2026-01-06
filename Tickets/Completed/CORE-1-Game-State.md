# CORE-1: Game State and Entities

## Goal
Implement the basic data structures and classes needed to represent a game of Shovels.

## Prerequisites
- Study the [Technical Specification](file:///c:/Users/jonat/Desktop/Personal/shovels/docs/TechnicalSpecification.md) for data models and constants.
- Reference the [Original Rules](file:///c:/Users/jonat/Desktop/Personal/shovels/Shovels%20%E2%80%91%20A%20Build%E2%80%91&%E2%80%91Battle%20Card%20Game.html).

## Description
Create the foundational Python classes in `shovels_engine/models.py`. Ensure all classes are serializable (e.g., using `pydantic` or `dataclasses` with JSON support):

- `Suit` (Enum): CLUBS, DIAMONDS, HEARTS, SPADES.
- `Card` (Class): `rank` (2-10, A=10), `suit`, `is_face` (bool).
- `Character` (Class): `rank` (J, Q, K), `suit`, `stack` (List[Card]), `is_tapped` (bool), `has_reactor_shield_used` (bool).
- `Player` (Class): `id`, `name`, `characters`, `coins` (int, default 0), `is_alive` (bool).
- `GameState` (Class): `deck` (List[Card]), `shop_pile` (List[Card]), `shop_row` (List[Card]), `discard_pile` (List[Card]), `players` (List[Player]), `current_turn_index` (int), `phase` (1 or 2).

## Definition of Done
- All classes implemented in `shovels_engine/models.py`.
- Initialization logic for a default 104-card deck (2x52).
- Basic unit tests covering initialization and serialization to JSON.
