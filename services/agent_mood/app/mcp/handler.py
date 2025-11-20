from typing import Dict, Any
from pydantic import BaseModel

from ..mood.classifier import analyze_mood


class MCPMessage(BaseModel):
    message_id: str
    sender: str
    receiver: str
    task: str
    payload: Dict[str, Any]


def handle_mcp(message: MCPMessage) -> Dict[str, Any]:
    if message.task != "analyze_mood":
        return {
            "message_id": message.message_id,
            "sender": "agent_mood",
            "receiver": message.sender,
            "task": message.task,
            "error": f"Unsupported task for agent_mood: {message.task}",
        }

    text = message.payload.get("text", "")
    user_id = message.payload.get("user_id")

    result = analyze_mood(text)

    return {
        "message_id": message.message_id,
        "sender": "agent_mood",
        "receiver": message.sender,
        "task": message.task,
        "payload": {
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
    }
