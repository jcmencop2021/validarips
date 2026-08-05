from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.dedupe import dedupe_documents, dedupe_path_strings, dedupe_records
from core.excel_export import ensure_template, export_to_excel
from core.factura_index import FacturaIndex
from core.loader import (
    build_records_from_rips,
    discover_json_paths,
    load_json_file,
    reload_records_with_facturas,
)
from core.prestadores import PrestadoresCatalog, load_prestadores_catalog
from core.validator import ValidationReport, validate_all
from models.relation_record import ADMIN_FIELDS, RELATION_COLUMNS, RelationRecord
from ui.factura_select_dialog import FacturaSelectDialog
from ui.json_select_dialog import JsonSelectDialog

APP_ROOT = Path(__file__).resolve().parent.parent
FIELD_WIDTH = 110


class MainWindow(QMainWindow):
    COL_EXPORT = 0

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Módulo RIPS — Relación Resolución 948 v1.0")
        self.resize(1280, 800)

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

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        btn_row = QHBoxLayout()
        self.btn_buscar = QPushButton("Buscar RIPS (JSON)")
        self.btn_carpeta = QPushButton("Buscar carpeta")
        self.btn_factura = QPushButton("Cargar datos factura")
        self.btn_validar = QPushButton("Validar")
        self.btn_ver_informe = QPushButton("Ver resultado / errores")
        self.btn_exportar = QPushButton("Exportar Excel")
        self.btn_descargar = QPushButton("Descargar informe")
        for btn in (
            self.btn_buscar,
            self.btn_carpeta,
            self.btn_factura,
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
        layout.addWidget(self.table, stretch=1)

        self.txt_validacion = QTextEdit()
        self.txt_validacion.setReadOnly(True)
        self.txt_validacion.setPlaceholderText("Resultado de validación RIPS…")
        self.txt_validacion.setMaximumHeight(140)
        layout.addWidget(self.txt_validacion)

    def _admin_values(self) -> dict[str, str]:
        return {k: w.text().strip() for k, w in self.admin_inputs.items()}

    def _pick_folder(self, title: str) -> str:
        start = self._last_folder or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, title, start)
        if folder:
            self._last_folder = folder
        return folder

    def _select_json_from_folder(self, folder: str) -> list[str]:
        dialog = JsonSelectDialog(Path(folder), self)
        if dialog.exec() != JsonSelectDialog.DialogCode.Accepted:
            return []
        return dialog.selected_paths()

    def on_buscar_archivos(self) -> None:
        folder = self._pick_folder("Carpeta donde están los archivos RIPS JSON")
        if not folder:
            return
        selected = self._select_json_from_folder(folder)
        if selected:
            self._load_paths(selected)

    def on_buscar_carpeta(self) -> None:
        folder = self._pick_folder("Seleccionar carpeta con archivos JSON")
        if not folder:
            return
        selected = self._select_json_from_folder(folder)
        if selected:
            self._load_paths(selected)

    def on_cargar_facturas(self) -> None:
        folder = self._pick_folder("Carpeta con XML/JSON de factura electrónica")
        if not folder:
            return
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
        json_paths = discover_json_paths(paths)
        if not json_paths:
            QMessageBox.warning(self, "Sin archivos", "No se encontraron archivos RIPS (.json).")
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
        skipped_dupes = len(paths) - len(json_paths)

        work_dirs: set[Path] = set()
        for jp in json_paths:
            work_dirs.add(jp.parent)
            if jp.parent.name.lower() in ("rips", "json", "entrada"):
                work_dirs.add(jp.parent.parent)
        self.prestadores = load_prestadores_catalog(work_dirs)
        self.lbl_prestadores.setText(
            f"Prestadores: {len(self.prestadores)}"
            + (f" ({self.prestadores.source_file})" if self.prestadores.source_file else "")
        )

        directories = {jp.parent for jp in json_paths}
        self.factura_index.scan_directories(directories)

        for jp in json_paths:
            resolved = str(jp.resolve())
            if resolved in seen_files:
                skipped_dupes += 1
                continue
            seen_files.add(resolved)

            data, err = load_json_file(jp)
            source = jp.name
            self._json_path_by_source[source] = jp
            if err or not isinstance(data, dict):
                self.documents.append((source, {}, []))
                continue
            recs = build_records_from_rips(
                data, source, jp, self.factura_index, self.prestadores
            )
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
            f"Archivos RIPS cargados: {len(self._json_path_by_source)}\n"
            f"Registros en grilla: {len(self.records)}"
            + (f"\nDuplicados omitidos: {skipped_dupes}" if skipped_dupes else ""),
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
