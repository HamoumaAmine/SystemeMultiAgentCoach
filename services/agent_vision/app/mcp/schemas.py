# services/agent_vision/app/mcp/schemas.py

from typing import Any, Dict, Optional

from pydantic import BaseModel


class MCPMessage(BaseModel):
    """
    Modèle générique pour un message MCP reçu par l'agent.

    Champs typiques :
      - message_id : identifiant unique (UUID ou autre)
      - type       : "request" / "response" / ...
      - from_agent : nom de l'agent appelant (ex: "orchestrator")
      - to_agent   : nom de l'agent cible (ex: "agent_vision")
      - payload    : contenu métier du message (dict)
      - context    : informations de contexte (user_id, etc.)
    """

    message_id: str
    type: str
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    context: Dict[str, Any] = {}


class MCPResponse(BaseModel):
    """
    Modèle standard de réponse MCP renvoyée par l'agent.

    On garde la même forme dans tous les services :
      - message_id : identifiant de la réponse (souvent un nouveau UUID)
      - to_agent   : l'agent à qui l'on répond (en général l'appelant)
      - payload    : dict avec status, task, result, message, etc.
      - context    : recopie optionnelle du contexte (user_id, etc.)
    """

    message_id: str
    to_agent: str
    payload: Dict[str, Any]
    context: Dict[str, Any] = {}
