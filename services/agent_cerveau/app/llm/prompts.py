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


def _format_mood(mood: Any) -> str:
    """
    Formate la description du mood / état pour le prompt.

    mood peut être :
      - une simple chaîne : "stressé mais motivé"
      - un dict mood_state :
          {
            "mood_label": "...",
            "valence": "...",
            "energy": "...",
            "physical_state": "...",
            "mental_state": "..."
          }
    """
    if not mood:
        return "Aucune information fiable sur l'état émotionnel ou physique actuel."

    # Cas dict complet
    if isinstance(mood, dict):
        label = mood.get("mood_label") or mood.get("label")
        valence = mood.get("valence")
        energy = mood.get("energy")
        phys = mood.get("physical_state")
        mental = mood.get("mental_state")

        parts: List[str] = []
        if label:
            parts.append(f"Ressenti global : {label}.")
        if valence:
            parts.append(f"Valence émotionnelle : {valence}.")
        if energy:
            parts.append(f"Niveau d'énergie perçu : {energy}.")
        if phys:
            parts.append(f"État physique estimé : {phys}.")
        if mental:
            parts.append(f"État mental estimé : {mental}.")

        if not parts:
            return "Analyse d'humeur disponible mais non interprétable."
        return " ".join(parts)

    # Cas simple : string
    if isinstance(mood, str):
        return f"L'utilisateur se décrit actuellement ainsi : {mood}."

    # Cas inattendu
    return f"Informations d'humeur brutes : {str(mood)}."


# -------------------------------------------------------------------------
# 1) EXTRACTION DES DONNÉES NUTRITIONNELLES
# -------------------------------------------------------------------------


def _extract_nutrition_from_expert_knowledge(
    expert_knowledge: Any,
) -> List[Dict[str, Any]]:
    """
    À partir de expert_knowledge (tel que reçu par agent_cerveau),
    on essaie d'extraire une liste de suggestions nutritionnelles.

    Structure typique :

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

    On reste robuste aux variantes.
    """
    suggestions: List[Dict[str, Any]] = []

    if not expert_knowledge:
        return suggestions

    try:
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
            "autres agents. Tu peux donner des conseils généraux, en restant prudent "
            "et en évitant les chiffres inventés."
        )

    lines: List[str] = []
    lines.append(
        "Les autres agents t'ont fourni une liste d'aliments issus d'une base de "
        "données nutritionnelle, avec quelques informations :"
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
        "Important : ces aliments viennent d'une base de données fiable. "
        "Appuie-toi en priorité sur eux pour illustrer tes conseils (par exemple en les "
        "intégrant dans des idées de repas ou de collations). Tu peux proposer d'autres "
        "aliments en complément, mais indique que ce sont des suggestions générales."
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
            "Si l'utilisateur parle d'une photo, base-toi uniquement sur sa description textuelle."
        )

    lines: List[str] = []
    lines.append(
        "L'agent de vision a analysé une ou plusieurs images (par exemple un repas en photo). "
        "Voici les principaux éléments à prendre en compte :"
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
            or vr.get("description_generale")
            or vr.get("description")
            or vr.get("analysis")
            or vr.get("advice")
        )

        calories_block = vr.get("calories_estimees") or vr.get("calories")
        calories = None
        if isinstance(calories_block, dict):
            calories = calories_block.get("total_kcal_approx")
        elif isinstance(calories_block, (int, float)):
            calories = calories_block

        details_parts: List[str] = []
        if summary:
            details_parts.append(f"Résumé visuel : {summary}")
        if calories is not None:
            details_parts.append(
                f"Estimation calorique (approximative) : {calories} kcal"
            )

        for key in ["risks", "nutrition_comment", "quality_comment", "limitations"]:
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
        "le contenu de l'assiette (types d'aliments, portions, sauces, équilibre global "
        "du repas) en lien avec l'objectif de l'utilisateur (perte de poids, santé, "
        "performance sportive)."
    )

    return "\n".join(lines)


# -------------------------------------------------------------------------
# 3) CONSTRUCTION DU PROMPT COMPLET
# -------------------------------------------------------------------------


def build_coach_prompt(
    user_input: str,
    mood: Optional[Any] = None,
    history: Any = None,
    expert_knowledge: Any = None,
) -> str:
    """
    Construit le prompt complet envoyé au LLM du coach.

    Paramètres :
      - user_input : message brut de l'utilisateur
      - mood : soit une description textuelle simple, soit un dict mood_state
      - history : historique récupéré depuis agent_memory (ou transmis par orchestrateur)
      - expert_knowledge : données expertes (nutrition, vision, etc.) agrégées
        par les autres agents (notamment agent_knowledge et agent_vision).
    """

    history_block = _format_history(history)
    mood_block = _format_mood(mood)
    nutrition_block = _format_nutrition_suggestions(expert_knowledge)
    vision_block = _format_vision_info(expert_knowledge)

    prompt = f"""
Tu es **SMARTCOACH**, un coach virtuel spécialisé en sport, santé et nutrition.
Tu t'adresses à l'utilisateur en français, avec un ton bienveillant, motivant
et concret, comme un coach humain qui parle à son élève.

CONTEXTE TECHNIQUE (pour toi, pas pour l'utilisateur) :
- Tu es l'agent_cerveau dans une architecture multi-agents (orchestrateur,
  agent_mood, agent_knowledge, agent_vision, agent_speech, agent_memory, etc.).
- Tu reçois déjà une analyse d'humeur, un historique de conversations et, parfois,
  des connaissances expertes (analyse nutritionnelle, analyse d'image de repas).

IMPORTANT :
- Ne mentionne JAMAIS ces détails techniques dans ta réponse (pas de "LLM",
  pas de "prompt", pas de "base SQL", pas "d'agent_vision", etc.).
- Tu tutoies l'utilisateur.
- Tu évites le ton scolaire ou trop académique.
- Tu peux structurer ta réponse avec 2 à 4 sous-titres maximum, au style naturel
  (par exemple : "Ce que je comprends", "Ce que je te propose pour aujourd'hui",
  "Plan simple pour la semaine"). Tu n'es PAS obligé d'utiliser la numérotation 1., 2., 3.

----------------------------------------------------------------------
DONNÉES UTILISATEUR
----------------------------------------------------------------------

Message actuel de l'utilisateur :
\"\"\"{user_input}\"\"\"


État émotionnel / physique estimé :
{mood_block}


Historique récent (extraits utiles) :
{history_block}

----------------------------------------------------------------------
CONNAISSANCES EXPERTES FOURNIES PAR LES AUTRES AGENTS
----------------------------------------------------------------------

SECTION NUTRITION (base de données d'aliments) :
{nutrition_block}

SECTION VISION (analyse d'une éventuelle photo de repas) :
{vision_block}

Ces connaissances sont considérées comme fiables lorsqu'elles existent.
Tu dois t'y référer en priorité pour tout ce qui concerne la nutrition
et l'analyse visuelle du repas (contenu de l'assiette, portions, sauces, etc.).

----------------------------------------------------------------------
OBJECTIF DE TA RÉPONSE
----------------------------------------------------------------------

À partir de ces éléments, rédige une réponse qui soit :

- claire et facile à comprendre pour quelqu'un qui n'est pas expert,
- personnalisée à la situation décrite par l'utilisateur,
- motivante mais réaliste.

Tu peux t'appuyer sur la structure suivante, que tu adaptes au contexte.
Tu as le droit de fusionner des parties si le message de l'utilisateur est simple.

IDÉE DE STRUCTURE (ADAPTÉE, PAS OBLIGATOIRE) :

- **Ce que je comprends de ta situation**
  - Reformule en quelques phrases ce que l'utilisateur vit en ce moment
    (humeur, fatigue, motivation, contraintes...).

- **Ce que je te conseille maintenant**
  - Si la demande touche au sport : conseille des séances adaptées (durée,
    intensité, type d'exercices) en tenant compte de l'état physique et émotionnel.
  - Si la demande touche à la nutrition : propose des pistes basées sur les
    aliments de la base de données ci-dessus et/ou l'analyse de la photo.
  - Si l'utilisateur est malade, blessé ou très fatigué : sois particulièrement
    prudent, suggère du repos ou une activité très légère, et rappelle que seul
    un professionnel de santé peut poser un diagnostic.

- **Petit plan simple à mettre en place**
  - Résume en 3 à 5 actions concrètes et réalisables (dans la journée ou la
    semaine) : exemples d'ajustements alimentaires, d'activité physique, de
    sommeil, d'hydratation, etc.
  - Donne envie à l'utilisateur de revenir te voir pour te dire comment ça s'est
    passé.

----------------------------------------------------------------------
FORMAT ATTENDU
----------------------------------------------------------------------

- Réponds TOUJOURS en français.
- Ne sois pas trop verbeux inutilement : privilégie la clarté et l'impact.
- Reste naturel : comme un bon coach qui parle à son élève, pas comme un rapport
  universitaire.
- Tu peux utiliser des listes à puces, mais évite les longues répétitions.

Maintenant, rédige ta réponse pour l'utilisateur.
"""
    # On strip pour éviter les grandes marges au début
    return prompt.strip()
