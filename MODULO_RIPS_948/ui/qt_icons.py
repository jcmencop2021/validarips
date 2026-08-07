from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QPushButton, QStyle, QWidget


def app_style() -> QStyle:
    return QApplication.instance().style() if QApplication.instance() else QStyle()


def std_icon(pixmap: QStyle.StandardPixmap) -> QIcon:
    return app_style().standardIcon(pixmap)


def decorate_button(
    btn: QPushButton,
    icon: QStyle.StandardPixmap,
    tooltip: str,
) -> None:
    btn.setIcon(std_icon(icon))
    btn.setToolTip(tooltip)


def set_widget_tooltip(widget: QWidget, text: str) -> None:
    widget.setToolTip(text)
