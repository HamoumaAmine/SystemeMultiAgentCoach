from fastapi import FastAPI, Request
from app.mcp.handler import process_mcp_message

app = FastAPI(title="Agent Cerveau")


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    Endpoint MCP principal de l'agent cerveau.
    Il reçoit un message JSON, le passe au handler,
    et renvoie la réponse MCP.
    """
    message = await request.json()
    response = await process_mcp_message(message)
    return response


@app.get("/health")
async def health_check():
    """
    Endpoint de santé pour vérifier que l'agent tourne.
    """
    return {"status": "ok", "service": "agent_cerveau"}
