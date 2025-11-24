from app.mood.classifier import analyze_mood


def test_fatigue_text():
    text = "Franchement je suis épuisé, j'en peux plus."
    result = analyze_mood(text)
    assert result.mood == "fatigue"
    assert result.score > 0.3


def test_neutral_text():
    text = "Bonjour, je voudrais un programme d'entraînement."
    result = analyze_mood(text)
    assert result.mood in ("neutre", "positif")