# services/agent_knowledge/main.py

import json
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from knowledge_agent import KnowledgeAgent

# -------------------------------------------------------------------
# Initialisation FastAPI + KnowledgeAgent
# -------------------------------------------------------------------

app = FastAPI(title="Agent Knowledge - Nutrition")
knowledge_agent = KnowledgeAgent()


# -------------------------------------------------------------------
# Schéma MCP minimal (comme les autres services)
# -------------------------------------------------------------------

class MCPMessage(BaseModel):
    message_id: str
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    type: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------------
# Endpoint MCP
# -------------------------------------------------------------------

@app.post("/mcp")
async def mcp_endpoint(msg: MCPMessage) -> Dict[str, Any]:
    """
    Endpoint MCP pour l'agent_knowledge.

    Tâche gérée :
      - "nutrition_suggestions" : reçoit un "goal" utilisateur
        et renvoie des suggestions nutritionnelles basées sur la BDD.

    Format attendu :
      payload = {
        "task": "nutrition_suggestions",
        "goal": "je veux perdre un peu de poids..."
      }

    Réponse :
      {
        "message_id": ...,
        "to_agent": ...,
        "payload": {
          "status": "ok" | "error",
          "task": "nutrition_suggestions",
          "result": { ... }   # dict Python
        },
        "context": { ... }
      }
    """

    payload = msg.payload or {}
    task = payload.get("task")

    # Vérification de la tâche
    if task != "nutrition_suggestions":
        return {
            "message_id": msg.message_id,
            "to_agent": msg.from_agent or "unknown",
            "payload": {
                "status": "error",
                "task": task,
                "message": f"Tâche inconnue pour agent_knowledge: {task!r}",
            },
            "context": msg.context or {},
        }

    # Récupérer le goal utilisateur
    user_goal: str = payload.get("goal", "") or ""
    use_llm: bool = bool(payload.get("use_llm", True))

    # Appel au KnowledgeAgent (qui renvoie un JSON string)
    try:
        raw_result = knowledge_agent.query(user_goal, use_llm=use_llm)

        # On essaie de parser en dict Python (le query renvoie un JSON string)
        try:
            result = json.loads(raw_result)
        except Exception:
            # Si jamais ce n'est pas un JSON pur, on encapsule brut
            result = {"raw": raw_result}

        response_payload: Dict[str, Any] = {
            "status": "ok",
            "task": "nutrition_suggestions",
            "goal": user_goal,
            "result": result,
        }

    except Exception as e:
        response_payload = {
            "status": "error",
            "task": "nutrition_suggestions",
            "message": f"Erreur interne agent_knowledge: {repr(e)}",
        }

    return {
        "message_id": msg.message_id,
        "to_agent": msg.from_agent or "unknown",
        "payload": response_payload,
        "context": msg.context or {},
    }
