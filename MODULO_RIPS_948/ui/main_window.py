from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
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

from core.excel_export import ensure_template, export_to_excel
from core.loader import build_records_from_rips, discover_json_paths, load_json_file
from core.validator import ValidationReport, validate_all
from models.relation_record import ADMIN_FIELDS, RELATION_COLUMNS, RelationRecord

APP_ROOT = Path(__file__).resolve().parent.parent


class MainWindow(QMainWindow):
    COL_APPLY = 0

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Módulo RIPS — Relación Resolución 948 v1.0")
        self.resize(1280, 800)

        self.config = self._load_config()
        self.records: list[RelationRecord] = []
        self.documents: list[tuple[str, dict, list[RelationRecord]]] = []
        self.validation_report: ValidationReport | None = None
        self.loaded_files: list[Path] = []

        self._build_ui()

    def _load_config(self) -> dict:
        cfg_path = APP_ROOT / "config.json"
        if cfg_path.is_file():
            try:
                return json.loads(cfg_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {"nombre_ips_por_codigo": {}}

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Botonera superior
        btn_row = QHBoxLayout()
        self.btn_buscar = QPushButton("Buscar RIPS (JSON)")
        self.btn_carpeta = QPushButton("Buscar carpeta")
        self.btn_validar = QPushButton("Validar")
        self.btn_ver_informe = QPushButton("Ver resultado / errores")
        self.btn_exportar = QPushButton("Exportar Excel")
        self.btn_descargar = QPushButton("Descargar informe")
        for btn in (
            self.btn_buscar,
            self.btn_carpeta,
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
        self.btn_validar.clicked.connect(self.on_validar)
        self.btn_ver_informe.clicked.connect(self.on_ver_informe)
        self.btn_exportar.clicked.connect(self.on_exportar)
        self.btn_descargar.clicked.connect(self.on_descargar_informe)

        # Estado
        status_box = QGroupBox("Estado")
        status_layout = QHBoxLayout(status_box)
        self.lbl_facturas = QLabel("Facturas: 0")
        self.lbl_pacientes = QLabel("Registros (usuarios): 0")
        self.lbl_total = QLabel("Valor total: 0")
        self.lbl_resultado = QLabel("Resultado RIPS: —")
        self.lbl_resultado.setStyleSheet("font-weight: bold;")
        for w in (self.lbl_facturas, self.lbl_pacientes, self.lbl_total, self.lbl_resultado):
            status_layout.addWidget(w)
        status_layout.addStretch()
        layout.addWidget(status_box)

        # Encabezado administrativo
        header_box = QGroupBox("Datos administrativos (comunes)")
        header_grid = QGridLayout(header_box)
        self.admin_inputs: dict[str, QLineEdit] = {}
        labels = {
            "CAJA": "Caja",
            "RADICADO": "Radicado",
            "FECHA RADICADO": "Fecha radicado",
            "PERIODO FACTURADO": "Periodo",
            "Fecha factura": "Fecha factura",
            "REL": "REL",
        }
        for i, field in enumerate(ADMIN_FIELDS):
            row, col = divmod(i, 3)
            header_grid.addWidget(QLabel(labels.get(field, field)), row * 2, col)
            edit = QLineEdit()
            self.admin_inputs[field] = edit
            header_grid.addWidget(edit, row * 2 + 1, col)
        self.btn_aplicar_todos = QPushButton("Aplicar a todos")
        self.btn_aplicar_todos.clicked.connect(self.on_aplicar_todos)
        header_grid.addWidget(self.btn_aplicar_todos, 4, 0, 1, 3)
        layout.addWidget(header_box)

        # Grilla
        self.table = QTableWidget(0, 1 + len(RELATION_COLUMNS))
        headers = ["Aplicar"] + RELATION_COLUMNS
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.cellChanged.connect(self.on_cell_changed)
        layout.addWidget(self.table, stretch=1)

        # Panel inferior validación
        self.txt_validacion = QTextEdit()
        self.txt_validacion.setReadOnly(True)
        self.txt_validacion.setPlaceholderText("Resultado de validación RIPS…")
        self.txt_validacion.setMaximumHeight(160)
        layout.addWidget(self.txt_validacion)

    def _admin_values(self) -> dict[str, str]:
        return {k: w.text().strip() for k, w in self.admin_inputs.items()}

    def on_buscar_archivos(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar archivos RIPS JSON",
            "",
            "Archivos JSON (*.json)",
        )
        if paths:
            self._load_paths(paths)

    def on_buscar_carpeta(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con JSON")
        if folder:
            self._load_paths([folder])

    def _load_paths(self, paths: list[str]) -> None:
        json_paths = discover_json_paths(paths)
        if not json_paths:
            QMessageBox.warning(self, "Sin archivos", "No se encontraron archivos .json.")
            return

        self.records.clear()
        self.documents.clear()
        self.loaded_files = json_paths
        ips_map = self.config.get("nombre_ips_por_codigo") or {}

        for jp in json_paths:
            data, err = load_json_file(jp)
            source = jp.name
            if err or not isinstance(data, dict):
                self.documents.append((source, {}, []))
                continue
            recs = build_records_from_rips(data, source, ips_map)
            self.records.extend(recs)
            self.documents.append((source, data, recs))

        self.validation_report = None
        self.lbl_resultado.setText("Resultado RIPS: — (pendiente validar)")
        self.lbl_resultado.setStyleSheet("font-weight: bold;")
        self.txt_validacion.clear()
        self._refresh_table()
        self._update_stats()
        QMessageBox.information(
            self,
            "Carga completada",
            f"Se cargaron {len(json_paths)} archivo(s) JSON.\n"
            f"Registros en grilla: {len(self.records)}",
        )

    def _refresh_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.records))
        for row, rec in enumerate(self.records):
            apply_item = QTableWidgetItem()
            apply_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
            if rec.admin_applied:
                apply_item.setCheckState(Qt.CheckState.Checked)
                apply_item.setFlags(Qt.ItemFlag.ItemIsSelectable)
            else:
                apply_item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, self.COL_APPLY, apply_item)

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

    def on_cell_changed(self, row: int, column: int) -> None:
        if row < 0 or row >= len(self.records):
            return
        if column == self.COL_APPLY:
            item = self.table.item(row, self.COL_APPLY)
            if item is None:
                return
            if item.checkState() == Qt.CheckState.Checked and not self.records[row].admin_applied:
                self._apply_admin_to_row(row)
            return
        if column > 0:
            col_name = RELATION_COLUMNS[column - 1]
            cell = self.table.item(row, column)
            if cell:
                self.records[row].values[col_name] = cell.text()

    def _apply_admin_to_row(self, row: int) -> None:
        admin = self._admin_values()
        if not any(admin.values()):
            QMessageBox.warning(
                self,
                "Datos vacíos",
                "Complete al menos un campo administrativo en el encabezado antes de aplicar.",
            )
            item = self.table.item(row, self.COL_APPLY)
            if item:
                self.table.blockSignals(True)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.table.blockSignals(False)
            return
        self.records[row].apply_admin(admin)
        self._refresh_table()

    def on_aplicar_todos(self) -> None:
        admin = self._admin_values()
        if not any(admin.values()):
            QMessageBox.warning(self, "Datos vacíos", "Ingrese los datos administrativos.")
            return
        for rec in self.records:
            rec.apply_admin(admin)
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
        for r in self.records:
            try:
                total += float(r.values.get("VlorNeto") or 0)
            except (TypeError, ValueError):
                pass
        self.lbl_facturas.setText(f"Facturas: {len(facturas)}")
        self.lbl_pacientes.setText(f"Registros (usuarios): {len(self.records)}")
        self.lbl_total.setText(f"Valor total: {total:,.0f}")

    def on_exportar(self) -> None:
        if not self.records:
            QMessageBox.warning(self, "Sin datos", "No hay registros para exportar.")
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
        export_to_excel(self.records, Path(path), template)
        QMessageBox.information(self, "Exportación", f"Archivo Excel generado:\n{path}")


def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
