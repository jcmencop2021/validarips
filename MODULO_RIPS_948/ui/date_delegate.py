from __future__ import annotations

from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import Qt, QRegularExpression
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
    """Fecha como texto dd/mm/aaaa (sin calendario)."""

    def createEditor(self, parent: QWidget, option, index):  # noqa: ANN001
        editor = QLineEdit(parent)
        editor.setPlaceholderText(DATE_PLACEHOLDER)
        editor.setInputMask("00/00/0000;_")
        rx = QRegularExpression(r"^\d{2}/\d{2}/\d{4}$")
        editor.setValidator(QRegularExpressionValidator(rx, editor))
        editor.setMaximumWidth(95)
        return editor

    def setEditorData(self, editor, index) -> None:  # noqa: ANN001
        text = str(index.model().data(index, Qt.ItemDataRole.DisplayRole) or "").strip()
        editor.setText(text)

    def setModelData(self, editor, model, index) -> None:  # noqa: ANN001
        model.setData(
            index,
            normalize_typed_date(editor.text()),
            Qt.ItemDataRole.EditRole,
        )
