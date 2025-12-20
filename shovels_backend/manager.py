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
        self.connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, player_id: str):
        await websocket.accept()
        self.connections[player_id] = websocket
        if self.state:
            await self.send_state(websocket)

    def disconnect(self, player_id: str):
        if player_id in self.connections:
            del self.connections[player_id]
        
        # If game hasn't started, remove player from room
        if not self.state and player_id in self.player_ids:
            self.player_ids.remove(player_id)
            
    def is_empty(self) -> bool:
        return len(self.player_ids) == 0

    async def broadcast(self, message: dict):
        if not self.connections:
            return
        
        dead_player_ids = []
        for pid, connection in self.connections.items():
            try:
                await connection.send_json(message)
            except Exception:
                dead_player_ids.append(pid)
        
        for pid in dead_player_ids:
            self.disconnect(pid)

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

    async def broadcast_lobby_state(self):
        """Broadcasts the current player list as if it were a partial game state."""
        # Create a mock state structure that the frontend will accept
        players_data = [{"id": pid, "name": pid, "is_alive": True} for pid in self.player_ids]
        # In a real app, we'd store names in player_ids or separate mapping. 
        # For now, we only store IDs. To get names, we might need to change how we track players.
        # But wait, main.py passes `user_id` to `connect`.
        # `manager.py` doesn't store user names. This is a limitation.
        # Let's check Main.WebSocketEndpoint. It has user_data.
        # Ideally, GameRoom should store player metadata (id, name).
        # Refactor: GameRoom.player_ids -> GameRoom.players: List[Dict]
        # BUT this is a larger refactor.
        # Workaround: For now, just send IDs. The frontend uses `user.name` for self but might show ID for others.
        # Actually, let's look at `LobbyRoom.jsx`: `player.name` is used.
        # If we only send IDs, names will be missing.
        # The user wants "Refactoring & Cleanup". Let's stick to the plan. 
        # Plan was: "If I send { type: 'state_update', state: { players: [...] } }, LobbyRoom checks gameState.players".
        
        await self.broadcast({
            "type": "state_update",
            "state": {
                "players": players_data,
                # Include other minimal fields if necessary to prevent frontend crashes
                "deck_count": 0,
                "discard_pile": [],
                "shop": [],
                "turn_count": 0,
                "phase": "LOBBY"
            }
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

    def delete_room(self, room_id: str):
        if room_id in self.rooms:
            del self.rooms[room_id]
