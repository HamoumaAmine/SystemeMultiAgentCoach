import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq

from .utils import normalize_text


# === Chargement du .env de manière robuste ===============================
#
# Avant : PROJECT_ROOT = Path(__file__).resolve().parents[5]  -> IndexError en Docker.
# Maintenant :
#   1. On remonte les parents du fichier jusqu'à trouver un ".env".
#   2. Si on ne trouve rien, on prend un fallback raisonnable (parents[2] => /app).
#

CURRENT_FILE = Path(__file__).resolve()

project_root_candidate: Optional[Path] = None
for parent in CURRENT_FILE.parents:
    if (parent / ".env").exists():
        project_root_candidate = parent
        break

if project_root_candidate is None:
    # Fallback : on suppose que le code est dans /app/app/...  -> racine = parents[2] (= /app)
    # On évite surtout d'accéder à un parents[5] inexistant.
    # On protège aussi si jamais il y a moins de 3 parents.
    parents = CURRENT_FILE.parents
    if len(parents) >= 3:
        project_root_candidate = parents[2]
    else:
        # Ultime fallback : le dossier du fichier
        project_root_candidate = parents[0]

PROJECT_ROOT = project_root_candidate
ENV_PATH = PROJECT_ROOT / ".env"

# On charge le .env s'il existe, sinon ce n'est pas grave :
# les variables d'environnement peuvent venir de Docker (docker-compose).
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)

print(f"[agent_mood] PROJECT_ROOT = {PROJECT_ROOT}")
print(f"[agent_mood] .env = {ENV_PATH} (exists={ENV_PATH.exists()})")


@dataclass
class MoodResult:
    """Structure de sortie normalisée pour l'agent mood."""
    mood: str                         # ex: "fatigue", "stress", "positif"
    score: float                      # 0.0 à 1.0 (intensité)
    valence: str                      # "negative" | "neutral" | "positive"
    energy: str                       # "low" | "medium" | "high"
    matched_keywords: Dict[str, List[str]]
    raw_explanation: Optional[str] = None


_client: Optional[Groq] = None


def _get_groq_client() -> Optional[Groq]:
    """
    Renvoie un client Groq prêt à l'emploi.

    Si la clé API n'est pas définie ou si quelque chose ne va pas,
    on renvoie None et on laissera le code appelant faire un fallback.
    """
    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print(
            "[agent_mood] Avertissement : GROQ_API_KEY non définie. "
            "L'agent mood utilisera uniquement le fallback par mots-clés."
        )
        return None

    try:
        _client = Groq(api_key=api_key)
        return _client
    except Exception as e:  # sécurité maximale
        print(f"[agent_mood] Erreur lors de la création du client Groq : {e}")
        return None


# === Fallback simple par mots-clés ==========================================

def _fallback_simple(text: str) -> MoodResult:
    """
    Analyse très simple basée sur quelques mots-clés.
    Utilisée quand le LLM n'est pas disponible.
    """
    lower = normalize_text(text)
    matched: Dict[str, List[str]] = {}

    def match_any(label: str, keywords: List[str]) -> bool:
        hits = [kw for kw in keywords if kw in lower]
        if hits:
            matched[label] = hits
            return True
        return False

    # 1) Fatigue / négatif / low energy
    if match_any("fatigue", ["epuise", "fatigue", "creve", "j'en peux plus", "hs"]):
        return MoodResult(
            mood="fatigue",
            score=0.7,
            valence="negative",
            energy="low",
            matched_keywords=matched,
            raw_explanation="Détection de mots-clés liés à la fatigue."
        )

    # 2) Stress / anxiété
    if match_any("stress", ["stress", "stresse", "angoisse", "anxieux"]):
        return MoodResult(
            mood="stress",
            score=0.6,
            valence="negative",
            energy="medium",
            matched_keywords=matched,
            raw_explanation="Détection de mots-clés liés au stress."
        )

    # 3) Positif / motivé
    if match_any("motivation", ["motive", "en forme", "au top", "super bien"]):
        return MoodResult(
            mood="positif",
            score=0.6,
            valence="positive",
            energy="high",
            matched_keywords=matched,
            raw_explanation="Détection de mots-clés liés à la motivation."
        )

    # 4) Par défaut neutre
    return MoodResult(
        mood="neutre",
        score=0.3,
        valence="neutral",
        energy="medium",
        matched_keywords=matched,
        raw_explanation="Aucun mot-clé caractéristique détecté, humeur neutre."
    )


# === Analyse basée sur un LLM Groq ==========================================

def _analyze_with_llm(text: str) -> MoodResult:
    """
    Utilise un modèle Groq pour analyser l'état mental et physique.

    Le modèle doit renvoyer un JSON strict avec les champs :
    - mood: str
    - score: float
    - valence: str
    - energy: str
    - matched_keywords: dict
    - explanation: str
    """
    client = _get_groq_client()
    if client is None:
        # Pas de LLM dispo -> fallback direct
        return _fallback_simple(text)

    model_name = os.getenv("GROQ_MOOD_MODEL", "llama-3.3-70b-versatile")

    system_prompt = (
        "Tu es un analyseur d'humeur (mood tracker). "
        "À partir d'un texte en français décrivant l'état mental et physique "
        "de l'utilisateur, tu dois produire un JSON strict avec les clés "
        "suivantes :\n"
        "- mood: étiquette courte (ex: 'fatigue', 'stress', 'positif', 'neutre')\n"
        "- score: nombre entre 0 et 1 indiquant l'intensité de l'état principal\n"
        "- valence: 'negative', 'neutral' ou 'positive'\n"
        "- energy: 'low', 'medium' ou 'high'\n"
        "- matched_keywords: dictionnaire (clé = étiquette, valeur = liste de mots détectés)\n"
        "- explanation: courte phrase expliquant ton raisonnement\n"
        "Réponds STRICTEMENT avec un JSON valide, sans autre texte autour."
    )

    user_prompt = f"Texte utilisateur : {text}"

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=512,
        )

        content = completion.choices[0].message.content.strip()
        data = json.loads(content)

        mood = str(data.get("mood", "neutre"))
        score = float(data.get("score", 0.5))
        valence = str(data.get("valence", "neutral"))
        energy = str(data.get("energy", "medium"))
        matched_keywords = data.get("matched_keywords") or {}
        if not isinstance(matched_keywords, dict):
            matched_keywords = {}
        explanation = str(data.get("explanation", ""))

        return MoodResult(
            mood=mood,
            score=score,
            valence=valence,
            energy=energy,
            matched_keywords=matched_keywords,
            raw_explanation=explanation,
        )

    except Exception as e:
        # Quelle que soit l'erreur (clé invalide, modèle indisponible, JSON mal formé...),
        # on ne casse pas le service : on log et on fait un fallback.
        print(f"[agent_mood] Erreur Groq / parsing JSON : {e}")
        return _fallback_simple(text)


def analyze_mood(text: str) -> MoodResult:
    """
    Point d'entrée public de l'agent mood.

    1. On nettoie le texte.
    2. On tente une analyse via LLM Groq.
    3. En cas de problème, on retombe sur le fallback par mots-clés.
    """
    if not text:
        return MoodResult(
            mood="neutre",
            score=0.0,
            valence="neutral",
            energy="medium",
            matched_keywords={},
            raw_explanation="Texte vide : humeur considérée comme neutre."
        )

    text = text.strip()
    return _analyze_with_llm(text)
