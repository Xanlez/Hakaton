"""Загрузка афиши с API, SQLite и вывод в консоль."""

import argparse
import sys
import time
from datetime import datetime, timedelta

from config import DB_PATH, SYNC_INTERVAL_SEC
from console_display import print_events
from database import count_events, init_db, latest_synced_at, save_events
from fetch_events import fetch_event_list, parse_events


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def sync(db_path: str = DB_PATH) -> tuple[int, int, str | None]:
    response = fetch_event_list()
    events = parse_events(response)
    conn = init_db(db_path)
    saved = save_events(conn, events)
    total = count_events(conn)
    synced_at = latest_synced_at(conn)
    print_events(conn, saved=saved, synced_at=synced_at)
    conn.close()
    return saved, total, synced_at


def run_once(db_path: str) -> int:
    try:
        sync(db_path)
    except (RuntimeError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    return 0


def run_loop(db_path: str, interval_sec: int) -> int:
    print("auto refresh every hour, Ctrl+C to stop\n")
    while True:
        try:
            sync(db_path)
        except (RuntimeError, ValueError) as exc:
            print(f"Ошибка синхронизации: {exc}", file=sys.stderr)

        next_run = datetime.now() + timedelta(seconds=interval_sec)
        print(f"next sync: {next_run:%Y-%m-%d %H:%M:%S} (+{interval_sec // 60} min)\n")
        try:
            time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\nstopped.")
            return 0


def main() -> int:
    configure_stdout()

    parser = argparse.ArgumentParser(description="Афиша Sirius → SQLite → консоль")
    parser.add_argument("--db", default=DB_PATH, help=f"Путь к БД (по умолчанию: {DB_PATH})")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Один раз загрузить и вывести, без цикла",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=SYNC_INTERVAL_SEC,
        metavar="SEC",
        help=f"Интервал обновления в секундах (по умолчанию: {SYNC_INTERVAL_SEC})",
    )
    args = parser.parse_args()

    if args.once:
        return run_once(args.db)
    return run_loop(args.db, args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
