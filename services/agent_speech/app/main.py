from fastapi import FastAPI, UploadFile, File
from app.stt.whisper_client import WhisperClient
from app.stt.utils import save_temp_file

app = FastAPI(title="Speech-to-Text Agent - Whisper Large v3 Turbo")

whisper = WhisperClient()

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):

    temp_path = save_temp_file(file)

    result = whisper.transcribe(temp_path)

    return result
