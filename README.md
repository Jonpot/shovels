# Shovels

A Build-&-Battle Card Game.

## Prerequisites

- Node.js (v18+)
- Python (v3.9+)

## Setup

1.  **Clone and Install Dependencies**

    ```bash
    # Backend
    python -m venv .venv
    source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
    pip install -r requirements.txt # Note: If requirements.txt is missing, install manually:
    # pip install fastapi uvicorn[standard] python-dotenv python-jose[cryptography] authlib httpx pydantic-settings

    # Frontend
    cd shovels_frontend
    npm install
    ```

2.  **Configuration**

    Create `shovels_backend/.env` with your secrets:
    ```env
    JWT_SECRET_KEY=your_secret_key
    GOOGLE_CLIENT_ID=your_google_client_id
    GOOGLE_CLIENT_SECRET=your_google_client_secret
    FRONTEND_URL=http://localhost:5173
    ```

## Running the App

### Backend
From the root directory:
```bash
# Activate venv if not active
source .venv/bin/activate
uvicorn shovels_backend.main:app --reload
```
Server runs on `http://localhost:8000`.

### Frontend
From `shovels_frontend`:
```bash
npm run dev
```
Client runs on `http://localhost:5173`.

## Development

- **Tests**: `pytest`
- **Frontend Config**: `shovels_frontend/src/config.js`
- **Backend Config**: `shovels_backend/config.py`
