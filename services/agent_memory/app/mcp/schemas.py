from pydantic import BaseModel
from typing import Any, Dict, Optional


class MCPMessage(BaseModel):
    """
    Schéma standard d'un message MCP échangé entre agents.
    Utilisé quand un autre agent envoie une requête à agent_memory.
    """
    message_id: str
    type: str               # "request" | "response" | "event"
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """
    Réponse MCP produite par l'agent mémoire.
    """
    message_id: str
    type: str = "response"
    from_agent: str = "agent_memory"
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
