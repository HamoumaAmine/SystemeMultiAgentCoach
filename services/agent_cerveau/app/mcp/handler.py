import uuid
from typing import Any, Dict, Optional

from app.mcp.schemas import MCPResponse
from app.llm.client import LLMClient
from app.llm.prompts import build_coach_prompt
from app.clients.memory_client import MemoryClient


# Client mémoire global pour l'agent cerveau
memory_client = MemoryClient()


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    Point d'entrée principal de l'agent cerveau.

    Pour l'instant, on gère principalement la tâche :
      - task == "coach_response"

    Le flux est le suivant :
      1. Récupérer user_input, mood, etc. depuis le payload
      2. Si user_id présent dans le contexte :
            - demander l'historique à agent_memory (get_history)
      3. Construire le prompt complet avec build_coach_prompt
      4. Appeler le LLM (Groq via LangChain) pour obtenir la réponse
      5. Si user_id présent :
            - enregistrer la question + la réponse dans agent_memory (save_interaction)
      6. Retourner la réponse dans un MCPResponse
    """

    payload: Dict[str, Any] = msg.get("payload", {}) or {}
    context: Dict[str, Any] = msg.get("context", {}) or {}
    task: Optional[str] = payload.get("task")

    # On essaie de récupérer un user_id pour personnaliser l'historique
    user_id: Optional[str] = context.get("user_id")

    # --- 1) Tâche principale : coach_response ---
    if task == "coach_response":
        user_input: str = payload.get("user_input", "")
        mood: Optional[str] = payload.get("mood")
        # Cet historique peut venir de l'interface, mais on va essayer
        # de le remplacer/compléter avec celui d'agent_memory.
        history_from_payload = payload.get("history") or []
        expert_knowledge = payload.get("expert_knowledge") or []

        # --- 2) Récupérer l'historique chez agent_memory (si user_id dispo) ---
        history: Any = history_from_payload
        if user_id:
            try:
                history = memory_client.get_history(user_id=user_id, limit=10)
            except Exception as e:
                # En cas d'erreur on loguerait normalement, mais pour le MVP
                # on se contente d'ignorer et de garder l'history du payload.
                history = history_from_payload

        # --- 3) Construire le prompt complet pour le LLM ---
        full_prompt = build_coach_prompt(
            user_input=user_input,
            mood=mood,
            history=history,
            expert_knowledge=expert_knowledge,
        )

        # --- 4) Appel au LLM (Groq via LangChain) ---
        llm = LLMClient()
        answer = llm.generate(full_prompt)

        # --- 5) Enregistrer la question + la réponse dans agent_memory ---
        if user_id:
            try:
                # Interaction utilisateur
                memory_client.save_interaction(
                    user_id=user_id,
                    role="user",
                    text=user_input,
                    metadata={"mood": mood},
                )

                # Interaction coach (réponse de l'agent cerveau)
                memory_client.save_interaction(
                    user_id=user_id,
                    role="coach",
                    text=answer,
                    metadata={},
                )
            except Exception:
                # En cas d'erreur d'écriture en mémoire, on n'empêche pas la réponse
                pass

        response_payload = {
            "status": "ok",
            "task": "coach_response",
            "answer": answer,
            # On renvoie l'historique utilisé pour debug / transparence
            "used_history": history,
        }

    # --- 6) Tâche inconnue ou non gérée ---
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
