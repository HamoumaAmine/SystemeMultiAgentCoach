from dotenv import load_dotenv 
import os
from pathlib import Path
import openai
load_dotenv()

class WhisperClient:
    def __init__(self):
        """Initialisation du client Whisper Large v3 Turbo via API OpenAI."""
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "whisper-large-v3-turbo"

    def transcribe(self, audio_path: str) -> dict:
        """
        Transcrit un fichier audio avec Whisper Large v3 Turbo.
        Retourne un dictionnaire structuré (texte + métadonnées).
        """
        audio_file = Path(audio_path)

        if not audio_file.exists():
            raise FileNotFoundError(f"Fichier introuvable : {audio_path}")

        with open(audio_file, "rb") as f:
            response = openai.audio.transcriptions.create(
                model=self.model,
                file=f,
                response_format="verbose_json"
            )

        return {
            "text": response.get("text", ""),
            "language": response.get("language", "unknown"),
            "duration": response.get("duration", 0),
            "segments": response.get("segments", [])
        }
