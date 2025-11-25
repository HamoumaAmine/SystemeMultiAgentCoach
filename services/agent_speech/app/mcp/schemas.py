# services/agent_speech/app/mcp/schemas.py

from typing import Any, Dict, Optional

from pydantic import BaseModel


class MCPRequest(BaseModel):
    """
    Message MCP générique reçu par l'agent_speech.
    """
    message_id: str
    type: str  # "request"
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """
    Réponse MCP renvoyée par l'agent_speech.
    """
    message_id: str
    type: str = "response"
    from_agent: str = "agent_speech"
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
