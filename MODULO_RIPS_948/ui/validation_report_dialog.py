from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)


class ValidationReportDialog(QDialog):
    """Informe completo que no se cierra solo; texto seleccionable y copiable."""

    def __init__(
        self,
        title: str,
        headline: str,
        body: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 520)
        layout = QVBoxLayout(self)
        lbl = QLabel(f"<b>{headline}</b>")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl)
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setPlainText(body)
        self.txt.setMinimumHeight(380)
        layout.addWidget(self.txt)
        hint = QLabel("Puede seleccionar el texto y copiarlo (Ctrl+C). Cierre con el botón.")
        hint.setStyleSheet("color: #555;")
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.setText("Cerrar")
        layout.addWidget(buttons)
