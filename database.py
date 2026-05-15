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
    event_description TEXT,
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
    event_description,
    image_bucket, image_uuid, image_url, synced_at
) VALUES (
    :event_id, :action_id, :event_name, :afisha_type_id, :afisha_type_name,
    :event_start_date, :event_start_time, :event_end_time, :is_all_day, :event_place,
    :event_description,
    :image_bucket, :image_uuid, :image_url, :synced_at
)
ON CONFLICT(event_id) DO UPDATE SET
    action_id=excluded.action_id, event_name=excluded.event_name,
    afisha_type_id=excluded.afisha_type_id, afisha_type_name=excluded.afisha_type_name,
    event_start_date=excluded.event_start_date, event_start_time=excluded.event_start_time,
    event_end_time=excluded.event_end_time, is_all_day=excluded.is_all_day,
    event_place=excluded.event_place,
    event_description=excluded.event_description,
    image_bucket=excluded.image_bucket,
    image_uuid=excluded.image_uuid, image_url=excluded.image_url,
    synced_at=excluded.synced_at
"""


def strip_html_markup(text: str) -> str:
    """Убираем теги; переносы из br/p сохраняем."""
    import re

    t = text or ""
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</p\s*>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _flatten_description(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return strip_html_markup(raw.strip())
    if isinstance(raw, dict):
        for key in ("text", "plain", "html", "value", "content"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return strip_html_markup(val.strip())
        return ""
    return strip_html_markup(str(raw).strip())


def pick_event_description(raw: dict) -> str:
    """Достаём описание из ответа API (разные возможные ключи)."""
    for key in (
        "eventDescription",
        "description",
        "shortDescription",
        "longDescription",
        "detailDescription",
        "annotation",
        "announcementText",
        "announce",
        "text",
        "content",
    ):
        s = _flatten_description(raw.get(key))
        if s:
            return s[:12000]
    return ""


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
    _migrate_events_schema(conn)
    conn.commit()
    return conn


def _migrate_events_schema(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()}
    if "event_description" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN event_description TEXT")


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
            "event_description": pick_event_description(raw),
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
                  is_all_day, event_name, afisha_type_name, event_place, event_description
           FROM events ORDER BY event_start_date, event_start_time, event_id"""
    ).fetchall()


def fetch_event_by_id(db_path: str | Path, event_id: int) -> sqlite3.Row | None:
    conn = init_db(db_path)
    try:
        return conn.execute(
            "SELECT * FROM events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    finally:
        conn.close()


def catalog_text(rows: list[sqlite3.Row]) -> str:
    # Текстовый каталог для GigaChat (без служебных id)
    lines = []
    for r in rows:
        place = (r["event_place"] or "").replace("\n", " ")
        nm = r["event_name"] or ""
        desc = ""
        if "event_description" in r.keys():
            desc = (r["event_description"] or "").strip()
        if len(desc) > 320:
            desc = desc[:317].rstrip() + "…"
        head = (
            f"{r['event_start_date'] or '—'} {event_time(r)} | {nm} | "
            f"{r['afisha_type_name'] or ''} | {place}"
        )
        lines.append(head + (f"\n    {desc}" if desc else ""))
    return "\n".join(lines)
