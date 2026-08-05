from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from core.dedupe import dedupe_path_strings
from core.factura_index import is_rips_payload
from core.loader import load_json_file


class RipsFolderDialog(QDialog):
    """Elige carpeta y muestra los JSON disponibles antes de confirmar."""

    def __init__(self, start_folder: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Carpeta de trabajo — archivos RIPS JSON")
        self.resize(640, 480)
        self._folder = Path(start_folder) if start_folder else Path.home()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Seleccione la carpeta y marque los archivos .json a cargar:"))

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(str(self._folder))
        self.btn_browse = QPushButton("Examinar carpeta…")
        self.btn_browse.setToolTip("Cambia la carpeta donde se listan los archivos .json.")
        folder_row.addWidget(self.folder_edit, stretch=1)
        folder_row.addWidget(self.btn_browse)
        layout.addLayout(folder_row)

        btn_row = QHBoxLayout()
        self.btn_all = QPushButton("Marcar todos")
        self.btn_all.setToolTip("Marca todos los archivos de la lista para cargarlos.")
        self.btn_none = QPushButton("Desmarcar todos")
        self.btn_none.setToolTip("Quita la selección de todos los archivos.")
        self.btn_refresh = QPushButton("Actualizar lista")
        self.btn_refresh.setToolTip("Vuelve a leer los .json de la carpeta indicada.")
        btn_row.addWidget(self.btn_all)
        btn_row.addWidget(self.btn_none)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        self.lbl_info = QLabel("")
        layout.addWidget(self.lbl_info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.btn_browse.clicked.connect(self._browse_folder)
        self.btn_all.clicked.connect(self._check_all)
        self.btn_none.clicked.connect(self._check_none)
        self.btn_refresh.clicked.connect(self._reload_list)
        self.folder_edit.editingFinished.connect(self._reload_list_from_edit)

        self._reload_list()

    def folder(self) -> str:
        return self.folder_edit.text().strip()

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta con archivos JSON", self.folder_edit.text()
        )
        if path:
            self.folder_edit.setText(path)
            self._reload_list()

    def _reload_list_from_edit(self) -> None:
        self._reload_list()

    def _reload_list(self) -> None:
        folder = Path(self.folder_edit.text().strip() or ".")
        self._folder = folder
        self.list_widget.clear()
        count = 0
        rips_count = 0
        if not folder.is_dir():
            self.lbl_info.setText("La ruta no es una carpeta válida.")
            return

        for path in sorted(folder.glob("*.json")):
            count += 1
            data, err = load_json_file(path)
            is_rips = not err and isinstance(data, dict) and is_rips_payload(data)
            if is_rips:
                rips_count += 1
            label = path.name
            if not is_rips:
                label = f"{label}  (no parece RIPS)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(path.resolve()))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if is_rips else Qt.CheckState.Unchecked)
            if not is_rips:
                item.setForeground(QColor("#b8860b"))
            self.list_widget.addItem(item)

        if count == 0:
            self.lbl_info.setText("No hay archivos .json en esta carpeta.")
        else:
            self.lbl_info.setText(
                f"Archivos JSON: {count} | Con estructura RIPS: {rips_count}"
            )

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


# Compatibilidad con import anterior
JsonSelectDialog = RipsFolderDialog
