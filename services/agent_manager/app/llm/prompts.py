from typing import List


def build_router_prompt(user_text: str) -> str:
    """
    Construit le prompt envoyé au LLM pour décider quels services appeler.

    Objectif :
      - Analyser la demande de l'utilisateur
      - Déterminer quels services (mood, coaching, nutrition, vision, history)
        doivent être appelés
      - Retourner STRICTEMENT un JSON respectant le schéma demandé
    """

    instructions = f"""
Tu es un routeur de services dans une application de coach sportif multi-agents.

Ton rôle :
- Lire la demande de l'utilisateur.
- Identifier quels services doivent être appelés.
- Découper le texte si besoin en plusieurs sous-commandes.
- Retourner STRICTEMENT un JSON, SANS texte additionnel, SANS explication autour.

Services disponibles :

1) "mood"
   - command: "analyze_mood"
   - Utilisation : quand l'utilisateur décrit son état physique ou mental
     (fatigue, stress, motivation, moral, émotions...).

2) "coaching"
   - command: "coach_response"
   - Utilisation : quand l'utilisateur demande des conseils de sport,
     un programme, une séance, une planification sportive, ou un accompagnement.

3) "nutrition"
   - command: "analyze_meal"
   - Utilisation : quand l'utilisateur parle d'un repas, d'aliments, de calories,
     ou envoie une description de ce qu'il a mangé.

4) "history"
   - command: "get_history"
   - Utilisation : quand l'utilisateur veut voir son historique, ses progrès,
     ses anciens plans, son évolution.

IMPORTANT :
- Le champ "text" dans chaque service doit contenir la partie de la phrase pertinente
  pour ce service.
- Tu peux retourner entre 1 et 4 services.
- Si tu n'es pas sûr, privilégie au moins le service "coaching".
- NE RAJOUTE PAS d'autres services que ceux listés.

Format de réponse attendu (STRICT) :

{{
  "services": [
    {{
      "service": "mood",
      "command": "analyze_mood",
      "text": "..."
    }},
    {{
      "service": "coaching",
      "command": "coach_response",
      "text": "..."
    }}
  ]
}}

NE RETOURNE QUE DU JSON VALIDE.
NE METS PAS de ```json, ni de texte avant ou après.
    """.strip()

    user_block = f'--- DEMANDE UTILISATEUR ---\n"{user_text.strip()}"'

    prompt = f"{instructions}\n\n{user_block}"
    return prompt
