import uuid
import json
from typing import Any, Dict, List, Optional

from app.mcp.schemas import MCPResponse
from app.llm.client import LLMClient
from app.llm.prompts import build_router_prompt


def _fallback_decide_services(user_text: str) -> List[Dict[str, Any]]:
    """
    Fallback simple au cas où le LLM échoue.
    Même logique que la version précédente règle-based.
    """
    text_lower = (user_text or "").lower()
    services: List[Dict[str, Any]] = []

    mood_keywords = ["fatigué", "fatigue", "stressé", "stresse", "motivé", "motivation", "moral"]
    if any(k in text_lower for k in mood_keywords):
        services.append(
            {
                "service": "mood",
                "command": "analyze_mood",
                "text": user_text,
            }
        )

    coaching_keywords = ["sport", "séance", "seance", "entrainement", "entraînement", "programme", "courir", "marathon"]
    if any(k in text_lower for k in coaching_keywords) or not services:
        services.append(
            {
                "service": "coaching",
                "command": "coach_response",
                "text": user_text,
            }
        )

    food_keywords = ["mangé", "mange", "repas", "déjeuner", "dîner", "couscous", "pizza", "calories"]
    if any(k in text_lower for k in food_keywords):
        services.append(
            {
                "service": "nutrition",
                "command": "analyze_meal",
                "text": user_text,
            }
        )

    return services


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Agent_Manager : reçoit une requête et renvoie une liste de services à appeler.

    Tâche principale :
      - "route_services"
    """
    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")

    if task != "route_services":
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue pour agent_manager: {task!r}",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    user_text: str = payload.get("text", "")

    services: List[Dict[str, Any]] = []
    error_info: Optional[str] = None

    # 1) Tenter la version LLM (Groq)
    try:
        router_prompt = build_router_prompt(user_text)
        llm_client = LLMClient()
        llm_output = llm_client.generate_json(router_prompt)

        # On s'attend à {"services": [...]}
        raw_services = llm_output.get("services", [])
        if isinstance(raw_services, list):
            # On garde uniquement les dicts bien formés
            for item in raw_services:
                if not isinstance(item, dict):
                    continue
                service_name = item.get("service")
                command = item.get("command")
                text_for_service = item.get("text", user_text)
                if service_name and command:
                    services.append(
                        {
                            "service": service_name,
                            "command": command,
                            "text": text_for_service,
                        }
                    )

    except Exception as e:
        # On note l'erreur mais on ne casse pas tout
        error_info = f"Erreur LLM router: {e!r}"

    # 2) Si le LLM n'a rien produit, fallback sur règles simples
    if not services:
        services = _fallback_decide_services(user_text)

    response_payload: Dict[str, Any] = {
        "status": "ok",
        "task": "route_services",
        "services": services,
    }
    if error_info:
        response_payload["llm_error"] = error_info

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
