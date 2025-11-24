import uuid
from typing import Any, Dict, Optional

from app.mcp.schemas import MCPResponse
from app.llm.client import LLMClient
from app.llm.prompts import build_coach_prompt
from app.clients.memory_client import MemoryClient


# Client mémoire global pour l'agent cerveau
memory_client = MemoryClient()


def _mood_from_payload(payload: Dict[str, Any]) -> Optional[str]:
    """
    Construit une description textuelle du mood à partir de :
      - payload["mood"] (texte simple) si présent
      - sinon payload["mood_state"] = {physical_state, mental_state}
    """
    mood = payload.get("mood")
    if mood:
        return str(mood)

    mood_state = payload.get("mood_state") or {}
    if isinstance(mood_state, dict):
        physical = mood_state.get("physical_state")
        mental = mood_state.get("mental_state")
        if physical or mental:
            parts = []
            if physical:
                parts.append(f"état physique: {physical}")
            if mental:
                parts.append(f"état mental: {mental}")
            return ", ".join(parts)

    return None


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Point d'entrée principal de l'agent cerveau.

    Dans l'architecture actuelle, l'agent cerveau est appelé par
    l'orchestrateur avec la tâche "coach_response".

    Flux :
      1. Récupérer user_input, mood / mood_state, éventuelles connaissances expertes.
      2. Récupérer l'historique utilisateur via agent_memory.
      3. Construire le prompt (build_coach_prompt).
      4. Appeler le LLM (Groq via LangChain).
      5. Sauvegarder question + réponse dans agent_memory.
      6. Retourner la réponse au caller (orchestrateur ou agent_interface).
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")

    user_id: Optional[str] = context.get("user_id")

    if task == "coach_response":
        user_input: str = payload.get("user_input", "")
        # mood peut être simple ("fatigué") ou structuré (mood_state)
        mood = _mood_from_payload(payload)

        # history transmis par l'orchestrateur (optionnel)
        history_from_payload = payload.get("history") or []

        # connaissances expertes éventuelles (Agent_Knowledge)
        expert_knowledge = payload.get("expert_knowledge") or payload.get(
            "knowledge_results", []
        )

        # --- 1) Récupérer l'historique chez agent_memory ---
        history: Any = history_from_payload
        if user_id:
            try:
                history = memory_client.get_history(user_id=user_id, limit=10)
            except Exception:
                # En cas de problème de mémoire, on retombe sur l'historique fourni
                history = history_from_payload

        # --- 2) Construire le prompt complet ---
        full_prompt = build_coach_prompt(
            user_input=user_input,
            mood=mood,
            history=history,
            expert_knowledge=expert_knowledge,
        )

        # --- 3) Appel au LLM (Groq via LangChain) ---
        llm = LLMClient()
        answer = llm.generate(full_prompt)

        # --- 4) Sauvegarder la question + la réponse dans la mémoire ---
        if user_id:
            try:
                # Interaction utilisateur
                memory_client.save_interaction(
                    user_id=user_id,
                    role="user",
                    text=user_input,
                    metadata={
                        "service": "coaching_sport",
                        "mood_raw": mood,
                    },
                )
                # Interaction coach (réponse)
                memory_client.save_interaction(
                    user_id=user_id,
                    role="coach",
                    text=answer,
                    metadata={"service": "coaching_sport"},
                )
            except Exception:
                # On n'empêche pas la réponse au cas où la mémoire est HS
                pass

        response_payload = {
            "status": "ok",
            "task": "coach_response",
            "answer": answer,
            "used_history": history,
        }

    else:
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue ou non prise en charge par agent_cerveau: {task!r}",
        }

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
