from fastapi import APIRouter
from models.schemas import UserMessage, CoachResponse
from mcp.client import send_mcp
from core.config import settings

router = APIRouter(prefix="/coach", tags=["coach"])

AGENT_CERVEAU_URL = settings.AGENT_CERVEAU_URL

@router.post("/", response_model=CoachResponse)
def talk_to_coach(msg: UserMessage):
    """
    Endpoint principal : transmet le message de user à l'agent cerveau via MCP.
    """
    payload = {
        "task": "coach_user",
        "text": msg.text,
        "user_id": msg.user_id
    }

    try:
        mcp_resp = send_mcp(AGENT_CERVEAU_URL, payload)
        answer = mcp_resp.get("payload", {}).get("answer", "Pas de réponse du cerveau.")
    except Exception as e:
        answer = f"Erreur lors de l'appel à l'agent_cerveau : {e}"

    return CoachResponse(answer=answer)
