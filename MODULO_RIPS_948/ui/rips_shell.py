from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from core.version import BUILD_ID, get_version
from core.paths import get_module_root
from ui.mode_selector_dialog import RipsMode
from ui.qt_icons import decorate_button, std_icon

SIDEBAR_EXPANDED = 248
SIDEBAR_COLLAPSED = 58


class RipsShellWindow(QMainWindow):
    """Contenedor con menú lateral: 948 / 3374 y pantalla dedicada al elegir modo."""

    def __init__(self) -> None:
        super().__init__()
        ver = get_version()
        self.setWindowTitle(f"Módulo RIPS — v{ver}")
        self.resize(1360, 880)
        self._expanded = True
        self._ctrl948 = None
        self._ctrl3374 = None

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._sidebar = QFrame()
        self._sidebar.setObjectName("ripsSidebar")
        self._sidebar.setFixedWidth(SIDEBAR_EXPANDED)
        self._sidebar.setStyleSheet(
            """
            QFrame#ripsSidebar {
                background-color: #1e293b;
                border-right: 1px solid #334155;
            }
            QPushButton#navBtn {
                text-align: left;
                padding: 12px 14px;
                color: #f1f5f9;
                background-color: #334155;
                border: none;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton#navBtn:hover { background-color: #475569; }
            QPushButton#navBtnActive {
                text-align: left;
                padding: 12px 14px;
                color: #fff;
                background-color: #e65100;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton#menuToggle {
                background-color: transparent;
                border: none;
                padding: 8px;
            }
            QLabel#sidebarTitle {
                color: #f8fafc;
                font-size: 15px;
                font-weight: bold;
                padding: 8px 4px;
            }
            QLabel#sidebarHint {
                color: #94a3b8;
                font-size: 11px;
                padding: 4px;
            }
            """
        )
        sb_layout = QVBoxLayout(self._sidebar)
        sb_layout.setContentsMargins(10, 14, 10, 14)
        sb_layout.setSpacing(10)

        self.btn_toggle = QPushButton()
        self.btn_toggle.setObjectName("menuToggle")
        self.btn_toggle.setIcon(std_icon(QStyle.StandardPixmap.SP_TitleBarUnshadeButton))
        self.btn_toggle.setToolTip(
            "Contraer o expandir el menú lateral. En modo trabajo el menú se oculta "
            "para dejar más espacio a la grilla."
        )
        self.btn_toggle.clicked.connect(self._on_toggle_sidebar)
        sb_layout.addWidget(self.btn_toggle)

        self.lbl_side_title = QLabel("Módulo RIPS")
        self.lbl_side_title.setObjectName("sidebarTitle")
        sb_layout.addWidget(self.lbl_side_title)

        self.lbl_side_hint = QLabel(
            f"v{ver} · {BUILD_ID}\nElija una normativa:"
        )
        self.lbl_side_hint.setObjectName("sidebarHint")
        sb_layout.addWidget(self.lbl_side_hint)

        self.btn_mode_948 = QPushButton("  Res. 948 (JSON)")
        self.btn_mode_948.setObjectName("navBtn")
        decorate_button(
            self.btn_mode_948,
            QStyle.StandardPixmap.SP_FileDialogContentsView,
            "Resolución 948 (2026): cargar RIPS en JSON, validar, relación Excel y datos de factura (FEV).",
        )
        self.btn_mode_948.clicked.connect(lambda: self.open_mode(RipsMode.RES_948))

        self.btn_mode_3374 = QPushButton("  Res. 3374 (TXT)")
        self.btn_mode_3374.setObjectName("navBtn")
        decorate_button(
            self.btn_mode_3374,
            QStyle.StandardPixmap.SP_DirIcon,
            "Resolución 3374: archivos planos CT, AF, US, AC, AP… en carpeta o ZIP. "
            "Validación de manifiesto CT.",
        )
        self.btn_mode_3374.clicked.connect(lambda: self.open_mode(RipsMode.RES_3374))

        sb_layout.addWidget(self.btn_mode_948)
        sb_layout.addWidget(self.btn_mode_3374)
        sb_layout.addStretch()

        self.btn_home = QPushButton("  Menú principal")
        self.btn_home.setObjectName("navBtn")
        self.btn_home.setVisible(False)
        decorate_button(
            self.btn_home,
            QStyle.StandardPixmap.SP_ArrowBack,
            "Volver al menú lateral y elegir otra normativa RIPS (948 o 3374).",
        )
        self.btn_home.clicked.connect(self.go_home)
        sb_layout.addWidget(self.btn_home)

        self.btn_exit = QPushButton("  Salir")
        self.btn_exit.setObjectName("navBtn")
        decorate_button(
            self.btn_exit,
            QStyle.StandardPixmap.SP_DialogCloseButton,
            "Cerrar el Módulo RIPS.",
        )
        self.btn_exit.clicked.connect(self.close)
        sb_layout.addWidget(self.btn_exit)

        self._stack = QStackedWidget()
        self._page_home = self._build_home_page()
        self._page_948 = QWidget()
        self._page_3374 = QWidget()
        self._stack.addWidget(self._page_home)
        self._stack.addWidget(self._page_948)
        self._stack.addWidget(self._page_3374)

        outer.addWidget(self._sidebar)
        outer.addWidget(self._stack, stretch=1)
        self._stack.setCurrentWidget(self._page_home)

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("<h2>Bienvenido al Módulo RIPS</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel(
            "<p style='color:#475569; max-width:520px;'>"
            "Use el <b>menú lateral</b> para elegir:<br>"
            "• <b>Resolución 948</b> — archivos JSON y exportación a Excel.<br>"
            "• <b>Resolución 3374</b> — archivos de texto CT/AF/US y ZIP.<br><br>"
            "Al entrar a un modo, el menú se <b>contrae</b> automáticamente. "
            "Pulse <b>Menú principal</b> o el icono superior para volver."
            "</p>"
        )
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        lay.addWidget(sub)
        path = QLabel(f"<small>Módulo: {get_module_root()}</small>")
        path.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(path)
        return page

    def _on_toggle_sidebar(self) -> None:
        if self._expanded:
            self._set_sidebar_expanded(False)
        else:
            self._set_sidebar_expanded(True)

    def _set_sidebar_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._sidebar.setFixedWidth(SIDEBAR_EXPANDED if expanded else SIDEBAR_COLLAPSED)
        show_labels = expanded
        self.lbl_side_title.setVisible(show_labels)
        self.lbl_side_hint.setVisible(show_labels)
        self.btn_mode_948.setText("  Res. 948 (JSON)" if show_labels else "")
        self.btn_mode_3374.setText("  Res. 3374 (TXT)" if show_labels else "")
        self.btn_home.setText("  Menú principal" if show_labels else "")
        self.btn_exit.setText("  Salir" if show_labels else "")
        icon = (
            QStyle.StandardPixmap.SP_TitleBarUnshadeButton
            if expanded
            else QStyle.StandardPixmap.SP_TitleBarShadeButton
        )
        self.btn_toggle.setIcon(std_icon(icon))

    def _embed_controller(self, mode: RipsMode):
        if mode == RipsMode.RES_948:
            if self._ctrl948 is None:
                from ui.main_window import MainWindow948

                self._ctrl948 = self._mount_window(MainWindow948, self._page_948)
            return self._ctrl948
        if self._ctrl3374 is None:
            from ui.main_window_3374 import MainWindow3374

            self._ctrl3374 = self._mount_window(MainWindow3374, self._page_3374)
        return self._ctrl3374

    def _mount_window(self, window_cls, host: QWidget):
        from ui.main_window import SessionEndReason

        win = window_cls()
        win.setParent(host)
        central = win.takeCentralWidget()
        if central is None:
            return win
        if host.layout() is None:
            lay = QVBoxLayout(host)
            lay.setContentsMargins(0, 0, 0, 0)
        else:
            lay = host.layout()
        lay.addWidget(central)
        win.session_ended.connect(self._on_child_home)
        win.hide()
        return win

    def _on_child_home(self, reason) -> None:
        from ui.main_window import SessionEndReason

        if reason == SessionEndReason.HOME:
            self.go_home()
        elif reason == SessionEndReason.EXIT:
            self.close()

    def open_mode(self, mode: RipsMode) -> None:
        self._embed_controller(mode)
        if mode == RipsMode.RES_948:
            self._stack.setCurrentWidget(self._page_948)
            self.btn_mode_948.setObjectName("navBtnActive")
            self.btn_mode_3374.setObjectName("navBtn")
        else:
            self._stack.setCurrentWidget(self._page_3374)
            self.btn_mode_3374.setObjectName("navBtnActive")
            self.btn_mode_948.setObjectName("navBtn")
        self.btn_home.setVisible(True)
        self._set_sidebar_expanded(False)

    def go_home(self) -> None:
        self._stack.setCurrentWidget(self._page_home)
        self.btn_mode_948.setObjectName("navBtn")
        self.btn_mode_3374.setObjectName("navBtn")
        self.btn_home.setVisible(False)
        self._set_sidebar_expanded(True)
        self._sidebar.style().unpolish(self._sidebar)
        self._sidebar.style().polish(self._sidebar)

    def closeEvent(self, event) -> None:  # noqa: N802
        reply = QMessageBox.question(
            self,
            "Salir",
            "¿Cerrar el Módulo RIPS?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
