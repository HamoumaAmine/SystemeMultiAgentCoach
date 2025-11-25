import uuid
from typing import Any, Dict, Optional

from app.mcp.schemas import MCPResponse
from app.llm.client import LLMClient
from app.llm.prompts import build_coach_prompt
from app.clients.memory_client import MemoryClient

# Client mémoire global
memory_client = MemoryClient()


def _mood_from_payload(payload: Dict[str, Any]) -> Optional[str]:
    """
    Mood simple (“triste”) OU mood structuré provenant de mood_state :
    { physical_state, mental_state }
    """
    mood = payload.get("mood")
    if mood:
        return str(mood)

    mood_state = payload.get("mood_state") or {}
    if isinstance(mood_state, dict):
        physical = mood_state.get("physical_state")
        mental = mood_state.get("mental_state")
        parts = []
        if physical:
            parts.append(f"état physique: {physical}")
        if mental:
            parts.append(f"état mental: {mental}")
        if parts:
            return ", ".join(parts)

    return None


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Handler principal de l’agent cerveau.

    Flux :
    1. Lire user_input + mood + expert knowledge (nutrition, vision, etc.)
    2. Charger l’historique user depuis agent_memory
    3. Construire le prompt complet (build_coach_prompt)
    4. Appeler LLM (Groq)
    5. Sauvegarder la conversation dans agent_memory
    6. Retourner réponse à l’orchestrateur
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")
    user_id: Optional[str] = context.get("user_id")

    # -------------------------------------------------------------------------
    # ❌ Tâche inconnue
    # -------------------------------------------------------------------------
    if task != "coach_response":
        response_payload = {
            "status": "error",
            "message": f"Tâche inconnue ou non prise en charge: {task!r}",
        }
        return MCPResponse(
            message_id=msg.get("message_id", str(uuid.uuid4())),
            to_agent=msg.get("from_agent", "unknown"),
            payload=response_payload,
            context=context,
        )

    # -------------------------------------------------------------------------
    # ✔️ Extraction des données de l’orchestrateur
    # -------------------------------------------------------------------------
    user_input: str = payload.get("user_input", "")
    mood = _mood_from_payload(payload)

    history_from_payload = payload.get("history") or []

    # ⚡ IMPORTANT
    # L’orchestrateur peut envoyer deux clés différentes selon les services :
    expert_knowledge = (
        payload.get("expert_knowledge")
        or payload.get("knowledge_results")
        or []
    )

    # LOG DEBUG (doit s’afficher dans terminal agent_cerveau)
    print("[AGENT_CERVEAU] expert_knowledge reçu :", expert_knowledge, flush=True)

    # -------------------------------------------------------------------------
    # ✔️ Charger l’historique depuis agent_memory
    # -------------------------------------------------------------------------
    history: Any = history_from_payload
    if user_id:
        try:
            history = memory_client.get_history(user_id=user_id, limit=10)
        except Exception:
            history = history_from_payload

    # -------------------------------------------------------------------------
    # ✔️ Construire prompt final (inclut mood + connaissances expertes)
    # -------------------------------------------------------------------------
    full_prompt = build_coach_prompt(
        user_input=user_input,
        mood=mood,
        history=history,
        expert_knowledge=expert_knowledge,
    )

    # -------------------------------------------------------------------------
    # ✔️ Appeler LLM
    # -------------------------------------------------------------------------
    llm = LLMClient()
    answer = llm.generate(full_prompt)

    # -------------------------------------------------------------------------
    # ✔️ Enregistrer l’interaction dans agent_memory
    # -------------------------------------------------------------------------
    if user_id:
        try:
            memory_client.save_interaction(
                user_id=user_id,
                role="user",
                text=user_input,
                metadata={"service": "coaching_sport", "mood_raw": mood},
            )
            memory_client.save_interaction(
                user_id=user_id,
                role="coach",
                text=answer,
                metadata={"service": "coaching_sport"},
            )
        except Exception:
            pass  # Pas de crash si memory est down

    # -------------------------------------------------------------------------
    # ✔️ Construire réponse MCP
    # -------------------------------------------------------------------------
    response_payload = {
        "status": "ok",
        "task": "coach_response",
        "answer": answer,
        "used_history": history,
    }

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=context,
    )
