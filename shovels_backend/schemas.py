from pydantic import BaseModel

class RoomCreateRequest(BaseModel):
    name: str

class PlayerInfo(BaseModel):
    id: str

class RoomInfoResponse(BaseModel):
    room_id: str
    name: str
    player_count: int
    is_started: bool
