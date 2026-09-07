# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""Экран загрузчика: ввод ссылки, очередь загрузок и журнал."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..i18n import t, tf
from ..widgets import icons
from ..widgets.thumbnail import fit

THUMB_SIZE = QSize(112, 63)

FORMATS = [
    ("MP4", "mp4"), ("MKV", "mkv"), ("WEBM", "webm"),
    (t("ui.downloader.audio_mp3", "MP3 · только звук"), "mp3"), (t("ui.downloader.audio_m4a", "M4A · только звук"), "m4a"),
    (t("ui.downloader.audio_opus", "OPUS · только звук"), "opus"), (t("ui.downloader.audio_flac", "FLAC · только звук"), "flac"),
]

RESOLUTIONS = [
    ("2160p · 4K", "2160"), ("1440p · 2K", "1440"), ("1080p · FullHD", "1080"),
    ("720p · HD", "720"), ("480p", "480"), ("360p", "360"), ("240p", "240"),
]

CODECS = [(t("downloader.codec_auto", "Автоматически"), "auto"), ("H.264", "h264"), ("H.265", "h265"), ("AV1", "av1")]

def status_text(status: str) -> str:
    """Подпись статуса берём из словаря переводов."""
    return {
        "queued":      t("downloader.status_waiting", "В очереди"),
        "downloading": t("status.downloading", "Загрузка"),
        "paused":      t("downloader.status_paused", "Пауза"),
        "error":       t("downloader.status_error", "Ошибка"),
        "done":        t("downloader.status_done", "Готово"),
    }.get(status, status)

AUDIO_ONLY = {"mp3", "m4a", "opus", "flac", "aac", "wav"}


class PlaylistDialog(QDialog):
    """Выбор роликов из найденного плейлиста."""

    def __init__(self, playlist: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(t("ui.downloader.playlist", "Плейлист"))
        self.setMinimumSize(560, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel(playlist.get("title", t("ui.downloader.playlist", "Плейлист")))
        title.setProperty("heading", "1")
        title.setWordWrap(True)
        layout.addWidget(title)

        items = playlist.get("items", [])
        hint = QLabel(tf(
            "ui.downloader.found_videos",
            "Найдено роликов: {count}. Отметьте нужные.",
            count=len(items)))
        hint.setProperty("muted", "true")
        layout.addWidget(hint)

        self.list = QListWidget()
        for entry in items:
            row = QListWidgetItem(f"{entry.get('title', '?')}   ·   {entry.get('duration', '')}")
            row.setFlags(row.flags() | Qt.ItemIsUserCheckable)
            row.setCheckState(Qt.Checked)
            row.setData(Qt.UserRole, entry.get("url"))
            self.list.addItem(row)
        layout.addWidget(self.list, 1)

        toggles = QHBoxLayout()
        select_all = QPushButton(t("ui.downloader.select_all", "Выбрать все"))
        select_all.setProperty("variant", "ghost")
        select_all.clicked.connect(lambda: self._set_all(Qt.Checked))
        clear_all = QPushButton(t("ui.downloader.deselect_all", "Снять все"))
        clear_all.setProperty("variant", "ghost")
        clear_all.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        toggles.addWidget(select_all)
        toggles.addWidget(clear_all)
        toggles.addStretch(1)
        layout.addLayout(toggles)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(t("add_to_queue", "Добавить в очередь"))
        buttons.button(QDialogButtonBox.Ok).setProperty("variant", "primary")
        buttons.button(QDialogButtonBox.Cancel).setText(t("ui.common.cancel", "Отмена"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_all(self, state) -> None:
        for index in range(self.list.count()):
            self.list.item(index).setCheckState(state)

    def selected_urls(self) -> list[str]:
        return [
            self.list.item(i).data(Qt.UserRole)
            for i in range(self.list.count())
            if self.list.item(i).checkState() == Qt.Checked
            and self.list.item(i).data(Qt.UserRole)
        ]


class DownloadCard(QFrame):
    """Карточка одной загрузки."""

    remove_requested = Signal(str)
    stop_requested = Signal(str)
    start_requested = Signal(str)
    settings_changed = Signal(str, str, str, str)   # id, format, resolution, codec

    def __init__(self, item: dict, loader, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        self.task_id = item["id"]
        self.item = item
        self._loader = loader
        self._thumb_url = item.get("thumbnail", "")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        self.thumb = QLabel()
        self.thumb.setFixedSize(THUMB_SIZE)
        self.thumb.setPixmap(fit(loader.request(self._thumb_url), THUMB_SIZE))
        layout.addWidget(self.thumb, 0, Qt.AlignTop)

        center = QVBoxLayout()
        center.setSpacing(6)

        top = QHBoxLayout()
        self.title = QLabel(item.get("title", ""))
        self.title.setProperty("heading", "2")
        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top.addWidget(self.title, 1)

        self.badge = QLabel(status_text(item.get("status", "queued")))
        self.badge.setProperty("badge", self._badge_kind(item.get("status", "queued")))
        top.addWidget(self.badge, 0, Qt.AlignRight)
        center.addLayout(top)

        meta = item.get("meta") or {}
        parts = [meta.get("uploader", ""), meta.get("duration", ""), meta.get("size", "")]
        self.meta = QLabel("  ·  ".join(p for p in parts if p))
        self.meta.setProperty("mono", "true")
        center.addWidget(self.meta)

        # --- параметры конкретного ролика ---
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.cmb_format = QComboBox()
        for label, value in FORMATS:
            self.cmb_format.addItem(label, value)
        self._select(self.cmb_format, item.get("format", "mp4"))
        self.cmb_format.setFixedWidth(150)
        controls.addWidget(self.cmb_format)

        self.cmb_resolution = QComboBox()
        for label, value in RESOLUTIONS:
            self.cmb_resolution.addItem(label, value)
        self._select(self.cmb_resolution, str(item.get("resolution", "1080")))
        self.cmb_resolution.setFixedWidth(130)
        controls.addWidget(self.cmb_resolution)

        self.cmb_codec = QComboBox()
        available = item.get("available_codecs") or []
        for label, value in CODECS:
            if value == "auto" or value in available:
                self.cmb_codec.addItem(label, value)
        self._select(self.cmb_codec, item.get("codec", "auto"))
        self.cmb_codec.setFixedWidth(120)
        controls.addWidget(self.cmb_codec)

        controls.addStretch(1)
        center.addLayout(controls)

        for combo in (self.cmb_format, self.cmb_resolution, self.cmb_codec):
            combo.currentIndexChanged.connect(self._emit_settings)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        center.addWidget(self.progress)

        self.stats = QLabel("")
        self.stats.setProperty("muted", "true")
        self.stats.setVisible(False)
        center.addWidget(self.stats)

        layout.addLayout(center, 1)

        side = QVBoxLayout()
        side.setSpacing(4)
        self.btn_stop = QPushButton()
        self.btn_stop.setProperty("variant", "icon")
        self.btn_stop.setToolTip(t("downloader.btn_stop", "Остановить"))
        self.btn_stop.clicked.connect(lambda: self.stop_requested.emit(self.task_id))
        side.addWidget(self.btn_stop)

        self.btn_remove = QPushButton()
        self.btn_remove.setProperty("variant", "icon")
        self.btn_remove.setToolTip(t("ui.common.remove_from_queue", "Убрать из очереди"))
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self.task_id))
        side.addWidget(self.btn_remove)
        side.addStretch(1)
        layout.addLayout(side, 0)

        self._sync_controls()

    @staticmethod
    def _select(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _badge_kind(status: str) -> str:
        return {
            "queued": "queued", "downloading": "processing",
            "paused": "queued", "error": "error", "done": "done",
        }.get(status, "queued")

    def _sync_controls(self) -> None:
        """Для аудиоформатов разрешение и видеокодек не применяются."""
        audio_only = self.cmb_format.currentData() in AUDIO_ONLY
        self.cmb_resolution.setEnabled(not audio_only)
        self.cmb_codec.setEnabled(not audio_only)

    def _emit_settings(self) -> None:
        self._sync_controls()
        self.settings_changed.emit(
            self.task_id,
            self.cmb_format.currentData(),
            self.cmb_resolution.currentData(),
            self.cmb_codec.currentData(),
        )

    # ------------------------------------------------------------------
    def refresh_icons(self, color: str, danger: str) -> None:
        self.btn_stop.setIcon(icons.icon("stop", color, 13))
        self.btn_remove.setIcon(icons.icon("trash", color, 15))

    def on_thumbnail(self, url: str, pixmap) -> None:
        if url == self._thumb_url:
            self.thumb.setPixmap(fit(pixmap, THUMB_SIZE))

    def set_progress(self, percent: float, speed: str, eta: str) -> None:
        self.progress.setVisible(True)
        self.progress.setValue(int(percent))

        details = [f"{percent:.0f}%"]
        if speed:
            details.append(speed)
        if eta:
            details.append(
                tf("ui.downloader.eta_left", "осталось {time}", time=eta))
        self.stats.setText("  ·  ".join(details))
        self.stats.setVisible(True)

        if percent >= 100:
            self.set_status("done")
        elif speed in ():
            pass
        else:
            self.set_status("downloading")

    def set_status(self, status: str) -> None:
        self.item["status"] = status
        self.badge.setText(status_text(status))
        self.badge.setProperty("badge", self._badge_kind(status))
        self.progress.setProperty("state", status if status in ("done", "error") else "")
        for widget in (self.badge, self.progress):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class DownloaderPage(QWidget):
    """Экран загрузчика целиком."""

    def __init__(self, downloader, channel, loader, parent: QWidget | None = None):
        super().__init__(parent)
        self.downloader = downloader
        self.channel = channel
        self.loader = loader
        self.cards: dict[str, DownloadCard] = {}
        self._icon_color = "#8b919e"
        self._danger_color = "#ef4444"

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(14)

        root.addLayout(self._build_header())
        root.addLayout(self._build_input_row())

        self.hint = QLabel(t("ui.downloader.placeholder", "Вставьте ссылку на ролик или плейлист и нажмите «Добавить»"))
        self.hint.setProperty("muted", "true")
        root.addWidget(self.hint)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.queue_host = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_host)
        self.queue_layout.setContentsMargins(0, 0, 6, 0)
        self.queue_layout.setSpacing(10)
        self.queue_layout.addStretch(1)
        self.scroll.setWidget(self.queue_host)
        root.addWidget(self.scroll, 1)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(92)
        self.log_view.setPlaceholderText(t("ui.downloader.log_title", "Журнал загрузок"))
        root.addWidget(self.log_view)

        self._connect_channel()
        self.loader.loaded.connect(self._on_thumbnail)

        # Очередь, сохранённая с прошлого запуска
        for item in list(getattr(self.downloader.ctx, "download_queue", []) or []):
            self.on_item_added(item)

    # ------------------------------------------------------------------
    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        title = QLabel(t("sections.video_downloader", "Загрузчик"))
        title.setProperty("heading", "1")
        header.addWidget(title)
        header.addStretch(1)

        self.btn_start = QPushButton(t("ui.downloader.start", "  Начать загрузку"))
        self.btn_start.setProperty("variant", "primary")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._on_start)
        header.addWidget(self.btn_start)

        self.btn_stop = QPushButton(t("downloader.btn_stop", "  Стоп"))
        self.btn_stop.setProperty("variant", "danger")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.downloader.stopDownload)
        header.addWidget(self.btn_stop)

        self.btn_folder = QPushButton()
        self.btn_folder.setProperty("variant", "icon")
        self.btn_folder.setToolTip(t("ui.downloader.open_folder", "Открыть папку загрузок"))
        self.btn_folder.setCursor(Qt.PointingHandCursor)
        self.btn_folder.clicked.connect(self.downloader.open_dl_folder)
        header.addWidget(self.btn_folder)
        return header

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.returnPressed.connect(self._on_add)
        row.addWidget(self.url_input, 1)

        self.cmb_format = QComboBox()
        for label, value in FORMATS:
            self.cmb_format.addItem(label, value)
        self.cmb_format.setFixedWidth(160)
        self.cmb_format.currentIndexChanged.connect(self._sync_default_controls)
        row.addWidget(self.cmb_format)

        self.cmb_resolution = QComboBox()
        for label, value in RESOLUTIONS:
            self.cmb_resolution.addItem(label, value)
        self.cmb_resolution.setCurrentIndex(2)     # 1080p
        self.cmb_resolution.setFixedWidth(140)
        row.addWidget(self.cmb_resolution)

        self.btn_add = QPushButton(t("ui.downloader.add", "  Добавить"))
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._on_add)
        row.addWidget(self.btn_add)
        return row

    def _sync_default_controls(self) -> None:
        self.cmb_resolution.setEnabled(self.cmb_format.currentData() not in AUDIO_ONLY)

    # ------------------------------------------------------------------
    def _on_add(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            return
        self.downloader.addVideoToQueue(
            url, self.cmb_format.currentData(), self.cmb_resolution.currentData()
        )
        self.url_input.clear()

    def _on_start(self) -> None:
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.downloader.startDownload()

    # ------------------------------------------------------------------
    def _connect_channel(self) -> None:
        signals = self.channel.signals
        signals.downloader_item_added.connect(self.on_item_added)
        signals.downloader_item_removed.connect(self.on_item_removed)
        signals.downloader_progress.connect(self.on_progress)
        signals.downloader_playlist_found.connect(self.on_playlist)
        signals.downloader_finished.connect(self.on_finished)
        signals.log.connect(self.append_log)

    def on_item_added(self, item: dict) -> None:
        if item["id"] in self.cards:
            return
        card = DownloadCard(item, self.loader)
        card.refresh_icons(self._icon_color, self._danger_color)
        card.remove_requested.connect(self.downloader.removeVideoFromQueue)
        card.stop_requested.connect(self.downloader.stop_single_task)
        card.settings_changed.connect(self.downloader.update_item_settings)
        self.cards[item["id"]] = card
        self.queue_layout.insertWidget(self.queue_layout.count() - 1, card)
        self.hint.setVisible(False)

    def on_item_removed(self, task_id: str) -> None:
        card = self.cards.pop(task_id, None)
        if card is not None:
            card.setParent(None)
            card.deleteLater()
        if not self.cards:
            self.hint.setVisible(True)

    def on_progress(self, task_id: str, percent: float, speed: str, eta: str) -> None:
        card = self.cards.get(task_id)
        if card is not None:
            card.set_progress(percent, speed, eta)

    def on_playlist(self, playlist: dict) -> None:
        dialog = PlaylistDialog(playlist, self)
        if dialog.exec() != QDialog.Accepted:
            return
        urls = dialog.selected_urls()
        if not urls:
            return
        fmt = self.cmb_format.currentData()
        res = self.cmb_resolution.currentData()
        self.append_log(tf(
            "ui.downloader.adding_from_playlist",
            "Добавляю из плейлиста: {count} шт.",
            count=len(urls)), "info")
        for url in urls:
            self.downloader.addVideoToQueue(url, fmt, res)

    def on_finished(self) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _on_thumbnail(self, url: str, pixmap) -> None:
        for card in self.cards.values():
            card.on_thumbnail(url, pixmap)

    def append_log(self, message: str, level: str = "info", code: str = "",
                   source: str = "") -> None:
        # Журнал экрана показывает только свои сообщения: канал общий
        # на всё приложение, и раньше сюда сыпались логи конвертера
        if source not in ("", "downloader"):
            return
        prefix = {"error": "✕", "success": "✓", "warn": "!"}.get(level, "·")
        self.log_view.appendPlainText(f"{prefix} {message}")

    # ------------------------------------------------------------------
    def apply_palette(self, palette: dict[str, str]) -> None:
        self._icon_color = palette.get("text-secondary", "#8b919e")
        self._danger_color = palette.get("danger-color", "#ef4444")
        text = palette.get("text-color", "#e6e8ec")
        self.btn_start.setIcon(icons.icon("download", "#ffffff", 15))
        self.btn_stop.setIcon(icons.icon("stop", self._danger_color, 12))
        self.btn_add.setIcon(icons.icon("plus", text, 15))
        self.btn_folder.setIcon(icons.icon("folder", self._icon_color, 16))
        for card in self.cards.values():
            card.refresh_icons(self._icon_color, self._danger_color)
