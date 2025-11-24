from typing import Any, Dict

from ..mood.classifier import analyze_mood
from .schemas import MCPRequest, MCPResponse


def handle_mcp(message: MCPRequest) -> MCPResponse:
    """
    Point d'entrée de l'agent_mood pour le protocole MCP.

    Tâche supportée :
    - payload.task == "analyze_mood"

    Payload attendu :
    {
      "task": "analyze_mood",
      "text": "...",
      "user_id": "user-123"   # optionnel
    }
    """
    payload: Dict[str, Any] = message.payload or {}
    task = payload.get("task")

    if task != "analyze_mood":
        # On renvoie une réponse d'erreur propre, pas une exception
        return MCPResponse(
            message_id=message.message_id,
            from_agent="agent_mood",
            to_agent=message.from_agent,
            payload={
                "status": "error",
                "message": f"Tâche inconnue pour agent_mood: {task!r}",
            },
            context=message.context or {},
        )

    text = payload.get("text", "")
    user_id = payload.get("user_id")  # non utilisé pour l'instant mais gardé

    result = analyze_mood(text)

    return MCPResponse(
        message_id=message.message_id,
        from_agent="agent_mood",
        to_agent=message.from_agent,
        payload={
            "status": "ok",
            "task": "analyze_mood",
            "user_id": user_id,
            "mood": result.mood,
            "score": result.score,
            "valence": result.valence,
            "energy": result.energy,
            "matched_keywords": result.matched_keywords,
            "debug": {
                "explanation": result.raw_explanation,
            },
        },
        context=message.context or {},
    )
