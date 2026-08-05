from __future__ import annotations

import json
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
BUILD_ID = "2026-08-05-007"


def get_version() -> str:
    cfg = APP_ROOT / "config.json"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            ver = str(data.get("version", "")).strip()
            if ver:
                return ver
        except json.JSONDecodeError:
            pass
    return "0.0.0"
