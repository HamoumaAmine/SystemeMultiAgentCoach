# services/agent_knowledge/app/mcp/handler.py

import json
import uuid
from typing import Any, Dict

from app.mcp.schemas import MCPResponse
from knowledge_agent import KnowledgeAgent

# On instancie l'agent knowledge une seule fois
knowledge_agent = KnowledgeAgent()


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Handler principal MCP pour agent_knowledge.

    Tâche gérée :
      - "nutrition_suggestions" : propose des aliments selon un objectif.
        payload attendu :
          - task: "nutrition_suggestions"
          - goal: str (objectif utilisateur)
    """
    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task = payload.get("task")

    if task != "nutrition_suggestions":
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue pour agent_knowledge: {task!r}",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    # Récupération de l'objectif (goal)
    goal = payload.get("goal") or payload.get("user_goal") or payload.get("text")
    if not isinstance(goal, str) or not goal.strip():
        response_payload = {
            "status": "error",
            "message": "Champ 'goal' manquant pour la tâche 'nutrition_suggestions'.",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    # Appel à l'agent knowledge
    try:
        result_dict = knowledge_agent.query(goal, use_llm=True)
        response_payload = {
            "status": "ok",
            "task": "nutrition_suggestions",
            "goal": goal,
            "result": result_dict,
        }
    except Exception as e:
        response_payload = {
            "status": "error",
            "message": f"Erreur interne agent_knowledge: {e}",
        }

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
