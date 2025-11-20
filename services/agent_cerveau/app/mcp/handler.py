import uuid
from typing import Any, Dict, List, Optional

from app.mcp.schemas import MCPResponse
from app.llm.client import LLMClient
from app.llm.prompts import build_coach_prompt


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Point d'entrée principal de l'agent cerveau.

    V2 :
    - On lit le payload du message MCP.
    - On regarde la tâche demandée (task).
    - Si task == "coach_response", on génère une réponse de coach.
    - Sinon, on renvoie une erreur "tâche inconnue".
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    task: Optional[str] = payload.get("task")

    # --- Cas 1 : on nous demande une réponse de coach ---
    if task == "coach_response":
        user_input: str = payload.get("user_input", "")
        mood: Optional[str] = payload.get("mood")
        history: List[Dict[str, Any]] = payload.get("history") or []
        expert_knowledge: List[str] = payload.get("expert_knowledge") or []

        # Construire le prompt complet pour le "LLM"
        full_prompt = build_coach_prompt(
            user_input=user_input,
            mood=mood,
            history=history,
            expert_knowledge=expert_knowledge,
        )

        # Appeler le client LLM (pour l'instant une version simple)
        llm = LLMClient()
        answer: str = llm.generate(full_prompt)

        response_payload = {
            "status": "ok",
            "task": "coach_response",
            "answer": answer,
        }

    # --- Cas 2 : aucune task ou task inconnue ---
    else:
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue ou absente dans le payload: {task!r}",
        }

    # Construction de la réponse MCP standardisée
    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=msg.get("context", {}),
    )
