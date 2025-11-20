from typing import Any, Dict, List, Optional


BASE_SYSTEM_PROMPT = """
Tu es un coach santé/sport/nutrition bienveillant.
Tu parles à l'utilisateur en français, avec un ton motivant mais réaliste.
Tu ne donnes pas de diagnostic médical, tu restes prudent si la santé est en jeu.
Tu proposes des conseils simples, organisés et applicables dans la vraie vie.
"""


def build_coach_prompt(
    user_input: str,
    mood: Optional[str] = None,
    history: Optional[List[Dict[str, Any]]] = None,
    expert_knowledge: Optional[List[str]] = None,
) -> str:
    """
    Construit le prompt complet envoyé au modèle de langage.

    - user_input : dernier message de l'utilisateur
    - mood : humeur actuelle (fatigué, motivé, stressé, etc.)
    - history : éventuellement quelques interactions passées
    - expert_knowledge : extraits de textes de référence (nutrition/sport)
    """

    history = history or []
    expert_knowledge = expert_knowledge or []

    parts: List[str] = []

    # 1) Rôle du coach
    parts.append(BASE_SYSTEM_PROMPT.strip())

    # 2) Contexte : mood
    if mood:
        parts.append(f"Humeur actuelle de l'utilisateur : {mood}.")

    # 3) Contexte : petit résumé d'historique (très simple pour l'instant)
    if history:
        parts.append("Historique récent de l'utilisateur :")
        for item in history[-3:]:
            # On prend maximum 3 entrées pour éviter que ce soit trop long.
            text = item.get("text") or item.get("message") or str(item)
            parts.append(f"- {text}")

    # 4) Connaissances expertes (éventuellement fournies par agent_knowledge)
    if expert_knowledge:
        parts.append("Extraits de connaissances expertes à prendre en compte :")
        for i, chunk in enumerate(expert_knowledge[:3], start=1):
            parts.append(f"[Doc {i}] {chunk}")

    # 5) Dernier message de l'utilisateur
    parts.append("Message actuel de l'utilisateur :")
    parts.append(user_input.strip())

    # 6) Instruction finale au modèle
    parts.append(
        "En te basant sur ces éléments, propose une réponse de coach claire, "
        "structurée en 2 ou 3 parties (par exemple : état des lieux, plan sportif, conseils nutrition), "
        "adaptée au niveau de motivation/humeur mentionné. "
        "Reste prudent sur les aspects médicaux."
    )

    # On assemble tout avec des doubles sauts de ligne pour plus de lisibilité
    full_prompt = "\n\n".join(parts)
    return full_prompt
