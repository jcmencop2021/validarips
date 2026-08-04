#!/usr/bin/env python3
"""Punto de entrada del Módulo RIPS Relación Resolución 948."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.main_window import run  # noqa: E402


if __name__ == "__main__":
    run()
