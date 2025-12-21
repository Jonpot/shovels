import pytest
import json
from fastapi.testclient import TestClient
from shovels_backend.main import app
from shovels_backend.auth import create_access_token, get_current_user

client = TestClient(app)

# Mock user dependency
def get_mock_user_1():
    return {"id": "user1", "email": "user1@example.com", "name": "User One"}

def get_mock_user_2():
    return {"id": "user2", "email": "user2@example.com", "name": "User Two"}

from fastapi import WebSocketDisconnect

def test_ws_unauthorized():
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/room/test_room?token=invalid") as websocket:
            pass
    assert excinfo.value.code == 4001

def test_ws_game_flow():
    # 1. Setup room and players
    app.dependency_overrides[get_current_user] = get_mock_user_1
    response = client.post("/rooms", json={"name": "WS Room"})
    room_id = response.json()["room_id"]
    client.post(f"/rooms/{room_id}/join?player_id=user1")
    
    app.dependency_overrides[get_current_user] = get_mock_user_2
    client.post(f"/rooms/{room_id}/join?player_id=user2")
    
    # 2. Get tokens
    token1 = create_access_token({"sub": "user1", "email": "user1@example.com", "name": "User One"})
    token2 = create_access_token({"sub": "user2", "email": "user2@example.com", "name": "User Two"})
    
    # 3. Connect User 1 and User 2
    with client.websocket_connect(f"/ws/room/{room_id}?token={token1}") as ws1:
        with client.websocket_connect(f"/ws/room/{room_id}?token={token2}") as ws2:
            # Drain lobby messages
            ws1.receive_json() # user1 joined
            ws1.receive_json() # user2 joined
            ws2.receive_json() # user2 joined (self)
            
            # 4. User 1 starts game
            ws1.send_json({"type": "start_game"})
            
            # 5. Verify both receive state
            data1 = ws1.receive_json()
            assert data1["type"] == "state_update"
            assert data1["state"]["phase"] == 1
            
            data2 = ws2.receive_json()
            assert data2["type"] == "state_update"
            assert data2["state"]["phase"] == 1
            assert data2["state"] == data1["state"]

            # 6. User 1 performs "draw" action
            # Figure out who the current player is
            state = data1["state"]
            current_player = state["players"][state["current_turn_index"]]
            
            if current_player["id"] == "user1":
                ws1.send_json({
                    "type": "action",
                    "data": {
                        "action_type": "draw",
                        "params": {"sources": ["DECK", "DECK"]}
                    }
                })
                
                # 7. Verify both receive update
                update1 = ws1.receive_json()
                assert update1["type"] == "state_update"
                assert update1["state"]["turn_subphase"] == "DISCARD"
                
                update2 = ws2.receive_json()
                assert update2["type"] == "state_update"
                assert update2["state"]["turn_subphase"] == "DISCARD"
    
    app.dependency_overrides.clear()
