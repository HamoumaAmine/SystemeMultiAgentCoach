import uuid
from typing import Any, Dict, Optional

from app.mcp.schemas import MCPResponse
from app.llm.client import LLMClient
from app.llm.prompts import build_coach_prompt
from app.clients.memory_client import MemoryClient

# Client mémoire global
memory_client = MemoryClient()


def _mood_from_payload(payload: Dict[str, Any]) -> Optional[Any]:
    """
    Mood utilisé pour le PROMPT du coach.

    - Si un dict complet mood_state est présent, on le renvoie tel quel
      (il contient typiquement : mood_label, valence, energy, physical_state, mental_state, score...).
    - Sinon, on renvoie le champ "mood" s'il existe (string simple).
    - Sinon, None.
    """
    mood_state = payload.get("mood_state")
    if isinstance(mood_state, dict) and mood_state:
        return mood_state  # laissé tel quel pour que build_coach_prompt le détaille

    mood = payload.get("mood")
    if mood:
        return str(mood)

    return None


def _mood_label_for_memory(mood: Any) -> Optional[str]:
    """
    Renvoie une version compacte du mood pour la mémoire (simple string).

    - Si mood est un dict, on essaye de prendre mood_label ou label.
    - Si mood est une string, on la renvoie telle quelle.
    """
    if isinstance(mood, dict):
        return mood.get("mood_label") or mood.get("label")
    if isinstance(mood, str):
        return mood
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
    mood_for_prompt: Any = _mood_from_payload(payload)
    history_from_payload = payload.get("history") or []

    # L’orchestrateur peut envoyer deux clés différentes selon les services :
    expert_knowledge = (
        payload.get("expert_knowledge")
        or payload.get("knowledge_results")
        or []
    )

    # LOG DEBUG (doit s’afficher dans terminal agent_cerveau)
    print("[AGENT_CERVEAU] expert_knowledge reçu :", expert_knowledge, flush=True)
    print("[AGENT_CERVEAU] mood_for_prompt reçu :", mood_for_prompt, flush=True)

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
        mood=mood_for_prompt,
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
            mood_label = _mood_label_for_memory(mood_for_prompt)

            # message utilisateur
            memory_client.save_interaction(
                user_id=user_id,
                role="user",
                text=user_input,
                metadata={
                    "service": "coaching_sport",
                    "mood_raw": mood_label or str(mood_for_prompt),
                },
            )
            # réponse coach
            memory_client.save_interaction(
                user_id=user_id,
                role="coach",
                text=answer,
                metadata={"service": "coaching_sport"},
            )
        except Exception:
            # Pas de crash si memory est down
            pass

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
