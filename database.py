# SQLite: хранение и выборка мероприятий
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
"""

UPSERT = """
INSERT INTO events (
    event_id, action_id, event_name, afisha_type_id, afisha_type_name,
    event_start_date, event_start_time, event_end_time, is_all_day, event_place,
    image_bucket, image_uuid, image_url, synced_at
) VALUES (
    :event_id, :action_id, :event_name, :afisha_type_id, :afisha_type_name,
    :event_start_date, :event_start_time, :event_end_time, :is_all_day, :event_place,
    :image_bucket, :image_uuid, :image_url, :synced_at
)
ON CONFLICT(event_id) DO UPDATE SET
    action_id=excluded.action_id, event_name=excluded.event_name,
    afisha_type_id=excluded.afisha_type_id, afisha_type_name=excluded.afisha_type_name,
    event_start_date=excluded.event_start_date, event_start_time=excluded.event_start_time,
    event_end_time=excluded.event_end_time, is_all_day=excluded.is_all_day,
    event_place=excluded.event_place, image_bucket=excluded.image_bucket,
    image_uuid=excluded.image_uuid, image_url=excluded.image_url,
    synced_at=excluded.synced_at
"""


def event_time(row: sqlite3.Row) -> str:
    if row["is_all_day"]:
        return "all-day"
    start, end = row["event_start_time"], row["event_end_time"]
    if start and end:
        return f"{start}-{end}"
    return start or "?"


def init_db(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def save_events(conn: sqlite3.Connection, events: list[dict]) -> int:
    synced_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for raw in events:
        img = raw.get("eventImage") if isinstance(raw.get("eventImage"), dict) else {}
        rows.append({
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
            "image_bucket": img.get("bucket"),
            "image_uuid": img.get("uuid"),
            "image_url": img.get("url"),
            "synced_at": synced_at,
        })
    conn.executemany(UPSERT, rows)
    conn.commit()
    return len(rows)


def count_events(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]


def latest_synced_at(conn: sqlite3.Connection) -> str | None:
    return conn.execute("SELECT MAX(synced_at) FROM events").fetchone()[0]


def load_catalog(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT event_id, event_start_date, event_start_time, event_end_time,
                  is_all_day, event_name, afisha_type_name, event_place
           FROM events ORDER BY event_start_date, event_start_time, event_id"""
    ).fetchall()


def catalog_text(rows: list[sqlite3.Row]) -> str:
    # Текстовый каталог для GigaChat
    lines = []
    for r in rows:
        place = (r["event_place"] or "").replace("\n", " ")
        lines.append(
            f"id={r['event_id']} | {r['event_start_date']} {event_time(r)} | "
            f"{r['event_name']} | {r['afisha_type_name'] or ''} | {place}"
        )
    return "\n".join(lines)
