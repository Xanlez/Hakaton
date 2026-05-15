import sqlite3


def _time_label(row: sqlite3.Row) -> str:
    if row["is_all_day"]:
        return "all-day"
    start = row["event_start_time"] or "?"
    end = row["event_end_time"]
    return f"{start}-{end}" if end else start


def print_events(
    conn: sqlite3.Connection,
    *,
    saved: int | None = None,
    synced_at: str | None = None,
) -> None:
    rows = conn.execute(
        """
        SELECT event_id, event_start_date, event_start_time, event_end_time,
               is_all_day, event_name, event_place
        FROM events
        ORDER BY event_start_date, event_start_time, event_id
        """
    ).fetchall()

    if saved is not None:
        print(f"sync: {saved} events, db: {len(rows)}")
    if synced_at:
        print(f"at: {synced_at}")
    print("-" * 60)

    for row in rows:
        date = row["event_start_date"] or "????-??-??"
        time_part = _time_label(row)
        name = row["event_name"]
        place = (row["event_place"] or "").replace("\n", " ")
        print(f"{row['event_id']:>4} | {date} {time_part:>11} | {name} | {place}")

    print("-" * 60)
    print(f"total: {len(rows)}")
