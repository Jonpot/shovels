# Local Mode Setup Guide

This guide explains how to run Shovels in local development mode without Google OAuth.

## Quick Start

### 1. Backend Setup

The `.env` file has already been created in `shovels_backend/.env` with:
```
LOCAL_MODE=true
JWT_SECRET_KEY=local-dev-secret-key-change-in-production
FRONTEND_URL=http://localhost:5173
```

### 2. Install Dependencies

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
# or
source .venv/bin/activate      # Unix/Mac

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Start Backend

```bash
# Run backend (ensure venv is activated)
uvicorn shovels_backend.main:app --reload
```

Backend should start on http://localhost:8000

### 4. Start Frontend

In a new terminal:
```bash
cd shovels_frontend
npm run dev
```

Frontend should start on http://localhost:5173

### 5. Login

1. Navigate to http://localhost:5173
2. You'll see a simple name input instead of "Login with Google"
3. Enter any name (e.g., "Alice") and click "Login (Local Mode)"
4. You'll be logged in without any OAuth flow!

## How It Works

**Backend Changes:**
- Added `LOCAL_MODE` setting in `config.py`
- Added `/auth/mode` endpoint to tell frontend which mode is active
- Added `/auth/local` endpoint that creates JWT tokens for local users
- User IDs are generated as `local_{name}` (e.g., `local_alice`)

**Frontend Changes:**
- Login page checks backend mode via `/auth/mode`
- Shows name input form when in local mode
- Shows Google OAuth button when in production mode

## Switching to Production Mode

To use Google OAuth:

1. Edit `shovels_backend/.env`:
   ```
   LOCAL_MODE=false
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

2. Restart the backend

3. Frontend will automatically detect the change and show Google login button

## Testing with Multiple Players

To test multiplayer locally:

1. Open http://localhost:5173 in one browser (e.g., Chrome)
2. Login as "Alice"
3. Open http://localhost:5173 in another browser (e.g., Firefox) or incognito window
4. Login as "Bob"
5. Both can join the same room and play!

## Security Note

Local mode is for development only. Never deploy with `LOCAL_MODE=true` in production!
