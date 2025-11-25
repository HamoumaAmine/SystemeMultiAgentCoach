from typing import Any, Dict

import requests
from fastapi import APIRouter, UploadFile, File, Header, HTTPException

from app.core.config import settings
from app.core.store import get_user_id_from_token
from app.mcp.client import send_mcp
from app.models.schemas import UserMessage, CoachResponse

router = APIRouter(prefix="/coach", tags=["coach"])

AGENT_SPEECH_URL = settings.AGENT_SPEECH_URL


@router.post("/", response_model=CoachResponse)
def talk_to_coach(
    msg: UserMessage,
    authorization: str = Header(...),
):
    """
    Endpoint TEXTE : envoie le message utilisateur à l'orchestrateur.

    - Récupère user_id depuis le token Authorization.
    - Appelle l'orchestrateur avec task="process_user_input".
    """
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")

    payload = {
        "task": "process_user_input",
        "user_input": msg.text,
    }
    context = {"user_id": user_id}

    try:
        mcp_resp = send_mcp("orchestrator", payload, context=context)
        payload_resp: Dict[str, Any] = mcp_resp.get("payload", {}) or {}
        answer = payload_resp.get("coach_answer") or "Pas de réponse du système."
    except Exception as e:
        answer = f"Erreur lors de l'appel à l'orchestrateur : {e}"

    return CoachResponse(answer=answer)


@router.post("/voice", response_model=CoachResponse)
async def talk_to_coach_voice(
    authorization: str = Header(...),
    file: UploadFile = File(...),
):
    """
    Endpoint VOCAL :

      1) Envoie le fichier audio à agent_speech (/transcribe-file) pour obtenir la transcription.
      2) Envoie la transcription à l'orchestrateur comme si c'était un message texte.

    On récupère user_id depuis le token (comme pour le texte).
    """
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")

    # 1) Appel à agent_speech pour transcrire l'audio
    try:
        file_bytes = await file.read()
        files = {
            "file": (file.filename or "voice.webm", file_bytes, file.content_type or "audio/webm")
        }
        resp = requests.post(
            f"{AGENT_SPEECH_URL}/transcribe-file",
            files=files,
            timeout=120,
        )
        resp.raise_for_status()
        speech_data = resp.json()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'appel à agent_speech : {e}",
        )

    transcribed_text = speech_data.get("output_text")
    if not transcribed_text:
        raise HTTPException(
            status_code=500,
            detail="Transcription vide ou indisponible.",
        )

    # 2) Envoi de la transcription à l'orchestrateur
    payload = {
        "task": "process_user_input",
        "user_input": transcribed_text,
    }
    context = {"user_id": user_id}

    try:
        mcp_resp = send_mcp("orchestrator", payload, context=context)
        payload_resp: Dict[str, Any] = mcp_resp.get("payload", {}) or {}
        answer = payload_resp.get("coach_answer") or "Pas de réponse du système."
    except Exception as e:
        answer = f"Erreur lors de l'appel à l'orchestrateur : {e}"

    return CoachResponse(answer=answer)
