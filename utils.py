# Вспомогательные функции
import sys


def setup_utf8() -> None:
    # Корректный вывод кириллицы в консоли Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass
