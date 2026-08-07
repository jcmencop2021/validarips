#!/usr/bin/env python3
"""Punto de entrada del Módulo RIPS (Res. 948 JSON y Res. 3374 TXT)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from ui.rips_shell import RipsShellWindow  # noqa: E402


def run() -> None:
    app = QApplication(sys.argv)
    shell = RipsShellWindow()
    shell.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
