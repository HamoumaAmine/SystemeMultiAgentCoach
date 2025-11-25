# services/agent_vision/app/vision/utils.py

from typing import Any, Dict


def normalize_vision_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise (au besoin) le résultat renvoyé par Groq Vision.

    Pour l’instant, on le renvoie tel quel. Cette fonction est là pour
    standardiser plus tard (par ex. s'assurer qu'on a bien:
      - "description"
      - "ingredients"
      - "macros_estimees"
      - ...
    )
    """
    if not isinstance(raw, dict):
        return {"raw": raw}
    return raw
