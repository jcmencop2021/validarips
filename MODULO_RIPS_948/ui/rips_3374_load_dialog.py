from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from core.rips_3374.txt_parser import (
    file_type_from_name,
    list_matching_txt_in_folder,
)


class Rips3374LoadDialog(QDialog):
    """ZIP o carpeta con .txt RIPS; vista previa antes de confirmar."""

    def __init__(self, start_folder: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cargar RIPS Res. 3374 — TXT o ZIP")
        self.resize(700, 520)
        self._folder = Path(start_folder) if start_folder else Path.home()
        self._zip_path: Path | None = None
        self._mode_zip = True

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "1) Elija ZIP o carpeta con archivos .txt (CT, AF, US, AC, AP, …).\n"
                "2) Revise la lista de archivos detectados.\n"
                "3) Pulse Aceptar solo si es la carpeta/paquete correcto."
            )
        )

        mode_row = QHBoxLayout()
        self.rb_zip = QRadioButton("Archivo ZIP con todos los .txt")
        self.rb_folder = QRadioButton("Carpeta con archivos .txt")
        self.rb_zip.setChecked(True)
        mode_row.addWidget(self.rb_zip)
        mode_row.addWidget(self.rb_folder)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        zip_row = QHBoxLayout()
        self.zip_edit = QLineEdit()
        self.btn_zip = QPushButton("Examinar ZIP…")
        self.btn_zip.setToolTip("Seleccione un .zip con los archivos RIPS en texto plano.")
        zip_row.addWidget(self.zip_edit, stretch=1)
        zip_row.addWidget(self.btn_zip)
        layout.addLayout(zip_row)

        folder_box = QGroupBox("Carpeta de archivos .txt")
        folder_layout = QVBoxLayout(folder_box)
        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(str(self._folder))
        self.btn_folder = QPushButton("Examinar carpeta…")
        self.btn_folder.setToolTip(
            "Al elegir carpeta se listan aquí los .txt RIPS encontrados antes de confirmar."
        )
        folder_row.addWidget(self.folder_edit, stretch=1)
        folder_row.addWidget(self.btn_folder)
        folder_layout.addLayout(folder_row)
        layout.addWidget(folder_box)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self.lbl_info = QLabel("")
        layout.addWidget(self.lbl_info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.rb_zip.toggled.connect(self._sync_mode)
        self.btn_zip.clicked.connect(self._browse_zip)
        self.btn_folder.clicked.connect(self._browse_folder)
        self.folder_edit.editingFinished.connect(self._reload_folder_list)
        self._sync_mode()

    def _sync_mode(self) -> None:
        self._mode_zip = self.rb_zip.isChecked()
        self.zip_edit.setEnabled(self._mode_zip)
        self.btn_zip.setEnabled(self._mode_zip)
        self.folder_edit.setEnabled(not self._mode_zip)
        self.btn_folder.setEnabled(not self._mode_zip)
        if self._mode_zip and self._zip_path:
            self._show_zip_preview()
        else:
            self._reload_folder_list()

    def _browse_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar ZIP RIPS",
            str(self._folder),
            "ZIP (*.zip)",
        )
        if path:
            self._zip_path = Path(path)
            self.zip_edit.setText(path)
            self._show_zip_preview()

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta — revise los .txt listados antes de Aceptar",
            self.folder_edit.text() or str(self._folder),
        )
        if path:
            self.folder_edit.setText(path)
            self._reload_folder_list()

    def _show_zip_preview(self) -> None:
        self.list_widget.clear()
        if not self._zip_path or not self._zip_path.is_file():
            self.lbl_info.setText("Seleccione un archivo ZIP.")
            return
        import zipfile

        types: list[str] = []
        try:
            with zipfile.ZipFile(self._zip_path, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    name = Path(info.filename).name
                    if not name.lower().endswith(".txt"):
                        continue
                    ftype = file_type_from_name(name)
                    label = f"{name}  [{ftype or '???'}]"
                    item = QListWidgetItem(label)
                    if not ftype:
                        item.setForeground(QColor("#b8860b"))
                    else:
                        types.append(ftype)
                    self.list_widget.addItem(item)
        except zipfile.BadZipFile:
            self.lbl_info.setText("ZIP inválido.")
            return
        self.lbl_info.setText(
            f"ZIP: {self._zip_path.name} | Archivos .txt RIPS: {len(types)} tipos detectados"
        )

    def _reload_folder_list(self) -> None:
        self.list_widget.clear()
        folder = Path(self.folder_edit.text().strip() or ".")
        self._folder = folder
        if not folder.is_dir():
            self.lbl_info.setText("Ruta de carpeta no válida.")
            return
        paths = list_matching_txt_in_folder(folder)
        for path in paths:
            ftype = file_type_from_name(path.name) or "??"
            item = QListWidgetItem(f"{path.name}  [{ftype}]")
            item.setData(Qt.ItemDataRole.UserRole, str(path.resolve()))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list_widget.addItem(item)
        if not paths:
            self.lbl_info.setText(
                "No hay archivos .txt RIPS en esta carpeta. Elija otra carpeta."
            )
        else:
            types = sorted({file_type_from_name(p.name) for p in paths if file_type_from_name(p.name)})
            self.lbl_info.setText(
                f"Carpeta: {folder} | Archivos: {len(paths)} | Tipos: {', '.join(types)}"
            )

    def _on_accept(self) -> None:
        if self._mode_zip:
            if not self._zip_path or not self._zip_path.is_file():
                self.lbl_info.setText("Debe seleccionar un ZIP válido.")
                return
            if self.list_widget.count() == 0:
                self.lbl_info.setText("El ZIP no contiene archivos .txt RIPS.")
                return
        else:
            if self.list_widget.count() == 0:
                self.lbl_info.setText("No hay archivos para cargar. Cambie de carpeta.")
                return
        self.accept()

    def is_zip_mode(self) -> bool:
        return self._mode_zip

    def zip_path(self) -> Path | None:
        return self._zip_path

    def folder_path(self) -> Path:
        return Path(self.folder_edit.text().strip())

    def selected_txt_paths(self) -> list[Path]:
        paths: list[Path] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                p = item.data(Qt.ItemDataRole.UserRole)
                if p:
                    paths.append(Path(p))
        return paths
