# services/agent_knowledge/app/mcp/schemas.py

from typing import Any, Dict
from pydantic import BaseModel


class MCPResponse(BaseModel):
    """
    Réponse standard MCP pour tous les agents.
    """
    message_id: str
    to_agent: str
    payload: Dict[str, Any]
    context: Dict[str, Any] = {}
