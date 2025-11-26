from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import (
    DashboardResponse,
    ServiceCard,
    MealCard,
)
from app.core.store import (
    get_user_id_from_token,
    get_user_by_id,
    load_profile,
)
from app.core.meals_store import get_last_meal

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_model=DashboardResponse)
def get_dashboard(authorization: str = Header(...)):
    """
    Données agrégées pour la homepage / dashboard :
      - message de bienvenue
      - résumé de l'objectif
      - résumé mood / progression (placeholder pour l'instant)
      - services proposés
      - dernier repas scanné
    """
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")

    # ------------------------------------------------------------------
    # 1) Récupérer infos utilisateur + profil
    # ------------------------------------------------------------------
    user = get_user_by_id(user_id)
    profile = load_profile(user_id)

    firstname = user["firstname"] if user else "Coaché"
    greeting = f"Bonjour {firstname} 👋 Bienvenue sur ton espace SmartCoach."

    # Objectif
    goal = profile.get("goal") if profile else None
    if goal:
        goal_summary = f"Ton objectif actuel : {goal}."
    else:
        goal_summary = (
            "Tu n'as pas encore défini d'objectif précis. "
            "Va dans la section \"Mon profil\" pour en fixer un."
        )

    # Mood / progression : pour l'instant, texte générique
    # (plus tard on branchera l'agent_mood + historique)
    mood_summary = (
        "Ton état d'humeur sera bientôt affiché ici grâce à l'agent_mood. "
        "Continue à discuter avec le coach pour enrichir ton historique."
    )

    sessions_per_week = profile.get("sessions_per_week") if profile else None
    if sessions_per_week:
        progress_summary = (
            f"Tu as indiqué vouloir t'entraîner {sessions_per_week} fois par semaine. "
            "SmartCoach adaptera progressivement tes recommandations."
        )
    else:
        progress_summary = (
            "Aucune fréquence d'entraînement définie. "
            "Commence par fixer un nombre de séances hebdomadaires dans ton profil."
        )

    # ------------------------------------------------------------------
    # 2) Cartes de services (sections de l'app)
    # ------------------------------------------------------------------
    services = [
        ServiceCard(
            key="profile",
            title="Mon profil",
            subtitle="Âge, poids, objectif, fréquence…",
            route="/ui/profile",
        ),
        ServiceCard(
            key="coach",
            title="Chat avec le coach IA",
            subtitle="Pose tes questions sport & nutrition.",
            route="/ui/home",
        ),
        ServiceCard(
            key="history",
            title="Historique",
            subtitle="Repas scannés et interactions (bientôt).",
            route="/ui/history",
        ),
    ]

    # ------------------------------------------------------------------
    # 3) Dernier repas scanné (depuis meals.db)
    # ------------------------------------------------------------------
    last_meal_raw = get_last_meal(user_id)
    last_meal_card = None

    if last_meal_raw is not None:
        last_meal_card = MealCard(
            title=last_meal_raw["title"],
            description=last_meal_raw["description"],
            image_url=last_meal_raw["image_url"],
            kcal=last_meal_raw["kcal"],
            scanned_at=last_meal_raw["scanned_at"],
        )

    return DashboardResponse(
        user_id=user_id,
        greeting=greeting,
        goal_summary=goal_summary,
        mood_summary=mood_summary,
        progress_summary=progress_summary,
        services=services,
        last_meal=last_meal_card,
    )
