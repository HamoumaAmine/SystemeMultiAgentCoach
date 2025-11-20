import os

from groq import Groq
from dotenv import load_dotenv


"""
Client LLM pour l'agent cerveau.

Version V3 : on utilise vraiment l'API Groq pour générer une réponse,
en gardant la même interface LLMClient.generate(prompt: str) -> str.

La clé API doit être fournie dans la variable d'environnement GROQ_API_KEY,
par exemple via un fichier .env à la racine du projet.
"""


class LLMClient:
    def __init__(self, model: str | None = None) -> None:
        # Charger les variables d'environnement depuis .env (en dev)
        load_dotenv()

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY est introuvable dans les variables d'environnement. "
                "Ajoute-la dans un fichier .env ou configure la variable avant de lancer le service."
            )

        # Initialisation du client Groq
        self.client = Groq(api_key=api_key)

        # Modèle utilisé (tu peux changer la valeur par défaut si besoin)
        self.model = model or "llama-3.3-70b-versatile"

    def generate(self, prompt: str) -> str:
        """
        Appelle l'API Groq pour générer une réponse à partir du prompt fourni.

        Le handler se charge de construire un prompt complet (voir build_coach_prompt),
        ici on l'envoie simplement au modèle comme message utilisateur.
        """

        chat_completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                # On pourrait aussi mettre le rôle du coach en "system",
                # mais pour l'instant tout le contexte est déjà dans le prompt.
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.4,   # un peu de créativité, mais pas trop
            max_tokens=800,    # limite raisonnable pour la réponse
        )

        # On récupère le texte de la première réponse
        answer = chat_completion.choices[0].message.content
        return answer
