from typing import Any, Dict, Optional

from pydantic import BaseModel


class MCPBaseMessage(BaseModel):
    """
    Schéma commun inspiré de ce qu'on utilise déjà pour agent_cerveau et agent_memory.
    """
    message_id: str
    type: str
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

    class Config:
        extra = "ignore"  # ignore les champs inattendus au lieu de planter


class MCPRequest(MCPBaseMessage):
    type: str = "request"


class MCPResponse(MCPBaseMessage):
    type: str = "response"

