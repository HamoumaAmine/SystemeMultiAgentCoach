import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.mcp.schemas import MCPResponse


# URLs des autres services (tu peux adapter les ports selon votre choix)
AGENT_MANAGER_URL = "http://127.0.0.1:8004/mcp"
AGENT_MOOD_URL = "http://127.0.0.1:8001/mcp"      # quand agent_mood existera
AGENT_CERVEAU_URL = "http://127.0.0.1:8002/mcp"


async def call_agent(url: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Appelle un autre agent via HTTP (MCP) et renvoie sa réponse JSON.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=message, timeout=30.0)
        resp.raise_for_status()
        return resp.json()


async def _route_with_manager(user_input: str, user_id: Optional[str]) -> List[Dict[str, Any]]:
    """
    Appelle l'agent_manager pour obtenir la liste des services à exécuter.
    """
    msg = {
        "message_id": str(uuid.uuid4()),
        "from_agent": "orchestrator",
        "to_agent": "agent_manager",
        "type": "request",
        "payload": {
            "task": "route_services",
            "text": user_input,
        },
        "context": {"user_id": user_id} if user_id else {},
    }

    response = await call_agent(AGENT_MANAGER_URL, msg)
    payload = response.get("payload", {})
    if payload.get("status") != "ok":
        return []

    services = payload.get("services", [])
    if not isinstance(services, list):
        return []

    return services


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Orchestrateur principal.

    Tâche gérée :
      - "process_user_input" : reçoit un texte utilisateur, orchestre les appels
        aux autres agents (mood, cerveau, etc.).

    Entrée attendue dans payload :
      - task: "process_user_input"
      - user_input: str
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")
    user_id: Optional[str] = context.get("user_id")

    if task != "process_user_input":
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue pour orchestrateur: {task!r}",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    user_input: str = payload.get("user_input", "")

    # 1) Demander à l'agent_manager quels services appeler
    services = await _route_with_manager(user_input, user_id)

    mood_state: Optional[Dict[str, Any]] = None
    coach_answer: Optional[str] = None

    # 2) Exécuter chaque service demandé
    for service_cmd in services:
        service_name = service_cmd.get("service")
        command = service_cmd.get("command")
        text_for_service = service_cmd.get("text", user_input)

        # --- Appel de l'agent_mood ---
        if service_name == "mood" and command == "analyze_mood":
            try:
                mood_msg = {
                    "message_id": str(uuid.uuid4()),
                    "from_agent": "orchestrator",
                    "to_agent": "agent_mood",
                    "type": "request",
                    "payload": {
                        "task": "analyze_mood",
                        "text": text_for_service,
                    },
                    "context": {"user_id": user_id} if user_id else {},
                }
                mood_resp = await call_agent(AGENT_MOOD_URL, mood_msg)
                mood_payload = mood_resp.get("payload", {})
                if mood_payload.get("status") == "ok":
                    mood_state = {
                        "physical_state": mood_payload.get("physical_state"),
                        "mental_state": mood_payload.get("mental_state"),
                    }
            except Exception:
                # On ignore les erreurs de mood pour ne pas casser le reste
                mood_state = None

        # --- Appel de l'agent_cerveau ---
        if service_name == "coaching" and command == "coach_response":
            try:
                brain_msg = {
                    "message_id": str(uuid.uuid4()),
                    "from_agent": "orchestrator",
                    "to_agent": "agent_cerveau",
                    "type": "request",
                    "payload": {
                        "task": "coach_response",
                        "user_input": text_for_service,
                        "mood_state": mood_state,
                        "history": [],
                        "expert_knowledge": [],
                    },
                    "context": {"user_id": user_id} if user_id else {},
                }
                brain_resp = await call_agent(AGENT_CERVEAU_URL, brain_msg)
                brain_payload = brain_resp.get("payload", {})
                if brain_payload.get("status") == "ok":
                    coach_answer = brain_payload.get("answer")
            except Exception:
                coach_answer = None

        # (plus tard : service "nutrition" → Vision + NutritionDB, etc.)

    # 3) Construire la réponse globale
    response_payload = {
        "status": "ok",
        "task": "process_user_input",
        "mood_state": mood_state,
        "coach_answer": coach_answer,
        "called_services": services,
    }

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
