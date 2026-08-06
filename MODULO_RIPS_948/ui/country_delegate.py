from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QStyledItemDelegate

from core.paises import country_choices, match_country_display


class CountryComboDelegate(QStyledItemDelegate):
    """Lista de países con iniciales (ej. CO - COLOMBIA)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._choices = country_choices()

    def createEditor(self, parent, option, index):  # noqa: ANN001
        combo = QComboBox(parent)
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for display, value in self._choices:
            combo.addItem(display, value)
        displays = [d for d, _ in self._choices]
        completer = QCompleter(displays, combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        combo.setCompleter(completer)
        combo.setMaxVisibleItems(20)
        return combo

    def setEditorData(self, editor, index) -> None:  # noqa: ANN001
        text = str(index.model().data(index, Qt.ItemDataRole.DisplayRole) or "").strip()
        if not text:
            editor.setCurrentIndex(-1)
            editor.setEditText("")
            return
        display = match_country_display(text)
        idx = editor.findText(display, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            editor.setCurrentIndex(idx)
        else:
            editor.setEditText(text)

    def setModelData(self, editor, model, index) -> None:  # noqa: ANN001
        idx = editor.currentIndex()
        if idx >= 0:
            value = editor.itemData(idx)
            model.setData(index, value or editor.currentText(), Qt.ItemDataRole.EditRole)
        else:
            model.setData(index, editor.currentText().strip(), Qt.ItemDataRole.EditRole)
