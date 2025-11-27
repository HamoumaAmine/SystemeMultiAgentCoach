# services/orchestrator/app/mcp/handler.py

import uuid
from typing import Any, Dict, List, Optional

from app.mcp.schemas import MCPResponse
from app.services_registry import (
    AGENT_MANAGER_URL,
    ServiceCommand,
    ServiceRegistry,
    call_agent,
)

# On instancie un registry global pour l'orchestrateur.
service_registry = ServiceRegistry()


async def _route_with_manager(
    user_input: str,
    user_id: Optional[str],
    audio_path: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Appelle l'agent_manager pour obtenir la liste des services à exécuter.

    Le résultat est une liste de dicts de la forme :
      {
        "service": "mood",
        "command": "analyze_mood",
        "text": "...",
        ...
      }

    Si audio_path est fourni, il est transmis à l'agent_manager pour qu'il
    ajoute éventuellement un service "speech"/"transcribe_audio".
    """

    payload: Dict[str, Any] = {
        "task": "route_services",
        "text": user_input,
    }
    if audio_path:
        payload["audio_path"] = audio_path

    msg: Dict[str, Any] = {
        "message_id": str(uuid.uuid4()),
        "from_agent": "orchestrator",
        "to_agent": "agent_manager",
        "type": "request",
        "payload": payload,
        "context": {"user_id": user_id} if user_id else {},
    }

    response = await call_agent(AGENT_MANAGER_URL, msg)
    payload_resp = response.get("payload", {}) or {}

    if payload_resp.get("status") != "ok":
        return []

    services = payload_resp.get("services", [])
    if not isinstance(services, list):
        return []

    return services


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Orchestrateur principal.

    Tâche gérée :
      - "process_user_input" : reçoit un texte utilisateur (et éventuellement
        un chemin audio et/ou un chemin image), orchestre les appels aux autres
        agents.

    Entrée attendue dans payload :
      - task: "process_user_input"
      - user_input: str (facultatif, texte brut fourni par l'interface)
      - audio_path: str (facultatif, chemin/identifiant du fichier audio)
      - image_path: str (facultatif, chemin/identifiant de l'image à analyser)

    La réponse contient :
      - status: "ok" ou "error"
      - task: "process_user_input"
      - user_id: str ou None
      - mood_state: dict ou None
      - coach_answer: str ou None
      - speech_transcription: dict ou None
      - nutrition_result: dict ou None
      - vision_result: dict ou None
      - called_services: liste brute des services reçus de l'agent_manager

    Comportement vocal :
      - si un service "speech"/"transcribe_audio" est exécuté et renvoie un
        "output_text", ce texte est utilisé comme entrée pour les services
        suivants (mood, nutrition, coaching, etc.).
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")
    user_id: Optional[str] = context.get("user_id")

    # -------------------------------------------------------------------------
    # Vérification de la tâche demandée
    # -------------------------------------------------------------------------
    if task != "process_user_input":
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue pour orchestrateur: {task!r}",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    user_input: str = payload.get("user_input", "") or ""
    audio_path: Optional[str] = payload.get("audio_path")
    image_path: Optional[str] = payload.get("image_path")

    # -------------------------------------------------------------------------
    # 1) Appeler l'agent_manager pour savoir quels services exécuter
    # -------------------------------------------------------------------------
    services = await _route_with_manager(user_input, user_id, audio_path)
    print("[ORCH] services demandés par agent_manager :", services, flush=True)

    # Convertir vers des objets ServiceCommand
    service_commands: List[ServiceCommand] = []
    has_speech_cmd = False
    has_coaching_cmd = False

    for service_cmd in services:
        service_name = service_cmd.get("service")
        command = service_cmd.get("command")
        text_for_service = service_cmd.get("text", user_input)

        if not service_name or not command:
            continue

        cmd = ServiceCommand(
            service=service_name,
            command=command,
            text=text_for_service,
        )
        service_commands.append(cmd)

        if cmd.service == "speech" and cmd.command == "transcribe_audio":
            has_speech_cmd = True
        if cmd.service == "coaching" and cmd.command == "coach_response":
            has_coaching_cmd = True

    # -------------------------------------------------------------------------
    # 1.a) S'assurer que le vocal est bien transcrit
    #   - si audio_path est présent mais pas de commande speech,
    #     on en injecte une nous-mêmes.
    #   - si une commande speech existe déjà, on force son .text = audio_path.
    # -------------------------------------------------------------------------
    if audio_path:
        if not has_speech_cmd:
            # On force une commande speech en premier
            service_commands.insert(
                0,
                ServiceCommand(
                    service="speech",
                    command="transcribe_audio",
                    text=audio_path,
                ),
            )
        else:
            for c in service_commands:
                if c.service == "speech" and c.command == "transcribe_audio":
                    c.text = audio_path

    # -------------------------------------------------------------------------
    # 1.b) Ajouter une commande vision si une image est fournie
    # -------------------------------------------------------------------------
    if image_path:
        service_commands.append(
            ServiceCommand(
                service="vision",
                command="analyze_image",
                text=image_path,
            )
        )

    # -------------------------------------------------------------------------
    # 2) Exécution des services en DEUX PASSES
    # -------------------------------------------------------------------------
    mood_state: Optional[Dict[str, Any]] = None
    coach_answer: Optional[str] = None

    transcription_result: Optional[Dict[str, Any]] = None
    transcribed_text: Optional[str] = None

    nutrition_result: Optional[Dict[str, Any]] = None
    vision_result: Optional[Dict[str, Any]] = None

    coaching_commands: List[ServiceCommand] = []

    # ------------------------- 2.1 Première passe ----------------------------
    for cmd in service_commands:
        # Cas spécial : speech
        if cmd.service == "speech" and cmd.command == "transcribe_audio":
            result = await service_registry.execute(
                cmd,
                user_id=user_id,
                mood_state=mood_state,
                nutrition_result=nutrition_result,
                vision_result=vision_result,
            )
            if isinstance(result, dict):
                transcription_result = result
                text_from_speech = result.get("output_text")
                if isinstance(text_from_speech, str) and text_from_speech.strip():
                    transcribed_text = text_from_speech
            continue

        # Cas spécial : vision
        if cmd.service == "vision" and cmd.command in (
            "analyze_image",
            "analyze_diet_image",
        ):
            result = await service_registry.execute(
                cmd,
                user_id=user_id,
                mood_state=mood_state,
                nutrition_result=nutrition_result,
                vision_result=vision_result,
            )
            if isinstance(result, dict):
                vision_result = result
            continue

        # On garde les commandes de coaching pour la 2ème passe
        if cmd.service == "coaching" and cmd.command == "coach_response":
            coaching_commands.append(cmd)
            continue

        # Pour les autres services, si on a une transcription, on l'utilise
        if transcribed_text:
            cmd.text = transcribed_text

        result = await service_registry.execute(
            cmd,
            user_id=user_id,
            mood_state=mood_state,
            nutrition_result=nutrition_result,
            vision_result=vision_result,
        )

        # mood
        if cmd.service == "mood" and cmd.command == "analyze_mood":
            if isinstance(result, Dict):
                mood_state = result

        # Agent knowledge / nutrition (deux syntaxes possibles)
        if (
            cmd.service == "knowledge"
            and cmd.command == "nutrition_suggestions"
            and isinstance(result, dict)
        ):
            nutrition_result = result

        if (
            cmd.service == "nutrition"
            and cmd.command == "analyze_meal"
            and isinstance(result, dict)
        ):
            nutrition_result = result

    # -------------------------------------------------------------------------
    # 2.1bis) Si aucun service de coaching n'a été prévu par l'agent_manager,
    #         on en ajoute un par défaut basé sur la transcription (ou le texte).
    # -------------------------------------------------------------------------
    if not coaching_commands:
        base_text = transcribed_text or (user_input or "")
        if base_text.strip():
            coaching_commands.append(
                ServiceCommand(
                    service="coaching",
                    command="coach_response",
                    text=base_text,
                )
            )

    # ------------------------- 2.2 Deuxième passe ----------------------------
    for cmd in coaching_commands:
        if transcribed_text:
            cmd.text = transcribed_text

        result = await service_registry.execute(
            cmd,
            user_id=user_id,
            mood_state=mood_state,
            nutrition_result=nutrition_result,
            vision_result=vision_result,
        )

        if isinstance(result, str):
            coach_answer = result

    # -------------------------------------------------------------------------
    # 3) Construire la réponse globale
    # -------------------------------------------------------------------------
    response_payload: Dict[str, Any] = {
        "status": "ok",
        "task": "process_user_input",
        "user_id": user_id,
        "mood_state": mood_state,
        "coach_answer": coach_answer,
        "speech_transcription": transcription_result,
        "nutrition_result": nutrition_result,
        "vision_result": vision_result,
        "called_services": services,
    }

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
