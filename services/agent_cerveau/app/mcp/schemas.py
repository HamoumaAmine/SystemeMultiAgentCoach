from typing import Any, Dict, Optional
from pydantic import BaseModel


class MCPMessage(BaseModel):
    """
    Modèle générique de message MCP.
    Utilisé si un jour on veut valider l'entrée côté agent_cerveau.
    """
    message_id: str
    type: str
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """
    Réponse MCP renvoyée par agent_cerveau.
    Ce format doit être identique à celui d'agent_memory
    pour que tous les agents puissent communiquer sans erreur.
    """
    message_id: str
    type: str = "response"
    from_agent: str = "agent_cerveau"
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
