# services/agent_vision/app/vision/client.py

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from groq import Groq

# Charge les variables d'environnement (.env)
load_dotenv()

# ---------------------------------------------------------------------------
# Gestion des chemins de fichiers (context.txt, prompt.txt, images, ...)
# ---------------------------------------------------------------------------

# On part du dossier "services/agent_vision"
BASE_DIR = Path(__file__).resolve().parents[2]

CONTEXT_PATH = BASE_DIR / "context.txt"
PROMPT_PATH = BASE_DIR / "prompt.txt"


def read_file(file_path: Path) -> str:
    """Lit un fichier texte en UTF-8 et renvoie son contenu."""
    with file_path.open("r", encoding="utf-8") as f:
        return f.read()


def encode_image(image_path: Path) -> str:
    """Encode une image en base64 (string)."""
    with image_path.open("rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def ask_vision(image_path: str | Path) -> Dict[str, Any]:
    """
    Appelle Groq Vision avec :
      - context.txt : contexte système
      - prompt.txt  : instructions utilisateur
      - image       : plat à analyser

    Renvoie le résultat JSON déjà parsé (dict).

    ⚠️ Le modèle doit retourner un JSON valide (response_format = json_object).
    """

    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"Image introuvable : {image_path}")

    base64_image = encode_image(image_path)

    groq_key = os.environ.get("GROQ_KEY")
    if not groq_key:
        raise RuntimeError("La variable d'environnement GROQ_KEY n'est pas définie.")

    client = Groq(api_key=groq_key)

    system_content = read_file(CONTEXT_PATH)
    user_prompt = read_file(PROMPT_PATH)

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_content,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            },
        ],
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        response_format={"type": "json_object"},
    )

    raw_content = chat_completion.choices[0].message.content
    # Le modèle renvoie du JSON au format texte -> on parse
    result = json.loads(raw_content)

    return result
