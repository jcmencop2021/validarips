from __future__ import annotations

import json
from pathlib import Path

from core.paths import config_path

BUILD_ID = "2026-08-06-006"


def get_version() -> str:
    cfg = config_path()
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            ver = str(data.get("version", "")).strip()
            if ver:
                return ver
        except json.JSONDecodeError:
            pass
    return "0.0.0"
