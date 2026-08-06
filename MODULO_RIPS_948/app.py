#!/usr/bin/env python3
"""Punto de entrada del Módulo RIPS (Res. 948 JSON y Res. 3374 TXT)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from ui.mode_selector_dialog import ModeSelectorDialog, RipsMode  # noqa: E402


def run() -> None:
    app = QApplication(sys.argv)
    selector = ModeSelectorDialog()
    if selector.exec() != ModeSelectorDialog.DialogCode.Accepted:
        sys.exit(0)
    mode = selector.mode()
    if mode == RipsMode.RES_3374:
        from ui.main_window_3374 import MainWindow3374

        window = MainWindow3374()
    else:
        from ui.main_window import MainWindow948

        window = MainWindow948()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
