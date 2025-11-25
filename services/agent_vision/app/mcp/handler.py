# services/agent_vision/app/mcp/handler.py

import uuid
import os
import base64
import json
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from groq import Groq

from app.mcp.schemas import MCPResponse

# Charge les variables d'environnement (.env)
load_dotenv()


# -------------------------------------------------------------------
# Utilitaires locaux (reprennent la logique de test_vision.py)
# -------------------------------------------------------------------
def _encode_image(image_path: str) -> str:
    """
    Lit une image en binaire et la convertit en base64 (string).
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _read_file(file_path: str) -> str:
    """
    Lit un fichier texte (UTF-8) et renvoie son contenu.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def _ask_vision(image_path: str, user_goal: Optional[str] = None) -> Dict[str, Any]:
    """
    Appelle le modèle Groq Vision en utilisant context.txt + prompt.txt
    et l'image encodée en base64.

    On renvoie un dict Python (JSON parsé).
    """
    base64_image = _encode_image(image_path)

    client = Groq(api_key=os.environ.get("GROQ_KEY"))

    system_content = _read_file("context.txt")

    # On enrichit le prompt avec l'objectif utilisateur si fourni
    base_prompt = _read_file("prompt.txt")
    if user_goal:
        full_prompt = f"{base_prompt}\n\nObjectif de l'utilisateur : {user_goal}"
    else:
        full_prompt = base_prompt

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_content,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": full_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            },
        ],
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        response_format={"type": "json_object"},
    )

    # Le modèle renvoie un JSON dans message.content
    raw_content = chat_completion.choices[0].message.content
    result = json.loads(raw_content)

    return result


# -------------------------------------------------------------------
# Handler MCP principal de l'agent_vision
# -------------------------------------------------------------------
async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Handler MCP pour l'agent_vision.

    Tâches gérées :
      - "analyze_image"
      - "analyze_diet_image" (alias, pour compatibilité)

    Payload attendu :
      - task: "analyze_image" ou "analyze_diet_image"
      - image_path: chemin local vers l'image à analyser
      - user_goal: texte optionnel (ex: "Je veux perdre du poids")

    Réponse (payload) :
      - status: "ok" ou "error"
      - task: "analyze_image"
      - agent: "vision"
      - image_path: ...
      - user_goal: ...
      - analysis: dict renvoyé par le modèle vision (JSON parsé)
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")
    user_id: Optional[str] = context.get("user_id")

    # ------------------------------------------------------------------ #
    # Vérification de la tâche
    # ------------------------------------------------------------------ #
    if task not in ("analyze_image", "analyze_diet_image"):
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

    image_path: Optional[str] = payload.get("image_path")
    user_goal: str = payload.get("user_goal", "")

    if not image_path:
        response_payload = {
            "status": "error",
            "message": "Champ 'image_path' manquant pour la tâche analyze_image.",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    # ------------------------------------------------------------------ #
    # Appel au modèle Vision (Groq)
    # ------------------------------------------------------------------ #
    try:
        analysis = _ask_vision(image_path=image_path, user_goal=user_goal)

        response_payload = {
            "status": "ok",
            "task": "analyze_image",
            "agent": "vision",
            "image_path": image_path,
            "user_goal": user_goal,
            "analysis": analysis,
        }

    except Exception as e:
        # On logge l'erreur côté serveur (facultatif)
        print("[AGENT_VISION] ERREUR interne :", repr(e), flush=True)

        response_payload = {
            "status": "error",
            "message": f"Erreur interne dans agent_vision: {e!r}",
        }

    # ------------------------------------------------------------------ #
    # Construction de la réponse MCP
    # ------------------------------------------------------------------ #
    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
