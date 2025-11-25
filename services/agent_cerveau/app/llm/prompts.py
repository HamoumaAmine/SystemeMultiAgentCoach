# services/agent_cerveau/app/llm/prompts.py

from typing import Any, Dict, List, Optional


def _format_history(history: Any) -> str:
    """
    Formate l'historique pour le prompt.

    On reste robuste :
      - si c'est une liste de dicts : on affiche 'role: text'
      - si c'est une liste de strings : on les concatène
      - sinon : on fait un str() simple
    """
    if not history:
        return "Aucun historique significatif disponible."

    try:
        if isinstance(history, list):
            lines: List[str] = []
            for item in history:
                if isinstance(item, dict):
                    role = item.get("role", "inconnu")
                    text = item.get("text", "")
                    lines.append(f"- {role}: {text}")
                else:
                    # string ou autre
                    lines.append(f"- {str(item)}")
            return "\n".join(lines)
        else:
            return str(history)
    except Exception:
        return str(history)


def _format_mood(mood: Optional[str]) -> str:
    """
    Formate la description du mood pour le prompt.
    """
    if not mood:
        return "Aucune information fiable sur le mood actuel."
    return f"L'utilisateur se décrit actuellement ainsi : {mood}."


def _extract_nutrition_from_expert_knowledge(
    expert_knowledge: Any,
) -> List[Dict[str, Any]]:
    """
    À partir de expert_knowledge (tel que reçu par agent_cerveau),
    on essaie d'extraire une liste de suggestions nutritionnelles.

    Dans nos logs, on a typiquement :
      expert_knowledge = [
        {
          "raw": {
            "goal": "...",
            "sql": "...",
            "suggestions": [
              { "alim_nom_fr": "...", "energie_reglement_ue_1169_kcal_100g": ..., ... },
              ...
            ]
          }
        }
      ]

    On renvoie une liste de dicts 'plats/aliments' pour le prompt.
    """
    suggestions: List[Dict[str, Any]] = []

    if not expert_knowledge:
        return suggestions

    try:
        # On autorise expert_knowledge à être une liste ou un dict
        if isinstance(expert_knowledge, dict):
            expert_knowledge = [expert_knowledge]

        if isinstance(expert_knowledge, list):
            for item in expert_knowledge:
                if not isinstance(item, dict):
                    continue

                raw = item.get("raw") or item
                raw_suggestions = raw.get("suggestions") or []
                if isinstance(raw_suggestions, list):
                    for sug in raw_suggestions:
                        if isinstance(sug, dict):
                            suggestions.append(sug)

        return suggestions
    except Exception:
        # En cas de souci, on renvoie ce qu'on a pu
        return suggestions


def _format_nutrition_suggestions(expert_knowledge: Any) -> str:
    """
    Transforme les suggestions nutritionnelles en texte clair pour le LLM.

    Objectif : encourager le modèle à s'appuyer sur ces données
    (base de données nutritionnelle) plutôt que d'inventer.
    """
    suggestions = _extract_nutrition_from_expert_knowledge(expert_knowledge)

    if not suggestions:
        return (
            "Aucune donnée nutritionnelle spécifique n'a été fournie par les "
            "autres agents. Tu peux donner des conseils généraux, en restant prudent."
        )

    lines: List[str] = []
    lines.append(
        "Les autres agents (base de connaissances nutritionnelles) t'ont "
        "fourni la liste d'aliments suivante, avec certaines informations :"
    )
    lines.append("")

    # On limite un peu le nombre de suggestions affichées pour ne pas exploser le prompt
    max_items = min(len(suggestions), 12)

    for i, sug in enumerate(suggestions[:max_items], start=1):
        nom = sug.get("alim_nom_fr", "Aliment inconnu")
        kcal = sug.get("energie_reglement_ue_1169_kcal_100g")
        prot = sug.get("proteines_n_x_6_25_g_100g") or sug.get('"proteines_n_x_6_25_g_100g"')
        gluc = sug.get("glucides_g_100g")
        lip = sug.get("lipides_g_100g")
        fibres = sug.get("fibres_alimentaires_g_100g") or sug.get('"fibres_alimentaires_g_100g"')

        desc_parts: List[str] = []
        if kcal is not None:
            desc_parts.append(f"~{kcal} kcal/100g (quand renseigné)")
        if prot not in (None, "proteines_n_x_6_25_g_100g"):
            desc_parts.append(f"protéines ≈ {prot} g/100g")
        if gluc is not None:
            desc_parts.append(f"glucides ≈ {gluc} g/100g")
        if lip is not None:
            desc_parts.append(f"lipides ≈ {lip} g/100g")
        if fibres not in (None, "fibres_alimentaires_g_100g"):
            desc_parts.append(f"fibres ≈ {fibres} g/100g")

        if desc_parts:
            desc = " ; ".join(desc_parts)
            lines.append(f"{i}. {nom} — {desc}")
        else:
            lines.append(f"{i}. {nom}")

    lines.append("")
    lines.append(
        "Important : ces aliments proviennent d'une base de données "
        "nutritionnelle. Appuie-toi PRIORITAIREMENT sur ces éléments pour "
        "proposer des repas ou des pistes d'amélioration en cohérence avec "
        "l'objectif de l'utilisateur (perte de poids, prise de muscle, etc.)."
    )
    lines.append(
        "Tu peux éventuellement suggérer d'autres aliments en complément, mais "
        "indique clairement qu'ils ne proviennent pas de la base de données "
        "et restent des conseils généraux."
    )

    return "\n".join(lines)


def build_coach_prompt(
    user_input: str,
    mood: Optional[str] = None,
    history: Any = None,
    expert_knowledge: Any = None,
) -> str:
    """
    Construit le prompt complet envoyé au LLM du coach.

    Paramètres :
      - user_input : message brut de l'utilisateur
      - mood : description textuelle de l'état émotionnel (peut venir de mood_state)
      - history : historique récupéré depuis agent_memory (ou transmis par orchestrateur)
      - expert_knowledge : données expertes (nutrition, vision, etc.) agrégées
        par les autres agents (notamment agent_knowledge).

    Objectif :
      - Donner au modèle un contexte clair (qui est l'utilisateur, ce qu'il veut)
      - Injecter l'humeur et l'historique
      - Injecter les connaissances expertes (ex : nutrition) de manière exploitable
      - Imposer une STRUCTURE de réponse en sections, pour le rapport et la soutenance.
    """

    history_block = _format_history(history)
    mood_block = _format_mood(mood)
    nutrition_block = _format_nutrition_suggestions(expert_knowledge)

    prompt = f"""
Tu es **SMARTCOACH**, un coach virtuel spécialisé en sport, santé et nutrition,
dans un système multi-agents universitaire. Tu dois adopter un ton pédagogue,
bienveillant et concret, en t'adressant à l'utilisateur en français.

Le contexte technique :
- Tu es l'**agent_cerveau** dans une architecture multi-agents (orchestrateur, agent_mood,
  agent_knowledge, agent_speech, agent_memory, etc.).
- Tu reçois déjà une analyse d'humeur, un historique de conversations et, parfois,
  des connaissances expertes (ex : analyse nutritionnelle issue d'une base de données).

RÔLE :
- Ton rôle est de produire une réponse synthétique, structurée et expliquant les
  choses de manière claire pour un utilisateur réel, mais aussi lisible pour un
  enseignant qui évaluera le projet.

CONTRAINTES GÉNÉRALES :
- Réponds TOUJOURS en français.
- Ne mentionne PAS les détails techniques du système (agents, SQL, etc.) dans ta réponse
  à l'utilisateur final.
- Ne parle pas de "prompt" ou de "LLM".
- Ta réponse doit être structurée en SECTIONS CLAIRES, avec des titres.

----------------------------------------------------------------------
DONNÉES UTILISATEUR
----------------------------------------------------------------------

Message actuel de l'utilisateur :
\"\"\"{user_input}\"\"\"

Mood / état estimé :
{mood_block}

Historique récent (extraits) :
{history_block}

----------------------------------------------------------------------
CONNAISSANCES EXPERTES FOURNIES PAR LES AUTRES AGENTS
----------------------------------------------------------------------

Les autres agents t'ont transmis les informations suivantes :

{nutrition_block}

Ces connaissances sont considérées comme fiables lorsqu'elles existent.
Tu dois t'y référer en priorité pour tout ce qui concerne la nutrition.

----------------------------------------------------------------------
OBJECTIF DE LA RÉPONSE
----------------------------------------------------------------------

À partir de ces éléments, tu dois répondre à l'utilisateur en structurant ta
réponse de manière lisible, en respectant le plan suivant (adapté selon le contexte) :

1. **Synthèse de ta situation actuelle**
   - Résume en quelques phrases ce que tu as compris de la demande de l'utilisateur
     (objectif, contexte global, contraintes éventuelles).

2. **Analyse de ton état (humeur, énergie, contexte)**
   - Reformule brièvement l'état physique / mental (à partir du mood quand c'est possible).
   - Explique comment cet état peut impacter la motivation, l'alimentation et l'entraînement.

3. **Analyse nutritionnelle basée sur la base de données**
   - Appuie-toi sur les données de la base (les aliments listés ci-dessus) pour :
     - Proposer des types de repas ou d'aliments adaptés à l'objectif décrit.
     - Expliquer pourquoi certains aliments sont intéressants (kcal, protéines, fibres, etc.).
   - Si tu proposes d'autres aliments qui ne sont pas dans la base, précise que ce
     sont des conseils généraux.
   - Donne des exemples de repas complets (matin / midi / soir) si pertinent.

4. **Recommandations sportives / d'activité physique**
   - Propose des conseils d'entraînement adaptés au niveau supposé de l'utilisateur
     (débutant / intermédiaire, surpoids, reprise du sport, etc.).
   - Donne des exemples concrets de séances (durée, types d'exercices, fréquence).
   - Adapte l'intensité si l'utilisateur semble fatigué / stressé / démotivé.

5. **Plan d'action concret et progressif**
   - Résume en 3 à 5 actions concrètes et réalisables dans la semaine :
     - ex : "Remplacer tel type de repas par...", "Ajouter 15–20 minutes de marche...",
       "Boire + d'eau", etc.
   - Sois motivant, sans culpabiliser.
   - Invite l'utilisateur à revenir te voir avec ses ressentis ou ses repas de la semaine.

----------------------------------------------------------------------
FORMAT ATTENDU
----------------------------------------------------------------------

- Utilise des titres clairs pour chaque section (ex: "1. Synthèse de ta situation").
- Utilise des listes à puces lorsque c'est utile.
- Adapte la longueur de la réponse : suffisamment détaillée pour être utile,
  mais pas un roman non plus. Privilégie la clarté.

Maintenant, rédige ta réponse structurée pour l'utilisateur.
"""
    # On strip pour éviter les grandes marges au début
    return prompt.strip()
