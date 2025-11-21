import os
import uuid
from typing import Any, Dict, List, Optional

import requests


"""
Client HTTP pour communiquer avec l'agent_memory via MCP.

Il expose deux méthodes principales :
  - get_history(user_id, limit)
  - save_interaction(user_id, role, text, metadata)

L'URL de base de l'agent mémoire peut être configurée avec
la variable d'environnement AGENT_MEMORY_URL.
Par défaut, on utilise http://127.0.0.1:8003 (dev local).
"""


class MemoryClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = base_url or os.getenv(
            "AGENT_MEMORY_URL",
            "http://127.0.0.1:8003",  # URL de dev local
        )

    def _post_mcp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envoie un message MCP à l'agent_memory et retourne la réponse JSON.
        """
        message = {
            "message_id": str(uuid.uuid4()),
            "from_agent": "agent_cerveau",
            "to_agent": "agent_memory",
            "type": "request",
            "payload": payload,
            "context": {},
        }

        url = f"{self.base_url}/mcp"
        response = requests.post(url, json=message, timeout=5)
        response.raise_for_status()
        return response.json()

    def get_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des interactions pour un utilisateur donné.
        Retourne une liste de dictionnaires (id, user_id, role, text, metadata, created_at).
        """
        payload = {
            "task": "get_history",
            "user_id": user_id,
            "limit": limit,
        }

        data = self._post_mcp(payload)
        resp_payload = data.get("payload", {}) or {}

        if resp_payload.get("status") != "ok":
            # En cas d'erreur, on renvoie une liste vide
            return []

        history = resp_payload.get("history", []) or []
        return history

    def save_interaction(
        self,
        user_id: str,
        role: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Demande à agent_memory d'enregistrer une interaction.
        Retourne l'id de l'interaction si succès, sinon None.
        """
        payload = {
            "task": "save_interaction",
            "user_id": user_id,
            "role": role,
            "text": text,
            "metadata": metadata or {},
        }

        data = self._post_mcp(payload)
        resp_payload = data.get("payload", {}) or {}

        if resp_payload.get("status") != "ok":
            return None

        return resp_payload.get("interaction_id")
