from app.stt.whisper_client_groq import WhisperClientGroq   # version Groq
import os
import json  # pour convertir dict -> str

class SpeechMCPHandler:
    def __init__(self):
        self.whisper = WhisperClientGroq()

    def process(self, audio_path: str):
        # Transcription de l'audio
        result = self.whisper.transcribe(audio_path)

        # Convertir en texte exploitable si c'est un dict
        if isinstance(result, dict):
            # Exemple : on prend juste la transcription texte si elle existe
            text = result.get("text") or json.dumps(result, indent=2)
        else:
            text = str(result)

        # Préparer le chemin du fichier texte
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        txt_path = os.path.join(os.path.dirname(audio_path), f"{base_name}.txt")

        # Écriture dans le fichier texte
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        return {
            "agent": "speech_to_text",
            "input_file": audio_path,
            "output_file": txt_path,
            "output_text": text
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.mcp.handler mp3.mp3")
        exit(1)

    audio_path = sys.argv[1]
    handler = SpeechMCPHandler()
    result = handler.process(audio_path)
    print(f"Transcription enregistrée dans : {result['output_file']}")
