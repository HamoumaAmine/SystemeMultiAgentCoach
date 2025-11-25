import uuid

# MVP simple: stockage RAM
USERS = {}      # email -> {user_id, firstname, lastname, password}
PROFILES = {}   # user_id -> profile dict
TOKENS = {}     # token -> user_id

def create_user(firstname, lastname, email, password):
    if email in USERS:
        raise ValueError("EMAIL_ALREADY_EXISTS")
    user_id = str(uuid.uuid4())
    USERS[email] = {
        "user_id": user_id,
        "firstname": firstname,
        "lastname": lastname,
        "email": email,
        "password": password,  # MVP (pas hashé). Plus tard hash.
    }
    return user_id

def check_user(email, password):
    u = USERS.get(email)
    if not u or u["password"] != password:
        return None
    return u["user_id"]

def create_token(user_id):
    token = str(uuid.uuid4())
    TOKENS[token] = user_id
    return token

def get_user_id_from_token(token):
    return TOKENS.get(token)

def get_user_by_id(user_id: str):
    for u in USERS.values():
        if u["user_id"] == user_id:
            return u
    return None