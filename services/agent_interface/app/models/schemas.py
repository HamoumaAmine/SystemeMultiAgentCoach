# services/agent_interface/app/models/schemas.py

from typing import List, Optional
from pydantic import BaseModel


# --------- MCP / Coach --------- #

class UserMessage(BaseModel):
    text: str


class CoachResponse(BaseModel):
    answer: str


# --------- Auth --------- #

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


# --------- Profil / onboarding --------- #

class ProfileUpdate(BaseModel):
    age: Optional[int] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None
    sessions_per_week: Optional[int] = None


class ProfileResponse(BaseModel):
    user_id: str
    profile: ProfileUpdate


# --------- Dashboard --------- #

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
