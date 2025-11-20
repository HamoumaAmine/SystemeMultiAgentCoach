import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from groq import Groq
from .utils import normalize_text


@dataclass
class MoodResult:
    mood: str           # ex: "fatigue"
    score: float        # 0.0 à 1.0
    valence: str        # "negative" | "neutral" | "positive"
    energy: str         # "low" | "medium" | "high"
    matched_keywords: Dict[str, List[str]]
    raw_explanation: Optional[str] = None


# Client Groq global (créé une seule fois)
_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY n'est pas défini dans les variables d'environnement.")
        _client = Groq(api_key=api_key)
    return _client


def _fallback_simple(text: str) -> MoodResult:
    """
    Fallback ultra simple en cas de problème avec Groq.
    On renvoie 'neutre' au lieu de crasher l'agent.
    """
    norm = normalize_text(text or "")

    # mini heuristique : positif / fatigué
    lower = norm.lower()
    if any(w in lower for w in ["epuise", "fatigue", "j en peux plus"]):
        return MoodResult(
            mood="fatigue",
            score=0.6,
            valence="negative",
            energy="low",
            matched_keywords={"fatigue": ["epuise/fatigue"]},
            raw_explanation="Fallback simple: mots liés à la fatigue détectés."
        )

    if any(w in lower for w in ["motivé", "motive", "en forme", "au top", "super bien"]):
        return MoodResult(
            mood="positif",
            score=0.6,
            valence="positive",
            energy="high",
            matched_keywords={"positif": ["motivé/en forme"]},
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
    Le LLM renvoie mood + score + valence + energy + matched_keywords + explanation.
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
        "Ton rôle est d'analyser le message d'un utilisateur francophone et de détecter :\n"
        "- son humeur principale (mood),\n"
        "- l'intensité / confiance de cette humeur (score entre 0 et 1),\n"
        "- la valence (positive / neutre / négative),\n"
        "- le niveau d'énergie (low / medium / high),\n"
        "- et quelques mots / expressions du texte qui t'ont servi d'indice.\n\n"
        "Tu dois OBLIGATOIREMENT répondre en JSON STRICT, SANS aucun texte autour,\n"
        "avec exactement la structure suivante :\n\n"
        "{\n"
        '  \"mood\": \"fatigue | demotivation | stress | tristesse | positif | neutre\",\n'
        "  \"score\": 0.0 à 1.0,\n"
        '  \"valence\": \"positive\" | \"neutral\" | \"negative\",\n'
        '  \"energy\": \"low\" | \"medium\" | \"high\",\n'
        "  \"matched_keywords\": {\n"
        '    \"categorie_principale\": [\"mot1\", \"mot2\"]\n'
        "  },\n"
        '  \"explanation\": \"courte explication en français\"\n'
        "}\n\n"
        "Règles importantes :\n"
        "- Utilise UNIQUEMENT les valeurs de mood listées ci-dessus.\n"
        "- \"score\" représente ton niveau de confiance et/ou l'intensité de l'humeur :\n"
        "    - proche de 0 : aucun signal clair,\n"
        "    - ~0.3-0.5 : humeur détectée mais modérée / incertaine,\n"
        "    - ~0.7-1.0 : humeur très claire et fortement exprimée.\n"
        "- Si le message est très factuel ou neutre, mood = \"neutre\" et score ≈ 0.5.\n"
        "- Ne JAMAIS ajouter de texte avant ou après le JSON.\n"
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
                content_str = content_str[first:last+1]

        data = json.loads(content_str)

        mood = data.get("mood", "neutre")
        score = data.get("score", 0.5)
        valence = data.get("valence", "neutral")
        energy = data.get("energy", "medium")
        matched_keywords = data.get("matched_keywords") or {}
        explanation = data.get("explanation")

        # Normalisation du mood
        if mood not in ["fatigue", "demotivation", "stress", "tristesse", "positif", "neutre"]:
            mood = "neutre"

        # Garde-fous sur le score
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
