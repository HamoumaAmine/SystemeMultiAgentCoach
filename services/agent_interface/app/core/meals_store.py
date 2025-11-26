import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("meals.db").resolve()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT,
            description TEXT,
            kcal REAL,
            image_url TEXT,
            scanned_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_meal(user_id, title, description, kcal, image_url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO meals (user_id, title, description, kcal, image_url, scanned_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, title, description, kcal, image_url, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_last_meal(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT title, description, kcal, image_url, scanned_at
        FROM meals
        WHERE user_id = ?
        ORDER BY scanned_at DESC
        LIMIT 1
    """, (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "title": row[0],
        "description": row[1],
        "kcal": row[2],
        "image_url": row[3],
        "scanned_at": row[4],
    }

# Initialisation DB auto
init_db()
