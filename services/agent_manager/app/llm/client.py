import os
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage


# === Chargement du fichier .env ===
#
# Ce fichier client.py est dans :
#   .../SystemeMultiAgentCoach/services/agent_manager/app/llm/client.py
# On remonte jusqu'à la racine du projet pour trouver .env
BASE_DIR = Path(__file__).resolve().parents[4]  # -> SystemeMultiAgentCoach
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)


class LLMClient:
    """
    Client LLM pour l'agent_manager.

    Utilise Groq (modèle Llama 3.1) via LangChain.
    """

    def __init__(
        self,
        model_name: str = "llama-3.1-8b-instant",
        temperature: float = 0.1,
    ) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "La variable d'environnement GROQ_API_KEY n'est pas définie. "
                "Vérifie ton fichier .env à la racine du projet."
            )

        self.llm = ChatGroq(
            model_name=model_name,
            temperature=temperature,
            groq_api_key=api_key,
        )

    def generate_raw(self, prompt: str) -> str:
        """
        Envoie un prompt au LLM et renvoie le texte brut.
        """
        messages = [
            SystemMessage(
                content=(
                    "Tu es un routeur de services pour une application de coach sportif. "
                    "Tu dois toujours répondre avec du JSON STRICTEMENT valide."
                )
            ),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        text = response.content

        # Nettoyage de base en cas de ```json ... ```
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        return cleaned

    def generate_json(self, prompt: str) -> Any:
        """
        Retourne le JSON parsé à partir de la sortie du LLM.
        Lève une ValueError si le JSON est invalide.
        """
        raw = self.generate_raw(prompt)
        return json.loads(raw)
