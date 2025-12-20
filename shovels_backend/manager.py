from typing import Dict, List, Optional
import uuid
from shovels_engine.models import GameState, setup_game

class GameRoom:
    def __init__(self, room_id: str, name: str):
        self.room_id = room_id
        self.name = name
        self.state: Optional[GameState] = None
        self.player_ids: List[str] = []

    def start_game(self):
        if len(self.player_ids) < 2:
            raise ValueError("Need at least 2 players to start game")
        self.state = setup_game(self.player_ids)

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
