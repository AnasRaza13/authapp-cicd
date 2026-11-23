"""Release information shown on the page footer and returned by /health.

VERSION   - edited by developers (for example 1.0.0 -> 1.1.0) to make a visible change.
BUILD_ID  - written into the package by the build step (scripts/package.py), for example
            "run42-1a2b3c4". It is how the pipeline proves WHICH build is live in production.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(name: str, default: str) -> str:
    try:
        text = (ROOT / name).read_text(encoding="utf-8").strip()
        return text or default
    except OSError:
        return default


APP_VERSION = _read("VERSION", "dev")
BUILD_ID = _read("BUILD_ID", "local")  # "local" when running from source, not from a build
