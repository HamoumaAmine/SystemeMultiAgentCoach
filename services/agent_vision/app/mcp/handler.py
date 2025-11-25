# services/agent_vision/app/mcp/handler.py

import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from app.mcp.schemas import MCPResponse
from app.vision.client import ask_vision
from app.vision.utils import normalize_vision_result


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Handler MCP principal pour l'agent_vision.

    Tâches gérées :
      - "analyze_meal_image" : analyse une image de plat/repas.

    Payload attendu :
      - task: "analyze_meal_image"
      - image_path: chemin local vers l'image (ex: "plat.jpg")

    Réponse :
      - status: "ok" ou "error"
      - task: "analyze_meal_image"
      - result: dict normalisé des informations nutritionnelles / description
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")

    # ------------------------------------------------------------------ #
    # Tâche non gérée
    # ------------------------------------------------------------------ #
    if task != "analyze_meal_image":
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue pour agent_vision: {task!r}",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    # ------------------------------------------------------------------ #
    # Récupération du chemin de l'image
    # ------------------------------------------------------------------ #
    image_path_raw = payload.get("image_path") or payload.get("path")
    if not image_path_raw:
        response_payload = {
            "status": "error",
            "message": "Champ 'image_path' manquant dans le payload.",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    image_path = Path(image_path_raw)

    try:
        raw_result = ask_vision(image_path)
        result = normalize_vision_result(raw_result)

        response_payload = {
            "status": "ok",
            "task": "analyze_meal_image",
            "image_path": str(image_path),
            "result": result,
        }
    except Exception as e:
        response_payload = {
            "status": "error",
            "task": "analyze_meal_image",
            "message": f"Erreur lors de l'appel à Groq Vision: {e!r}",
        }

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
