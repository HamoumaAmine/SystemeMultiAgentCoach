from pydantic import BaseModel, EmailStr
from typing import Optional, List

# =========================
# Coach (déjà utilisé par /coach)
# =========================

class UserMessage(BaseModel):
    user_id: str
    text: str

class CoachResponse(BaseModel):
    answer: str


# =========================
# Auth
# =========================

class SignupRequest(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    user_id: str
    token: str


# =========================
# Profil / Onboarding
# =========================

class ProfileUpdate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None            # lose | gain | fit | perf
    activity_level: Optional[str] = None  # low | medium | high
    diet: Optional[str] = None            # omnivore | vegan | halal ...
    allergies: Optional[str] = None
    injuries: Optional[str] = None
    motivation: Optional[str] = None
    sessions_per_week: Optional[int] = None
    equipment: Optional[str] = None       # none | minimal | home | gym
    time_per_session_min: Optional[int] = None

class ProfileResponse(BaseModel):
    user_id: str
    profile: ProfileUpdate


# =========================
# Dashboard / Services
# =========================

class ServiceCard(BaseModel):
    key: str
    title: str
    subtitle: str
    route: str

class DashboardResponse(BaseModel):
    user_id: str
    greeting: str
    goal_summary: str
    mood_summary: str
    progress_summary: str
    services: List[ServiceCard]
