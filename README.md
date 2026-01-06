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
    pip install -r requirements.txt

    # Frontend
    cd shovels_frontend
    npm install
    ```

2.  **Configuration**

    For local development (no Google OAuth required):
    ```bash
    # The .env file is already set up with LOCAL_MODE=true
    # Just start the servers!
    ```

    For production (Google OAuth):
    ```bash
    # Edit shovels_backend/.env:
    LOCAL_MODE=false
    JWT_SECRET_KEY=your_secret_key
    GOOGLE_CLIENT_ID=your_google_client_id
    GOOGLE_CLIENT_SECRET=your_google_client_secret
    FRONTEND_URL=http://localhost:5173
    ```

    See [LOCAL_MODE_SETUP.md](LOCAL_MODE_SETUP.md) for detailed local development instructions.

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
