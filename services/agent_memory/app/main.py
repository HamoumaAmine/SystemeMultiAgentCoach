from fastapi import FastAPI, Request
from app.mcp.handler import process_mcp_message
from app.db.models import Base
from app.db.session import engine

app = FastAPI(title="Agent Memory")

# Création des tables au démarrage (pour SQLite)
Base.metadata.create_all(bind=engine)


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    message = await request.json()
    response = await process_mcp_message(message)
    return response


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "agent_memory"}
