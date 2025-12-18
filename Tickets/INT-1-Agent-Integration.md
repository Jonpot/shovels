# INT-1: Agent Integration

## Goal
Enable RL agents to play in the web application.

## Prerequisites
- [GYM-2: Training Pipeline](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/GYM-2-Training-Pipeline.md)
- [BE-3: Real-time Comms](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/BE-3-Real-time-Comms.md)
- [Technical Specification](file:///c:/Users/jonat/Desktop/Personal/shovels/docs/TechnicalSpecification.md)

## Description
- Create a "Bot Client" in `shovels_agent/bot_client.py`.
- This client should:
  - Connect to a room via WebSockets (acting like a player).
  - Use a trained SB3 model to predict actions based on the game state received.
  - Send actions back to the server.
- Backend should support spawning these bot clients on-demand when a user clicks "Add AI Bot" in the lobby.

## Definition of Done
- Users can add an AI opponent to their lobby.
- The AI plays legally and manages its stacks/actions based on its training.
