import logging
import os
import sqlite3

logger = logging.getLogger("app.db")


def _ensure_db_dir(db_path: str) -> None:
    parent = os.path.dirname(os.path.abspath(db_path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def get_db_path() -> str:
    return os.getenv("DATABASE_PATH", "./data/app.db")


def init_db(db_path: str) -> None:
    _ensure_db_dir(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                created_at INTEGER,
                received_at TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.commit()


def record_event(event_id: str, event_type: str, created: int, status: str = "received") -> bool:
    """
    Insert event_id as the idempotency key.
    Returns True if inserted (new), False if duplicate (replay).
    """
    db_path = get_db_path()
    _ensure_db_dir(db_path)

    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO events (id, type, created_at, received_at, status) VALUES (?, ?, ?, datetime('now'), ?)",
                (event_id, event_type, created, status),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        # Replay detected (id collision)
        return False
    except Exception as e:
        logger.error(f"DB Error: {e}")
        raise


def list_events(limit: int = 50) -> list[dict]:
    """
    Return the last `limit` events, decending by received_at.
    """
    db_path = get_db_path()
    # It's possible the DB doesn't exist yet if no events recorded
    if not os.path.exists(db_path):
        return []

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, type, created_at, received_at, status
                FROM events
                ORDER BY received_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"DB Read Error: {e}")
        return []

