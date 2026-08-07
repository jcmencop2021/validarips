from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class RipsMode(str, Enum):
    RES_948 = "948"
    RES_3374 = "3374"


class ModeSelectorDialog(QDialog):
    """Pantalla inicial: elegir normativa RIPS."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Módulo RIPS — Selección de normativa")
        self.resize(520, 280)
        self._mode: RipsMode | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "<b>Seleccione el tipo de RIPS a procesar:</b><br><br>"
                "• <b>Resolución 948 (2026)</b> — archivos JSON + relación Excel + FEV.<br>"
                "• <b>Resolución 3374 (2000)</b> — archivos planos .txt o ZIP "
                "(CT, AF, US, AC, AP, AM, AT, etc.).<br><br>"
                "En cualquier modo puede usar <b>Cambiar normativa (inicio)</b> "
                "para volver aquí sin cerrar el programa."
            )
        )

        btn_948 = QPushButton("RIPS Resolución 948 (JSON)")
        btn_948.setToolTip(
            "Validación y relación para RIPS en formato JSON (norma vigente Res. 948)."
        )
        btn_3374 = QPushButton("RIPS Resolución 3374 (archivos TXT / ZIP)")
        btn_3374.setToolTip(
            "Carga paquete RIPS en archivos de texto según Res. 3374 de 2000."
        )
        btn_cancel = QPushButton("Salir")
        layout.addWidget(btn_948)
        layout.addWidget(btn_3374)
        layout.addWidget(btn_cancel)

        btn_948.clicked.connect(lambda: self._choose(RipsMode.RES_948))
        btn_3374.clicked.connect(lambda: self._choose(RipsMode.RES_3374))
        btn_cancel.clicked.connect(self.reject)

        box = QDialogButtonBox()
        layout.addWidget(box)

    def _choose(self, mode: RipsMode) -> None:
        self._mode = mode
        self.accept()

    def mode(self) -> RipsMode | None:
        return self._mode
