# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Оболочка главного окна: безрамочное окно, заголовок, боковая навигация,
область страниц и строка состояния.

Ресайз отдан системе через QWindow.startSystemResize. Прежняя реализация
слала WM_NCLBUTTONDOWN через ctypes и искала HWND по заголовку окна
(FindWindowW по строке) — это ломалось, если пользователь открывал два
экземпляра или менялся заголовок. Нативный путь заодно возвращает
Aero Snap и корректную работу на нескольких мониторах.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .widgets import icons
from .widgets.titlebar import TitleBar
from .i18n import t

# Ширина зоны захвата у края окна для изменения размера
RESIZE_MARGIN = 6

_EDGES = (
    (Qt.TopEdge | Qt.LeftEdge,     Qt.SizeFDiagCursor),
    (Qt.TopEdge | Qt.RightEdge,    Qt.SizeBDiagCursor),
    (Qt.BottomEdge | Qt.LeftEdge,  Qt.SizeBDiagCursor),
    (Qt.BottomEdge | Qt.RightEdge, Qt.SizeFDiagCursor),
    (Qt.TopEdge,                   Qt.SizeVerCursor),
    (Qt.BottomEdge,                Qt.SizeVerCursor),
    (Qt.LeftEdge,                  Qt.SizeHorCursor),
    (Qt.RightEdge,                 Qt.SizeHorCursor),
)


class Sidebar(QFrame):
    """Вертикальная навигация по разделам."""

    page_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(212)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 0)
        self._layout.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self.page_changed)

        self._buttons: list[QPushButton] = []

        self._layout.addStretch(1)
        self.footer = QLabel()
        self.footer.setObjectName("SidebarFooter")
        self._layout.addWidget(self.footer)

    def add_item(self, index: int, label: str, icon_name: str) -> QPushButton:
        button = QPushButton(f"  {label}")
        button.setProperty("nav", "true")
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)
        button._icon_name = icon_name
        self._group.addButton(button, index)
        self._buttons.append(button)
        # Вставляем перед распоркой и подвалом
        self._layout.insertWidget(self._layout.count() - 2, button)
        return button

    def select(self, index: int) -> None:
        button = self._group.button(index)
        if button is not None:
            button.setChecked(True)

    def refresh_icons(self, idle_color: str, active_color: str) -> None:
        for button in self._buttons:
            color = active_color if button.isChecked() else idle_color
            button.setIcon(icons.icon(button._icon_name, color, 17))

    def set_footer(self, text: str) -> None:
        self.footer.setText(text)


class MainWindow(QWidget):
    """Главное окно приложения."""

    closing = Signal()

    def __init__(self, title: str = "ClipTide", version: str = ""):
        super().__init__()
        self.setObjectName("RootWindow")
        self.setWindowTitle(f"{title} {version}".strip())
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setMinimumSize(900, 620)
        self.resize(1200, 780)
        self.setMouseTracking(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- заголовок ---
        self.titlebar = TitleBar(title, version, self)
        self.titlebar.minimize_requested.connect(self.showMinimized)
        self.titlebar.maximize_requested.connect(self.toggle_maximized)
        self.titlebar.close_requested.connect(self.close)
        root.addWidget(self.titlebar)

        # --- тело ---
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = Sidebar(self)
        self.sidebar.page_changed.connect(self._on_page_changed)
        body.addWidget(self.sidebar)

        self.pages = QStackedWidget(self)
        self.pages.setObjectName("Content")
        self.pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body.addWidget(self.pages, 1)

        root.addLayout(body, 1)

        # --- строка состояния ---
        self.statusbar = QFrame(self)
        self.statusbar.setObjectName("StatusBar")
        status_layout = QHBoxLayout(self.statusbar)
        status_layout.setContentsMargins(12, 0, 12, 0)
        self.status_label = QLabel(t("ui.status.ready", "Готово"))
        status_layout.addWidget(self.status_label)
        status_layout.addStretch(1)
        self.status_right = QLabel("")
        status_layout.addWidget(self.status_right)
        root.addWidget(self.statusbar)

        self._icon_idle = "#8b919e"
        self._icon_active = "#e6e8ec"

    # ------------------------------------------------------------------
    # Страницы
    # ------------------------------------------------------------------
    def add_page(self, widget: QWidget, label: str, icon_name: str) -> int:
        index = self.pages.addWidget(widget)
        self.sidebar.add_item(index, label, icon_name)
        if index == 0:
            self.sidebar.select(0)
        return index

    def _on_page_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.sidebar.refresh_icons(self._icon_idle, self._icon_active)

    def show_page(self, index: int) -> None:
        self.sidebar.select(index)
        self._on_page_changed(index)

    # ------------------------------------------------------------------
    # Тема
    # ------------------------------------------------------------------
    def apply_palette(self, palette: dict[str, str]) -> None:
        """Перекрашивает нарисованные кодом иконки под текущую тему."""
        icons.clear_cache()
        self._icon_idle = palette.get("text-secondary", "#8b919e")
        self._icon_active = palette.get("text-color", "#e6e8ec")
        self.sidebar.refresh_icons(self._icon_idle, self._icon_active)
        self.titlebar.refresh_glyphs(
            palette.get("titlebar-text", "#e6e8ec"), self.isMaximized()
        )

    def set_app_icon(self, pixmap: QPixmap) -> None:
        self.titlebar.set_icon(pixmap)

    # ------------------------------------------------------------------
    # Состояние окна
    # ------------------------------------------------------------------
    def toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            maximized = self.isMaximized()
            self.titlebar.refresh_glyphs(self._icon_active, maximized)
            # В развёрнутом виде скругление и рамка окну не нужны
            self.layout().setContentsMargins(0, 0, 0, 0)
        super().changeEvent(event)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def closeEvent(self, event):
        self.closing.emit()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Изменение размера за края окна
    # ------------------------------------------------------------------
    def _edge_at(self, pos: QPoint):
        if self.isMaximized() or self.isFullScreen():
            return None
        x, y = pos.x(), pos.y()
        width, height = self.width(), self.height()
        m = RESIZE_MARGIN

        left, right = x <= m, x >= width - m
        top, bottom = y <= m, y >= height - m

        if top and left:      return Qt.TopEdge | Qt.LeftEdge
        if top and right:     return Qt.TopEdge | Qt.RightEdge
        if bottom and left:   return Qt.BottomEdge | Qt.LeftEdge
        if bottom and right:  return Qt.BottomEdge | Qt.RightEdge
        if top:               return Qt.TopEdge
        if bottom:            return Qt.BottomEdge
        if left:              return Qt.LeftEdge
        if right:             return Qt.RightEdge
        return None

    def mouseMoveEvent(self, event):
        edge = self._edge_at(event.position().toPoint())
        if edge is None:
            self.unsetCursor()
        else:
            for candidate, cursor in _EDGES:
                if candidate == edge:
                    self.setCursor(cursor)
                    break
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._edge_at(event.position().toPoint())
            if edge is not None:
                handle = self.windowHandle()
                if handle is not None:
                    handle.startSystemResize(edge)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)
