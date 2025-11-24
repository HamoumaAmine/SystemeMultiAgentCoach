import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Normalise le texte pour l'analyse de mood :
    - mise en minuscules
    - suppression des accents
    - suppression des caractères spéciaux / emojis
    - réduction des espaces multiples
    """
    if not text:
        return ""

    # Lowercase
    text = text.lower()

    # Supprimer les accents
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")

    # Supprimer les caractères bizarres / emojis
    text = re.sub(r"[^a-z0-9\s\.,!\?']", " ", text)

    # Réduire les espaces multiples
    text = re.sub(r"\s+", " ", text).strip()

    return text