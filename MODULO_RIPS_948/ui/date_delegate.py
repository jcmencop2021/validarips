from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QStyledItemDelegate, QWidget

from core.date_fmt import DATE_PLACEHOLDER, normalize_typed_date

GRID_DATE_COLUMNS: frozenset[str] = frozenset(
    {
        "FECHA RADICADO",
        "Fecha factura",
        "FECHAING",
        "FECHAFIN",
    }
)


class DateLineDelegate(QStyledItemDelegate):
    """Fecha como texto dd/mm/aaaa (sin calendario ni máscara que bloquee tecleo)."""

    def createEditor(self, parent: QWidget, option, index):  # noqa: ANN001
        editor = QLineEdit(parent)
        editor.setPlaceholderText(DATE_PLACEHOLDER)
        editor.setClearButtonEnabled(True)
        return editor

    def setEditorData(self, editor, index) -> None:  # noqa: ANN001
        text = str(index.model().data(index, Qt.ItemDataRole.DisplayRole) or "").strip()
        editor.setText(text)

    def setModelData(self, editor, model, index) -> None:  # noqa: ANN001
        raw = editor.text().strip()
        value = normalize_typed_date(raw) if raw else ""
        model.setData(index, value, Qt.ItemDataRole.EditRole)
