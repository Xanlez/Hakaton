# CLI: загрузка афиши в БД
import argparse
import sys
import time
from datetime import datetime, timedelta

from config import DB_PATH, SYNC_INTERVAL_SEC
from sync_afisha import sync
from utils import setup_utf8


def main() -> int:
    setup_utf8()
    p = argparse.ArgumentParser(description="Афиша Sirius -> SQLite")
    p.add_argument("--db", default=DB_PATH)
    p.add_argument("--once", action="store_true", help="Один запуск")
    p.add_argument("--interval", type=int, default=SYNC_INTERVAL_SEC, help="Секунды между обновлениями")
    args = p.parse_args()

    if args.once:
        try:
            sync(args.db)
        except (RuntimeError, ValueError) as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            return 1
        return 0

    print("Обновление раз в час. Ctrl+C — стоп.\n")
    while True:
        try:
            sync(args.db)
        except (RuntimeError, ValueError) as e:
            print(f"Ошибка: {e}", file=sys.stderr)
        nxt = datetime.now() + timedelta(seconds=args.interval)
        print(f"следующее: {nxt:%Y-%m-%d %H:%M}\n")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nстоп.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
