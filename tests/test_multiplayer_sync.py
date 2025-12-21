import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from shovels_backend.manager import GameRoom, GameRoomManager
from fastapi import WebSocket

@pytest.mark.asyncio
async def test_lobby_join_broadcasts_update():
    """
    Test that when a second player joins, BOTH players receive an update
    with the full list of players.
    """
    # 1. Setup Room
    manager = GameRoomManager()
    room = manager.create_room("Test Room")
    
    # 2. Mock WebSockets
    ws1 = AsyncMock(spec=WebSocket)
    ws2 = AsyncMock(spec=WebSocket)
    
    # 3. Player 1 Connects
    manager.join_room(room.room_id, "p1", "Player One")
    await room.connect(ws1, "p1")
    
    # Expect P1 to get an update about themselves
    # The current code might or might not do this, but the fix should ensure it does.
    # We want to check what happens when P2 joins.
    
    # 4. Player 2 Connects
    manager.join_room(room.room_id, "p2", "Player Two")
    await room.connect(ws2, "p2")
    
    # 5. Verify P1 received an update about P2 joining
    # ws1.send_json should have been called with a message containing 2 players
    
    # Collect all calls to send_json for P1
    p1_calls = ws1.send_json.call_args_list
    
    found_p2_update = False
    for call in p1_calls:
        args, _ = call
        msg = args[0]
        if msg.get("type") == "state_update" and "players" in msg.get("state", {}):
            players = msg["state"]["players"]
            if len(players) == 2:
                names = set(p["name"] for p in players)
                if "Player One" in names and "Player Two" in names:
                    found_p2_update = True
                    break
    
    assert found_p2_update, "Player 1 did not receive a lobby update with 2 players when Player 2 joined"
    
    # 6. Verify P2 received the initial state with 2 players as well
    p2_calls = ws2.send_json.call_args_list
    found_initial_state = False
    for call in p2_calls:
        args, _ = call
        msg = args[0]
        if msg.get("type") == "state_update" and "players" in msg.get("state", {}):
            players = msg["state"]["players"]
            if len(players) == 2:
                found_initial_state = True
                break
                
    assert found_initial_state, "Player 2 did not receive the lobby state with 2 players upon joining"
