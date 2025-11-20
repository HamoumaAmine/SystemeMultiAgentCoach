import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.mcp.schemas import MCPResponse
from app.db.session import SessionLocal
from app.repositories.interactions import create_interaction, get_user_history


def get_db() -> Session:
    """
    Fournit une session DB.
    Ici on ne passe pas par FastAPI Depends, donc on gère
    l'ouverture/fermeture manuellement dans process_mcp_message.
    """
    return SessionLocal()


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Point d'entrée principal de l'agent mémoire.

    Gère deux tâches principales :
      - task == "save_interaction"
      - task == "get_history"
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    task: Optional[str] = payload.get("task")

    # On ouvre une session DB
    db = get_db()

    try:
        # --- 1) Sauvegarder une interaction ---
        if task == "save_interaction":
            user_id = payload.get("user_id")
            role = payload.get("role") or "user"
            text = payload.get("text") or ""
            metadata = payload.get("metadata") or {}

            if not user_id or not text:
                response_payload = {
                    "status": "error",
                    "message": "user_id et text sont obligatoires pour save_interaction.",
                }
            else:
                interaction = create_interaction(
                    db=db,
                    user_id=user_id,
                    role=role,
                    text=text,
                    metadata=metadata,
                )
                response_payload = {
                    "status": "ok",
                    "task": "save_interaction",
                    "interaction_id": interaction.id,
                }

        # --- 2) Récupérer l'historique ---
        elif task == "get_history":
            user_id = payload.get("user_id")
            limit = int(payload.get("limit", 5))

            if not user_id:
                response_payload = {
                    "status": "error",
                    "message": "user_id est obligatoire pour get_history.",
                }
            else:
                interactions = get_user_history(db=db, user_id=user_id, limit=limit)
                history = [
                    {
                        "id": it.id,
                        "user_id": it.user_id,
                        "role": it.role,
                        "text": it.text,
                        "metadata": it.metadata_json,
                        "created_at": it.created_at.isoformat(),
                    }
                    for it in interactions
                ]
                response_payload = {
                    "status": "ok",
                    "task": "get_history",
                    "history": history,
                }

        # --- 3) Tâche inconnue ---
        else:
            response_payload = {
                "status": "error",
                "message": f"Tâche inconnue ou absente dans le payload: {task!r}",
            }

    finally:
        # On ferme proprement la session DB
        db.close()

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=msg.get("context", {}),
    )
