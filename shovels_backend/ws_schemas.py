from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class WsMessage(BaseModel):
    type: str # "action", "chat", "error", "start_game"
    data: Optional[Dict[str, Any]] = None

class ActionData(BaseModel):
    action_type: str # "draw", "discard", "play", "buy", "refresh", "tap", "gravedig", "action", "strike"
    params: Dict[str, Any]
