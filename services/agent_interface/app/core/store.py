import uuid
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# =============================================================================
# CONFIG : emplacement de la base users.db
# =============================================================================

DB_PATH = Path("users.db").resolve()

# -----------------------------------------------------------------------------
# Connexion / initialisation
# -----------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    Ouvre une connexion SQLite vers users.db.
    Chaque appel renvoie une nouvelle connexion (à fermer après usage).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # permet d'accéder aux colonnes par nom
    return conn


def init_db() -> None:
    """
    Crée les tables si elles n'existent pas encore :
      - users
      - profiles
      - tokens
    """
    conn = get_connection()
    cur = conn.cursor()

    # Table des utilisateurs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            firstname TEXT NOT NULL,
            lastname TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )

    # Table des profils (infos complémentaires)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            user_id TEXT PRIMARY KEY,
            age INTEGER,
            height_cm INTEGER,
            weight_kg REAL,
            goal TEXT,
            sessions_per_week INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    # Table des tokens (authentification)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()


# Initialisation automatique à l'import du module
init_db()


# =============================================================================
# COMPATIBILITÉ AVEC L'ANCIEN CODE (USERS / PROFILES / TOKENS en mémoire)
# -----------------------------------------------------------------------------
# On laisse ces variables pour ne pas casser d'import éventuel,
# mais la "vraie" source de vérité est désormais SQLite.
# =============================================================================

USERS: Dict[str, Dict[str, Any]] = {}
PROFILES: Dict[str, Dict[str, Any]] = {}
TOKENS: Dict[str, str] = {}


# =============================================================================
# FONCTIONS UTILISATEURS (create_user, check_user, get_user_by_id)
# =============================================================================

def create_user(firstname: str, lastname: str, email: str, password: str) -> str:
    """
    Crée un utilisateur dans la table `users`.
    - Vérifie que l'email n'est pas déjà utilisé.
    - Retourne user_id (UUID string).
    - En cas de doublon email, lève ValueError("EMAIL_ALREADY_EXISTS")
      (comportement identique à l'ancienne version).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Vérifier si l'email existe déjà
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    if row is not None:
        conn.close()
        raise ValueError("EMAIL_ALREADY_EXISTS")

    user_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO users (id, firstname, lastname, email, password)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, firstname, lastname, email, password),
    )
    conn.commit()
    conn.close()
    return user_id


def check_user(email: str, password: str) -> Optional[str]:
    """
    Vérifie email + password.
    Retourne user_id si OK, None sinon.
    (Pour l'instant, mot de passe en clair comme dans le MVP d'origine.)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, password FROM users WHERE email = ?",
        (email,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    stored_password = row["password"]
    if stored_password != password:
        return None

    return row["id"]


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère un utilisateur par son user_id.
    Retourne un dict {user_id, firstname, lastname, email, password} ou None.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, firstname, lastname, email, password
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "user_id": row["id"],
        "firstname": row["firstname"],
        "lastname": row["lastname"],
        "email": row["email"],
        "password": row["password"],
    }


# =============================================================================
# FONCTIONS TOKENS (create_token, get_user_id_from_token)
# =============================================================================

def create_token(user_id: str) -> str:
    """
    Crée un token d'authentification et l'enregistre en base.
    - Retourne le token (string UUID).
    - Pour simplifier, on laisse plusieurs tokens possibles par user.
      (On pourrait aussi nettoyer les anciens si on veut.)
    """
    token = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tokens (token, user_id, created_at)
        VALUES (?, ?, ?)
        """,
        (token, user_id, created_at),
    )
    conn.commit()
    conn.close()

    return token


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Retourne le user_id associé à un token, ou None si token inconnu.
    """
    if not token:
        return None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id FROM tokens WHERE token = ?",
        (token,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return row["user_id"]


# =============================================================================
# FONCTIONS PROFIL (load_profile / save_profile)
# =============================================================================

PROFILE_FIELDS = ["age", "height_cm", "weight_kg", "goal", "sessions_per_week"]


def load_profile(user_id: str) -> Dict[str, Any]:
    """
    Récupère le profil d'un utilisateur.
    Retourne un dict avec les clés de ProfileUpdate :
      - age
      - height_cm
      - weight_kg
      - goal
      - sessions_per_week
    Si aucun profil n'est encore enregistré, retourne {}.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT age, height_cm, weight_kg, goal, sessions_per_week
        FROM profiles
        WHERE user_id = ?
        """,
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return {}

    return {
        "age": row["age"],
        "height_cm": row["height_cm"],
        "weight_kg": row["weight_kg"],
        "goal": row["goal"],
        "sessions_per_week": row["sessions_per_week"],
    }


def save_profile(user_id: str, update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Met à jour (ou crée) le profil de l'utilisateur.
    - `update` contient uniquement les champs à mettre à jour (age, height_cm, etc.)
    - Si aucun profil existant -> INSERT.
    - Sinon -> UPDATE partiel.
    Retourne le profil complet après mise à jour.
    """
    # Nettoyer les champs pour ne garder que ceux connus
    clean_update = {k: v for k, v in update.items() if k in PROFILE_FIELDS}

    conn = get_connection()
    cur = conn.cursor()

    # Vérifier s'il existe déjà un profil
    cur.execute("SELECT user_id FROM profiles WHERE user_id = ?", (user_id,))
    exists = cur.fetchone() is not None

    if not exists:
        # On insère un nouveau profil avec les valeurs fournies
        # et NULL pour les valeurs manquantes
        values = {
            "age": None,
            "height_cm": None,
            "weight_kg": None,
            "goal": None,
            "sessions_per_week": None,
        }
        values.update(clean_update)

        cur.execute(
            """
            INSERT INTO profiles (
                user_id, age, height_cm, weight_kg, goal, sessions_per_week
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                values["age"],
                values["height_cm"],
                values["weight_kg"],
                values["goal"],
                values["sessions_per_week"],
            ),
        )
    else:
        # UPDATE des colonnes fournies
        set_parts = []
        params = []
        for field, value in clean_update.items():
            set_parts.append(f"{field} = ?")
            params.append(value)

        if set_parts:
            params.append(user_id)
            query = f"UPDATE profiles SET {', '.join(set_parts)} WHERE user_id = ?"
            cur.execute(query, params)

    conn.commit()
    conn.close()

    # On renvoie le profil complet après mise à jour
    return load_profile(user_id)

# ---------------------------------------------------------------------
# Sauvegarde et récupération de la prochaine séance recommandée
# ---------------------------------------------------------------------

NEXT_TRAINING_FILE = Path("data/next_training.json")
NEXT_TRAINING_FILE.parent.mkdir(parents=True, exist_ok=True)

def save_next_training(user_id: str, training: str):
    """
    Sauvegarde la prochaine séance recommandée dans un petit fichier JSON.
    Structure :
    {
        "user_id1": "séance recommandée...",
        "user_id2": "..."
    }
    """
    data = {}
    if NEXT_TRAINING_FILE.exists():
        try:
            data = json.loads(NEXT_TRAINING_FILE.read_text())
        except json.JSONDecodeError:
            data = {}

    data[user_id] = training
    NEXT_TRAINING_FILE.write_text(json.dumps(data, indent=2))


def load_next_training(user_id: str) -> Optional[str]:
    """Récupère la prochaine séance recommandée pour afficher dans le dashboard."""
    if not NEXT_TRAINING_FILE.exists():
        return None

    try:
        data = json.loads(NEXT_TRAINING_FILE.read_text())
        return data.get(user_id)
    except Exception:
        return None
