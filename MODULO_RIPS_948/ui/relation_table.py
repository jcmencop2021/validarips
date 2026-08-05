from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import QAbstractItemView, QTableWidget


class RelationTable(QTableWidget):
    """Grilla con copia TSV (Ctrl+C) para pegar en Excel."""

    COL_EXPORT = 0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.CurrentChanged
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        copy_action = QAction("Copiar", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.copy_selection_to_clipboard)
        self.addAction(copy_action)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection_to_clipboard()
            event.accept()
            return
        super().keyPressEvent(event)

    def _cell_text(self, row: int, col: int) -> str:
        item = self.item(row, col)
        if item is None:
            return ""
        if col == self.COL_EXPORT:
            return "1" if item.checkState() == Qt.CheckState.Checked else ""
        return item.text().replace("\t", " ").replace("\r", " ").replace("\n", " ")

    def copy_selection_to_clipboard(self) -> None:
        indexes = self.selectedIndexes()
        if not indexes:
            return
        by_row: dict[int, dict[int, str]] = {}
        for idx in indexes:
            by_row.setdefault(idx.row(), {})[idx.column()] = self._cell_text(
                idx.row(), idx.column()
            )
        lines: list[str] = []
        for row in sorted(by_row.keys()):
            cols = by_row[row]
            line = "\t".join(cols[c] for c in sorted(cols.keys()))
            lines.append(line)
        QGuiApplication.clipboard().setText("\n".join(lines))
