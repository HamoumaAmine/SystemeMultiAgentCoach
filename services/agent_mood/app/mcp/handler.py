from typing import Dict, Any

from app.mood.classifier import analyze_mood
from .schemas import MCPMessage, MCPResponse


def handle_mcp(message: MCPMessage) -> MCPResponse:
    """
    Agent_Mood : analyse l'état émotionnel de l'utilisateur.

    Attend dans payload :
      - task: "analyze_mood"
      - text: str (obligatoire)
      - user_id: str (optionnel)
    """

    payload: Dict[str, Any] = message.payload or {}
    task = payload.get("task")

    if task != "analyze_mood":
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

    text = payload.get("text", "") or ""
    user_id = payload.get("user_id")

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
            "debug": {
                "matched_keywords": result.matched_keywords,
                "explanation": result.raw_explanation,
            },
        },
        context=message.context or {},
    )
