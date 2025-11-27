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

from app.core.meals_store import get_last_meal, get_recent_meals
from app.core.mood_store import get_last_mood

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_model=DashboardResponse)
def get_dashboard(authorization: str = Header(...)):
    """
    Données agrégées pour la homepage / dashboard :
      - message de bienvenue
      - résumé de l'objectif
      - résumé mood / progression
      - services proposés (tuiles)
      - dernier repas scanné
    """
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")

    # ------------------------------------------------------------------
    # 1) Infos utilisateur + profil
    # ------------------------------------------------------------------
    user = get_user_by_id(user_id)
    profile = load_profile(user_id)

    firstname = user["firstname"] if user else "Coaché"
    greeting = f"Bonjour {firstname} 👋 Bienvenue sur ton espace SmartCoach."

    goal = profile.get("goal") if profile else None
    if goal:
        goal_summary = f"Ton objectif actuel : {goal}."
    else:
        goal_summary = (
            "Tu n'as pas encore défini d'objectif précis. "
            "Va dans la section \"Mon profil\" pour en fixer un."
        )

    # Mood : pour l'instant, texte générique (sera remplacé par le dernier mood)
    mood_summary = (
        "Ton état d'humeur sera bientôt affiché ici grâce à l’agent d’humeur. "
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
    # 2) Cartes de services (tuiles du milieu)
    # ------------------------------------------------------------------
    services = [
        ServiceCard(
            key="profile",
            title="Mon profil",
            subtitle="Âge, poids, objectif, fréquence…",
            # Renvoie vers la section profil de la home
            route="#profile-section",
        ),
        ServiceCard(
            key="coach",
            title="Chat avec le coach IA",
            subtitle="Pose tes questions sport & nutrition.",
            route="#chat-section",
        ),
        ServiceCard(
            key="nutrition",
            title="Nutrition",
            subtitle="Repas, calories et macros.",
            route="#nutrition-section",
        ),
        ServiceCard(
            key="mood",
            title="Humeur",
            subtitle="Suivi mental et énergie.",
            route="#mood-section",
        ),
        ServiceCard(
            key="history",
            title="Historique",
            subtitle="Repas scannés et échanges.",
            route="#history-section",
        ),
        ServiceCard(
            key="stats",
            title="Statistiques",
            subtitle="Progrès sport & nutrition.",
            route="#stats-section",
        ),
    ]

    # ------------------------------------------------------------------
    # 3) Dernier repas scanné (meals.db)
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

    # ------------------------------------------------------------------
    # 4) Équilibre nutritionnel dynamique
    # ------------------------------------------------------------------

    meals = get_recent_meals(user_id, limit=3)

    nutri_score = 50  # par défaut

    if meals:
        total_kcal = 0
        total_prot = 0
        total_carb = 0
        total_fat = 0

        for m in meals:
            # kcal toujours disponible
            kcal = m.get("kcal")
            try:
                total_kcal += float(kcal)
            except:
                pass

            # protéines
            prot = m.get("proteins_g")
            try:
                total_prot += float(prot)
            except:
                pass

            # glucides
            carb = m.get("carbs_g")
            try:
                total_carb += float(carb)
            except:
                pass

            # lipides
            fat = m.get("fats_g")
            try:
                total_fat += float(fat)
            except:
                pass


        # ratios simplifiés
        cal_from_prot = total_prot * 4
        cal_from_carb = total_carb * 4
        cal_from_fat = total_fat * 9

        pct_prot = cal_from_prot / total_kcal if total_kcal else 0
        pct_carb = cal_from_carb / total_kcal if total_kcal else 0
        pct_fat = cal_from_fat / total_kcal if total_kcal else 0

        # profil influence les ratios idéaux
        goal = (profile.get("goal") or "").lower() if profile else ""

        if "perte" in goal:
            ideal = {"prot": 0.35, "carb": 0.35, "fat": 0.30}
        elif "muscle" in goal:
            ideal = {"prot": 0.40, "carb": 0.30, "fat": 0.30}
        else:
            ideal = {"prot": 0.30, "carb": 0.45, "fat": 0.25}

        # scoring simple : écart moyen
        score = (
            abs(pct_prot - ideal["prot"]) +
            abs(pct_carb - ideal["carb"]) +
            abs(pct_fat - ideal["fat"])
        )

        # Score inversé
        nutri_score = max(5, int((1 - score) * 100))


    # ------------------------------------------------------------------
    # 4) Génération dynamique de la prochaine séance
    # ------------------------------------------------------------------
    goal = profile.get("goal", "fit") if profile else "fit"
    age = profile.get("age", 25) if profile else 25
    sessions = profile.get("sessions_per_week", 2) if profile else 2

    # Intensité de base selon objectif
    if goal in ["fit", "bien-être"]:
        intensity = "modérée"
    elif goal in ["perte_de_poids"]:
        intensity = "haute"
    elif goal in ["muscle"]:
        intensity = "élevée"
    else:
        intensity = "modérée"

    # Ajustement selon âge
    if age > 45 and intensity == "élevée":
        intensity = "modérée"

    # Durée selon intensité
    duration_map = {
        "douce": 25,
        "modérée": 35,
        "haute": 40,
        "élevée": 45,
    }
    duration = duration_map.get(intensity, 30)

    # Exercices recommandés
    if intensity == "douce":
        exercises = [
            {"name": "Marche active", "series": "10 min"},
            {"name": "Étirements", "series": "5 min"},
            {"name": "Respiration profonde", "series": "5 min"},
        ]
    elif intensity == "modérée":
        exercises = [
            {"name": "Squats", "series": "3×12"},
            {"name": "Pompes", "series": "3×10"},
            {"name": "Gainage", "series": "3×30s"},
        ]
    elif intensity in ["haute", "élevée"]:
        exercises = [
            {"name": "Burpees", "series": "3×10"},
            {"name": "Squats sautés", "series": "4×12"},
            {"name": "Mountain climbers", "series": "3×45s"},
        ]

    next_training = {
        "title": f"Séance {intensity}",
        "duration": duration,
        "intensity": intensity,
        "exercises": exercises,
    }

    mood_data = get_last_mood(user_id)

    if mood_data:
        summary_parts = []
        if mood_data.get("label"):
            summary_parts.append(f"Humeur {mood_data['label']}")
        if mood_data.get("energy_level"):
            summary_parts.append(f"Énergie {mood_data['energy_level']}")
        if mood_data.get("mental_state"):
            summary_parts.append(f"Mental {mood_data['mental_state']}")

        mood_summary = " · ".join(summary_parts) if summary_parts else "Humeur détectée."

    return DashboardResponse(
        user_id=user_id,
        greeting=greeting,
        goal_summary=goal_summary,
        mood_summary=mood_summary,
        progress_summary=progress_summary,
        services=services,
        last_meal=last_meal_card,
        next_training=next_training,
        nutri_score=nutri_score,
    )
