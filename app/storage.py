from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def static_path(url: str) -> Path:
    return STATIC_DIR / url.lstrip("/")


def delete_file(url: str | None) -> None:
    if url:
        static_path(url).unlink(missing_ok=True)
