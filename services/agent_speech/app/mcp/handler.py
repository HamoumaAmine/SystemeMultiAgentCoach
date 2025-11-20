from app.stt.whisper_client import WhisperClient


class SpeechMCPHandler:
    def __init__(self):
        self.whisper = WhisperClient()

    def process(self, audio_path: str):
        """
        Appelé par le LLM ou le routeur MCP.
        Retourne une transcription structurée.
        """
        result = self.whisper.transcribe(audio_path)

        return {
            "agent": "speech_to_text",
            "input_file": audio_path,
            "output": result
        }
