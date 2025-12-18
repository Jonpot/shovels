# BE-1: Server Skeleton

## Goal
Set up the FastAPI server and game session management.

## Prerequisites
- [CORE-5: Game Loop & Conditions](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/CORE-5-Game-Loop.md)
- [Technical Specification §2 (Data Models)](file:///c:/Users/jonat/Desktop/Personal/shovels/docs/TechnicalSpecification.md#2-core-data-models)

## Description
- Initialize a FastAPI project in `shovels_backend/`.
- Implement `GameRoomManager`:
  - Handle creating rooms, joining rooms, and listing rooms.
  - Store game instances in memory (or Redis for scalability).
- Define REST endpoints for:
  - `GET /rooms`: List available lobbies.
  - `POST /rooms`: Create a new lobby.
- Setup CORS for the frontend.

## Definition of Done
- FastAPI server running with health check.
- Functional room manager that can hold multiple game states.
