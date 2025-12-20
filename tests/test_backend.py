import pytest
from fastapi.testclient import TestClient
from shovels_backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_and_list_rooms():
    # Initially no rooms
    response = client.get("/rooms")
    assert response.status_code == 200
    assert response.json() == []

    # Create a room
    response = client.post("/rooms", json={"name": "Test Room"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Room"
    room_id = data["room_id"]

    # List rooms again
    response = client.get("/rooms")
    assert response.status_code == 200
    rooms = response.json()
    assert len(rooms) == 1
    assert rooms[0]["room_id"] == room_id

def test_join_room():
    # Create a room
    response = client.post("/rooms", json={"name": "Join Test"})
    room_id = response.json()["room_id"]

    # Join the room
    response = client.post(f"/rooms/{room_id}/join?player_id=player1")
    assert response.status_code == 200
    assert response.json() == {"message": "Joined successfully"}

    # Verify player count
    response = client.get("/rooms")
    rooms = response.json()
    # Find the correct room in the list
    room = next(r for r in rooms if r["room_id"] == room_id)
    assert room["player_count"] == 1
