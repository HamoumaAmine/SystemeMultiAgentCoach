# services/agent_interface/app/routers/coach.py

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel

from app.clients.orchestrator_client import (
    call_orchestrator,
    get_history,
    save_memory,
)
from app.core.store import get_user_by_id, get_user_id_from_token
from app.core.meals_store import save_meal, get_recent_meals  # ✅ historique des repas
from app.core.mood_store import save_mood

router = APIRouter(prefix="/coach", tags=["coach"])


# ---------------------------------------------------------------------------
# 1) Modèles Pydantic pour les requêtes / réponses
# ---------------------------------------------------------------------------


class CoachTextRequest(BaseModel):
    text: str


class CoachAnswer(BaseModel):
    """
    Réponse renvoyée au front pour le chat / vocal / image.

    - answer        : texte du coach (agent_cerveau)
    - meal          : résumé du repas si une analyse a été faite
    - mood          : état d'humeur renvoyé par l'orchestrateur (agent_mood)
    - transcription : résultat brut de la transcription vocale (agent_speech)
    """
    answer: str
    meal: Optional[Dict[str, Any]] = None
    mood: Optional[Dict[str, Any]] = None
    transcription: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# 2) Helpers d’authentification (décodage du token)
# ---------------------------------------------------------------------------


async def get_current_user(
    authorization: str = Header(..., description="Header Authorization: Bearer <token>"),
) -> Dict[str, Any]:
    """
    Décode le token JWT envoyé dans le header Authorization
    et renvoie un dict représentant l'utilisateur courant.

    On utilise les fonctions de app.core.store :
      - get_user_id_from_token(token)
      - get_user_by_id(user_id)
    """

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header Authorization manquant ou invalide",
        )

    token = authorization.split(" ", 1)[1].strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable",
        )

    # On renvoie un dict qui contient au minimum user_id
    return {"user_id": user_id, **user}


# ---------------------------------------------------------------------------
# 3) Helpers : repas & transcription
# ---------------------------------------------------------------------------


def build_meal_from_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    À partir du payload renvoyé par l’orchestrateur,
    construit un petit dict "meal" pour l’interface.

    On se base surtout sur vision_result.analysis et on
    nettoie les infos de calories pour éviter d'afficher
    un dict brut dans le front.
    """
    vision_result = payload.get("vision_result") or {}
    analysis = vision_result.get("analysis") or {}

    if not analysis:
        return None

    aliments = analysis.get("aliments_detectes") or []
    desc_generale = analysis.get("description_generale") or "Repas analysé"
    calories_estimees = analysis.get("calories_estimees")

    total_kcal: Optional[float] = None
    niveau_calorique: Optional[str] = None

    # On gère le cas où l'agent vision renvoie un dict structuré
    # du type {"total_kcal_approx": 550, "niveau_calorique": "moyen", ...}
    if isinstance(calories_estimees, dict):
        total_kcal = calories_estimees.get("total_kcal_approx")
        niveau_calorique = calories_estimees.get("niveau_calorique")
    elif isinstance(calories_estimees, (int, float, str)):
        # Cas simple : un nombre ou une chaîne directement
        try:
            total_kcal = float(calories_estimees)
        except Exception:
            total_kcal = None

    # Petite description textuelle pour la carte
    parts = [desc_generale]

    if aliments:
        parts.append("Aliments détectés : " + ", ".join(map(str, aliments)))

    if total_kcal is not None:
        parts.append(f"Estimation : ~{total_kcal} kcal (approx.)")

    if niveau_calorique:
        parts.append(f"Niveau calorique : {niveau_calorique}")

    description = " ".join(parts)
    image_url = payload.get("image_url")

    meal: Dict[str, Any] = {
        "title": desc_generale,
        "description": description,
        "image_url": image_url,  # URL réelle /uploads/... fournie par l’endpoint
        "kcal": total_kcal,
        # On n’a pas encore les macros détaillées => None
        "proteins_g": None,
        "carbs_g": None,
        "fats_g": None,
        "scanned_at": datetime.now().strftime("%d/%m/%Y"),
    }

    return meal


def extract_transcription_obj(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Essaie de récupérer l'objet de transcription renvoyé par l'agent_speech
    dans différents champs possibles.
    """
    tr = (
        payload.get("speech_transcription")
        or payload.get("stt_result")
        or payload.get("transcription")
    )

    if tr is None:
        return None

    # On renvoie toujours un dict pour que le front traite ça proprement
    if isinstance(tr, dict):
        return tr
    if isinstance(tr, str):
        return {"text": tr}

    # On ne connaît pas la forme exacte, on enveloppe
    return {"raw": tr}


def extract_transcription_text(transcription: Optional[Dict[str, Any]]) -> str:
    """
    À partir de l'objet transcription (dict), essaie d'en extraire une chaîne.
    """
    if transcription is None:
        return ""

    if "text" in transcription and isinstance(transcription["text"], str):
        return transcription["text"]

    if "transcript" in transcription and isinstance(transcription["transcript"], str):
        return transcription["transcript"]

    if "transcription" in transcription and isinstance(transcription["transcription"], str):
        return transcription["transcription"]

    if "raw" in transcription and isinstance(transcription["raw"], str):
        return transcription["raw"]

    # Dernier recours : on prend la première valeur string
    for v in transcription.values():
        if isinstance(v, str):
            return v

    return ""


# ---------------------------------------------------------------------------
# 4) Endpoint : texte -> orchestrateur
# ---------------------------------------------------------------------------


@router.post("/", response_model=CoachAnswer)
async def coach_text(
    req: CoachTextRequest,
    user: Dict[str, Any] = Depends(get_current_user),
) -> CoachAnswer:
    """
    Reçoit un message texte depuis l’interface,
    appelle l’orchestrateur, et renvoie :

      - answer : texte du coach (agent_cerveau)
      - meal   : éventuellement un résumé de repas si vision/nutrition ont été appelés
      - mood   : état d'humeur analysé par agent_mood
    """

    user_id = user["user_id"]

    try:
        orch_resp = await call_orchestrator(
            user_input=req.text,
            user_id=user_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de communication avec l’orchestrateur: {e}",
        )

    payload = orch_resp.get("payload", {}) or {}
    answer = payload.get("coach_answer") or "Je n’ai pas pu générer de réponse pour le moment."

    meal = build_meal_from_payload(payload)
    # 🔥 Récupération du mood envoyé par l’orchestrateur
    mood = payload.get("mood_state") or payload.get("mood_result")

    # Sauvegarde du mood si détecté
    if mood:
        try:
            save_mood(user_id, mood)
        except Exception:
            pass

    # ✅ Si le texte a déclenché une analyse de repas (ex: il décrit une photo déjà connue)
    if meal is not None:
        try:
            save_meal(
                user_id=user_id,
                title=meal["title"],
                description=meal["description"],
                kcal=meal["kcal"],
                image_url=meal["image_url"],
            )
        except Exception:
            # On ne bloque pas la réponse si la persistance échoue
            pass

    # ✅ Sauvegarde dans l’agent de mémoire (historique de chat)
    try:
        await save_memory(
            user_id=user_id,
            memory={
                "type": "text",
                "user_message": req.text,
                "coach_answer": answer,
                "mood": mood,
                "meal": meal,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
    except Exception:
        # On ne casse jamais la réponse pour un problème de mémoire
        pass

    # Pas de transcription dans le cas texte
    return CoachAnswer(answer=answer, meal=meal, mood=mood, transcription=None)


# ---------------------------------------------------------------------------
# 5) Config upload (audio + image)  ➜ chemin ABSOLU
# ---------------------------------------------------------------------------

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 6) Endpoint : vocal -> orchestrateur (audio_path)
# ---------------------------------------------------------------------------


@router.post("/voice", response_model=CoachAnswer)
async def coach_voice(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
) -> CoachAnswer:
    """
    Reçoit un fichier audio (webm, mp3, etc.) depuis l’interface,
    le sauvegarde temporairement, et appelle l’orchestrateur
    avec audio_path.

    Si l'orchestrateur renvoie une transcription mais pas de coach_answer,
    on fait un deuxième appel texte avec cette transcription pour obtenir
    une vraie réponse du coach.
    """

    user_id = user["user_id"]

    ext = os.path.splitext(file.filename or "")[1] or ".webm"
    tmp_name = f"voice_{uuid.uuid4().hex}{ext}"
    tmp_path = (UPLOAD_DIR / tmp_name).resolve()

    with tmp_path.open("wb") as f:
        f.write(await file.read())

    # 1) Premier appel : avec audio_path (agent_speech)
    try:
        orch_resp = await call_orchestrator(
            user_input="",
            user_id=user_id,
            audio_path=str(tmp_path),
        )
    finally:
        # Pour l’instant on garde le fichier pour debug.
        # tmp_path.unlink(missing_ok=True)
        pass

    payload = orch_resp.get("payload", {}) or {}
    answer = payload.get("coach_answer")

    meal = build_meal_from_payload(payload)
    mood = payload.get("mood_state") or payload.get("mood_result")
    transcription = extract_transcription_obj(payload)
    transcription_text = extract_transcription_text(transcription)

    # Sauvegarde du mood si détecté
    if mood:
        try:
            save_mood(user_id, mood)
        except Exception:
            pass

    # ✅ Si le vocal a entraîné l’analyse d’un repas, on le sauvegarde aussi
    if meal is not None:
        try:
            save_meal(
                user_id=user_id,
                title=meal["title"],
                description=meal["description"],
                kcal=meal["kcal"],
                image_url=meal["image_url"],
            )
        except Exception:
            # On ne fait rien si ça plante, l’important est de répondre
            pass

    # 2) Si pas de réponse mais on a une transcription,
    #    on refait un appel texte avec cette transcription.
    if not answer and transcription_text:
        try:
            orch_resp2 = await call_orchestrator(
                user_input=transcription_text,
                user_id=user_id,
            )
            payload2 = orch_resp2.get("payload", {}) or {}
            answer = payload2.get("coach_answer") or answer

            # On peut aussi récupérer un mood/meal complémentaires
            mood2 = payload2.get("mood_state") or payload2.get("mood_result")
            if mood2 and not mood:
                mood = mood2

            meal2 = build_meal_from_payload(payload2)
            if meal2 and not meal:
                meal = meal2

        except Exception:
            # On ne veut pas casser la réponse si le deuxième appel échoue
            pass

    # 3) Fallback final si toujours rien
    if not answer:
        if transcription_text:
            answer = (
                "J’ai bien reçu ton vocal et je l’ai transcrit, "
                "mais je n’ai pas réussi à générer une réponse adaptée pour l’instant."
            )
        else:
            answer = "Je n’ai pas pu générer de réponse pour ce vocal."

    # ✅ Sauvegarde dans l’agent de mémoire
    try:
        await save_memory(
            user_id=user_id,
            memory={
                "type": "voice",
                "audio_file": str(tmp_path),
                "transcription": transcription_text or None,
                "user_message": transcription_text or None,
                "coach_answer": answer,
                "mood": mood,
                "meal": meal,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
    except Exception:
        pass

    return CoachAnswer(answer=answer, meal=meal, mood=mood, transcription=transcription)


# ---------------------------------------------------------------------------
# 7) Endpoint : image / repas -> orchestrateur (image_path)
# ---------------------------------------------------------------------------


@router.post("/image", response_model=CoachAnswer)
async def coach_image(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
) -> CoachAnswer:
    """
    Reçoit une photo de repas, la sauvegarde, et appelle l’orchestrateur
    avec image_path pour que agent_vision + agent_knowledge travaillent.
    """

    user_id = user["user_id"]

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    tmp_name = f"meal_{uuid.uuid4().hex}{ext}"
    tmp_path = (UPLOAD_DIR / tmp_name).resolve()

    with tmp_path.open("wb") as f:
        f.write(await file.read())

    try:
        orch_resp = await call_orchestrator(
            user_input="Analyse mon repas sur la photo",
            user_id=user_id,
            image_path=str(tmp_path),
        )
    finally:
        # idem : on garde le fichier pour investiguer si besoin
        # tmp_path.unlink(missing_ok=True)
        pass

    # ✅ URL publique de l’image, servie par /uploads dans main.py
    image_url = f"/uploads/{tmp_name}"

    payload = orch_resp.get("payload", {}) or {}
    payload["image_url"] = image_url
    answer = payload.get("coach_answer") or "Je n’ai pas pu analyser ce repas."

    meal = build_meal_from_payload(payload)
    mood = payload.get("mood_state") or payload.get("mood_result")
    transcription = extract_transcription_obj(payload)

    # Sauvegarde du mood si détecté
    if mood:
        try:
            save_mood(user_id, mood)
        except Exception:
            pass

    # ✅ Sauvegarde dans l’historique des repas
    if meal is not None:
        try:
            save_meal(
                user_id=user_id,
                title=meal["title"],
                description=meal["description"],
                kcal=meal["kcal"],
                image_url=meal["image_url"],
            )
        except Exception:
            pass

    # ✅ Sauvegarde aussi dans la mémoire globale
    try:
        await save_memory(
            user_id=user_id,
            memory={
                "type": "image",
                "image_url": image_url,
                "user_message": "Analyse mon repas sur la photo",
                "coach_answer": answer,
                "mood": mood,
                "meal": meal,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
    except Exception:
        pass

    return CoachAnswer(answer=answer, meal=meal, mood=mood, transcription=transcription)


# ---------------------------------------------------------------------------
# 7bis) Alias rétro-compat : /photo-meal -> même logique que /image
# ---------------------------------------------------------------------------


@router.post("/photo-meal", response_model=CoachAnswer)
async def coach_photo_meal(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
) -> CoachAnswer:
    """
    Alias de /coach/image pour compatibilité avec l’ancien frontend.
    """

    user_id = user["user_id"]

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    tmp_name = f"meal_{uuid.uuid4().hex}{ext}"
    tmp_path = (UPLOAD_DIR / tmp_name).resolve()

    with tmp_path.open("wb") as f:
        f.write(await file.read())

    try:
        orch_resp = await call_orchestrator(
            user_input="Analyse mon repas sur la photo",
            user_id=user_id,
            image_path=str(tmp_path),
        )
    finally:
        # idem : on garde le fichier pour investiguer si besoin
        # tmp_path.unlink(missing_ok=True)
        pass

    image_url = f"/uploads/{tmp_name}"
    payload = orch_resp.get("payload", {}) or {}
    payload["image_url"] = image_url
    answer = payload.get("coach_answer") or "Je n’ai pas pu analyser ce repas."

    meal = build_meal_from_payload(payload)
    mood = payload.get("mood_state") or payload.get("mood_result")
    transcription = extract_transcription_obj(payload)

    # Sauvegarde du mood si détecté
    if mood:
        try:
            save_mood(user_id, mood)
        except Exception:
            pass

    # ✅ Sauvegarde aussi via cet alias
    if meal is not None:
        try:
            save_meal(
                user_id=user_id,
                title=meal["title"],
                description=meal["description"],
                kcal=meal["kcal"],
                image_url=meal["image_url"],
            )
        except Exception:
            pass

    # ✅ Sauvegarde dans la mémoire
    try:
        await save_memory(
            user_id=user_id,
            memory={
                "type": "image",
                "image_url": image_url,
                "user_message": "Analyse mon repas sur la photo",
                "coach_answer": answer,
                "mood": mood,
                "meal": meal,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
    except Exception:
        pass

    return CoachAnswer(answer=answer, meal=meal, mood=mood, transcription=transcription)


# ---------------------------------------------------------------------------
# 8) Endpoints pour l’historique / mémoire
# ---------------------------------------------------------------------------


@router.get("/history")
async def coach_history(
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Historique combiné :
      - logs mémorisés par agent_memory (via orchestrateur_client.get_history)
      - derniers repas scannés (meals.db)

    On renvoie un objet JSON du type :
    {
      "memory": ...  # ce que renvoie agent_memory
      "meals": [ { title, description, kcal, image_url, scanned_at, ... }, ... ]
    }
    """
    user_id = user["user_id"]

    # 1) historique "mémoire" (agent_memory)
    memory_raw = await get_history(user_id=user_id)

    # 2) derniers repas (par ex. 20 derniers)
    meals = get_recent_meals(user_id=user_id, limit=20)

    return {
        "memory": memory_raw,
        "meals": meals,
    }


@router.post("/memory")
async def coach_save_memory(
    data: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Sauvegarde manuellement une mémoire (si besoin) via agent_memory.
    """
    user_id = user["user_id"]
    return await save_memory(user_id=user_id, memory=data)
