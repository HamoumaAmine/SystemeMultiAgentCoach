# services/agent_interface/app/routers/api.py

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import BackgroundTasks
from pydantic import BaseModel

from app.clients.orchestrator_client import (
    call_orchestrator,
    get_user_history,
)

router = APIRouter(prefix="/api", tags=["api"])


# ---------------------- Schémas Pydantic ---------------------- #

class ChatRequest(BaseModel):
    user_input: str
    user_id: Optional[str] = None
    image_path: Optional[str] = None
    audio_path: Optional[str] = None


# ------------------------- Endpoints -------------------------- #

@router.post("/chat")
async def api_chat(req: ChatRequest) -> Dict[str, Any]:
    """
    Endpoint principal pour la conversation texte (et optionnellement image/audio).

    - Reçoit : user_input (+ user_id, image_path, audio_path éventuels)
    - Appelle l'orchestrateur
    - Retourne une réponse structurée pour le front :
      coach_answer, mood_state, nutrition_result, vision_result, payload_brut
    """
    try:
        orch_resp = await call_orchestrator(
            user_input=req.user_input,
            user_id=req.user_id,
            image_path=req.image_path,
            audio_path=req.audio_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur orchestrateur: {e!r}")

    payload = orch_resp.get("payload", {}) or {}

    return {
        "status": payload.get("status", "error"),
        "coach_answer": payload.get("coach_answer"),
        "mood_state": payload.get("mood_state"),
        "nutrition_result": payload.get("nutrition_result"),
        "vision_result": payload.get("vision_result"),
        "speech_transcription": payload.get("speech_transcription"),
        "called_services": payload.get("called_services"),
        "raw_payload": payload,
    }


@router.post("/upload_image")
async def api_upload_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
) -> Dict[str, Any]:
    """
    Upload d'une image de repas.

    - Sauvegarde l'image dans un dossier 'uploaded_images'
    - Retourne le chemin absolu (à envoyer ensuite à /api/chat dans image_path)
    """

    # Dossier local où on stocke les images
    upload_dir = Path("uploaded_images")
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = upload_dir / file.filename

    try:
        content = await file.read()
        dest_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement fichier: {e!r}")

    # On renvoie un chemin absolu pour que l'orchestrateur/agent_vision y accède
    return {
        "status": "ok",
        "image_path": str(dest_path.resolve()),
        "filename": file.filename,
    }


@router.get("/history/{user_id}")
async def api_history(user_id: str, limit: int = 20) -> Dict[str, Any]:
    """
    Récupère l'historique utilisateur via agent_memory et le renvoie brut au front.
    """
    try:
        mem_resp = await get_user_history(user_id=user_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur agent_memory: {e!r}")

    payload = mem_resp.get("payload", {}) or {}

    if payload.get("status") != "ok":
        raise HTTPException(
            status_code=500,
            detail=f"Erreur agent_memory: {payload.get('message', 'inconnu')}",
        )

    return {
        "status": "ok",
        "history": payload.get("history", []),
    }
