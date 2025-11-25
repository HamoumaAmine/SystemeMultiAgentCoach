# services/agent_speech/app/main.py

from fastapi import FastAPI, UploadFile, File
from app.mcp.schemas import MCPRequest, MCPResponse
from app.mcp.handler import process_mcp_message, SpeechMCPHandler
from app.stt.utils import save_temp_file

app = FastAPI(title="Agent Speech (Speech-to-Text)")


@app.post("/mcp", response_model=MCPResponse)
async def mcp_endpoint(msg: MCPRequest) -> MCPResponse:
    """
    Endpoint MCP, comme pour les autres agents.
    On délègue la logique à process_mcp_message.
    """
    return await process_mcp_message(msg.dict())


@app.post("/transcribe-file")
async def transcribe_file(file: UploadFile = File(...)):
    """
    Endpoint pratique pour tester l'agent en uploadant un fichier audio
    depuis un client HTTP (Postman, navigateur...).

    - On sauvegarde le fichier dans un fichier temporaire.
    - On appelle SpeechMCPHandler.process() dessus.
    - On renvoie le résultat JSON.
    """
    temp_path = save_temp_file(file)

    handler = SpeechMCPHandler()
    result = handler.process(temp_path)

    return result


@app.get("/health")
async def health_check():
    """
    Pour vérifier que le service est vivant (Docker, monitoring, etc.).
    """
    return {"status": "ok", "service": "agent_speech"}
