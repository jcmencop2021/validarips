#!/usr/bin/env python3
"""Punto de entrada del Módulo RIPS (Res. 948 JSON y Res. 3374 TXT)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QEventLoop  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ui.main_window import SessionEndReason  # noqa: E402
from ui.mode_selector_dialog import ModeSelectorDialog, RipsMode  # noqa: E402


def _open_main_window(mode: RipsMode):
    if mode == RipsMode.RES_3374:
        from ui.main_window_3374 import MainWindow3374

        return MainWindow3374()
    from ui.main_window import MainWindow948

    return MainWindow948()


def run() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    while True:
        selector = ModeSelectorDialog()
        if selector.exec() != ModeSelectorDialog.DialogCode.Accepted:
            break
        mode = selector.mode()
        if mode is None:
            continue

        window = _open_main_window(mode)
        end_reason: list[SessionEndReason | None] = [None]
        loop = QEventLoop()

        def on_session_ended(reason: SessionEndReason) -> None:
            end_reason[0] = reason
            loop.quit()

        window.session_ended.connect(on_session_ended)
        window.show()
        loop.exec()
        window.deleteLater()

        if end_reason[0] != SessionEndReason.HOME:
            break

    sys.exit(0)


if __name__ == "__main__":
    run()
