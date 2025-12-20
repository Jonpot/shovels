from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from shovels_backend.manager import GameRoomManager
from shovels_backend.schemas import RoomCreateRequest, RoomInfoResponse
from shovels_backend.auth import oauth, create_access_token, get_current_user, SECRET_KEY, decode_access_token
from shovels_backend.ws_schemas import WsMessage
from shovels_engine import engine
from typing import List
import os
import json

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

@app.websocket("/ws/room/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str):
    # Verify JWT from query param
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
        user_data = {"id": user_id, "email": payload.get("email"), "name": payload.get("name")}
    except Exception:
        await websocket.close(code=4001)
        return

    room = room_manager.get_room(room_id)
    if not room:
        await websocket.close(code=4004)
        return

    await room.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_dict = json.loads(data)
            msg = WsMessage(**message_dict)
            
            if msg.type == "start_game":
                try:
                    await room.start_game()
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Could not start game: {str(e)}"})
            
            elif msg.type == "action":
                if not room.state:
                    await websocket.send_json({"type": "error", "message": "Game not started"})
                    continue
                
                action_data = msg.data
                action_type = action_data.get("action_type")
                params = action_data.get("params", {})
                
                try:
                    # Map action types to engine functions
                    if action_type == "draw":
                        engine.draw_cards(room.state, user_data["id"], **params)
                    elif action_type == "discard":
                        engine.discard_card(room.state, user_data["id"], **params)
                    elif action_type == "play":
                        engine.play_card(room.state, user_data["id"], **params)
                    elif action_type == "buy":
                        engine.buy_card(room.state, user_data["id"], **params)
                    elif action_type == "refresh":
                        engine.refresh_shop(room.state, user_data["id"])
                    elif action_type == "tap":
                        engine.tap_hero_power(room.state, user_data["id"], **params)
                    elif action_type == "gravedig":
                        engine.resolve_gravedig(room.state, user_data["id"], **params)
                    elif action_type == "action":
                        engine.perform_action(room.state, user_data["id"], **params)
                    elif action_type == "strike":
                        engine.apply_face_strike(room.state, user_data["id"], **params)
                    else:
                        await websocket.send_json({"type": "error", "message": f"Unknown action: {action_type}"})
                        continue
                        
                    # Broadcast update
                    await room.broadcast_state()
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        room.disconnect(websocket)
