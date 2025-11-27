# services/agent_interface/app/routers/dashboard.py

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
from app.core.store import load_next_training

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_model=DashboardResponse)
def get_dashboard(authorization: str = Header(...)):
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

    # Mood
    mood_raw = get_last_mood(user_id)
    mood_summary = "Aucune analyse d'humeur pour le moment."
    mood_details = {
        "energy_value": 0,
        "mental_value": 0,
        "label": None,
    }

    if mood_raw:
        parts = []

        if mood_raw.get("label"):
            parts.append(f"Humeur : {mood_raw.get('label')}")
            mood_details["label"] = mood_raw["label"]

        if mood_raw.get("energy_level_value"):
            ev = mood_raw["energy_level_value"]
            mood_details["energy_value"] = ev
            parts.append(f"Énergie : {ev}%")

        if mood_raw.get("mental_state_value"):
            mv = mood_raw["mental_state_value"]
            mood_details["mental_value"] = mv
            parts.append(f"Mental : {mv}%")

        mood_summary = " · ".join(parts) if parts else "Humeur analysée."

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
    # 2) Cartes de services
    # ------------------------------------------------------------------
    services = [
        ServiceCard(
            key="profile",
            title="Mon profil",
            subtitle="Âge, poids, objectif, fréquence…",
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
    # 3) Dernier repas scanné
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
            try:
                if m.get("kcal") is not None:
                    total_kcal += float(m["kcal"])
            except Exception:
                pass

            try:
                if m.get("proteins_g") is not None:
                    total_prot += float(m["proteins_g"])
            except Exception:
                pass

            try:
                if m.get("carbs_g") is not None:
                    total_carb += float(m["carbs_g"])
            except Exception:
                pass

            try:
                if m.get("fats_g") is not None:
                    total_fat += float(m["fats_g"])
            except Exception:
                pass

        cal_from_prot = total_prot * 4
        cal_from_carb = total_carb * 4
        cal_from_fat = total_fat * 9

        pct_prot = cal_from_prot / total_kcal if total_kcal else 0
        pct_carb = cal_from_carb / total_kcal if total_kcal else 0
        pct_fat = cal_from_fat / total_kcal if total_kcal else 0

        goal_str = (profile.get("goal") or "").lower() if profile else ""

        if "perte" in goal_str:
            ideal = {"prot": 0.35, "carb": 0.35, "fat": 0.30}
        elif "masse" in goal_str or "muscle" in goal_str:
            ideal = {"prot": 0.40, "carb": 0.30, "fat": 0.30}
        else:
            ideal = {"prot": 0.30, "carb": 0.45, "fat": 0.25}

        score = (
            abs(pct_prot - ideal["prot"]) +
            abs(pct_carb - ideal["carb"]) +
            abs(pct_fat - ideal["fat"])
        )

        nutri_score = max(5, int((1 - score) * 100))

    # ------------------------------------------------------------------
    # 5) Prochaine séance (basée sur ce que le coach a recommandé)
    # ------------------------------------------------------------------
    next_training_dynamic = load_next_training(user_id)

    # Nettoyage du texte brut du coach
    def clean_training_text(text: str) -> str:
        """Extrait seulement les phrases utiles pour la séance."""
        import re
        if not text:
            return ""

        # On enlève les titres Markdown (**Ce que je comprends..., etc.)
        text = re.sub(r"\*\*.*?\*\*", "", text)

        # On garde uniquement les phrases contenant des mots liés au sport
        keywords = ["minute", "marche", "échauffement", "séance", "exercice", "étirement"]
        lines = text.splitlines()

        selected = []
        for l in lines:
            if any(k in l.lower() for k in keywords):
                selected.append(l.strip("-•* ").strip())

        if selected:
            return " ".join(selected)

        # fallback : 1–2 phrases maximum
        sentences = re.split(r"[.!?]", text)
        return ". ".join(sentences[:2]).strip()


    # ---------------------------
    # Nouvelle génération séance
    # ---------------------------
    if next_training_dynamic:
        cleaned = clean_training_text(next_training_dynamic)

        next_training = {
            "title": "Séance recommandée",
            "description": cleaned if cleaned else "Une séance est disponible."
        }
    else:
        next_training = {
            "title": "Aucune séance recommandée",
            "description": (
                "Discute avec le coach pour recevoir une séance adaptée "
                "à ton humeur et ton objectif."
            )
        }


    # ------------------------------------------------------------------
    # Retour
    # ------------------------------------------------------------------
    return DashboardResponse(
        user_id=user_id,
        greeting=greeting,
        goal_summary=goal_summary,
        mood_summary=mood_summary,
        mood_details=mood_details,
        progress_summary=progress_summary,
        services=services,
        last_meal=last_meal_card,
        next_training=next_training,
        nutri_score=nutri_score,
    )
