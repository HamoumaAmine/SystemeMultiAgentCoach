# services/agent_interface/app/clients/orchestrator_client.py

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

import httpx

# ---------------------------------------------------------------------
# URLs des services (override possibles par variables d'environnement)
# ---------------------------------------------------------------------

ORCHESTRATOR_URL = os.getenv(
    "ORCHESTRATOR_URL",
    "http://127.0.0.1:8005/mcp",
)

AGENT_MEMORY_URL = os.getenv(
    "AGENT_MEMORY_URL",
    "http://127.0.0.1:8003/mcp",
)


# ---------------------------------------------------------------------
# Fonction générique : appel de l'orchestrateur
# ---------------------------------------------------------------------
async def call_orchestrator(
    user_input: str = "",
    *,
    user_id: Optional[str] = None,
    image_path: Optional[str] = None,
    audio_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Appelle l'orchestrateur (service /orchestrator) via MCP.

    - user_input : texte tapé par l'utilisateur (chat)
    - image_path : chemin local vers une image de repas (pour agent_vision)
    - audio_path : chemin local vers un fichier audio (pour agent_speech)
    - user_id    : identifiant utilisateur (pour le contexte / mémoire)

    Renvoie **la réponse JSON brute** de l'orchestrateur, de la forme :

      {
        "message_id": "...",
        "to_agent": "agent_interface",
        "payload": {
          "status": "ok",
          "task": "process_user_input",
          "user_id": "...",
          "coach_answer": "...",
          "mood_state": {...} | null,
          "speech_transcription": {...} | null,
          "nutrition_result": {...} | null,
          "vision_result": {...} | null,
          "called_services": [...]
        },
        "context": { ... }
      }
    """

    payload: Dict[str, Any] = {
        "task": "process_user_input",
        "user_input": user_input or "",
    }
    if audio_path:
        payload["audio_path"] = audio_path
    if image_path:
        payload["image_path"] = image_path

    msg: Dict[str, Any] = {
        "message_id": str(uuid.uuid4()),
        "type": "request",
        "from_agent": "agent_interface",
        "to_agent": "orchestrator",
        "payload": payload,
        "context": {"user_id": user_id} if user_id else {},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(ORCHESTRATOR_URL, json=msg, timeout=60.0)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------
# Accès à l'agent_memory (historique utilisateur)
# ---------------------------------------------------------------------
async def get_user_history(
    user_id: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Récupère l'historique de l'utilisateur auprès de l'agent_memory.

    Renvoie la réponse JSON brute de l'agent_memory.
    """

    msg: Dict[str, Any] = {
        "message_id": str(uuid.uuid4()),
        "type": "request",
        "from_agent": "agent_interface",
        "to_agent": "agent_memory",
        "payload": {
            "task": "get_history",
            "user_id": user_id,
            "limit": limit,
        },
        "context": {"user_id": user_id},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(AGENT_MEMORY_URL, json=msg, timeout=30.0)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------
# WRAPPERS DE COMPATIBILITÉ (pour l'ancien coach.py)
# ---------------------------------------------------------------------
# Ils gardent les anciens noms utilisés dans le routeur coach,
# mais délèguent tout à call_orchestrator(). Le paramètre `token`
# est accepté pour compatibilité mais **non utilisé** ici.
# ---------------------------------------------------------------------

async def query_orchestrator(
    text: str,
    user_id: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ancien wrapper pour une requête texte simple vers l'orchestrateur.

    Renvoie la même chose que call_orchestrator().
    """
    return await call_orchestrator(
        user_input=text,
        user_id=user_id,
    )


async def query_orchestrator_with_voice(
    audio_path: str,
    user_id: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ancien wrapper pour une requête avec fichier audio.
    """
    return await call_orchestrator(
        user_input="",
        user_id=user_id,
        audio_path=audio_path,
    )


async def query_orchestrator_with_image(
    image_path: str,
    user_id: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ancien wrapper pour une requête avec image de repas.
    """
    # On peut envoyer un user_input générique, l'orchestrateur l'ignore
    # si ce n'est pas utile.
    return await call_orchestrator(
        user_input="Analyse mon repas sur la photo",
        user_id=user_id,
        image_path=image_path,
    )


async def save_memory(
    user_id: str,
    memory_type: str,
    content: str,
) -> Dict[str, Any]:
    """
    Wrapper de compatibilité pour enregistrer un souvenir dans agent_memory.
    Le coach.py l'utilise encore (ex : garder une trace d'un repas ou d'un message).
    """
    msg = {
        "message_id": str(uuid.uuid4()),
        "type": "request",
        "from_agent": "agent_interface",
        "to_agent": "agent_memory",
        "payload": {
            "task": "save_memory",
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content,
        },
        "context": {"user_id": user_id},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(AGENT_MEMORY_URL, json=msg, timeout=30)
        resp.raise_for_status()
        return resp.json()

# ---------------------------------------------------------------------
# Récupération de l'historique utilisateur (compatibilité coach.py)
# ---------------------------------------------------------------------
async def get_history(user_id: str, limit: int = 20) -> Dict[str, Any]:
    """
    Wrapper pour interroger agent_memory et récupérer l'historique:
    - messages du chat
    - repas scannés
    - états mood
    - objectifs
    - événements
    """
    msg = {
        "message_id": str(uuid.uuid4()),
        "type": "request",
        "from_agent": "agent_interface",
        "to_agent": "agent_memory",
        "payload": {
            "task": "get_history",
            "user_id": user_id,
            "limit": limit,
        },
        "context": {"user_id": user_id},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(AGENT_MEMORY_URL, json=msg, timeout=30)
        resp.raise_for_status()
        return resp.json()
