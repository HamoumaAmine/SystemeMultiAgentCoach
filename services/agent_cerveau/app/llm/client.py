import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage


"""
Client LLM pour l'agent cerveau (version LangChain + Groq).

On garde la même interface LLMClient.generate(prompt: str) -> str,
mais à l'intérieur on utilise LangChain pour appeler le modèle Groq.
"""


class LLMClient:
    def __init__(self, model: str | None = None) -> None:
        # Charger les variables d'environnement depuis .env
        load_dotenv()

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY est introuvable dans les variables d'environnement. "
                "Ajoute-la dans un fichier .env ou configure la variable avant de lancer le service."
            )

        # Modèle par défaut (tu peux en changer si tu veux)
        self.model_name = model or "llama-3.3-70b-versatile"

        # Initialisation du LLM LangChain pour Groq
        self.llm = ChatGroq(
            model=self.model_name,
            api_key=api_key,
            temperature=0.4,
            max_tokens=800,
        )

    def generate(self, prompt: str) -> str:
        """
        Génère une réponse textuelle à partir d'un prompt complet.

        Pour l'instant, on envoie le prompt en un seul bloc comme un message "user".
        Si tu veux séparer system / user plus tard, tu pourras adapter la logique.
        """

        # On crée un message Human (utilisateur) avec le prompt complet
        messages = [HumanMessage(content=prompt)]

        # Appel au modèle via LangChain
        response = self.llm.invoke(messages)

        # response.content contient le texte produit par le modèle
        return response.content
