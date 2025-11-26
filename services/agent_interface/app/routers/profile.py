from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import ProfileUpdate, ProfileResponse
from app.core.store import get_user_id_from_token, load_profile, save_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/", response_model=ProfileResponse)
def get_profile(authorization: str = Header(...)):
    """
    Récupère le profil de l'utilisateur courant à partir du token.
    """
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")

    profile_dict = load_profile(user_id)
    # profile_dict peut être vide -> ProfileUpdate() gère les valeurs None
    profile = ProfileUpdate(**profile_dict) if profile_dict else ProfileUpdate()

    return ProfileResponse(user_id=user_id, profile=profile)


@router.post("/", response_model=ProfileResponse)
def update_profile(update: ProfileUpdate, authorization: str = Header(...)):
    """
    Met à jour (ou crée) le profil de l'utilisateur courant.
    Les champs non fournis ne sont pas modifiés.
    """
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")

    # On ne garde que les champs non None
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    new_profile = save_profile(user_id, update_data)

    return ProfileResponse(user_id=user_id, profile=ProfileUpdate(**new_profile))
