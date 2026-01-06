import os
import sqlite3
from datetime import datetime, timezone

def ensure_db(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen (
            link TEXT PRIMARY KEY,
            first_seen_utc TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def already_seen(conn: sqlite3.Connection, link: str) -> bool:
    cur = conn.execute("SELECT 1 FROM seen WHERE link = ? LIMIT 1", (link,))
    return cur.fetchone() is not None


def mark_seen(conn: sqlite3.Connection, link: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO seen(link, first_seen_utc) VALUES (?, ?)",
        (link, now),
    )
    conn.commit()
