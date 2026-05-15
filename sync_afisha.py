# Синхронизация API -> SQLite
from config import DB_PATH
from console_display import print_events
from database import count_events, init_db, latest_synced_at, save_events
from fetch_events import fetch_event_list, parse_events


def sync(db_path: str = DB_PATH) -> tuple[int, int, str | None]:
    events = parse_events(fetch_event_list())
    conn = init_db(db_path)
    saved = save_events(conn, events)
    total = count_events(conn)
    synced_at = latest_synced_at(conn)
    print_events(conn, saved=saved, synced_at=synced_at)
    conn.close()
    return saved, total, synced_at
