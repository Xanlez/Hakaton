# CLI: чат с GigaChat по мероприятиям из БД
import argparse
import sys

from config import DB_PATH
from gigachat_advisor import recommend_events
from sync_afisha import ensure_db
from utils import setup_utf8


def ask(query: str, db_path: str) -> None:
    print(recommend_events(query, db_path))


def chat_loop(db_path: str) -> int:
    print("Советы по афише. exit — выход.\n")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nпока.")
            return 0
        if not q:
            continue
        if q.lower() in {"exit", "quit", "q", "выход"}:
            return 0
        try:
            print(f"\n{recommend_events(q, db_path)}\n")
        except Exception as e:
            print(f"Ошибка: {e}\n", file=sys.stderr)


def main() -> int:
    setup_utf8()
    p = argparse.ArgumentParser(description="GigaChat + афиша")
    p.add_argument("query", nargs="?", help="Вопрос одной строкой")
    p.add_argument("--db", default=DB_PATH)
    p.add_argument("--sync", action="store_true", help="Обновить БД перед ответом")
    args = p.parse_args()

    try:
        ensure_db(args.db, args.sync)
    except (RuntimeError, ValueError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1

    if args.query:
        try:
            ask(args.query, args.db)
        except Exception as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            return 1
        return 0
    return chat_loop(args.db)


if __name__ == "__main__":
    raise SystemExit(main())
