from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QDateEdit,
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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.dedupe import dedupe_documents, dedupe_path_strings, dedupe_records
from core.excel_export import ensure_template, export_to_excel
from core.factura_index import FacturaIndex, is_rips_payload
from core.date_fmt import DISPLAY_FMT
from core.loader import (
    build_records_from_rips,
    discover_json_paths,
    load_json_file,
    reload_records_with_facturas,
)
from core.prestadores import PrestadoresCatalog, load_prestadores_catalog
from core.version import BUILD_ID, get_version
from core.validator import ValidationReport, validate_all
from models.relation_record import ADMIN_FIELDS, RELATION_COLUMNS, RelationRecord
from ui.factura_select_dialog import FacturaSelectDialog
from ui.json_select_dialog import DateTableDelegate, GRID_DATE_COLUMNS, RipsFolderDialog

APP_ROOT = Path(__file__).resolve().parent.parent
FIELD_WIDTH = 110


class MainWindow(QMainWindow):
    COL_EXPORT = 0

    def __init__(self) -> None:
        super().__init__()
        self._app_version = get_version()
        self.setWindowTitle(f"Módulo RIPS — Relación Res. 948 — v{self._app_version}")
        self.resize(1280, 860)

        self._last_folder = ""
        self.factura_index = FacturaIndex()
        self.prestadores = PrestadoresCatalog()
        self._ingested_factura_files: set[str] = set()
        self._json_path_by_source: dict[str, Path] = {}
        self.records: list[RelationRecord] = []
        self.documents: list[tuple[str, dict, list[RelationRecord]]] = []
        self.validation_report: ValidationReport | None = None
        self.loaded_files: list[Path] = []

        self._build_ui()
        self._show_version_banner()

    def _show_version_banner(self) -> None:
        QMessageBox.information(
            self,
            f"Versión {self._app_version}",
            f"Módulo instalado desde:\n{APP_ROOT}\n\n"
            f"Build: {BUILD_ID}\n\n"
            "Si no ve el cartel naranja arriba con la misma versión,\n"
            "está ejecutando una carpeta antigua. Lea LEEME_ACTUALIZACION.txt",
        )

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
        self.btn_buscar = QPushButton("Buscar RIPS (JSON)")
        self.btn_carpeta = QPushButton("Buscar carpeta")
        self.btn_factura = QPushButton("Cargar datos factura")
        self.btn_prestadores = QPushButton("Catálogo prestadores")
        self.btn_validar = QPushButton("Validar")
        self.btn_ver_informe = QPushButton("Ver resultado / errores")
        self.btn_exportar = QPushButton("Exportar Excel")
        self.btn_descargar = QPushButton("Descargar informe")
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
        btn_row.addStretch()
        layout.addLayout(btn_row)

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
            if field == "FECHA RADICADO":
                edit: QLineEdit | QDateEdit = QDateEdit()
                edit.setCalendarPopup(True)
                edit.setDisplayFormat(DISPLAY_FMT)
                edit.setMaximumWidth(130)
            else:
                edit = QLineEdit()
                edit.setMaximumWidth(FIELD_WIDTH)
            self.admin_inputs[field] = edit
            col.addWidget(lbl)
            col.addWidget(edit)
            header_row.addLayout(col)
        header_row.addStretch()
        self.btn_aplicar_todos = QPushButton("Aplicar a todos")
        self.btn_aplicar_todos.setMaximumWidth(120)
        self.btn_aplicar_todos.clicked.connect(self.on_aplicar_todos)
        header_row.addWidget(self.btn_aplicar_todos)
        layout.addWidget(header_box)

        self.table = QTableWidget(0, 1 + len(RELATION_COLUMNS))
        headers = ["Aplicar"] + RELATION_COLUMNS
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.cellChanged.connect(self.on_cell_changed)
        self._date_delegate = DateTableDelegate(self.table)
        for col_name in GRID_DATE_COLUMNS:
            if col_name in RELATION_COLUMNS:
                col_idx = 1 + RELATION_COLUMNS.index(col_name)
                self.table.setItemDelegateForColumn(col_idx, self._date_delegate)
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
        layout.addWidget(splitter, stretch=1)

    def _admin_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key, widget in self.admin_inputs.items():
            if isinstance(widget, QDateEdit):
                values[key] = widget.date().toString(DISPLAY_FMT)
            else:
                values[key] = widget.text().strip()
        return values

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
                item = QTableWidgetItem("" if value is None else str(value))
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
        if "Nombre" in RELATION_COLUMNS:
            nombre_col = 1 + RELATION_COLUMNS.index("Nombre")
            self.table.setColumnWidth(nombre_col, 360)
        if "NombreIps" in RELATION_COLUMNS:
            ips_col = 1 + RELATION_COLUMNS.index("NombreIps")
            self.table.setColumnWidth(ips_col, 300)
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
                self.records[row].export_selected = False
            self._update_stats()
            return
        if column > 0:
            col_name = RELATION_COLUMNS[column - 1]
            cell = self.table.item(row, column)
            if cell:
                self.records[row].values[col_name] = cell.text()

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
        self.validation_report = validate_all(self.documents)
        self.txt_validacion.setPlainText(self.validation_report.summary_text())
        status = self.validation_report.status_label
        self.lbl_resultado.setText(f"Resultado RIPS: {status}")
        color = {"OK": "#1b7f3a", "ADVERTENCIA": "#b8860b", "ERROR": "#b00020"}.get(
            status, "#333"
        )
        self.lbl_resultado.setStyleSheet(f"font-weight: bold; color: {color};")

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
        template = APP_ROOT / "templates" / "plantilla_relacion.xlsx"
        ensure_template(template)
        export_to_excel(selected, Path(path), template)
        QMessageBox.information(
            self,
            "Exportación",
            f"Archivo Excel generado con {len(selected)} registro(s):\n{path}",
        )


def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
