from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox

from core.date_fmt import format_date_display
from core.rips_3374.records import build_records_from_package
from core.rips_3374.txt_parser import load_from_txt_paths, load_from_zip
from core.rips_3374.validator import validate_package, validation_summary_3374
from core.validator import Severity
from ui.main_window import MainWindow948
from ui.rips_3374_load_dialog import Rips3374LoadDialog
from ui.validation_report_dialog import ValidationReportDialog


class MainWindow3374(MainWindow948):
    """Relación y validación RIPS archivos planos (Res. 3374)."""

    def __init__(self) -> None:
        self._grid_profile = "3374"
        super().__init__()
        self.setWindowTitle(
            self.windowTitle().replace("948", "3374").replace("Relación", "Relación TXT")
        )
        self.package = None
        self.btn_carpeta.setVisible(False)
        self.btn_buscar.setText("Buscar archivos RIPS (TXT / ZIP)")
        self.btn_buscar.setToolTip(
            "Abre el selector de ZIP o carpeta con archivos .txt (CT, AF, US, AC, AP, …). "
            "Muestra los archivos encontrados antes de confirmar."
        )
        self.btn_validar.setToolTip(
            "Valida el manifiesto CT (archivos del paquete y cantidad de registros), "
            "usuarios en US, totales AF vs servicios, etc."
        )
        self.btn_errores = self._add_toolbar_button(
            "Solo errores",
            "Muestra únicamente los errores de la última validación.",
            after=self.btn_ver_informe,
        )
        self.btn_errores.clicked.connect(self.on_solo_errores)
        self.lbl_resultado.setText("Resultado RIPS 3374: —")

    def _enrich_records_from_factura_index(self) -> None:
        for rec in self.records:
            nro = str(rec.values.get("NroFac") or "").strip()
            if not nro:
                continue
            meta = self.factura_index.get(nro)
            if not meta:
                continue
            if meta.fecha_factura and not rec.values.get("Fecha factura"):
                rec.values["Fecha factura"] = format_date_display(meta.fecha_factura)
            if meta.nombre_ips and not rec.values.get("NombreIps"):
                rec.values["NombreIps"] = meta.nombre_ips
            if meta.nombre_paciente and not rec.values.get("Nombre"):
                rec.values["Nombre"] = meta.nombre_paciente

    def _add_toolbar_button(self, text: str, tooltip: str, after) -> object:
        row = after.parentWidget()
        lay = row.layout()
        btn = type(after)(text)
        btn.setToolTip(tooltip)
        idx = lay.indexOf(after)
        lay.insertWidget(idx + 1, btn)
        return btn

    def on_descargar_informe(self) -> None:
        if not self.validation_report:
            self.on_validar()
        if not self.validation_report:
            return
        from pathlib import Path

        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar informe de validación RIPS 3374",
            "informe_validacion_rips_3374.txt",
            "Texto (*.txt)",
        )
        if path:
            Path(path).write_text(
                validation_summary_3374(self.validation_report), encoding="utf-8"
            )
            QMessageBox.information(self, "Informe", f"Informe guardado en:\n{path}")

    def _open_rips_picker(self) -> list[str]:
        return []

    def on_buscar_archivos(self) -> None:
        self._open_3374_loader()

    def on_buscar_carpeta(self) -> None:
        self._open_3374_loader()

    def _open_3374_loader(self) -> None:
        dialog = Rips3374LoadDialog(self._last_folder, self)
        if dialog.exec() != Rips3374LoadDialog.DialogCode.Accepted:
            return
        if dialog.is_zip_mode():
            zp = dialog.zip_path()
            if not zp:
                return
            self._last_folder = str(zp.parent)
            self.package = load_from_zip(zp)
        else:
            folder = dialog.folder_path()
            self._last_folder = str(folder)
            paths = dialog.selected_txt_paths()
            if not paths:
                from core.rips_3374.txt_parser import list_matching_txt_in_folder

                paths = list_matching_txt_in_folder(folder)
            self.package = load_from_txt_paths(paths)
            self.factura_index.scan_directories({folder})
        self.records = build_records_from_package(self.package)
        self._enrich_records_from_factura_index()
        self.documents = []
        self.validation_report = None
        self.lbl_resultado.setText("Resultado RIPS 3374: — (pendiente validar)")
        self._refresh_table()
        self._update_stats()
        self.on_validar()
        self.lbl_facturas.setText(
            self.lbl_facturas.text()
            + f" | Tipos cargados: {len(self.package.rows)}"
        )

    def on_validar(self) -> None:
        if not self.package or not self.package.rows:
            QMessageBox.warning(
                self,
                "Sin datos",
                "Cargue un ZIP o carpeta con archivos .txt RIPS (Res. 3374).",
            )
            return
        self.btn_validar.setEnabled(False)
        prev = self.btn_validar.text()
        self.btn_validar.setText("Validando…")
        self.txt_validacion.setPlainText(
            "Validando manifiesto CT y archivos RIPS 3374… por favor espere."
        )
        QApplication.processEvents()
        try:
            self.validation_report = validate_package(self.package)
            body = validation_summary_3374(self.validation_report)
            if not body.strip():
                body = "Sin mensajes de validación (revise que el CT y los .txt estén cargados)."
            self._show_validation_panel(
                body,
                self.validation_report.status_label,
                "Resultado RIPS 3374",
            )
        finally:
            self.btn_validar.setEnabled(True)
            self.btn_validar.setText(prev)

    def on_solo_errores(self) -> None:
        if not self.validation_report:
            self.on_validar()
        if not self.validation_report:
            return
        errs = [
            m.line()
            for m in self.validation_report.messages
            if m.severity == Severity.ERROR
        ]
        body = "\n".join(errs) if errs else "No hay errores en la última validación."
        dlg = ValidationReportDialog(
            "Errores RIPS 3374",
            f"Errores encontrados: {len(errs)}",
            body,
            self,
        )
        dlg.exec()

    def on_ver_informe(self) -> None:
        if not self.validation_report:
            self.on_validar()
        if self.validation_report:
            body = validation_summary_3374(self.validation_report)
            dlg = ValidationReportDialog(
                "Resultado validación RIPS 3374",
                f"Estado: {self.validation_report.status_label}",
                body,
                self,
            )
            dlg.exec()
