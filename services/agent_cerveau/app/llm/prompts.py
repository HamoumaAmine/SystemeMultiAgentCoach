from typing import Any, Dict, List, Optional


def _format_mood(mood: Optional[str]) -> str:
    """
    Retourne une phrase expliquant l'humeur de l'utilisateur,
    et des consignes pour adapter le ton.
    """
    if not mood:
        return (
            "Humeur actuelle détectée : non précisée.\n"
            "Adapte ton ton de manière neutre mais bienveillante."
        )

    mood = mood.strip().lower()

    if mood in {"fatigué", "fatigue", "épuisé", "epuise"}:
        return (
            "Humeur actuelle détectée : fatigué.\n"
            "- Sois compréhensif et rassurant.\n"
            "- Propose des actions simples et réalistes.\n"
            "- Insiste sur la récupération, le sommeil et la gestion de la charge.\n"
        )
    if mood in {"stressé", "stresse", "anxieux"}:
        return (
            "Humeur actuelle détectée : stressé.\n"
            "- Aide à réduire la pression.\n"
            "- Propose des stratégies de gestion du stress (respiration, pauses, marche).\n"
            "- Évite de fixer des objectifs trop agressifs.\n"
        )
    if mood in {"motivé", "motivé(e)", "tres motive"}:
        return (
            "Humeur actuelle détectée : motivé.\n"
            "- Profite de cette motivation pour proposer un plan un peu plus ambitieux mais réaliste.\n"
            "- Donne des objectifs mesurables et progressifs.\n"
        )

    # Par défaut : mood reconnu mais pas de règle spécifique
    return (
        f"Humeur actuelle détectée : {mood}.\n"
        "Adapte ton ton de manière adaptée à cette humeur, en restant bienveillant."
    )


def _format_history(history: Any) -> str:
    """
    Transforme l'historique brut en texte lisible pour le LLM.

    On s'attend à recevoir une liste de dictionnaires avec au moins :
      - role: 'user' ou 'coach' ou 'mood'
      - text: str
      - metadata: dict optionnel, pouvant contenir par exemple :
          - service: "coaching_sport", "mood_tracker", ...
          - mood: str
          - physical_state: str
          - mental_state: str
    """

    if not history:
        return "Historique récent : aucun échange enregistré avec cet utilisateur.\n"

    # Si on reçoit autre chose qu'une liste de dicts (par ex. liste de strings),
    # on gère de manière robuste.
    if isinstance(history, list) and all(isinstance(item, str) for item in history):
        joined = "\n".join(f"- {item}" for item in history)
        return (
            "Historique récent (format simple) :\n"
            f"{joined}\n"
        )

    # Sinon, on suppose une liste de dicts renvoyés par agent_memory
    lines: List[str] = []
    lines.append(
        "Historique récent avec cet utilisateur (du plus ancien au plus récent) :"
    )

    # L'historique qu'on reçoit est normalement du plus récent au plus ancien,
    # donc on inverse pour reconstituer la chronologie.
    try:
        items = list(reversed(history))
    except TypeError:
        items = history

    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        role = item.get("role", "unknown")
        text = item.get("text", "").strip()
        metadata: Dict[str, Any] = item.get("metadata") or {}

        # Label du rôle
        role_lower = str(role).lower()
        if role_lower == "user":
            role_label = "Utilisateur"
        elif role_lower == "coach":
            role_label = "Coach"
        elif role_lower == "mood":
            role_label = "MoodTracker"
        else:
            role_label = role

        # Récupération des infos de contexte dans metadata
        service = metadata.get("service")
        mood_label = metadata.get("mood")
        physical = metadata.get("physical_state")
        mental = metadata.get("mental_state")

        details: List[str] = []

        if service:
            details.append(f"service: {service}")
        if mood_label:
            details.append(f"mood: {mood_label}")
        # états physique / mental issus du mood tracker
        pm_parts: List[str] = []
        if physical:
            pm_parts.append(f"physique={physical}")
        if mental:
            pm_parts.append(f"mental={mental}")
        if pm_parts:
            details.append(" / ".join(pm_parts))

        if details:
            mood_info = "(" + ", ".join(details) + ")"
        else:
            mood_info = ""

        lines.append(f"{idx}. [{role_label}] {mood_info}".strip())
        if text:
            lines.append(f"   {text}")

    lines.append("")  # ligne vide finale
    return "\n".join(lines)


def _format_expert_knowledge(expert_knowledge: Any) -> str:
    """
    Formate les connaissances expertes (documents) si disponibles.

    On s'attend idéalement à une liste de chaînes, ou de dicts avec 'title'/'content'.
    """

    if not expert_knowledge:
        return (
            "Aucun extrait de document expert n'est fourni pour cette requête.\n"
            "Appuie-toi sur tes connaissances générales en sport et nutrition."
        )

    lines: List[str] = []
    lines.append("Extraits de documents experts disponibles :")

    if isinstance(expert_knowledge, list):
        for idx, item in enumerate(expert_knowledge, start=1):
            if isinstance(item, str):
                lines.append(f"- [Doc {idx}] {item}")
            elif isinstance(item, dict):
                title = item.get("title", f"Doc {idx}")
                content = item.get("content", "")
                lines.append(f"- [{title}] {content}")
    else:
        # Format inconnu : on cast en str
        lines.append(str(expert_knowledge))

    lines.append("")
    return "\n".join(lines)


def build_coach_prompt(
    user_input: str,
    mood: Optional[str] = None,
    history: Any = None,
    expert_knowledge: Any = None,
) -> str:
    """
    Construit le prompt complet envoyé au LLM.

    On combine :
      - rôle du modèle (coach sportif & nutrition)
      - humeur actuelle (ou état physique/mental agrégé)
      - historique conversationnel (avec service, mood tracker, etc.)
      - éventuels extraits de documents experts
      - demande actuelle de l'utilisateur
    """

    mood_block = _format_mood(mood)
    history_block = _format_history(history)
    expert_block = _format_expert_knowledge(expert_knowledge)

    system_instructions = """
Tu es un coach sportif et nutritionnel personnel.
Ton objectif est d'aider l'utilisateur à améliorer sa santé, son bien-être
et ses performances, en respectant :

- Son niveau actuel (débutant, intermédiaire, avancé).
- Son contexte de vie (travail, fatigue, disponibilité).
- Sa sécurité (ne propose jamais quelque chose de dangereux).
- Une approche progressive et réaliste.

IMPORTANT :
- Réponds toujours en français.
- Utilise un ton motivant mais bienveillant, jamais culpabilisant.
- Propose des actions concrètes, simples à appliquer.
- Lorsque c'est pertinent, découpe les conseils en étapes (1., 2., 3., ...).
- Si l'utilisateur donne très peu d'informations, pose 2–3 questions de clarification à la fin.
"""

    prompt = f"""
{system_instructions.strip()}

=== Contexte émotionnel (mood) ===
{mood_block.strip()}

=== Historique des échanges ===
{history_block.strip()}

=== Connaissances expertes ===
{expert_block.strip()}

=== Demande actuelle de l'utilisateur ===
{user_input.strip()}

=== Instructions de réponse ===
- Commence par reformuler très brièvement la situation de l'utilisateur.
- Adapte ton ton à l'humeur décrite (et à l'état physique/mental si disponible).
- Fournis ensuite un plan d'action clair (par exemple : section Sport, section Nutrition, section Récupération).
- Termine par un petit message motivant et, si besoin, 1 à 3 questions pour mieux personnaliser l'accompagnement.
"""

    return prompt.strip()
