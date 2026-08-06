from __future__ import annotations

import json

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QHeaderView, QTableWidget


_ORG = "ModuloRIPS"
_APP = "Relacion948"


def load_column_widths(table: QTableWidget, profile: str) -> None:
    settings = QSettings(_ORG, _APP)
    raw = settings.value(f"column_widths/{profile}", "")
    if not raw:
        return
    try:
        data = json.loads(str(raw))
        if not isinstance(data, dict):
            return
        for key, width in data.items():
            col = int(key)
            w = int(width)
            if 0 <= col < table.columnCount() and w > 20:
                table.setColumnWidth(col, w)
    except (json.JSONDecodeError, TypeError, ValueError):
        return


def save_column_widths(table: QTableWidget, profile: str) -> None:
    data = {str(c): table.columnWidth(c) for c in range(table.columnCount())}
    settings = QSettings(_ORG, _APP)
    settings.setValue(f"column_widths/{profile}", json.dumps(data))


def attach_column_width_persistence(table: QTableWidget, profile: str) -> None:
    load_column_widths(table, profile)
    header: QHeaderView = table.horizontalHeader()

    def _on_resize(_idx: int, _old: int, _new: int) -> None:
        save_column_widths(table, profile)

    header.sectionResized.connect(_on_resize)
