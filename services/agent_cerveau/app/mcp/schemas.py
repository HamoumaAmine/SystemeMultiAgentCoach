from pydantic import BaseModel
from typing import Any, Dict, Optional


class MCPMessage(BaseModel):
    """
    Schéma standard d'un message MCP échangé entre agents.
    """
    message_id: str
    type: str               # "request" | "response" | "event"
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """
    Réponse MCP produite par l'agent cerveau.
    """
    message_id: str
    type: str = "response"
    from_agent: str = "agent_cerveau"
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
