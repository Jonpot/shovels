# BE-3: Real-time Comms

## Goal
Implement WebSockets for real-time game synchronization.

## Prerequisites
- [BE-1: Server Skeleton](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/BE-1-Server-Skeleton.md)

## Description
- Implement `/ws/room/{room_id}` endpoint.
- Broadcast game state updates to all connected users in a room.
- Handle player actions (clicks from frontend) via WebSocket incoming messages.
- Logic to handle disconnections and re-joins.

## Definition of Done
- Multi-client synchronization of a shared game state.
- Actions performed by one client are visible to others in real-time.
