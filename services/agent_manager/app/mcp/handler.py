# services/agent_manager/app/mcp/handler.py

import uuid
from typing import Any, Dict, List, Optional

from app.llm.client import LLMClient
from app.llm.prompts import build_router_prompt
from app.mcp.schemas import MCPMessage, MCPResponse


def _fallback_decide_services(user_text: str) -> List[Dict[str, Any]]:
    """
    Stratégie de secours / d'enrichissement basée sur des mots-clés.

    On utilise quelques règles simples pour choisir les services
    "mood", "coaching" et "nutrition".

    ⚠️ IMPORTANT :
    - Cette fonction est utilisée même quand le LLM routeur répond,
      pour S'AJOUTER aux services proposés, sans doublon.
    """
    text_lower = user_text.lower()
    services: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Mots-clés liés à l'humeur
    # ------------------------------------------------------------------ #
    mood_keywords = [
        "fatigué",
        "fatigue",
        "épuisé",
        "stressé",
        "déprimé",
        "motivé",
        "démotivé",
        "anxieux",
        "angoissé",
        "moral",
    ]
    if any(k in text_lower for k in mood_keywords):
        services.append(
            {
                "service": "mood",
                "command": "analyze_mood",
                "text": user_text,
            }
        )

    # ------------------------------------------------------------------ #
    # Mots-clés liés au sport / entraînement
    # ------------------------------------------------------------------ #
    coaching_keywords = [
        "sport",
        "séance",
        "entrainement",
        "entraînement",
        "programme",
        "musculation",
        "cardio",
        "course",
        "marathon",
        "footing",
        "perte de poids",
        "reprendre le sport",
    ]
    if any(k in text_lower for k in coaching_keywords) or not services:
        services.append(
            {
                "service": "coaching",
                "command": "coach_response",
                "text": user_text,
            }
        )

    # ------------------------------------------------------------------ #
    # Mots-clés liés à la nutrition
    #  + objectifs de poids (perdre du poids, maigrir, etc.)
    # ------------------------------------------------------------------ #
    nutrition_keywords = [
        "repas",
        "déjeuner",
        "dejeuner",
        "dîner",
        "diner",
        "calories",
        "calorique",
        "manger",
        "nutrition",
        "plat",
        "menu",
        "couscous",
        "burger",
        "pizza",
    ]

    weight_goal_keywords = [
        "perdre du poids",
        "perte de poids",
        "perdre du gras",
        "perte de gras",
        "maigrir",
        "mincir",
        "sèche",
        "seche",
    ]

    if any(k in text_lower for k in nutrition_keywords) or any(
        k in text_lower for k in weight_goal_keywords
    ):
        services.append(
            {
                "service": "nutrition",
                "command": "analyze_meal",
                "text": user_text,
            }
        )

    return services


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Gestionnaire MCP pour l'agent_manager.

    Tâche gérée :
      - "route_services" : reçoit un texte utilisateur (et éventuellement un
        chemin audio) et décide quels services doivent être appelés.

    Payload attendu :
      - task: "route_services"
      - text: str (facultatif, texte de la demande)
      - audio_path: str (facultatif, chemin d'un fichier audio à transcrire)

    Réponse :
      - status: "ok" ou "error"
      - task: "route_services"
      - services: liste de dicts {service, command, text, ...}
      - llm_error: message d'erreur éventuel du routeur LLM
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")

    if task != "route_services":
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue pour agent_manager: {task!r}",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    user_text: str = payload.get("text", "") or ""
    audio_path: Optional[str] = payload.get("audio_path")

    services: List[Dict[str, Any]] = []
    error_info: Optional[str] = None

    # ------------------------------------------------------------------ #
    # 1) Si un chemin audio est fourni, on ajoute systématiquement
    #    un service speech/transcribe_audio.
    # ------------------------------------------------------------------ #
    if audio_path:
        services.append(
            {
                "service": "speech",
                "command": "transcribe_audio",
                "text": audio_path,  # utilisé comme chemin audio par le registry
            }
        )

    # ------------------------------------------------------------------ #
    # 2) Utiliser le LLM routeur pour les autres services (mood, coaching,
    #    nutrition, history), à partir du texte utilisateur.
    # ------------------------------------------------------------------ #
    if user_text.strip():
        try:
            router_prompt = build_router_prompt(user_text)
            llm_client = LLMClient()
            llm_output = llm_client.generate_json(router_prompt)

            raw_services = llm_output.get("services", [])
            if isinstance(raw_services, list):
                for item in raw_services:
                    if not isinstance(item, dict):
                        continue
                    svc = item.get("service")
                    cmd = item.get("command")
                    txt = item.get("text", user_text)
                    if not svc or not cmd:
                        continue
                    services.append(
                        {
                            "service": svc,
                            "command": cmd,
                            "text": txt,
                        }
                    )
        except Exception as e:
            error_info = f"Erreur LLM router: {e!r}"

    # ------------------------------------------------------------------ #
    # 3) Calculer les services de fallback (mots-clés) ET les fusionner
    #    avec ceux du LLM, sans doublons.
    # ------------------------------------------------------------------ #
    fallback_services: List[Dict[str, Any]] = []
    if user_text.strip():
        fallback_services = _fallback_decide_services(user_text)

    if fallback_services:
        existing_pairs = {
            (s.get("service"), s.get("command"))
            for s in services
            if isinstance(s, dict)
        }
        for fs in fallback_services:
            key = (fs.get("service"), fs.get("command"))
            if key not in existing_pairs:
                services.append(fs)

    # (Optionnel) log debug pour voir ce qui est renvoyé
    # print("[AGENT_MANAGER] services finaux :", services, flush=True)

    response_payload: Dict[str, Any] = {
        "status": "ok",
        "task": "route_services",
        "services": services,
    }
    if error_info:
        response_payload["llm_error"] = error_info

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
