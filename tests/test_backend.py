import pytest
from fastapi.testclient import TestClient
from shovels_backend.main import app

client = TestClient(app)

from fastapi import Depends
from shovels_backend.auth import get_current_user

# Mock user
def get_mock_user():
    return {"id": "test_user", "email": "test@example.com", "name": "Test User"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_unauthorized_access():
    response = client.get("/rooms")
    assert response.status_code == 401

def test_create_and_list_rooms():
    # Override auth
    app.dependency_overrides[get_current_user] = get_mock_user
    
    # Initially no rooms (clean state for this test if possible, but manager is global)
    # For now just check we can create one
    response = client.post("/rooms", json={"name": "Test Room"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Room"
    room_id = data["room_id"]

    # List rooms again
    response = client.get("/rooms")
    assert response.status_code == 200
    rooms = response.json()
    assert any(r["room_id"] == room_id for r in rooms)
    
    # Clean up override
    app.dependency_overrides.clear()

def test_join_room():
    app.dependency_overrides[get_current_user] = get_mock_user
    
    # Create a room
    response = client.post("/rooms", json={"name": "Join Test"})
    room_id = response.json()["room_id"]

    # Join the room
    response = client.post(f"/rooms/{room_id}/join?player_id=player1")
    assert response.status_code == 200
    assert response.json() == {"message": "Joined successfully"}

    # Verify player count (creator + player1)
    response = client.get("/rooms")
    rooms = response.json()
    room = next(r for r in rooms if r["room_id"] == room_id)
    assert room["player_count"] == 2
    
    app.dependency_overrides.clear()
