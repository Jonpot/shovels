# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shovels is a Build-&-Battle card game built with:
- **Backend**: FastAPI with WebSocket support for real-time multiplayer
- **Frontend**: React (Vite) with framer-motion for animations
- **Game Engine**: Pure Python implementation with Pydantic models
- **Testing**: pytest for all game logic

The game has two distinct phases:
1. **Phase 1 (Character Creation)**: Draw, discard, and play cards to build characters
2. **Phase 2 (Battle)**: Use character stacks to perform suit-based actions (Clubs=attack, Diamonds=shop, Hearts=defense, Spades=dig)

## Development Commands

### Backend
```bash
# First time setup: Install dependencies
pip install -r requirements.txt

# Activate virtual environment (Windows)
.\.venv\Scripts\Activate.ps1

# Activate virtual environment (Unix/Mac)
source .venv/bin/activate

# Run backend server
uvicorn shovels_backend.main:app --reload

# Server runs on http://localhost:8000
```

### Frontend
```bash
cd shovels_frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm build

# Lint code
npm run lint

# Server runs on http://localhost:5173
```

### Testing
```bash
# Run all tests (use PYTHONPATH to ensure modules are found)
PYTHONPATH=. pytest

# Run specific test file
PYTHONPATH=. pytest tests/test_phase1.py

# Run with verbose output
PYTHONPATH=. pytest -v

# Run specific test by name
PYTHONPATH=. pytest tests/test_phase1.py::test_draw_two_from_deck
```

### Code Quality
```bash
# Run linter
ruff check .

# Run type checker
pyright shovels_backend shovels_engine tests
```

### CLI Tool
```bash
# Play game in terminal (useful for testing)
python play_cli.py
```

## Architecture Overview

### Three-Layer Architecture

1. **shovels_engine/** - Pure game logic (no I/O)
   - `models.py`: Pydantic models for Card, Character, Player, GameState
   - `engine.py`: Core game mechanics (draw_cards, play_card, perform_action, etc.)
   - `agents.py`: Bot agents (RandomAgent for testing)
   - `cli_utils.py`: Terminal display helpers

2. **shovels_backend/** - FastAPI multiplayer server
   - `main.py`: HTTP/WebSocket endpoints, action routing
   - `manager.py`: GameRoom and GameRoomManager (multiplayer state)
   - `auth.py`: Google OAuth with JWT tokens
   - `config.py`: Environment configuration
   - `schemas.py`: Request/response models
   - `ws_schemas.py`: WebSocket message schemas

3. **shovels_frontend/src/** - React UI
   - `App.jsx`: Main app with routing between views
   - `views/`: LoginPage, LobbyBrowser, LobbyRoom, GameBoard
   - `components/`: Button, Card, Stack (reusable UI)
   - `components/game/`: Game-specific components
   - `utils/api.js`: API client and WebSocket wrapper
   - `config.js`: Backend URL configuration

### Game State Flow

**Setup**: `setup_game()` in `models.py` creates initial state
- Deals 3 face cards to each player as characters
- Creates shop pile (20 cards) and main deck
- Returns GameState object

**Phase 1**: Draw → Discard → Play → End Turn
- Engine functions: `draw_cards()`, `discard_card()`, `play_card()`
- Transitions to Phase 2 when deck is empty after equal turns

**Phase 2**: Battle Actions → End Turn
- Engine functions: `perform_action()`, `apply_face_strike()`, `tap_hero_power()`
- Shop system: `buy_card()`, `refresh_shop()`
- Turn ends via `end_turn()` which checks win conditions

**WebSocket Flow**:
1. Client sends action via WebSocket to `/ws/room/{room_id}`
2. `main.py` routes to appropriate engine function
3. GameRoom broadcasts updated state to all connected players
4. Frontend re-renders based on new state

### Critical Game Rules

**Card Stack Order**: Character stacks grow upward - `stack[-1]` is the top card (most recent)

**Action Atomicity**: Draw operations check availability BEFORE modifying state to maintain atomicity

**Suit Effects** (in `resolve_suit_effect()`):
- Clubs: Attack with damage = sum of ranks
- Diamonds: Gain coins, enter SHOPPING subphase
- Spades: Dig cards into dug_cards pool, allows recursive actions
- Hearts: No effect (stalling)

**Heart Protection**: Hearts in stack absorb damage if damage >= (heart_rank + character_shield). All cards from heart upward are discarded when broken.

**Fatigue Rule**: If a player cannot take a valid action (no cards to discard, no powers to tap, no valid strikes), they lose a character

**Subphases**: Phase 2 uses subphases (BATTLE_ACTION, SHOPPING, SHOP_FREE_BUY, GRAVEDIGGING) to handle complex turn flows

## Configuration

### Backend Environment (.env in shovels_backend/)

**Local Development Mode** (no Google OAuth required):
```bash
cp shovels_backend/.env.example shovels_backend/.env
# Edit .env and set LOCAL_MODE=true
```

Required variables for local mode:
```
LOCAL_MODE=true
JWT_SECRET_KEY=local-dev-secret-key-change-in-production
FRONTEND_URL=http://localhost:5173
```

Required variables for production (Google OAuth):
```
LOCAL_MODE=false
JWT_SECRET_KEY=your_secret_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
FRONTEND_URL=http://localhost:5173
```

### Frontend Config
Edit `shovels_frontend/src/config.js` to change API URL (defaults to `http://localhost:8000`)

## Testing Guidelines

- Game engine tests are in `tests/` at root level
- Test files follow pattern: `test_*.py`
- Use pytest fixtures for common setup
- Integration tests verify full game flows (see `test_integration_full_game.py`)
- Backend tests cover auth and WebSocket functionality

## Key Files to Understand

**Game Logic**:
- `shovels-full-rules.html` - Official technical specification
- `shovels_engine/engine.py` - All game mechanics (970 lines, well-documented)
- `shovels_engine/models.py` - Data structures and setup_game()

**Multiplayer**:
- `shovels_backend/main.py` - WebSocket handler and action routing
- `shovels_backend/manager.py` - Room state management

**UI**:
- `shovels_frontend/src/views/GameBoard.jsx` - Main game interface
- `shovels_frontend/src/utils/api.js` - WebSocket communication

**Docs**:
- `docs/TechnicalSpecification.md` - Complete game rules reference
- `Tickets/` - Implementation tickets and task breakdown
