from fastapi import APIRouter, HTTPException, Header
from models.schemas import SignupRequest, LoginRequest, AuthResponse
from core.store import create_user, check_user, create_token, get_user_id_from_token, get_user_by_id

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    try:
        user_id = create_user(
            firstname=payload.firstname,
            lastname=payload.lastname,
            email=payload.email,
            password=payload.password
        )
    except ValueError as e:
        if str(e) == "EMAIL_ALREADY_EXISTS":
            raise HTTPException(status_code=409, detail="Email déjà utilisé")
        raise

    token = create_token(user_id)
    return AuthResponse(user_id=user_id, token=token)

@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    user_id = check_user(payload.email, payload.password)
    if not user_id:
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    token = create_token(user_id)
    return AuthResponse(user_id=user_id, token=token)

@router.get("/me")
def me(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(401, "Token invalide")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User introuvable")

    return {
        "user_id": user_id,
        "firstname": user["firstname"],
        "lastname": user["lastname"],
        "email": user["email"]
    }
