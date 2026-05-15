import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY,
    action_id INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    afisha_type_id INTEGER,
    afisha_type_name TEXT,
    event_start_date TEXT,
    event_start_time TEXT,
    event_end_time TEXT,
    is_all_day INTEGER NOT NULL DEFAULT 0,
    event_place TEXT,
    image_bucket TEXT,
    image_uuid TEXT,
    image_url TEXT,
    synced_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_start_date ON events(event_start_date);
CREATE INDEX IF NOT EXISTS idx_events_afisha_type ON events(afisha_type_id);
"""


def _normalize_event(raw: dict, synced_at: str) -> dict:
    image = raw.get("eventImage") or {}
    if image and not isinstance(image, dict):
        image = {}

    return {
        "event_id": raw["eventId"],
        "action_id": raw["actionId"],
        "event_name": raw.get("eventName", "").strip(),
        "afisha_type_id": raw.get("afishaTypeId"),
        "afisha_type_name": raw.get("afishaTypeName"),
        "event_start_date": raw.get("eventStartDate"),
        "event_start_time": raw.get("eventStartTime"),
        "event_end_time": raw.get("eventEndTime"),
        "is_all_day": 1 if raw.get("isAllDay") else 0,
        "event_place": raw.get("eventPlace"),
        "image_bucket": image.get("bucket"),
        "image_uuid": image.get("uuid"),
        "image_url": image.get("url"),
        "synced_at": synced_at,
    }


def init_db(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def save_events(conn: sqlite3.Connection, events: list[dict]) -> int:
    synced_at = datetime.now(timezone.utc).isoformat()
    rows = [_normalize_event(item, synced_at) for item in events]

    conn.executemany(
        """
        INSERT INTO events (
            event_id, action_id, event_name,
            afisha_type_id, afisha_type_name,
            event_start_date, event_start_time, event_end_time,
            is_all_day, event_place,
            image_bucket, image_uuid, image_url,
            synced_at
        ) VALUES (
            :event_id, :action_id, :event_name,
            :afisha_type_id, :afisha_type_name,
            :event_start_date, :event_start_time, :event_end_time,
            :is_all_day, :event_place,
            :image_bucket, :image_uuid, :image_url,
            :synced_at
        )
        ON CONFLICT(event_id) DO UPDATE SET
            action_id = excluded.action_id,
            event_name = excluded.event_name,
            afisha_type_id = excluded.afisha_type_id,
            afisha_type_name = excluded.afisha_type_name,
            event_start_date = excluded.event_start_date,
            event_start_time = excluded.event_start_time,
            event_end_time = excluded.event_end_time,
            is_all_day = excluded.is_all_day,
            event_place = excluded.event_place,
            image_bucket = excluded.image_bucket,
            image_uuid = excluded.image_uuid,
            image_url = excluded.image_url,
            synced_at = excluded.synced_at
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def count_events(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]


def latest_synced_at(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT MAX(synced_at) FROM events").fetchone()
    return row[0] if row else None
