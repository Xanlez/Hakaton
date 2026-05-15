# Загрузка афиши с API Sirius
import json
import urllib.error
import urllib.request

from config import API_URL


def fetch_event_list(body: dict | None = None, timeout: int = 30) -> dict:
    payload = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Сеть: {exc.reason}") from exc


def parse_events(response: dict) -> list[dict]:
    code = response.get("code")
    if code is not None:
        ok = (isinstance(code, int) and code < 400) or (
            isinstance(code, str) and (code.isdigit() and int(code) < 400 or code.upper() in ("OK", "SUCCESS"))
        )
        if not ok:
            msg = response.get("message") or response.get("description") or "ошибка API"
            raise ValueError(msg)

    payload = response.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("нет payload")
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("нет events")
    return events
