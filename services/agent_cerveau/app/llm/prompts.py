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


# -------------------------------------------------------------------------
# 1) EXTRACTION DES DONNÉES NUTRITIONNELLES
# -------------------------------------------------------------------------


def _extract_nutrition_from_expert_knowledge(
    expert_knowledge: Any,
) -> List[Dict[str, Any]]:
    """
    À partir de expert_knowledge (tel que reçu par agent_cerveau),
    on essaie d'extraire une liste de suggestions nutritionnelles.

    Avec ton orchestrateur actuel, la structure typique est :

      expert_knowledge = [
        {
          "type": "nutrition",
          "data": {
            "raw": {
              "goal": "...",
              "sql": "...",
              "suggestions": [
                { "alim_nom_fr": "...", "energie_reglement_ue_1169_kcal_100g": ..., ... },
                ...
              ]
            }
          }
        },
        {
          "type": "vision",
          "data": { ... }
        }
      ]

    Mais on reste ROBUSTE :
      - on gère aussi le cas où l'item est directement le résultat (sans "type"),
      - ou bien où les suggestions sont déjà au niveau courant.
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

                # Cas structuré via orchestrateur : {"type": "nutrition", "data": {...}}
                if item.get("type") == "nutrition":
                    data = item.get("data") or {}
                    if isinstance(data, dict):
                        raw_container = data
                    else:
                        raw_container = {}
                else:
                    # Cas plus simple / ancien : on travaille directement sur l'item
                    raw_container = item

                raw = raw_container.get("raw") or raw_container
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
        prot = (
            sug.get("proteines_n_x_6_25_g_100g")
            or sug.get('"proteines_n_x_6_25_g_100g"')
        )
        gluc = sug.get("glucides_g_100g")
        lip = sug.get("lipides_g_100g")
        fibres = (
            sug.get("fibres_alimentaires_g_100g")
            or sug.get('"fibres_alimentaires_g_100g"')
        )

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


# -------------------------------------------------------------------------
# 2) EXTRACTION / FORMATAGE DES DONNÉES VISION
# -------------------------------------------------------------------------


def _extract_vision_from_expert_knowledge(
    expert_knowledge: Any,
) -> List[Dict[str, Any]]:
    """
    Récupère les résultats de l'agent_vision à partir d'expert_knowledge.

    Avec ton orchestrateur actuel, on a typiquement :

      expert_knowledge = [
        { "type": "nutrition", "data": {...} },
        { "type": "vision", "data": { ...analyse image... } }
      ]

    On renvoie une liste de dicts "analyse vision".
    """
    results: List[Dict[str, Any]] = []

    if not expert_knowledge:
        return results

    try:
        if isinstance(expert_knowledge, dict):
            expert_knowledge = [expert_knowledge]

        if isinstance(expert_knowledge, list):
            for item in expert_knowledge:
                if not isinstance(item, dict):
                    continue

                # Cas structuré : {"type": "vision", "data": {...}}
                if item.get("type") == "vision":
                    data = item.get("data")
                    if isinstance(data, dict):
                        results.append(data)
                    else:
                        # on garde quand même quelque chose
                        results.append({"raw": data})
                    continue

                # Cas plus brut : un dict qui ressemble déjà à un résultat vision
                if item.get("agent") == "vision" or item.get("task") == "analyze_image":
                    results.append(item)
                elif "vision_result" in item and isinstance(
                    item.get("vision_result"), dict
                ):
                    results.append(item["vision_result"])

        return results
    except Exception:
        return results


def _format_vision_info(expert_knowledge: Any) -> str:
    """
    Formate les informations issues de l'agent_vision pour le LLM.

    Objectif : pousser le modèle à commenter VRAIMENT ce qu'il y a sur la photo
    (type d'aliments visibles, portions, sauces, aspect global du repas, etc.).
    """
    vision_results = _extract_vision_from_expert_knowledge(expert_knowledge)

    if not vision_results:
        return (
            "Aucune analyse d'image n'a été fournie par l'agent de vision. "
            "Si l'utilisateur fait référence à une photo, base-toi uniquement "
            "sur sa description textuelle."
        )

    lines: List[str] = []
    lines.append(
        "L'agent de vision a analysé une ou plusieurs images (par exemple un repas en photo). "
        "Voici les informations principales à prendre en compte :"
    )
    lines.append("")

    max_items = min(len(vision_results), 3)
    for i, vr in enumerate(vision_results[:max_items], start=1):
        if not isinstance(vr, dict):
            lines.append(f"{i}. Analyse brute (non structurée) : {str(vr)}")
            continue

        title = vr.get("title") or vr.get("label") or f"Analyse d'image #{i}"

        summary = (
            vr.get("summary")
            or vr.get("description")
            or vr.get("analysis")
            or vr.get("advice")
        )

        calories = (
            vr.get("estimated_calories_kcal")
            or vr.get("calories_estimate")
            or vr.get("calories")
        )

        details_parts: List[str] = []
        if summary:
            details_parts.append(f"Résumé visuel : {summary}")
        if calories is not None:
            details_parts.append(f"Estimation calorique (approximative) : {calories} kcal")

        # On ajoute éventuellement d'autres champs si présents
        for key in ["risks", "nutrition_comment", "quality_comment"]:
            if key in vr and vr[key]:
                details_parts.append(f"{key} : {vr[key]}")

        if details_parts:
            details = " | ".join(details_parts)
            lines.append(f"{i}. {title} — {details}")
        else:
            lines.append(f"{i}. {title} — (détails non structurés : {vr})")

    lines.append("")
    lines.append(
        "Important : utilise ces informations visuelles pour commenter concrètement "
        "le contenu de l'assiette (types d'aliments, portions, sauces, équilibre "
        "global du repas) en lien avec l'objectif de l'utilisateur (perte de poids, "
        "santé, performance sportive)."
    )

    return "\n".join(lines)


# -------------------------------------------------------------------------
# 3) CONSTRUCTION DU PROMPT COMPLET
# -------------------------------------------------------------------------


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
        par les autres agents (notamment agent_knowledge et agent_vision).

    Avec la nouvelle architecture, expert_knowledge ressemble à :
      [
        { "type": "nutrition", "data": {...result DB...} },
        { "type": "vision", "data": {...analyse image...} }
      ]
    """

    history_block = _format_history(history)
    mood_block = _format_mood(mood)
    nutrition_block = _format_nutrition_suggestions(expert_knowledge)
    vision_block = _format_vision_info(expert_knowledge)

    prompt = f"""
Tu es **SMARTCOACH**, un coach virtuel spécialisé en sport, santé et nutrition,
dans un système multi-agents universitaire. Tu dois adopter un ton pédagogue,
bienveillant et concret, en t'adressant à l'utilisateur en français.

Le contexte technique :
- Tu es l'**agent_cerveau** dans une architecture multi-agents (orchestrateur, agent_mood,
  agent_knowledge, agent_vision, agent_speech, agent_memory, etc.).
- Tu reçois déjà une analyse d'humeur, un historique de conversations et, parfois,
  des connaissances expertes (ex : analyse nutritionnelle issue d'une base de données,
  analyse d'image d'un repas via un modèle de vision).

RÔLE :
- Ton rôle est de produire une réponse synthétique, structurée et expliquant les
  choses de manière claire pour un utilisateur réel, mais aussi lisible pour un
  enseignant qui évaluera le projet.

CONTRAINTES GÉNÉRALES :
- Réponds TOUJOURS en français.
- Ne mentionne PAS les détails techniques du système (agents, SQL, vision model, etc.)
  dans ta réponse à l'utilisateur final.
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

SECTION NUTRITION (base de données d'aliments) :
{nutrition_block}

SECTION VISION (analyse de la photo / de l'image) :
{vision_block}

Ces connaissances sont considérées comme fiables lorsqu'elles existent.
Tu dois t'y référer en priorité pour tout ce qui concerne la nutrition
et l'analyse visuelle du repas (contenu de l'assiette, portions, sauces, etc.).

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

3. **Analyse nutritionnelle basée sur la base de données et, si disponible, la photo**
   - Appuie-toi sur les données de la base (les aliments listés ci-dessus) pour :
     - Proposer des types de repas ou d'aliments adaptés à l'objectif décrit.
     - Expliquer pourquoi certains aliments sont intéressants (kcal, protéines, fibres, etc.).
   - SI UNE ANALYSE D'IMAGE EST DISPONIBLE :
     - Commente concrètement ce que tu vois dans l'assiette (types d'aliments, éventuelles sauces,
       taille des portions, équilibre global du repas) en lien avec l'objectif de l'utilisateur.
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
       "Boire plus d'eau", etc.
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
