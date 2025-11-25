# services/agent_vision/test_vision.py

from pathlib import Path

from app.vision.client import ask_vision


if __name__ == "__main__":
    # Image de test fournie par le prof
    image_path = Path("plat.jpg")

    print(f"[TEST_VISION] Analyse de l'image : {image_path}")
    result = ask_vision(image_path)
    print("[TEST_VISION] Résultat brut :")
    print(result)
