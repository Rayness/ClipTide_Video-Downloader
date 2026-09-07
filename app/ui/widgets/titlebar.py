# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""Заголовок безрамочного окна: логотип, название, кнопки управления."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

TITLEBAR_HEIGHT = 38


def _glyph(kind: str, color: str, size: int = 10) -> QIcon:
    """
    Значки кнопок окна рисуем сами вместо шрифта иконок.
    Раньше интерфейс тянул Font Awesome с CDN — без интернета иконки
    просто не появлялись. Здесь отрисовка локальная и всегда чёткая.
    """
    scale = 2  # рисуем крупнее и отдаём как HiDPI-пиксмап
    px = QPixmap(size * scale, size * scale)
    px.fill(Qt.transparent)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing, kind == "close")
    pen = QPen(color)
    pen.setWidth(scale)
    pen.setCapStyle(Qt.FlatCap)
    painter.setPen(pen)

    end = size * scale - scale
    mid = (size * scale) // 2

    if kind == "minimize":
        painter.drawLine(0, mid, end, mid)
    elif kind == "maximize":
        painter.drawRect(0, 0, end, end)
    elif kind == "restore":
        painter.drawRect(0, scale * 2, end - scale * 2, end - scale * 2)
        painter.drawLine(scale * 2, scale * 2, scale * 2, 0)
        painter.drawLine(scale * 2, 0, end, 0)
        painter.drawLine(end, 0, end, end - scale * 2)
    elif kind == "close":
        painter.drawLine(0, 0, end, end)
        painter.drawLine(0, end, end, 0)
    painter.end()

    px.setDevicePixelRatio(scale)
    return QIcon(px)


class TitleBar(QFrame):
    """Полоса заголовка. Сама ничего не решает — только сообщает наверх."""

    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self, title: str, version: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(TITLEBAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(QSize(18, 18))
        self.icon_label.setScaledContents(True)
        layout.addWidget(self.icon_label)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("TitleBarText")
        layout.addWidget(self.title_label)

        self.version_label = QLabel(version)
        self.version_label.setObjectName("TitleBarVersion")
        layout.addWidget(self.version_label)

        layout.addStretch(1)

        self.btn_minimize = self._window_button("minimize", "Свернуть")
        self.btn_maximize = self._window_button("maximize", "Развернуть")
        self.btn_close = self._window_button("close", "Закрыть", close=True)

        self.btn_minimize.clicked.connect(self.minimize_requested)
        self.btn_maximize.clicked.connect(self.maximize_requested)
        self.btn_close.clicked.connect(self.close_requested)

        for button in (self.btn_minimize, self.btn_maximize, self.btn_close):
            layout.addWidget(button)

    def _window_button(self, kind: str, tooltip: str, close: bool = False) -> QPushButton:
        button = QPushButton()
        button.setProperty("winctl", "close" if close else "true")
        button.setToolTip(tooltip)
        button.setCursor(Qt.ArrowCursor)
        button.setFocusPolicy(Qt.NoFocus)
        button.setIconSize(QSize(10, 10))
        button._glyph_kind = kind
        return button

    # ------------------------------------------------------------------
    def set_icon(self, pixmap: QPixmap) -> None:
        self.icon_label.setPixmap(pixmap)

    def set_version(self, version: str) -> None:
        self.version_label.setText(version)

    def refresh_glyphs(self, color: str, maximized: bool = False) -> None:
        """Перерисовывает значки под цвет текущей темы."""
        self.btn_minimize.setIcon(_glyph("minimize", color))
        self.btn_maximize.setIcon(_glyph("restore" if maximized else "maximize", color))
        self.btn_close.setIcon(_glyph("close", color))

    # ------------------------------------------------------------------
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.maximize_requested.emit()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        # Перетаскивание отдаём системе: сохраняются Aero Snap и «прилипание»
        # к краям, которых не было у прежней реализации через WM_NCLBUTTONDOWN.
        if event.button() == Qt.LeftButton:
            window = self.window().windowHandle()
            if window is not None:
                window.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)
