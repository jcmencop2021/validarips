from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from core.dedupe import dedupe_path_strings
from core.factura_index import is_rips_payload
from core.loader import load_json_file


class JsonSelectDialog(QDialog):
    """Lista los .json de una carpeta para que el usuario elija cuáles cargar."""

    def __init__(self, folder: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Seleccionar archivos RIPS JSON")
        self.resize(520, 420)
        self._folder = folder
        self._paths: list[Path] = []
        for path in sorted(folder.glob("*.json")):
            data, err = load_json_file(path)
            if err or not isinstance(data, dict) or not is_rips_payload(data):
                continue
            self._paths.append(path)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(f"Carpeta: {folder}\nMarque los archivos JSON que desea cargar:")
        )

        btn_row = QHBoxLayout()
        self.btn_all = QPushButton("Marcar todos")
        self.btn_none = QPushButton("Desmarcar todos")
        btn_row.addWidget(self.btn_all)
        btn_row.addWidget(self.btn_none)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.list_widget = QListWidget()
        for path in self._paths:
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path.resolve()))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        if not self._paths:
            layout.addWidget(QLabel("No hay archivos RIPS (.json con usuarios) en esta carpeta."))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.btn_all.clicked.connect(self._check_all)
        self.btn_none.clicked.connect(self._check_none)

    def _check_all(self) -> None:
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def _check_none(self) -> None:
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def selected_paths(self) -> list[str]:
        paths: list[str] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                paths.append(item.data(Qt.ItemDataRole.UserRole))
        return dedupe_path_strings(paths)
