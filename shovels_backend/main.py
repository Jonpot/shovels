from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shovels_backend.manager import GameRoomManager
from shovels_backend.schemas import RoomCreateRequest, RoomInfoResponse
from typing import List

app = FastAPI(title="Shovels API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

room_manager = GameRoomManager()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/rooms", response_model=List[RoomInfoResponse])
def list_rooms():
    rooms = room_manager.list_rooms()
    return [
        RoomInfoResponse(
            room_id=r.room_id,
            name=r.name,
            player_count=len(r.player_ids),
            is_started=r.state is not None
        ) for r in rooms
    ]

@app.post("/rooms", response_model=RoomInfoResponse)
def create_room(request: RoomCreateRequest):
    room = room_manager.create_room(request.name)
    return RoomInfoResponse(
        room_id=room.room_id,
        name=room.name,
        player_count=len(room.player_ids),
        is_started=room.state is not None
    )

@app.post("/rooms/{room_id}/join")
def join_room(room_id: str, player_id: str):
    try:
        room_manager.join_room(room_id, player_id)
        return {"message": "Joined successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
