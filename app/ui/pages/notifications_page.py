# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""Экран уведомлений: история завершённых загрузок и конвертаций."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.modules.settings.settings import open_folder
from app.utils.notifications.notifications import (
    delete_notification,
    load_notifications,
    save_notifications,
)

from ..i18n import t
from ..widgets import icons

SOURCE_ICON = {"downloader": "download", "converter": "convert"}


class NotificationCard(QFrame):
    remove_requested = Signal(str)
    open_requested = Signal(str)

    def __init__(self, entry: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        self.entry_id = str(entry.get("id", ""))

        payload = entry.get("payload") or {}
        folder = payload.get("folder", "")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        self.icon = QLabel()
        self.icon.setFixedSize(22, 22)
        self._icon_name = SOURCE_ICON.get(entry.get("source", ""), "bell")
        layout.addWidget(self.icon, 0, Qt.AlignTop)

        center = QVBoxLayout()
        center.setSpacing(4)

        title = QLabel(entry.get("message") or entry.get("title", ""))
        title.setProperty("heading", "2")
        title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        center.addWidget(title)

        details = [entry.get("title", ""), entry.get("timestamp", "")]
        fmt = payload.get("format")
        if fmt:
            details.insert(1, str(fmt).upper())
        resolution = payload.get("resolution")
        if resolution:
            details.insert(2, f"{resolution}p")
        meta = QLabel("  ·  ".join(str(d) for d in details if d))
        meta.setProperty("mono", "true")
        center.addWidget(meta)

        layout.addLayout(center, 1)

        self.btn_open = QPushButton()
        self.btn_open.setProperty("variant", "icon")
        self.btn_open.setToolTip("Открыть папку")
        self.btn_open.setEnabled(bool(folder) and os.path.isdir(folder))
        self.btn_open.clicked.connect(lambda: self.open_requested.emit(folder))
        layout.addWidget(self.btn_open, 0, Qt.AlignTop)

        self.btn_remove = QPushButton()
        self.btn_remove.setProperty("variant", "icon")
        self.btn_remove.setToolTip("Удалить запись")
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self.entry_id))
        layout.addWidget(self.btn_remove, 0, Qt.AlignTop)

    def refresh_icons(self, color: str, accent: str) -> None:
        self.icon.setPixmap(icons.icon(self._icon_name, accent, 20).pixmap(20, 20))
        self.btn_open.setIcon(icons.icon("folder", color, 15))
        self.btn_remove.setIcon(icons.icon("trash", color, 15))


class NotificationsPage(QWidget):
    def __init__(self, channel, parent: QWidget | None = None):
        super().__init__(parent)
        self.channel = channel
        self.cards: list[NotificationCard] = []
        self._icon_color = "#8b919e"
        self._accent = "#3b82f6"

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(t("sections.notifications", "Уведомления"))
        title.setProperty("heading", "1")
        header.addWidget(title)
        header.addStretch(1)

        self.btn_clear = QPushButton("Очистить всё")
        self.btn_clear.setProperty("variant", "danger")
        self.btn_clear.clicked.connect(self._clear_all)
        header.addWidget(self.btn_clear)
        root.addLayout(header)

        self.empty = QLabel(t("history.empty", "Пока пусто — здесь появится история загрузок и конвертаций"))
        self.empty.setProperty("muted", "true")
        root.addWidget(self.empty)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.host = QWidget()
        self.list_layout = QVBoxLayout(self.host)
        self.list_layout.setContentsMargins(0, 0, 6, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.host)
        root.addWidget(self.scroll, 1)

        channel.signals.notifications_reloaded.connect(self.reload)
        self.reload(load_notifications())

    # ------------------------------------------------------------------
    def reload(self, notifications: list) -> None:
        for card in self.cards:
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()

        # Свежие сверху: add_notification дописывает в конец списка
        for entry in reversed(notifications or []):
            card = NotificationCard(entry)
            card.refresh_icons(self._icon_color, self._accent)
            card.remove_requested.connect(self._remove)
            card.open_requested.connect(open_folder)
            self.cards.append(card)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        has_items = bool(self.cards)
        self.empty.setVisible(not has_items)
        self.btn_clear.setEnabled(has_items)

    def _remove(self, entry_id: str) -> None:
        self.reload(delete_notification(entry_id))

    def _clear_all(self) -> None:
        save_notifications([])
        self.reload([])

    # ------------------------------------------------------------------
    def apply_palette(self, palette: dict[str, str]) -> None:
        self._icon_color = palette.get("text-secondary", "#8b919e")
        self._accent = palette.get("accent-color", "#3b82f6")
        for card in self.cards:
            card.refresh_icons(self._icon_color, self._accent)
