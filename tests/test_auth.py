import pytest
from datetime import timedelta
from jose import jwt
from shovels_backend.auth import create_access_token, ALGORITHM, SECRET_KEY, get_current_user
from fastapi import HTTPException
import asyncio

def test_create_access_token():
    data = {"sub": "user123", "email": "user@example.com"}
    token = create_access_token(data)
    assert isinstance(token, str)
    
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user123"
    assert payload["email"] == "user@example.com"
    assert "exp" in payload

@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    data = {"sub": "user123", "email": "user@example.com", "name": "User One"}
    token = create_access_token(data)
    
    user = await get_current_user(token)
    assert user["id"] == "user123"
    assert user["email"] == "user@example.com"
    assert user["name"] == "User One"

@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user("invalid_token")
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Could not validate credentials"

@pytest.mark.asyncio
async def test_get_current_user_missing_sub():
    data = {"email": "user@example.com"} # Missing 'sub'
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token)
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid token"
