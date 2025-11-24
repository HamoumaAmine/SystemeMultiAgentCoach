# services/orchestrator/app/services_registry.py

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

import httpx

# URLs des services (à synchroniser avec docker-compose si besoin)
AGENT_MANAGER_URL = "http://127.0.0.1:8004/mcp"
AGENT_MOOD_URL = "http://127.0.0.1:8001/mcp"
AGENT_CERVEAU_URL = "http://127.0.0.1:8002/mcp"


async def call_agent(url: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Appelle un autre agent via HTTP (protocole MCP) et renvoie sa réponse JSON.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=message, timeout=30.0)
        resp.raise_for_status()
        return resp.json()


@dataclass
class ServiceCommand:
    """
    Représente une commande telle que renvoyée par l'agent_manager :
      - service : ex. "mood", "coaching"
      - command : ex. "analyze_mood", "coach_response"
      - text    : texte sur lequel ce service doit travailler
    """

    service: str
    command: str
    text: str


# Type d'un handler pour un service.
ServiceHandler = Callable[
    [ServiceCommand, Optional[str], Optional[Dict[str, Any]]],
    Awaitable[Any],
]


class ServiceRegistry:
    """
    Registre central qui associe (service, command) -> handler asynchrone.

    L'Orchestrator lui délègue l'exécution concrète :
      - appel de l'agent_mood
      - appel de l'agent_cerveau
      - plus tard : agent_vision, agent_speech, etc.
    """

    def __init__(self) -> None:
        self._handlers: Dict[Tuple[str, str], ServiceHandler] = {}
        self._register_default_handlers()

    # --------------------------------------------------------------------- #
    # Gestion des handlers
    # --------------------------------------------------------------------- #
    def register(
        self,
        service: str,
        command: str,
        handler: ServiceHandler,
    ) -> None:
        key = (service, command)
        if key in self._handlers:
            raise ValueError(
                f"Handler déjà enregistré pour service={service!r}, "
                f"command={command!r}."
            )
        self._handlers[key] = handler

    def get_handler(self, service: str, command: str) -> ServiceHandler:
        key = (service, command)
        try:
            return self._handlers[key]
        except KeyError:
            raise KeyError(
                f"Aucun handler pour service={service!r}, command={command!r}."
            )

    async def execute(
        self,
        command: ServiceCommand,
        *,
        user_id: Optional[str],
        mood_state: Optional[Dict[str, Any]],
    ) -> Any:
        """
        Exécute le handler associé à la commande donnée.
        """
        handler = self.get_handler(command.service, command.command)
        return await handler(command, user_id, mood_state)

    # --------------------------------------------------------------------- #
    # Handlers par défaut
    # --------------------------------------------------------------------- #
    def _register_default_handlers(self) -> None:
        """
        Enregistre les handlers de base :
          - mood/analyze_mood
          - coaching/coach_response
        """
        self.register("mood", "analyze_mood", self._handle_mood_analyze)
        self.register("coaching", "coach_response", self._handle_coach_response)

    # ------------------------ Utils de mapping mood ----------------------- #
    @staticmethod
    def _map_valence_to_mental_state(valence: Optional[str]) -> str:
        """
        Convertit la valence ('negative', 'neutral', 'positive') en
        un état mental simplifié ('very_low', 'medium', 'high', ...).
        """
        if not valence:
            return "medium"

        v = valence.lower()
        if v == "negative":
            return "low"
        if v == "positive":
            return "high"
        return "medium"

    @staticmethod
    def _map_energy_to_physical_state(energy: Optional[str]) -> str:
        """
        Convertit l'énergie ('low', 'medium', 'high') en état physique.
        """
        if not energy:
            return "medium"

        e = energy.lower()
        if e in ("low", "very_low"):
            return "low"
        if e in ("high", "very_high"):
            return "high"
        return "medium"

    # ------------------------------ Handlers ------------------------------ #
    async def _handle_mood_analyze(
        self,
        command: ServiceCommand,
        user_id: Optional[str],
        mood_state: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Appelle l'agent_mood et renvoie un dict mood_state normalisé :

        {
          "mood_label": "...",
          "score": 0.7,
          "valence": "negative",
          "energy": "low",
          "physical_state": "low",
          "mental_state": "low",
          "matched_keywords": {...}
        }
        """

        msg: Dict[str, Any] = {
            "message_id": str(uuid.uuid4()),
            "type": "request",
            "from_agent": "orchestrator",
            "to_agent": "agent_mood",
            "payload": {
                "task": "analyze_mood",
                "text": command.text,
                "user_id": user_id,
            },
            "context": {"user_id": user_id} if user_id else {},
        }

        try:
            resp = await call_agent(AGENT_MOOD_URL, msg)
            payload = resp.get("payload", {}) or {}

            if payload.get("status") != "ok":
                return None

            mood_label = payload.get("mood")
            score = payload.get("score", 0.0)
            valence = payload.get("valence")
            energy = payload.get("energy")
            matched_keywords = payload.get("matched_keywords") or {}

            mental_state = self._map_valence_to_mental_state(valence)
            physical_state = self._map_energy_to_physical_state(energy)

            return {
                "mood_label": mood_label,
                "score": score,
                "valence": valence,
                "energy": energy,
                "physical_state": physical_state,
                "mental_state": mental_state,
                "matched_keywords": matched_keywords,
            }
        except Exception:
            # Si l'agent mood plante, on ne bloque pas tout.
            return None

    async def _handle_coach_response(
        self,
        command: ServiceCommand,
        user_id: Optional[str],
        mood_state: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Appelle l'agent_cerveau pour générer la réponse de coaching.

        On lui passe :
          - user_input = command.text
          - mood_state = dict éventuellement issu de l'agent_mood
          - mood = mood_state["mood_label"] si dispo
        """

        payload: Dict[str, Any] = {
            "task": "coach_response",
            "user_input": command.text,
            "history": [],
            "expert_knowledge": [],
        }

        # Si un mood_state est connu, on le injecte dans le payload
        if mood_state:
            payload["mood_state"] = mood_state
            # on ajoute aussi un champ "mood" plus simple si dispo
            mood_label = mood_state.get("mood_label")
            if mood_label:
                payload["mood"] = mood_label

        msg: Dict[str, Any] = {
            "message_id": str(uuid.uuid4()),
            "type": "request",
            "from_agent": "orchestrator",
            "to_agent": "agent_cerveau",
            "payload": payload,
            "context": {"user_id": user_id} if user_id else {},
        }

        try:
            resp = await call_agent(AGENT_CERVEAU_URL, msg)
            payload_resp = resp.get("payload", {}) or {}
            if payload_resp.get("status") != "ok":
                return None

            return payload_resp.get("answer")
        except Exception:
            return None
