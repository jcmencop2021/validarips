from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
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
    display_path_under_root,
    file_type_from_name,
    list_txt_in_folder_for_preview,
    normalize_folder_path,
    scan_folder_warning,
)


class _FolderScanThread(QThread):
    done = Signal(list)
    error = Signal(str)

    def __init__(self, folder: Path) -> None:
        super().__init__()
        self._folder = folder

    def run(self) -> None:
        try:
            paths = list_txt_in_folder_for_preview(self._folder)
            self.done.emit([str(p.resolve()) for p in paths])
        except Exception as exc:  # noqa: BLE001 — informar al usuario
            self.error.emit(str(exc))


class Rips3374LoadDialog(QDialog):
    """ZIP o carpeta con .txt RIPS; vista previa antes de confirmar."""

    def __init__(self, start_folder: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cargar RIPS Res. 3374 — TXT o ZIP")
        self.resize(700, 520)
        self._browse_start = start_folder.strip() or str(Path.home())
        self._zip_path: Path | None = None
        self._mode_zip = True
        self._scan_thread: _FolderScanThread | None = None
        self._scanned_folder: Path | None = None

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
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.rb_zip)
        self._mode_group.addButton(self.rb_folder)
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
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText(
            "Pulse «Examinar carpeta…» (ej. D:\\rips\\…\\9959) — no use su carpeta de usuario."
        )
        self.btn_folder = QPushButton("Examinar carpeta…")
        self.btn_folder.setToolTip(
            "Elija la carpeta de la remisión; luego se listan los CT/AF/US… sin bloquear la ventana."
        )
        self.btn_refresh = QPushButton("Volver a listar")
        self.btn_refresh.setToolTip("Vuelve a buscar archivos en la ruta mostrada arriba.")
        folder_row.addWidget(self.folder_edit, stretch=1)
        folder_row.addWidget(self.btn_folder)
        folder_row.addWidget(self.btn_refresh)
        folder_layout.addLayout(folder_row)
        layout.addWidget(folder_box)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self.lbl_info = QLabel("")
        layout.addWidget(self.lbl_info)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.rb_zip.toggled.connect(self._sync_mode)
        self.btn_zip.clicked.connect(self._browse_zip)
        self.btn_folder.clicked.connect(self._browse_folder)
        self.btn_refresh.clicked.connect(self._reload_folder_list)
        self._sync_mode()

    def _set_busy(self, busy: bool) -> None:
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(not busy)
        self.rb_zip.setEnabled(not busy)
        self.rb_folder.setEnabled(not busy)
        self.btn_zip.setEnabled(not busy and self._mode_zip)
        self.btn_folder.setEnabled(not busy and not self._mode_zip)
        self.btn_refresh.setEnabled(not busy and not self._mode_zip)
        self.folder_edit.setEnabled(not busy and not self._mode_zip)

    def _sync_mode(self) -> None:
        self._mode_zip = self.rb_zip.isChecked()
        self.zip_edit.setEnabled(self._mode_zip)
        self.btn_zip.setEnabled(self._mode_zip)
        folder_on = not self._mode_zip
        self.folder_edit.setEnabled(folder_on)
        self.btn_folder.setEnabled(folder_on)
        self.btn_refresh.setEnabled(folder_on)
        if self._mode_zip:
            self._cancel_scan()
            if self._zip_path:
                self._show_zip_preview()
            else:
                self.list_widget.clear()
                self.lbl_info.setText("Seleccione un ZIP o elija «Carpeta con archivos .txt».")
        else:
            self.list_widget.clear()
            self.lbl_info.setText(
                "Modo carpeta: pulse «Examinar carpeta…» y seleccione la remisión "
                "(carpeta con CT9959.txt, AF9959.txt, …)."
            )

    def _cancel_scan(self) -> None:
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.requestInterruption()
            self._scan_thread.wait(2000)
        self._scan_thread = None
        self._set_busy(False)

    def _browse_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar ZIP RIPS",
            self._browse_start,
            "ZIP (*.zip)",
        )
        if path:
            self._zip_path = Path(path)
            self.zip_edit.setText(path)
            self._browse_start = str(Path(path).parent)
            self._show_zip_preview()

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de la remisión RIPS (CTxxxx.txt)",
            self.folder_edit.text().strip() or self._browse_start,
        )
        if path:
            self.folder_edit.setText(path)
            self._browse_start = path
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
                    if not name.lower().endswith(".txt") and not (
                        file_type_from_name(name) and Path(name).suffix == ""
                    ):
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
        if self._mode_zip:
            return
        self._cancel_scan()
        self.list_widget.clear()
        folder = normalize_folder_path(self.folder_edit.text())
        if folder is None or not folder.is_dir():
            self.lbl_info.setText(
                f"No se puede abrir la carpeta:\n{self.folder_edit.text().strip()}"
            )
            return
        warn = scan_folder_warning(folder)
        if warn:
            self.lbl_info.setText(warn)
            return
        self._scanned_folder = folder
        self.folder_edit.setText(str(folder))
        self.lbl_info.setText(f"Buscando archivos RIPS en:\n{folder}\n(un momento…)")
        self._set_busy(True)
        self._scan_thread = _FolderScanThread(folder)
        self._scan_thread.done.connect(self._on_scan_done)
        self._scan_thread.error.connect(self._on_scan_error)
        self._scan_thread.finished.connect(lambda: self._set_busy(False))
        self._scan_thread.start()

    def _on_scan_error(self, message: str) -> None:
        self.lbl_info.setText(f"Error al listar carpeta:\n{message}")

    def _on_scan_done(self, path_strs: list[str]) -> None:
        folder = self._scanned_folder
        if folder is None:
            return
        paths = [Path(p) for p in path_strs]
        recognized = 0
        for path in paths:
            ftype = file_type_from_name(path.name)
            rel = display_path_under_root(folder, path)
            label = f"{rel}  [{ftype or '???'}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(path.resolve()))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if ftype:
                item.setCheckState(Qt.CheckState.Checked)
                recognized += 1
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setForeground(QColor("#b8860b"))
            self.list_widget.addItem(item)
        if not paths:
            self.lbl_info.setText(
                f"No se encontraron archivos CT/AF/US… bajo:\n{folder}\n"
                "Compruebe que eligió la carpeta correcta (ej. …\\9959)."
            )
        elif recognized == 0:
            self.lbl_info.setText(
                f"{len(paths)} archivo(s) sin nombre RIPS (deben empezar por CT, AF, US, …)."
            )
        else:
            types = sorted(
                {file_type_from_name(p.name) for p in paths if file_type_from_name(p.name)}
            )
            self.lbl_info.setText(
                f"Raíz: {folder} | Archivos RIPS: {recognized} | Tipos: {', '.join(types)}"
            )

    def closeEvent(self, event) -> None:  # noqa: N802
        self._cancel_scan()
        super().closeEvent(event)

    def _on_accept(self) -> None:
        if self._scan_thread and self._scan_thread.isRunning():
            self.lbl_info.setText("Espere a que termine de listar la carpeta.")
            return
        if self._mode_zip:
            if not self._zip_path or not self._zip_path.is_file():
                self.lbl_info.setText("Debe seleccionar un ZIP válido.")
                return
            if self.list_widget.count() == 0:
                self.lbl_info.setText("El ZIP no contiene archivos .txt RIPS.")
                return
        else:
            if self.list_widget.count() == 0:
                self.lbl_info.setText(
                    "Pulse «Examinar carpeta…», elija la remisión y espere la lista."
                )
                return
            if not any(
                self.list_widget.item(i).checkState() == Qt.CheckState.Checked
                for i in range(self.list_widget.count())
            ):
                self.lbl_info.setText(
                    "Marque al menos un archivo .txt RIPS reconocido (CT, AF, US, …)."
                )
                return
        self.accept()

    def is_zip_mode(self) -> bool:
        return self._mode_zip

    def zip_path(self) -> Path | None:
        return self._zip_path

    def folder_path(self) -> Path:
        p = normalize_folder_path(self.folder_edit.text())
        return p if p is not None else Path(self.folder_edit.text().strip())

    def selected_txt_paths(self) -> list[Path]:
        paths: list[Path] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                p = item.data(Qt.ItemDataRole.UserRole)
                if p:
                    paths.append(Path(p))
        return paths
