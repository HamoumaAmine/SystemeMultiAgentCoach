# services/agent_knowledge/app/main.py

from typing import Any, Dict

from fastapi import FastAPI

from app.mcp.handler import process_mcp_message
from app.mcp.schemas import MCPResponse

app = FastAPI(title="SMARTCOACH - Agent Knowledge")


@app.post("/mcp", response_model=MCPResponse)
async def mcp_endpoint(msg: Dict[str, Any]):
    """
    Point d'entrée MCP pour l'orchestrateur.
    """
    return await process_mcp_message(msg)


@app.get("/health")
def health():
    return {"status": "ok"}

