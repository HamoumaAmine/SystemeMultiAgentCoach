from fastapi import APIRouter, Header, HTTPException
from models.schemas import ProfileUpdate, ProfileResponse
from core.store import PROFILES, get_user_id_from_token

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/", response_model=ProfileResponse)
def get_profile(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(401, "Token invalide")

    profile = PROFILES.get(user_id, {})
    return ProfileResponse(user_id=user_id, profile=ProfileUpdate(**profile))

@router.post("/", response_model=ProfileResponse)
def update_profile(update: ProfileUpdate, authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(401, "Token invalide")

    current = PROFILES.get(user_id, {})
    current.update({k: v for k, v in update.dict().items() if v is not None})
    PROFILES[user_id] = current

    return ProfileResponse(user_id=user_id, profile=ProfileUpdate(**current))