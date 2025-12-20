from typing import Dict, List, Optional, Set
import uuid
import json
from fastapi import WebSocket
from shovels_engine.models import GameState, setup_game

class GameRoom:
    def __init__(self, room_id: str, name: str):
        self.room_id = room_id
        self.name = name
        self.state: Optional[GameState] = None
        self.player_ids: List[str] = []
        self.connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)
        if self.state:
            await self.send_state(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def broadcast(self, message: dict):
        if not self.connections:
            return
        
        # Create a list to avoid "Set size changed during iteration" errors
        dead_connections = []
        for connection in list(self.connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        for dead in dead_connections:
            self.connections.remove(dead)

    async def send_state(self, websocket: WebSocket):
        if self.state:
            await websocket.send_json({
                "type": "state_update",
                "state": self.state.model_dump()
            })

    async def broadcast_state(self):
        if self.state:
            await self.broadcast({
                "type": "state_update",
                "state": self.state.model_dump()
            })

    async def start_game(self):
        if len(self.player_ids) < 2:
            raise ValueError("Need at least 2 players to start game")
        self.state = setup_game(self.player_ids)
        await self.broadcast_state()

class GameRoomManager:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}

    def create_room(self, name: str) -> GameRoom:
        room_id = str(uuid.uuid4())[:8]
        room = GameRoom(room_id, name)
        self.rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Optional[GameRoom]:
        return self.rooms.get(room_id)

    def list_rooms(self) -> List[GameRoom]:
        return list(self.rooms.values())

    def join_room(self, room_id: str, player_id: str):
        room = self.get_room(room_id)
        if not room:
            raise ValueError("Room not found")
        if player_id not in room.player_ids:
            room.player_ids.append(player_id)
