from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from shovels_backend.manager import GameRoomManager
from shovels_backend.schemas import RoomCreateRequest, RoomInfoResponse
from shovels_backend.auth import oauth, create_access_token, get_current_user, SECRET_KEY
from typing import List
import os

app = FastAPI(title="Shovels API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware required for OAuth state
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

room_manager = GameRoomManager()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Auth Endpoints
@app.get("/auth/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@app.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
    
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")
    
    # Create JWT
    access_token = create_access_token(
        data={
            "sub": user_info['sub'],
            "email": user_info['email'],
            "name": user_info.get('name')
        }
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/rooms", response_model=List[RoomInfoResponse])
def list_rooms(user: dict = Depends(get_current_user)):
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
def create_room(request: RoomCreateRequest, user: dict = Depends(get_current_user)):
    room = room_manager.create_room(request.name)
    return RoomInfoResponse(
        room_id=room.room_id,
        name=room.name,
        player_count=len(room.player_ids),
        is_started=room.state is not None
    )

@app.post("/rooms/{room_id}/join")
def join_room(room_id: str, player_id: str, user: dict = Depends(get_current_user)):
    try:
        room_manager.join_room(room_id, player_id)
        return {"message": "Joined successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
