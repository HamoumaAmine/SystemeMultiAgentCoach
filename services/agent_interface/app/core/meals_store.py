# services/agent_interface/app/core/meals_store.py

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 1) Configuration du chemin vers la base meals.db
# ---------------------------------------------------------------------------

DB_PATH = Path(os.getenv("MEALS_DB_PATH", "meals.db")).resolve()


def get_connection() -> sqlite3.Connection:
    """
    Ouvre une connexion SQLite vers meals.db avec row_factory=Row.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# 2) Création de la table si elle n'existe pas
# ---------------------------------------------------------------------------

def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            image_url TEXT,
            kcal REAL,
            proteins_g REAL,
            carbs_g REAL,
            fats_g REAL,
            scanned_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()


# Initialise la base au chargement du module
init_db()


# ---------------------------------------------------------------------------
# 3) Sauvegarde d’un repas
# ---------------------------------------------------------------------------

def save_meal(
    user_id: str,
    title: str,
    description: str,
    kcal: Optional[float] = None,
    image_url: Optional[str] = None,
    proteins_g: Optional[float] = None,
    carbs_g: Optional[float] = None,
    fats_g: Optional[float] = None,
    scanned_at: Optional[str] = None,
) -> None:
    """
    Enregistre un repas dans la table meals.
    """
    if scanned_at is None:
        scanned_at = datetime.now().strftime("%d/%m/%Y")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO meals (
            user_id, title, description, image_url,
            kcal, proteins_g, carbs_g, fats_g, scanned_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            title,
            description,
            image_url,
            kcal,
            proteins_g,
            carbs_g,
            fats_g,
            scanned_at,
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 4) Dernier repas (pour la carte dashboard)
# ---------------------------------------------------------------------------

def get_last_meal(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id, user_id, title, description, image_url,
            kcal, proteins_g, carbs_g, fats_g, scanned_at
        FROM meals
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "description": row["description"],
        "image_url": row["image_url"],
        "kcal": row["kcal"],
        "proteins_g": row["proteins_g"],
        "carbs_g": row["carbs_g"],
        "fats_g": row["fats_g"],
        "scanned_at": row["scanned_at"],
    }


# ---------------------------------------------------------------------------
# 5) N derniers repas (dashboard + historique)
# ---------------------------------------------------------------------------

def get_recent_meals(user_id: str, limit: int = 3) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id, user_id, title, description, image_url,
            kcal, proteins_g, carbs_g, fats_g, scanned_at
        FROM meals
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()

    meals: List[Dict[str, Any]] = []
    for row in rows:
        meals.append(
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "title": row["title"],
                "description": row["description"],
                "image_url": row["image_url"],
                "kcal": row["kcal"],
                "proteins_g": row["proteins_g"],
                "carbs_g": row["carbs_g"],
                "fats_g": row["fats_g"],
                "scanned_at": row["scanned_at"],
            }
        )

    return meals
