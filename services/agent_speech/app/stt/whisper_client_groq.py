import os
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class WhisperClientGroq:
    def __init__(self):
        """Initialisation du client Groq Whisper via l’API Groq."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("La variable d'environnement GROQ_API_KEY est manquante.")
        
        self.client = Groq(api_key=api_key)
        self.model = "whisper-large-v3-turbo"  # ou autre modèle Groq whisper

    def transcribe(self, audio_path: str) -> dict:
        """
        Transcrit un fichier audio via Groq Whisper API.
        Retourne un dict structuré (texte + métadonnées).
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Fichier introuvable : {audio_path}")
        
        # On envoie le fichier audio à Groq
        response = self.client.audio.transcriptions.create(
            model=self.model,
            file=audio_file,  # le SDK groq accepte un Path
            response_format="verbose_json",  # ou "json" ou "text"
            
        )

        # Le type de response dépend du SDK Groq : on va supposer que c'est un objet Pydantic
        return {
            "text": response.text,
            # Groq ne renvoie pas forcément "language" ni "duration", ça dépend de la réponse
            "response_raw": response.model_dump(),  
        }
