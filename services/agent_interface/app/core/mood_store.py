# services/agent_interface/app/core/mood_store.py

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# -------------------------------------------------------------------
# Chemin de la base SQLite des humeurs
# -------------------------------------------------------------------
DB_PATH = Path(os.getenv("MOODS_DB_PATH", "data/moods.db")).resolve()


def get_connection() -> sqlite3.Connection:
    """
    Ouvre une connexion SQLite vers la base des humeurs.
    Crée le dossier parent si besoin.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Crée la table moods si elle n'existe pas encore.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS moods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            mood_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


# 🔥 On initialise la base AU CHARGEMENT DU MODULE
# (comme ça pas besoin de penser à appeler init_db() ailleurs)
init_db()


def save_mood(user_id: str, mood: Dict[str, Any]) -> None:
    """
    Sauvegarde un état d'humeur complet en JSON pour un utilisateur.
    Utilisé par coach.py à chaque fois que l'orchestrateur renvoie un mood.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO moods (user_id, mood_json, created_at)
        VALUES (?, ?, ?)
        """,
        (user_id, json.dumps(mood), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_last_mood(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère le DERNIER mood enregistré pour cet utilisateur.
    Renvoie:
      - un dict Python (décodé depuis JSON) + champ "_created_at"
      - ou None s'il n'y a encore aucun enregistrement.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT mood_json, created_at
        FROM moods
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    mood = json.loads(row["mood_json"])
    # On recopie dans un dict indépendant et on ajoute la date
    mood = dict(mood)
    mood["_created_at"] = row["created_at"]
    return mood
