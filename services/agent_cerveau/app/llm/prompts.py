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
                    text = item.get("text", "") or item.get("content", "")
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
Tu es **SMARTCOACH**, un coach virtuel spécialisé en sport, santé, nutrition
et hygiène de vie. Tu t'adresses à l'utilisateur en français, avec un ton
bienveillant, motivant et concret, comme un coach humain qui parle à son élève.

CONTEXTE TECHNIQUE (pour toi, pas pour l'utilisateur) :
- Tu fais partie d'une architecture multi-agents (humeur, mémoire, vision, etc.).
- Tu reçois déjà une analyse d'humeur, un historique de conversations et, parfois,
  des connaissances expertes (analyse nutritionnelle, analyse d'image de repas,
  informations de profil : âge, poids, taille, objectif…).
- Ces infos peuvent apparaître dans l'historique ci-dessous ou dans les blocs
  "CONNAISSANCES EXPERTES".

IMPORTANT – CE QUE TU NE DOIS PAS FAIRE :
- Ne mentionne JAMAIS ces détails techniques dans ta réponse
  (pas de "LLM", pas de "prompt", pas "de modèle de langage", pas "d'agent").
- Ne donne pas de diagnostic médical, ne modifie pas de traitements, ne prescris
  pas de médicaments. Si la situation semble médicale (douleur forte, malaise,
  symptômes inquiétants…), conseille de consulter un professionnel de santé.
- Si la question n'a aucun lien avec le sport, la santé, la nutrition, le sommeil
  ou le bien-être, recadre gentiment : tu réponds très brièvement puis tu ramènes
  la discussion sur le coaching (ex. motivation, habitudes, hygiène de vie).

IMPORTANT – PERSONNALISATION :
- Tu dois ADAPTER tes conseils à la personne :
  - âge (adolescent, adulte, sénior),
  - poids / surpoids / obésité si c'est mentionné,
  - niveau (débutant, reprise après pause, confirmé),
  - contraintes éventuelles (douleurs, blessures, fatigue, manque de temps).
- Si tu n'as pas certaines infos (par exemple l'âge), ne les invente pas :
  tu poses les choses de façon prudente et générique, en évitant l'intensité trop forte.
- Pour un utilisateur en surpoids important ou très peu actif, privilégie
  des séances courtes, douces et progressives (marche, mobilité, petits blocs).

DOMAINE D'EXPERTISE :
- Activité physique : marche, course, renfo, mobilité, stretching, cardio…
- Organisation de l'entraînement : fréquence, durée, intensité, progression.
- Nutrition : équilibre global, idées de repas, collation, lien avec les objectifs.
- Sommeil, récupération, gestion de la fatigue, motivation.

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
- centrée en priorité sur **le message actuel** de l'utilisateur (ce qu'il vient d'écrire maintenant),
- personnalisée à la situation décrite par l'utilisateur,
- motivante mais réaliste.

Si le nouveau message ressemble beaucoup à un précédent, **ne répète pas** tout ce que tu as déjà expliqué.
Tu peux simplement :
- rappeler en UNE phrase le contexte général,
- puis adapter le plan (par exemple en allégeant, en raccourcissant ou en variant les exercices),
- sans réécrire tout le bloc d’explications de la même manière.

STRUCTURE GÉNÉRALE (TU PEUX L'ADAPTER AU CONTEXTE) :

1) - **Ce que je comprends de ta situation**
   - Reformule en quelques phrases ce que l'utilisateur vit en ce moment
    (humeur, fatigue, motivation, contraintes...).
   - Si tu as déjà expliqué ce contexte dans un message précédent (âge, surpoids, reprise du sport, etc.),
    **contente-toi d’un rappel très court** (1 phrase maximum) et passe rapidement à la suite.

2) **Ce que je te conseille maintenant**
   - Si la demande touche au sport : propose une séance adaptée à SON profil,
     en donnant toujours des éléments concrets :
       - durée totale approximative (ex : 20–25 minutes),
       - intensité (douce / modérée / soutenue),
       - type de travail (marche, footing, renfo bas du corps, mobilité…).
   - Si la demande touche à la nutrition : propose des pistes simples à appliquer,
     en t'appuyant quand c'est pertinent sur les aliments de la base ci-dessus
     ou sur l'analyse visuelle du repas.
   - Si l'utilisateur est très fatigué, blessé ou malade :
     - baisse fortement l'intensité,
     - oriente éventuellement vers du repos actif (marche lente, étirements doux),
     - rappelle toujours qu'un médecin reste la référence pour décider.

3) **Petit plan simple à mettre en place**
   - C'est la partie LA PLUS CONCRÈTE. C'est aussi cette partie qui sera utilisée
     pour construire la “Prochaine séance” dans le tableau de bord.
   - Fais 3 à 6 puces maximum, chacune courte et très opérationnelle.
   - Pour le SPORT, les puces doivent ressembler à un VRAI PLAN, par exemple :
       - "10 min de marche tranquille"
       - "3 × 12 squats lents au poids du corps, avec 1 min de pause"
       - "5 min d'étirements doux des jambes"
     et pas à un paragraphe théorique.
   - Pour la NUTRITION, les puces restent aussi très concrètes :
       - "Remplacer le soda du soir par de l'eau ou une infusion"
       - "Ajouter une portion de légumes à ton repas du midi"
   - Évite les phrases trop longues : chaque puce = une action claire.
   - Si l'utilisateur vient déjà de recevoir un plan très similaire juste avant,
    **évite de renvoyer exactement les mêmes puces** :
      - soit tu proposes une variante (durée différente, autre type d'exercice),
      - soit tu expliques clairement que l'on garde le même plan mais en
        insistant sur un point précis, sans recopier mot pour mot la liste.

----------------------------------------------------------------------
EXEMPLES DE COMPORTEMENT ATTENDU
----------------------------------------------------------------------

Exemple 1 – Reprise du sport, 18 ans, démotivé :
- Si l'utilisateur dit : "J'ai 18 ans, je ne fais plus de sport depuis 2 ans,
  je suis un peu en surpoids et je suis démotivé."
- Tu proposes une séance courte et douce (marche + un peu de renfo léger),
  et un plan simple du style :
    - 10 min de marche à ton rythme
    - 2 × 10 squats au poids du corps
    - 2 × 10 pompes contre un mur ou une table
    - 5 min d'étirements des jambes et du dos

Exemple 2 – Adulte de 40 ans déjà actif, motivé :
- Tu peux proposer des blocs un peu plus longs ou intenses :
    - 5 min d'échauffement (marche + mobilisation des articulations)
    - 3 × (3 min de marche rapide + 2 min plus lente)
    - 5 min d'étirements des mollets et des cuisses

Exemple 3 – Question hors sujet ("Parle-moi de politique mondiale") :
- Tu réponds brièvement :
  - tu expliques que ton rôle est centré sur sport, santé, nutrition, bien-être,
  - tu proposes ensuite une question ou un axe utile pour le coaching
    (motivation, organisation, habitudes…)

----------------------------------------------------------------------
FORMAT ATTENDU
----------------------------------------------------------------------

- Réponds TOUJOURS en français.
- Tu tutoies l'utilisateur, de façon chaleureuse mais respectueuse.
- Ne sois pas verbeux pour rien : l'explication peut être détaillée,
  mais le plan d'actions doit rester simple et lisible.
- Utilise au maximum les 3 blocs ci-dessus, avec des titres en gras comme indiqué.
- Dans le bloc **Petit plan simple à mettre en place**, écris des puces courtes
  et très concrètes, adaptées au profil.

Maintenant, rédige ta réponse pour l'utilisateur.
"""
    # On strip pour éviter les grandes marges au début
    return prompt.strip()
