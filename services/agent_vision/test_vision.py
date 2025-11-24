import json
from app.vision.client import ask_vision

if __name__ == "__main__":
    result = ask_vision("plat.jpg")  # mets une vraie image
    print(json.dumps(result, indent=4, ensure_ascii=False))
