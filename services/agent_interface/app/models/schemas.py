# services/agent_interface/app/models/schemas.py

from typing import List, Optional, Any
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 1) Messages du coach / réponse orchestrateur
# ---------------------------------------------------------------------------

class UserMessage(BaseModel):
    text: str


class CoachResponse(BaseModel):
    answer: str


# ---------------------------------------------------------------------------
# 2) Authentification : signup / login
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    firstname: str
    lastname: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    token: str


# ---------------------------------------------------------------------------
# 3) Profil utilisateur
# ---------------------------------------------------------------------------

class ProfileUpdate(BaseModel):
    age: Optional[int] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None
    sessions_per_week: Optional[int] = None


class ProfileResponse(BaseModel):
    user_id: str
    profile: ProfileUpdate


# ---------------------------------------------------------------------------
# 4) Meals / Nutrition
# ---------------------------------------------------------------------------

class MealCard(BaseModel):
    """
    Représente un repas scanné par l’utilisateur.
    Utilisé à la fois dans :
      - /dashboard  (last_meal)
      - /coach/history (liste des repas)
    """
    title: str
    description: str
    image_url: Optional[str]
    kcal: Optional[float]
    proteins_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fats_g: Optional[float] = None
    scanned_at: str


# ---------------------------------------------------------------------------
# 5) Dashboard : services + dernière séance / repas
# ---------------------------------------------------------------------------

class ServiceCard(BaseModel):
    key: str
    title: str
    subtitle: str
    route: str


class ExerciseItem(BaseModel):
    name: str
    series: str


class NextTraining(BaseModel):
    """
    Modèle flexible pour la prochaine séance :
      - soit une séance "texte libre" envoyée par le coach :
          { "title": "...", "description": "..." }
      - soit une séance structurée avec durée / intensité / exercices.
    """
    title: str
    description: Optional[str] = None
    duration: Optional[int] = None
    intensity: Optional[str] = None
    exercises: Optional[List[ExerciseItem]] = None


class MoodDetails(BaseModel):
    """
    Détails numériques pour les barres Énergie / Mental du dashboard.
    """
    energy_value: int
    mental_value: int
    label: Optional[str] = None


class DashboardResponse(BaseModel):
    user_id: str
    greeting: str
    goal_summary: str
    mood_summary: str
    mood_details: MoodDetails
    progress_summary: str
    services: List[ServiceCard]
    last_meal: Optional[MealCard] = None
    next_training: NextTraining
    nutri_score: int


# ---------------------------------------------------------------------------
# 6) Payload d'humeur renvoyé par l'orchestrateur / agent_mood
# ---------------------------------------------------------------------------

class MoodPayload(BaseModel):
    label: Optional[str] = None
    energy_level: Optional[str] = None
    mental_state: Optional[str] = None
    physical_state: Optional[str] = None

    # valeurs numériques éventuelles
    energy_value: Optional[int] = None
    mental_value: Optional[int] = None
    energy_level_value: Optional[int] = None
    mental_state_value: Optional[int] = None


# ---------------------------------------------------------------------------
# 7) Transcription vocale renvoyée par l'agent_speech
# ---------------------------------------------------------------------------

class TranscriptionPayload(BaseModel):
    text: Optional[str] = None
    transcript: Optional[str] = None
    transcription: Optional[str] = None
    raw: Optional[Any] = None
    output_text: Optional[str] = None


# ---------------------------------------------------------------------------
# 8) CoachAnswer — modèle utilisé par les endpoints /coach
# ---------------------------------------------------------------------------

class CoachAnswer(BaseModel):
    """
    Réponse renvoyée au front pour le chat / vocal / image.
    """
    answer: str
    meal: Optional[MealCard] = None
    mood: Optional[MoodPayload] = None
    transcription: Optional[TranscriptionPayload] = None
