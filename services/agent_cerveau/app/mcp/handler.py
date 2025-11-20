import uuid
from typing import Any, Dict
from app.mcp.schemas import MCPResponse


async def process_mcp_message(msg: Dict[str, Any]) -> MCPResponse:
    """
    MVP : le cerveau ne fait encore rien d'intelligent.
    Il renvoie juste un accusé de réception.
    Plus tard, on branchera ici :
      - les appels LLM (LangChain)
      - les interactions avec agent_memory
      - les interactions avec agent_knowledge
      - les interactions avec agent_mood
    """

    response_payload = {
        "status": "ok",
        "message": "Agent Cerveau opérationnel (MVP)."
    }

    return MCPResponse(
        message_id=msg.get("message_id", str(uuid.uuid4())),
        to_agent=msg.get("from_agent", "unknown"),
        payload=response_payload,
        context=msg.get("context", {}),
    )
