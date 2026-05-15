import json
import urllib.error
import urllib.request

from config import API_URL


def fetch_event_list(body: dict | None = None, timeout: int = 30) -> dict:
    payload = json.dumps(body or {}).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ошибка сети: {exc.reason}") from exc


def _is_success_code(code) -> bool:
    if code is None:
        return True
    if isinstance(code, int):
        return 0 <= code < 400
    if isinstance(code, str):
        return code.isdigit() and int(code) < 400 or code.upper() in ("OK", "SUCCESS")
    return False


def parse_events(response: dict) -> list[dict]:
    if not _is_success_code(response.get("code")):
        message = response.get("message") or response.get("description") or "неизвестная ошибка"
        raise ValueError(f"API вернул ошибку: {message}")

    payload = response.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("В ответе нет поля payload")

    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("В payload нет списка events")

    return events
