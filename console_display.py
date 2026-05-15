# Вывод списка мероприятий в консоль

import sqlite3



from database import event_time





def print_events(conn: sqlite3.Connection, saved: int | None = None, synced_at: str | None = None) -> None:

    rows = conn.execute(

        """SELECT event_start_date, event_start_time, event_end_time,

                  is_all_day, event_name, event_place

           FROM events ORDER BY event_start_date, event_start_time, event_id"""

    ).fetchall()



    if saved is not None:

        print(f"sync: {saved}, total: {len(rows)}")

    if synced_at:

        print(f"at: {synced_at}")

    print("-" * 72)



    for row in rows:

        date = row["event_start_date"] or "????-??-??"

        place = (row["event_place"] or "").replace("\n", " ").strip()

        nm = row["event_name"] or ""

        slug = nm if len(nm) <= 52 else nm[:49] + "…"

        when = event_time(row)

        print(f"{date} | {when:11} | {slug}")

        if place:

            print(f"  └ {place}")



    print("-" * 72)

    print(f"total: {len(rows)}")

