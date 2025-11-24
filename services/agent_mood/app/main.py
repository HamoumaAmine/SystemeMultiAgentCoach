from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from .mcp.handler import handle_mcp
from .mcp.schemas import MCPRequest, MCPResponse


app = FastAPI(
    title="Agent Mood",
    description="Micro-service de suivi d'humeur (mood tracker) pour le coach multi-agents.",
    version="0.1.0",
)


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    """
    Simple endpoint pour vérifier que le service tourne.
    """
    return HealthResponse(status="ok", service="agent_mood")


@app.post("/mcp", response_model=MCPResponse)
def mcp_endpoint(message: MCPRequest) -> MCPResponse:
    """
    Endpoint MCP de l'agent_mood.

    Tu peux le tester avec Thunder Client avec un JSON de ce type :

    {
      "message_id": "mood-test-1",
      "type": "request",
      "from_agent": "tester",
      "to_agent": "agent_mood",
      "payload": {
        "task": "analyze_mood",
        "text": "Franchement je suis épuisé, j'en peux plus.",
        "user_id": "user-demo"
      },
      "context": {}
    }
    """
    return handle_mcp(message)
