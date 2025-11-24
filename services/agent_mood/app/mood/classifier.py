import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from groq import Groq
from .utils import normalize_text


@dataclass
class MoodResult:
    mood: str           # ex: "fatigue"
    score: float        # 0.0 à 1.0 (intensité de l'émotion)
    valence: str        # "negative" | "neutral" | "positive"
    energy: str         # "low" | "medium" | "high"
    matched_keywords: Dict[str, List[str]]
    raw_explanation: Optional[str] = None


# Client Groq global (créé une seule fois)
_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    """
    Retourne un client Groq (singleton simple).
    Nécessite la variable d'environnement GROQ_API_KEY.
    """
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY n'est pas défini dans les variables d'environnement."
            )
        _client = Groq(api_key=api_key)
    return _client


def _fallback_simple(text: str) -> MoodResult:
    """
    Fallback ultra simple en cas de problème avec Groq.
    On renvoie un MoodResult basique au lieu de crasher l'agent.
    """
    norm = normalize_text(text or "")

    # mini heuristique : positif / fatigué
    lower = norm.lower()
    if any(w in lower for w in ["epuise", "fatigue", "j en peux plus"]):
        return MoodResult(
            mood="fatigue",
            score=0.6,  # intensité moyenne de fatigue
            valence="negative",
            energy="low",
            matched_keywords={"fatigue": ["epuise/fatigue"]},
            raw_explanation="Fallback simple: mots liés à la fatigue détectés."
        )

    if any(w in lower for w in ["motive", "en forme", "au top", "super bien"]):
        return MoodResult(
            mood="positif",
            score=0.6,  # intensité moyenne de positivité
            valence="positive",
            energy="high",
            matched_keywords={"positif": ["motive/en forme"]},
            raw_explanation="Fallback simple: mots positifs détectés."
        )

    return MoodResult(
        mood="neutre",
        score=0.5,
        valence="neutral",
        energy="medium",
        matched_keywords={},
        raw_explanation="Fallback simple: aucun signal clair."
    )


def analyze_mood(text: str) -> MoodResult:
    """
    Analyse du mood basée sur un LLM Groq.

    Le LLM renvoie :
      - mood
      - score (intensité de l'émotion entre 0 et 1)
      - valence
      - energy
      - matched_keywords
      - explanation

    On conserve le score fourni par le modèle (en le bornant à [0, 1]).
    """
    norm = normalize_text(text or "")
    if not norm:
        return MoodResult(
            mood="neutre",
            score=0.5,
            valence="neutral",
            energy="medium",
            matched_keywords={},
            raw_explanation="Texte vide ou non fourni."
        )

    client = get_groq_client()

    system_prompt = (
    "Tu es un analyseur d'humeur (mood tracker) pour un coach sport/nutrition.\n"
    "Ton rôle est d'analyser un message d'utilisateur francophone et de retourner :\n"
    "- son humeur principale (mood),\n"
    "- un score d'intensité entre 0 et 1,\n"
    "- la valence (positive / neutral / negative),\n"
    "- le niveau d'énergie (low / medium / high),\n"
    "- les mots-clés qui justifient ton analyse.\n\n"

    "⚠️ IMPORTANT :\n"
    "- Le champ \"score\" NE représente PAS une confiance.\n"
    "- Le score doit représenter UNIQUEMENT **l'intensité émotionnelle**.\n"
    "- Si l'émotion est négative (fatigue, stress, tristesse, démotivation), "
    "le score doit être **proche de 0**.\n"
    "- Si l'émotion est positive (motivation, optimisme, énergie), "
    "le score doit être **proche de 1**.\n"
    "- Une émotion neutre doit produire un score autour de 0.5.\n\n"

    "Échelle exacte à utiliser :\n"
    "- 0.0 -0.2 : émotion fortement négative (fatigue extrême, épuisement, tristesse).\n"
    "- 0.2 - 0.4 : émotion négative faible à modérée.\n"
    "- 0.4 - 0.6 : état neutre ou ambigu.\n"
    "- 0.6 - 0.8 : émotion positive faible à modérée.\n"
    "- 0.8 - 1.0 : émotion fortement positive (forte motivation, euphorie, énergie).\n\n"

    "Format de sortie :\n"
    "{\n"
    '  \"mood\": \"fatigue | demotivation | stress | tristesse | positif | neutre\",\n'
    '  \"score\": 0.0 à 1.0,  # intensité selon l’échelle ci-dessus\n'
    '  \"valence\": \"positive\" | \"neutral\" | \"negative\",\n'
    '  \"energy\": \"low\" | \"medium\" | \"high\",\n'
    "  \"matched_keywords\": {\n"
    '    \"categorie_principale\": [\"mot1\", \"mot2\"]\n'
    "  },\n"
    '  \"explanation\": \"courte explication en français montrant comment tu as évalué l’intensité\"\n'
    "}\n\n"

    "Exemples :\n"
    "- \"je suis complètement épuisé\" → mood=fatigue, score ≈ 0.1, valence=negative.\n"
    "- \"je suis un peu stressé mais ça va\" → mood=stress, score ≈ 0.3.\n"
    "- \"ça va, journée normale\" → mood=neutre, score ≈ 0.5.\n"
    "- \"je suis super motivé, j’ai trop d’énergie\" → mood=positif, score ≈ 0.9.\n\n"

    "Réponds STRICTEMENT en JSON sans aucune phrase autour."
)


    user_prompt = (
        "Message utilisateur (en français) :\n"
        f"\"{norm}\"\n\n"
        "Analyse ce message et renvoie UNIQUEMENT le JSON décrit dans les consignes."
    )

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )

        content = completion.choices[0].message.content or ""
        content_str = content.strip()

        # Si le modèle renvoie du texte autour, on essaie d'isoler le JSON
        if not content_str.startswith("{"):
            first = content_str.find("{")
            last = content_str.rfind("}")
            if first != -1 and last != -1 and last > first:
                content_str = content_str[first:last + 1]

        data = json.loads(content_str)

        mood = data.get("mood", "neutre")
        score = data.get("score", 0.5)
        valence = data.get("valence", "neutral")
        energy = data.get("energy", "medium")
        matched_keywords = data.get("matched_keywords") or {}
        explanation = data.get("explanation")

        # Normalisation du mood
        if mood not in ["fatigue", "demotivation", "stress",
                        "tristesse", "positif", "neutre"]:
            mood = "neutre"

        # Garde-fous sur le score (intensité)
        try:
            score = float(score)
        except Exception:
            score = 0.5

        if not 0.0 <= score <= 1.0:
            score = 0.5

        # Normalisation valence / energy / matched_keywords
        if valence not in ["positive", "neutral", "negative"]:
            valence = "neutral"
        if energy not in ["low", "medium", "high"]:
            energy = "medium"
        if not isinstance(matched_keywords, dict):
            matched_keywords = {}

        return MoodResult(
            mood=mood,
            score=score,          
            valence=valence,
            energy=energy,
            matched_keywords=matched_keywords,
            raw_explanation=explanation,
        )

    except Exception as e:
        print(f"[agent_mood] Erreur Groq : {e}")
        # Fallback en cas de bug LLM
        return _fallback_simple(text)
