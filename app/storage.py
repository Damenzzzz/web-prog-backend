from datetime import datetime
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

items: dict[int, dict] = {}
looks: dict[int, dict] = {}
users: dict[int, dict] = {}
fitting_rooms: dict[int, list[dict]] = {}
orders: dict[int, dict] = {}
try_ons: dict[int, dict] = {}
try_on_times: dict[int, list[datetime]] = {}

_last_ids = {"item": 0, "look": 0, "user": 0, "order": 0, "try_on": 0}


def next_id(kind: str) -> int:
    _last_ids[kind] += 1
    return _last_ids[kind]


def static_path(url: str) -> Path:
    return STATIC_DIR / url.lstrip("/")


def delete_file(url: str | None) -> None:
    if url:
        static_path(url).unlink(missing_ok=True)
