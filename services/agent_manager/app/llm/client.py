import os
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage


# === Chargement du fichier .env de manière robuste ===
#
# Avant : BASE_DIR = Path(__file__).resolve().parents[4] -> IndexError en Docker.
# Maintenant :
#   1. On remonte les parents du fichier jusqu'à trouver un ".env".
#   2. Si on ne trouve rien, on prend un fallback raisonnable (parents[2] => /app).
#

CURRENT_FILE = Path(__file__).resolve()

base_dir_candidate: Path | None = None
for parent in CURRENT_FILE.parents:
    if (parent / ".env").exists():
        base_dir_candidate = parent
        break

if base_dir_candidate is None:
    parents = CURRENT_FILE.parents
    if len(parents) >= 3:
        base_dir_candidate = parents[2]  # typiquement /app dans le conteneur
    else:
        base_dir_candidate = parents[0]

BASE_DIR = base_dir_candidate
dotenv_path = BASE_DIR / ".env"

# Charge le .env s'il existe, mais ne plante pas s'il n'existe pas :
load_dotenv(dotenv_path=dotenv_path)

print(f"[agent_manager] BASE_DIR = {BASE_DIR}")
print(f"[agent_manager] .env = {dotenv_path} (exists={dotenv_path.exists()})")


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
                "Vérifie ton fichier .env à la racine du projet ou la config Docker."
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
