import sqlite3
from typing import List, Dict, Any


DB_PATH = "db/nutrition.db"


def run_query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
