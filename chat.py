import argparse
import sys

from config import DB_PATH, load_env
from database import count_events, init_db
from gigachat_advisor import recommend_events
from main import sync


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def ensure_db(db_path: str, force_sync: bool) -> None:
    conn = init_db(db_path)
    total = count_events(conn)
    conn.close()
    if total == 0 or force_sync:
        print("sync afisha...")
        sync(db_path)
        print()


def run_interactive(db_path: str) -> int:
    print("GigaChat advisor (events from DB). exit / quit — выход.\n")
    while True:
        try:
            query = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return 0

        if not query:
            continue
        if query.lower() in {"exit", "quit", "q", "выход"}:
            print("bye.")
            return 0

        try:
            answer = recommend_events(query, db_path)
        except Exception as exc:
            print(f"error: {exc}\n", file=sys.stderr)
            continue

        print(f"\nbot> {answer}\n")
    return 0


def main() -> int:
    load_env()
    configure_stdout()

    parser = argparse.ArgumentParser(description="GigaChat: советы по мероприятиям из БД")
    parser.add_argument("query", nargs="?", help="Один вопрос (без интерактива)")
    parser.add_argument("--db", default=DB_PATH, help=f"Путь к БД ({DB_PATH})")
    parser.add_argument("--sync", action="store_true", help="Обновить афишу перед ответом")
    args = parser.parse_args()

    try:
        ensure_db(args.db, args.sync)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.query:
        try:
            print(recommend_events(args.query, args.db))
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0

    return run_interactive(args.db)


if __name__ == "__main__":
    raise SystemExit(main())
