# services/agent_speech/app/mcp/handler.py

import os
import uuid
import json
from typing import Any, Dict, Optional

from app.mcp.schemas import MCPResponse
from app.stt.whisper_client_groq import WhisperClientGroq


class SpeechMCPHandler:
    """
    Petit wrapper autour de WhisperClientGroq pour :
      - transcrire un fichier audio
      - créer un fichier texte voisin
      - renvoyer un résultat structuré
    """

    def __init__(self) -> None:
        self.whisper = WhisperClientGroq()

    def process(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcrit l'audio situé à audio_path.

        Retourne un dict contenant :
          - agent: nom de l'agent
          - input_file: chemin audio
          - output_file: chemin texte
          - output_text: texte transcrit
        """
        # 1. Transcription de l'audio
        result = self.whisper.transcribe(audio_path)

        # 2. Extraction du texte principal
        if isinstance(result, dict):
            text = result.get("text") or json.dumps(result, indent=2, ensure_ascii=False)
        else:
            text = str(result)

        # 3. Préparer le chemin du fichier texte (même dossier, même nom, extension .txt)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        txt_path = os.path.join(os.path.dirname(audio_path), f"{base_name}.txt")

        # 4. Écriture dans le fichier texte
        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        return {
            "agent": "speech_to_text",
            "input_file": audio_path,
            "output_file": txt_path,
            "output_text": text,
        }


speech_handler = SpeechMCPHandler()


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Point d'entrée MCP pour l'agent_speech.

    Tâche gérée :
      - "transcribe_audio" : on reçoit un chemin de fichier audio, on renvoie la transcription.

    Payload attendu :
      {
        "task": "transcribe_audio",
        "audio_path": "/chemin/vers/fichier.mp3"
      }
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")

    if task != "transcribe_audio":
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue pour agent_speech: {task!r}",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    audio_path: Optional[str] = payload.get("audio_path")

    if not audio_path:
        response_payload = {
            "status": "error",
            "task": "transcribe_audio",
            "message": "Champ 'audio_path' manquant dans le payload.",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    try:
        result = speech_handler.process(audio_path)
        response_payload = {
            "status": "ok",
            "task": "transcribe_audio",
            **result,
        }
    except Exception as e:
        response_payload = {
            "status": "error",
            "task": "transcribe_audio",
            "message": str(e),
        }

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
