from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from pathlib import Path
from dotenv import load_dotenv

from .mcp.handler import MCPMessage, handle_mcp


# === Charger le fichier .env placé dans le même répertoire que main.py ===
BASE_DIR = Path(__file__).resolve().parent  # -> services/agent_mood/app
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)


class HealthResponse(BaseModel):
    status: str


app = FastAPI(
    title="Agent Mood - Mood Tracker",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Permet de vérifier que le service est up.
    """
    return HealthResponse(status="ok")


@app.post("/mcp")
def mcp_endpoint(message: MCPMessage) -> Dict[str, Any]:
    """
    Endpoint MCP : reçoit un message, renvoie un message.
    """
    response = handle_mcp(message)
    return response
