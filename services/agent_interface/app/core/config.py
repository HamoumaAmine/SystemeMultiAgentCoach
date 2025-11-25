# services/agent_interface/app/core/config.py

import os
from dotenv import load_dotenv

# Charge le fichier .env à la racine du projet
load_dotenv()


class Settings:
    # URL de l'orchestrateur (point d'entrée multi-agents)
    ORCHESTRATOR_URL: str = os.getenv(
        "ORCHESTRATOR_URL",
        "http://orchestrator:8005",  # valeur par défaut (Docker)
    )

    # URL de l'agent_speech (pour upload vocal)
    AGENT_SPEECH_URL: str = os.getenv(
        "AGENT_SPEECH_URL",
        "http://agent_speech:8006",
    )


settings = Settings()
