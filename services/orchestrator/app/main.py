from fastapi import FastAPI

from app.mcp.handler import process_mcp_message
from app.mcp.schemas import MCPMessage, MCPResponse

app = FastAPI(title="Orchestrator")


@app.post("/mcp", response_model=MCPResponse)
async def mcp_endpoint(msg: MCPMessage) -> MCPResponse:
    """
    Endpoint MCP de l'orchestrateur.
    """
    return await process_mcp_message(msg.dict())
