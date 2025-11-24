from fastapi import APIRouter, Header, HTTPException
from models.schemas import DashboardResponse, ServiceCard
from core.store import get_user_id_from_token, PROFILES

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DEFAULT_SERVICES = [
    ServiceCard(key="coach", title="Coach IA", subtitle="Texte / vocal", route="/coach"),
    ServiceCard(key="sport", title="Programme", subtitle="Tes séances", route="/training"),
    ServiceCard(key="nutri", title="Nutrition", subtitle="Repas & macros", route="/nutrition"),
    ServiceCard(key="mood", title="Mood", subtitle="Humeur du jour", route="/mood"),
    ServiceCard(key="photo", title="Photo repas", subtitle="Analyse image", route="/image"),
    ServiceCard(key="stats", title="Progrès", subtitle="Historique", route="/history"),
]

GOAL_LABELS = {
    "lose": "perte de poids",
    "gain": "prise de masse",
    "fit": "remise en forme",
    "perf": "performance"
}

@router.get("/", response_model=DashboardResponse)
def dashboard(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(401, "Token invalide")

    profile = PROFILES.get(user_id, {})
    goal_code = profile.get("goal", "non défini")
    goal_label = GOAL_LABELS.get(goal_code, goal_code)
    sessions = profile.get("sessions_per_week", "?")

    return DashboardResponse(
        user_id=user_id,
        greeting="Bon retour 👋",
        goal_summary=f"{goal_label} • {sessions} séances/sem",
        mood_summary="neutre",
        progress_summary="premiers jours",
        services=DEFAULT_SERVICES
    )