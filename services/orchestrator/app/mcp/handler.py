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
) -> List[Dict[str, Any]]:
    """
    Appelle l'agent_manager pour obtenir la liste des services à exécuter.

    Le résultat est une liste de dicts de la forme :
      {
        "service": "mood",
        "command": "analyze_mood",
        "text": "..."
      }
    """

    msg: Dict[str, Any] = {
        "message_id": str(uuid.uuid4()),
        "from_agent": "orchestrator",
        "to_agent": "agent_manager",
        "type": "request",
        "payload": {
            "task": "route_services",
            "text": user_input,
        },
        "context": {"user_id": user_id} if user_id else {},
    }

    response = await call_agent(AGENT_MANAGER_URL, msg)
    payload = response.get("payload", {}) or {}

    if payload.get("status") != "ok":
        return []

    services = payload.get("services", [])
    if not isinstance(services, list):
        return []

    return services


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Orchestrateur principal.

    Tâche gérée :
      - "process_user_input" : reçoit un texte utilisateur (et éventuellement
        une transcription audio), orchestre les appels aux autres agents.

    Entrée attendue dans payload :
      - task: "process_user_input"
      - user_input: str (facultatif, texte brut fourni par l'interface)

    La réponse contient :
      - status: "ok" ou "error"
      - task: "process_user_input"
      - user_id: str ou None
      - mood_state: dict ou None
      - coach_answer: str ou None
      - speech_transcription: dict ou None
      - called_services: liste des services exécutés

    Comportement particulier :
      - si un service "speech"/"transcribe_audio" est exécuté en premier et
        renvoie un "output_text", ce texte est utilisé comme entrée pour les
        services suivants (mood, coaching, etc.).
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

    # -------------------------------------------------------------------------
    # 1) Appeler l'agent_manager pour savoir quels services exécuter
    # -------------------------------------------------------------------------
    services = await _route_with_manager(user_input, user_id)

    # Convertir vers des objets ServiceCommand
    service_commands: List[ServiceCommand] = []
    for service_cmd in services:
        service_name = service_cmd.get("service")
        command = service_cmd.get("command")
        text_for_service = service_cmd.get("text", user_input)

        if not service_name or not command:
            continue

        service_commands.append(
            ServiceCommand(
                service=service_name,
                command=command,
                text=text_for_service,
            )
        )

    # -------------------------------------------------------------------------
    # 2) Exécuter chaque service via ServiceRegistry
    # -------------------------------------------------------------------------
    mood_state: Optional[Dict[str, Any]] = None
    coach_answer: Optional[str] = None

    # Nouveau : pour gérer la transcription de l'audio
    transcription_result: Optional[Dict[str, Any]] = None
    transcribed_text: Optional[str] = None

    for cmd in service_commands:
        # -------------------------------------------------------------
        # 2.a) Cas spécial : service SPEECH (transcription audio)
        # -------------------------------------------------------------
        if cmd.service == "speech" and cmd.command == "transcribe_audio":
            result = await service_registry.execute(
                cmd,
                user_id=user_id,
                mood_state=mood_state,
            )

            if isinstance(result, dict):
                transcription_result = result
                text_from_speech = result.get("output_text")
                if isinstance(text_from_speech, str) and text_from_speech.strip():
                    transcribed_text = text_from_speech

            # On passe au service suivant (on ne traite pas mood/coach ici)
            continue

        # -------------------------------------------------------------
        # 2.b) Pour les autres services (mood, coaching, nutrition...)
        #      si une transcription existe, on l'utilise comme texte.
        # -------------------------------------------------------------
        if transcribed_text:
            cmd.text = transcribed_text

        result = await service_registry.execute(
            cmd,
            user_id=user_id,
            mood_state=mood_state,
        )

        # Interprétation du résultat selon le type de service
        if cmd.service == "mood" and cmd.command == "analyze_mood":
            if isinstance(result, dict):
                mood_state = result

        if cmd.service == "coaching" and cmd.command == "coach_response":
            if isinstance(result, str):
                coach_answer = result

        # Plus tard :
        # - service "nutrition"
        # - service "vision"
        # - etc.

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
        "called_services": services,
    }

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
