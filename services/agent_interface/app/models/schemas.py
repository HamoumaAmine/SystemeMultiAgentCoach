# services/agent_interface/app/models/schemas.py

from typing import List, Optional
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
# 4) Meals / Nutrition (NOUVEAU)
# ---------------------------------------------------------------------------

class MealCard(BaseModel):
    """
    Représente un repas scanné par l’utilisateur.
    Utilisé à la fois dans :
      - /dashboard  (last_meal)
      - endpoints historiques futurs
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
# 5) Dashboard : services + dernier repas scanné
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
    title: str
    duration: int
    intensity: str
    exercises: List[ExerciseItem]


class DashboardResponse(BaseModel):
    user_id: str
    greeting: str
    goal_summary: str
    mood_summary: str
    progress_summary: str
    services: List[ServiceCard]
    next_training: NextTraining
    nutri_score: int
    # Ajout essentiel pour afficher le dernier repas scanné
    last_meal: Optional[MealCard] = None


class MoodPayload(BaseModel):
    label: Optional[str] = None
    energy_level: Optional[str] = None
    mental_state: Optional[str] = None
    physical_state: Optional[str] = None


# ---------------------------------------------------------------------------
# 6) CoachAnswer — modèle utilisé par coach.py
# ---------------------------------------------------------------------------

class CoachAnswer(BaseModel):
    answer: str
    meal: Optional[MealCard] = None
    mood: Optional[MoodPayload] = None

