# services/agent_interface/app/mcp/client.py

import uuid
from typing import Any, Dict, Optional

import requests
from core.config import settings


def send_mcp(
    to_agent: str,
    payload: Dict[str, Any],
    *,
    from_agent: str = "agent_interface",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Envoie un message MCP standard à l'orchestrateur.

    - to_agent : nom logique de l'agent visé ("orchestrator", "agent_cerveau", ...)
    - payload  : ex. {"task": "process_user_input", "user_input": "..."}
    - context  : ex. {"user_id": "..."}
    """
    if context is None:
        context = {}

    message = {
        "message_id": str(uuid.uuid4()),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "type": "request",
        "payload": payload,
        "context": context,
    }

    url = f"{settings.ORCHESTRATOR_URL}/mcp"
    resp = requests.post(url, json=message, timeout=20)
    resp.raise_for_status()
    return resp.json()
