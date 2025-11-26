# services/agent_interface/app/routers/dashboard.py

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import DashboardResponse, ServiceCard
from app.core.store import get_user_id_from_token, PROFILES
from app.core.meals_store import get_last_meal  # ✅ NOUVEAU : dernier repas scanné

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ---------------------------------------------------------------------------
# Cartes de services affichées sur la page d’accueil
# ---------------------------------------------------------------------------

DEFAULT_SERVICES = [
    ServiceCard(key="coach", title="Coach IA", subtitle="Texte / vocal", route="/coach"),
    ServiceCard(key="sport", title="Programme", subtitle="Tes séances", route="/training"),
    ServiceCard(key="nutri", title="Nutrition", subtitle="Repas & macros", route="/nutrition"),
    ServiceCard(key="mood", title="Mood", subtitle="Humeur du jour", route="/mood"),
    ServiceCard(key="photo", title="Photo repas", subtitle="Analyse image", route="/image"),
    ServiceCard(key="stats", title="Progrès", subtitle="Historique", route="/history"),
]

# ---------------------------------------------------------------------------
# Labels pour transformer les codes objectifs en texte lisible
# ---------------------------------------------------------------------------

GOAL_LABELS = {
    "perte_poids": "Perte de poids",
    "prise_masse": "Prise de masse",
    "reprise": "Reprise en douceur",
    "performance": "Performance",
}

# ---------------------------------------------------------------------------
# Endpoint principal : /dashboard/
# ---------------------------------------------------------------------------


@router.get("/", response_model=DashboardResponse)
def get_dashboard(authorization: str = Header(...)):
    """
    Renvoie le tableau de bord : objectif, humeur, progrès + dernières actions.
    Désormais inclut : le dernier repas scanné.
    """

    # 1) Vérification du token
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")

    # 2) Récupération du profil utilisateur
    profile = PROFILES.get(user_id, {})
    goal_code = profile.get("goal", "non défini")
    goal_label = GOAL_LABELS.get(goal_code, goal_code)
    sessions = profile.get("sessions_per_week", "?")

    # 3) Récupération du dernier repas scanné
    try:
        last_meal = get_last_meal(user_id)
    except Exception:
        last_meal = None  # On ne bloque pas si aucun repas ou DB KO

    # 4) Construction de la réponse complète
    return DashboardResponse(
        user_id=user_id,
        greeting="Bon retour 👋",
        goal_summary=f"{goal_label} • {sessions} séances/sem",
        mood_summary="neutre",
        progress_summary="premiers jours",
        services=DEFAULT_SERVICES,
        last_meal=last_meal,  # ✅ NOUVEAU
    )
