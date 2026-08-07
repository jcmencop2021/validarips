from __future__ import annotations

import sys
from datetime import datetime
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.dedupe import dedupe_documents, dedupe_path_strings, dedupe_records
from core.excel_export import ensure_template, export_to_excel
from core.factura_index import FacturaIndex, is_rips_payload
from core.date_fmt import DATE_PLACEHOLDER, format_date_display, normalize_typed_date
from core.loader import (
    build_records_from_rips,
    discover_json_paths,
    load_json_file,
    reload_records_with_facturas,
)
from core.grid_prefs import attach_column_width_persistence
from core.prestadores import PrestadoresCatalog, load_prestadores_catalog
from core.paths import get_module_root, template_path
from core.version import BUILD_ID, get_version
from core.validator import ValidationReport, validate_all
from models.relation_record import ADMIN_FIELDS, RELATION_COLUMNS, RelationRecord
from ui.country_delegate import CountryComboDelegate
from ui.date_delegate import GRID_DATE_COLUMNS, DateLineDelegate
from ui.factura_select_dialog import FacturaSelectDialog
from ui.json_select_dialog import RipsFolderDialog
from ui.relation_table import RelationTable

APP_ROOT = get_module_root()

# Anchos iniciales (px): fechas/periodo angostos, nombres amplios
COL_WIDTH: dict[str, int] = {
    "CAJA": 46,
    "RADICADO": 64,
    "FECHA RADICADO": 76,
    "PERIODO FACTURADO": 62,
    "Fecha factura": 76,
    "FECHAING": 76,
    "FECHAFIN": 76,
    "CodIps": 64,
    "NombreIps": 175,
    "NroFac": 78,
    "TipoIde": 46,
    "NumIde": 88,
    "Nombre": 220,
    "VlorNeto": 68,
    "SERVICIO": 58,
    "REL": 36,
    "NACION": 76,
}
COL_EXPORT_WIDTH = 48
ADMIN_FIELD_WIDTH: dict[str, int] = {
    "CAJA": 72,
    "REL": 56,
    "RADICADO": 88,
    "FECHA RADICADO": 92,
    "PERIODO FACTURADO": 72,
}


class SessionEndReason(Enum):
    HOME = "home"
    EXIT = "exit"


class MainWindow948(QMainWindow):
    COL_EXPORT = 0
    session_ended = Signal(object)  # SessionEndReason

    def __init__(self) -> None:
        super().__init__()
        self._closing_for_home = False
        self._app_version = get_version()
        self.setWindowTitle(f"Módulo RIPS — Relación Res. 948 — v{self._app_version}")
        self.resize(1320, 860)

        self._last_folder = ""
        self.factura_index = FacturaIndex()
        self.prestadores = PrestadoresCatalog()
        self._ingested_factura_files: set[str] = set()
        self._json_path_by_source: dict[str, Path] = {}
        self.records: list[RelationRecord] = []
        self.documents: list[tuple[str, dict, list[RelationRecord]]] = []
        self.validation_report: ValidationReport | None = None
        self.loaded_files: list[Path] = []
        self._grid_profile = "948"

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.lbl_version_banner = QLabel(
            f"  VERSIÓN {self._app_version} — {BUILD_ID}  |  Módulo: {APP_ROOT}"
        )
        self.lbl_version_banner.setStyleSheet(
            "background-color: #e65100; color: white; font-weight: bold; padding: 8px;"
        )
        layout.addWidget(self.lbl_version_banner)

        btn_row = QHBoxLayout()
        self.btn_inicio = QPushButton("Cambiar normativa (inicio)")
        self.btn_inicio.setToolTip(
            "Vuelve a la pantalla inicial para elegir Resolución 948 (JSON) o 3374 (TXT/ZIP) "
            "sin cerrar el programa."
        )
        self.btn_inicio.setStyleSheet("font-weight: bold;")
        btn_row.addWidget(self.btn_inicio)
        self.btn_buscar = QPushButton("Buscar RIPS (JSON)")
        self.btn_carpeta = QPushButton("Buscar carpeta")
        self.btn_factura = QPushButton("Cargar datos factura")
        self.btn_prestadores = QPushButton("Catálogo prestadores")
        self.btn_validar = QPushButton("Validar")
        self.btn_ver_informe = QPushButton("Ver resultado / errores")
        self.btn_exportar = QPushButton("Exportar Excel")
        self.btn_descargar = QPushButton("Descargar informe")
        self._tooltips = {
            self.btn_buscar: (
                "Abre el selector de carpeta y archivos JSON RIPS para cargarlos en la grilla."
            ),
            self.btn_carpeta: (
                "Igual que «Buscar RIPS»: elige la carpeta de trabajo y marca los archivos .json a importar."
            ),
            self.btn_factura: (
                "Carga XML o JSON de factura electrónica (FEV) para completar fecha de factura, "
                "nombre de la IPS y nombre del paciente cuando el RIPS no los trae."
            ),
            self.btn_prestadores: (
                "Carga un Excel o CSV con NIT y nombre de prestadores para completar la columna NombreIps."
            ),
            self.btn_validar: (
                "Valida los archivos RIPS cargados según la Resolución 948 y muestra el resultado abajo."
            ),
            self.btn_ver_informe: (
                "Abre una ventana con el detalle del último informe de validación (errores y advertencias)."
            ),
            self.btn_exportar: (
                "Genera el archivo Excel de relación solo con las filas que tienen marcado «Aplicar»."
            ),
            self.btn_descargar: (
                "Guarda el informe de validación RIPS en un archivo de texto (.txt)."
            ),
        }
        for btn in (
            self.btn_buscar,
            self.btn_carpeta,
            self.btn_factura,
            self.btn_prestadores,
            self.btn_validar,
            self.btn_ver_informe,
            self.btn_exportar,
            self.btn_descargar,
        ):
            btn_row.addWidget(btn)
        for btn, tip in self._tooltips.items():
            btn.setToolTip(tip)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.btn_inicio.clicked.connect(self.on_volver_pantalla_inicio)
        self.btn_buscar.clicked.connect(self.on_buscar_archivos)
        self.btn_carpeta.clicked.connect(self.on_buscar_carpeta)
        self.btn_factura.clicked.connect(self.on_cargar_facturas)
        self.btn_prestadores.clicked.connect(self.on_cargar_prestadores)
        self.btn_validar.clicked.connect(self.on_validar)
        self.btn_ver_informe.clicked.connect(self.on_ver_informe)
        self.btn_exportar.clicked.connect(self.on_exportar)
        self.btn_descargar.clicked.connect(self.on_descargar_informe)

        status_box = QGroupBox("Estado")
        status_layout = QHBoxLayout(status_box)
        self.lbl_facturas = QLabel("Facturas: 0")
        self.lbl_pacientes = QLabel("Registros: 0")
        self.lbl_total = QLabel("Valor total: 0")
        self.lbl_export = QLabel("Marcados Excel: 0")
        self.lbl_factura_idx = QLabel("Facturas (datos FEV): 0")
        self.lbl_prestadores = QLabel("Prestadores: 0")
        self.lbl_resultado = QLabel("Resultado RIPS: —")
        self.lbl_resultado.setStyleSheet("font-weight: bold;")
        for w in (
            self.lbl_facturas,
            self.lbl_pacientes,
            self.lbl_total,
            self.lbl_export,
            self.lbl_factura_idx,
            self.lbl_prestadores,
            self.lbl_resultado,
        ):
            status_layout.addWidget(w)
        status_layout.addStretch()
        layout.addWidget(status_box)

        header_box = QGroupBox("Datos administrativos (comunes)")
        header_row = QHBoxLayout(header_box)
        self.admin_inputs: dict[str, QLineEdit] = {}
        labels = {
            "CAJA": "Caja",
            "REL": "REL",
            "RADICADO": "Radicado",
            "FECHA RADICADO": "F. radicado",
            "PERIODO FACTURADO": "Periodo",
        }
        for field in ADMIN_FIELDS:
            col = QVBoxLayout()
            lbl = QLabel(labels.get(field, field))
            edit = QLineEdit()
            w = ADMIN_FIELD_WIDTH.get(field, 88)
            edit.setMaximumWidth(w)
            if field == "FECHA RADICADO":
                edit.setPlaceholderText(DATE_PLACEHOLDER)
            self.admin_inputs[field] = edit
            col.addWidget(lbl)
            col.addWidget(edit)
            header_row.addLayout(col)
        header_row.addStretch()
        self.btn_aplicar_todos = QPushButton("Aplicar a todos")
        self.btn_aplicar_todos.setMaximumWidth(120)
        self.btn_aplicar_todos.setToolTip(
            "Copia Caja, REL, Radicado, fecha radicado y periodo del encabezado a todas las filas, "
            "las marca con «Aplicar» y las incluye en la exportación a Excel."
        )
        self.btn_aplicar_todos.clicked.connect(self.on_aplicar_todos)
        header_row.addWidget(self.btn_aplicar_todos)
        layout.addWidget(header_box)

        self.table = RelationTable(0, 1 + len(RELATION_COLUMNS))
        grid_font = QFont(self.table.font())
        grid_font.setPointSize(8)
        self.table.setFont(grid_font)
        hdr = self.table.horizontalHeader()
        hdr_font = QFont(hdr.font())
        hdr_font.setPointSize(8)
        hdr.setFont(hdr_font)
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        headers = ["Aplicar"] + RELATION_COLUMNS
        self.table.setHorizontalHeaderLabels(headers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        self.table.setColumnWidth(self.COL_EXPORT, COL_EXPORT_WIDTH)
        for name, width in COL_WIDTH.items():
            if name in RELATION_COLUMNS:
                col_idx = 1 + RELATION_COLUMNS.index(name)
                self.table.setColumnWidth(col_idx, width)
        self.table.setAlternatingRowColors(True)
        self.table.setToolTip(
            "Grilla de relación. Un clic en una celda para editar. "
            "Columna Aplicar: marca para exportar (aplica el encabezado); al desmarcar revierte esos datos. "
            "Ctrl+C copia la selección para pegar en Excel."
        )
        self.table.cellChanged.connect(self.on_cell_changed)
        self._date_delegate = DateLineDelegate(self.table)
        for col_name in GRID_DATE_COLUMNS:
            if col_name in RELATION_COLUMNS:
                col_idx = 1 + RELATION_COLUMNS.index(col_name)
                self.table.setItemDelegateForColumn(col_idx, self._date_delegate)
        if "NACION" in RELATION_COLUMNS:
            nacion_col = 1 + RELATION_COLUMNS.index("NACION")
            self.table.setItemDelegateForColumn(
                nacion_col, CountryComboDelegate(self.table)
            )
        attach_column_width_persistence(self.table, self._grid_profile)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.table)

        result_box = QGroupBox("Resultado RIPS")
        result_layout = QVBoxLayout(result_box)
        self.txt_validacion = QTextEdit()
        self.txt_validacion.setReadOnly(True)
        self.txt_validacion.setPlaceholderText("Resultado de validación RIPS…")
        self.txt_validacion.setMinimumHeight(220)
        result_layout.addWidget(self.txt_validacion)
        splitter.addWidget(result_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self._main_splitter = splitter
        layout.addWidget(splitter, stretch=1)

    def _show_validation_panel(self, body: str, status: str, title_prefix: str) -> None:
        stamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        text = f"Última validación: {stamp}\nEstado: {status}\n{'—' * 40}\n{body}"
        self.txt_validacion.setPlainText(text)
        cursor = self.txt_validacion.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.txt_validacion.setTextCursor(cursor)
        self.lbl_resultado.setText(f"{title_prefix}: {status}")
        color = {"OK": "#1b7f3a", "ADVERTENCIA": "#b8860b", "ERROR": "#b00020"}.get(
            status, "#333"
        )
        self.lbl_resultado.setStyleSheet(f"font-weight: bold; color: {color};")
        if hasattr(self, "_main_splitter"):
            total = sum(self._main_splitter.sizes()) or 900
            self._main_splitter.setSizes([int(total * 0.52), int(total * 0.48)])

    def on_volver_pantalla_inicio(self) -> None:
        reply = QMessageBox.question(
            self,
            "Cambiar normativa",
            "¿Volver a la pantalla inicial?\n\n"
            "Podrá elegir de nuevo Resolución 948 (JSON) o 3374 (TXT/ZIP). "
            "Los datos cargados en esta ventana no se guardan automáticamente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._closing_for_home = True
        self.session_ended.emit(SessionEndReason.HOME)
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._closing_for_home:
            super().closeEvent(event)
            return
        reply = QMessageBox.question(
            self,
            "Cerrar programa",
            "¿Salir del Módulo RIPS?\n\n"
            "Use «Cambiar normativa (inicio)» si desea pasar a 948 o 3374 sin salir.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.session_ended.emit(SessionEndReason.EXIT)
            super().closeEvent(event)
        else:
            event.ignore()

    def _admin_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key, widget in self.admin_inputs.items():
            text = widget.text().strip()
            if key == "FECHA RADICADO" and text:
                text = normalize_typed_date(text)
            values[key] = text
        return values

    def _display_cell_value(self, col_name: str, value: object) -> str:
        if value is None:
            return ""
        text = str(value)
        if col_name in GRID_DATE_COLUMNS:
            return format_date_display(text)
        return text

    def _open_rips_picker(self) -> list[str]:
        dialog = RipsFolderDialog(self._last_folder, self)
        if dialog.exec() != RipsFolderDialog.DialogCode.Accepted:
            return []
        folder = dialog.folder()
        if folder:
            self._last_folder = folder
        return dialog.selected_paths()

    def on_buscar_archivos(self) -> None:
        selected = self._open_rips_picker()
        if selected:
            self._load_paths(selected)

    def on_buscar_carpeta(self) -> None:
        selected = self._open_rips_picker()
        if selected:
            self._load_paths(selected)

    def on_cargar_prestadores(self) -> None:
        start = self._last_folder or str(APP_ROOT.parent)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de prestadores (NIT / nombre IPS)",
            start,
            "Excel/CSV (*.xlsx *.xlsm *.csv *.txt)",
        )
        if not path:
            return
        self.prestadores = PrestadoresCatalog()
        count = self.prestadores.load_file(Path(path))
        if count == 0:
            QMessageBox.warning(
                self,
                "Catálogo prestadores",
                "No se leyeron filas. Revise columnas NIT y nombre/razón social.",
            )
            return
        self.lbl_prestadores.setText(
            f"Prestadores: {len(self.prestadores)} filas ({Path(path).name})"
        )
        if self.documents:
            self._apply_factura_index_to_grid()
        QMessageBox.information(
            self,
            "Prestadores cargados",
            f"Se cargaron {count} filas desde:\n{path}",
        )

    def on_cargar_facturas(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Carpeta con XML/JSON de factura electrónica",
            self._last_folder or str(Path.home()),
        )
        if not folder:
            return
        self._last_folder = folder
        dialog = FacturaSelectDialog(Path(folder), self)
        if dialog.exec() != FacturaSelectDialog.DialogCode.Accepted:
            return
        selected = dialog.selected_paths()
        if not selected:
            return
        new_files = [p for p in selected if p not in self._ingested_factura_files]
        if not new_files:
            QMessageBox.information(
                self,
                "Sin archivos nuevos",
                "Esos archivos de factura ya estaban cargados.",
            )
            return
        self.factura_index.ingest_paths(new_files)
        self._ingested_factura_files.update(new_files)
        self._apply_factura_index_to_grid()
        QMessageBox.information(
            self,
            "Facturas cargadas",
            f"Índice de facturas: {len(self.factura_index)} registro(s).\n"
            "Se actualizó la grilla con fecha, IPS y nombres disponibles.",
        )

    def _apply_factura_index_to_grid(self) -> None:
        if not self.documents:
            return
        self.records, self.documents = reload_records_with_facturas(
            self.documents,
            self._json_path_by_source,
            self.factura_index,
            self.prestadores,
        )
        self._refresh_table()
        self._update_stats()
        self.lbl_factura_idx.setText(f"Facturas (datos FEV): {len(self.factura_index)}")

    def _load_paths(self, paths: list[str]) -> None:
        paths = dedupe_path_strings(paths)
        json_paths = discover_json_paths(paths, rips_only=False)
        if not json_paths:
            QMessageBox.warning(self, "Sin archivos", "No se encontraron archivos .json.")
            return

        seen_files: set[str] = set()
        unique_json_paths: list[Path] = []
        for jp in json_paths:
            key = str(jp.resolve())
            if key in seen_files:
                continue
            seen_files.add(key)
            unique_json_paths.append(jp)
        json_paths = unique_json_paths

        self.records.clear()
        self.documents.clear()
        self._json_path_by_source.clear()
        self.loaded_files = json_paths
        skipped_dupes = max(0, len(paths) - len(json_paths))

        work_dirs: set[Path] = {APP_ROOT, Path.cwd()}
        if self._last_folder:
            work_dirs.add(Path(self._last_folder))
        for jp in json_paths:
            work_dirs.add(jp.parent)
            work_dirs.add(jp.parent.parent)
        self.prestadores = load_prestadores_catalog(work_dirs)
        if self.prestadores.source_file:
            self.lbl_prestadores.setText(
                f"Prestadores: {len(self.prestadores)} filas ({Path(self.prestadores.source_file).name})"
            )
        else:
            self.lbl_prestadores.setText("Prestadores: no se encontró docs/")

        directories = {jp.parent for jp in json_paths}
        self.factura_index.scan_directories(directories)

        failed_rips: list[str] = []
        for jp in json_paths:
            data, err = load_json_file(jp)
            source = jp.name
            self._json_path_by_source[source] = jp
            if err or not isinstance(data, dict) or not is_rips_payload(data):
                failed_rips.append(source)
                self.documents.append((source, {}, []))
                continue
            recs = build_records_from_rips(
                data, source, jp, self.factura_index, self.prestadores
            )
            if not recs:
                continue
            self.records.extend(recs)
            self.documents.append((source, data, recs))

        self.records, skipped_rows = dedupe_records(self.records)
        skipped_dupes += skipped_rows
        self.documents, skipped_docs = dedupe_documents(self.documents)
        skipped_dupes += skipped_docs

        self.validation_report = None
        self.lbl_resultado.setText("Resultado RIPS: — (pendiente validar)")
        self.lbl_resultado.setStyleSheet("font-weight: bold; color: #333;")
        self.txt_validacion.clear()
        self._refresh_table()
        self._update_stats()
        self.lbl_factura_idx.setText(f"Facturas (datos FEV): {len(self.factura_index)}")
        QMessageBox.information(
            self,
            "Carga completada",
            f"Versión módulo: {self._app_version}\n"
            f"Archivos RIPS cargados: {len(self._json_path_by_source)}\n"
            f"Registros en grilla: {len(self.records)}\n"
            f"Prestadores en índice: {len(self.prestadores)}"
            + (f"\nDuplicados omitidos: {skipped_dupes}" if skipped_dupes else "")
            + (
                f"\n\nArchivos no RIPS (omitidos): {', '.join(failed_rips)}"
                if failed_rips
                else ""
            ),
        )

    def _refresh_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.records))
        for row, rec in enumerate(self.records):
            export_item = QTableWidgetItem()
            export_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
            export_item.setCheckState(
                Qt.CheckState.Checked if rec.export_selected else Qt.CheckState.Unchecked
            )
            self.table.setItem(row, self.COL_EXPORT, export_item)

            for col, name in enumerate(RELATION_COLUMNS, start=1):
                value = rec.values.get(name, "")
                display = self._display_cell_value(name, value)
                item = QTableWidgetItem(display)
                if name in ADMIN_FIELDS and rec.admin_applied:
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                    item.setBackground(QColor(230, 230, 230))
                else:
                    item.setFlags(
                        Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsEditable
                        | Qt.ItemFlag.ItemIsEnabled
                    )
                self.table.setItem(row, col, item)
        self.table.blockSignals(False)

    def _apply_admin_to_row(self, row: int) -> bool:
        """Copia encabezado administrativo a la fila. Devuelve False si no hay datos."""
        admin = self._admin_values()
        if not any(admin.values()):
            QMessageBox.warning(
                self,
                "Datos vacíos",
                "Complete los campos del encabezado (Caja, REL, Radicado, etc.) antes de aplicar.",
            )
            return False
        self.records[row].apply_admin(admin)
        return True

    def on_cell_changed(self, row: int, column: int) -> None:
        if row < 0 or row >= len(self.records):
            return
        if column == self.COL_EXPORT:
            item = self.table.item(row, self.COL_EXPORT)
            if item is None:
                return
            checked = item.checkState() == Qt.CheckState.Checked
            if checked:
                if self._apply_admin_to_row(row):
                    self.records[row].export_selected = True
                    self._refresh_table()
                else:
                    self.table.blockSignals(True)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    self.records[row].export_selected = False
                    self.table.blockSignals(False)
            else:
                self.records[row].revert_admin()
                self._refresh_table()
            self._update_stats()
            return
        if column > 0:
            col_name = RELATION_COLUMNS[column - 1]
            cell = self.table.item(row, column)
            if cell:
                text = cell.text()
                if col_name in GRID_DATE_COLUMNS:
                    text = normalize_typed_date(text)
                    if text != cell.text():
                        self.table.blockSignals(True)
                        cell.setText(text)
                        self.table.blockSignals(False)
                self.records[row].values[col_name] = text

    def on_aplicar_todos(self) -> None:
        admin = self._admin_values()
        if not any(admin.values()):
            QMessageBox.warning(self, "Datos vacíos", "Ingrese los datos administrativos.")
            return
        for rec in self.records:
            rec.apply_admin(admin)
            rec.export_selected = True
        self._refresh_table()

    def on_validar(self) -> None:
        if not self.documents:
            QMessageBox.warning(self, "Sin datos", "Cargue archivos RIPS JSON primero.")
            return
        self.btn_validar.setEnabled(False)
        prev_label = self.btn_validar.text()
        self.btn_validar.setText("Validando…")
        self.txt_validacion.setPlainText("Validando archivos RIPS… por favor espere.")
        QApplication.processEvents()
        try:
            self.validation_report = validate_all(self.documents)
            self._show_validation_panel(
                self.validation_report.summary_text(),
                self.validation_report.status_label,
                "Resultado RIPS",
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Error al validar",
                f"La validación no pudo completarse:\n{exc}",
            )
            self.txt_validacion.setPlainText(f"Error al validar:\n{exc}")
        finally:
            self.btn_validar.setEnabled(True)
            self.btn_validar.setText(prev_label)

    def on_ver_informe(self) -> None:
        if not self.validation_report:
            self.on_validar()
        if self.validation_report:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Informe de validación RIPS")
            dlg.setText(self.validation_report.status_label)
            dlg.setDetailedText(self.validation_report.summary_text())
            dlg.exec()

    def on_descargar_informe(self) -> None:
        if not self.validation_report:
            self.on_validar()
        if not self.validation_report:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar informe de validación",
            "informe_validacion_rips.txt",
            "Texto (*.txt)",
        )
        if path:
            Path(path).write_text(self.validation_report.to_file_text(), encoding="utf-8")
            QMessageBox.information(self, "Informe", f"Informe guardado en:\n{path}")

    def _update_stats(self) -> None:
        facturas = {r.values.get("NroFac") for r in self.records if r.values.get("NroFac")}
        total = 0.0
        marked = 0
        for r in self.records:
            if r.export_selected:
                marked += 1
                try:
                    total += float(r.values.get("VlorNeto") or 0)
                except (TypeError, ValueError):
                    pass
        self.lbl_facturas.setText(f"Facturas: {len(facturas)}")
        self.lbl_pacientes.setText(f"Registros: {len(self.records)}")
        self.lbl_total.setText(f"Valor total marcados: {total:,.0f}")
        self.lbl_export.setText(f"Marcados Excel: {marked}")

    def on_exportar(self) -> None:
        selected, _ = dedupe_records([r for r in self.records if r.export_selected])
        if not selected:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Marque la columna Aplicar en cada fila (copia el encabezado y la incluye en Excel), "
                "o use Aplicar a todos.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar relación Excel",
            "relacion_rips.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        template = template_path()
        ensure_template(template)
        export_to_excel(selected, Path(path), template)
        QMessageBox.information(
            self,
            "Exportación",
            f"Archivo Excel generado con {len(selected)} registro(s):\n{path}",
        )


def run_948() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow948()
    window.show()
    if QApplication.instance() is None:
        sys.exit(app.exec())


# Compatibilidad
MainWindow = MainWindow948


def run() -> None:
    run_948()


if __name__ == "__main__":
    run()
