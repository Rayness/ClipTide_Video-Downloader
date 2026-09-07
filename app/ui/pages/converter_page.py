# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""Экран конвертера: очередь файлов, настройки вывода и журнал."""

from __future__ import annotations

import base64
import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.modules.converter.encoders import VIDEO_ENCODERS, available_encoders
from ..i18n import t
from ..widgets import icons

THUMB_SIZE = QSize(96, 54)

def status_text(status: str) -> str:
    """Подпись статуса берём из словаря переводов."""
    return {
        "queued":     t("converter.status_queued", "В очереди"),
        "processing": t("converter.status_processing", "Конвертация"),
        "done":       t("converter.status_done", "Готово"),
        "error":      t("converter.status_error", "Ошибка"),
    }.get(status, status)

VIDEO_CONTAINERS = [("MP4", "mp4"), ("MKV", "mkv"), ("MOV", "mov"), ("WEBM", "webm"), ("AVI", "avi")]
AUDIO_CONTAINERS = [("MP3", "mp3"), ("AAC", "aac"), ("WAV", "wav"), ("FLAC", "flac"), ("OPUS", "opus")]
IMAGE_CONTAINERS = [("JPG", "jpg"), ("PNG", "png"), ("WEBP", "webp"), ("BMP", "bmp"), ("ICO", "ico"), ("PDF", "pdf")]

RESOLUTIONS = [
    (t("converter.val_original", "Оригинал"), "original"), ("2160p (4K)", "4K"), ("1440p (2K)", "2K"),
    ("1080p", "1080"), ("720p", "720"), ("480p", "480"), ("360p", "360"),
]

IMAGE_RESIZES = [
    (t("converter.val_original", "Оригинал"), "original"), ("50%", "50%"), ("25%", "25%"),
    ("Не больше 1920px", "1920"), ("Не больше 1080px", "1080"),
]

#: Расширения источников, которые обрабатываются как изображения/документы
SOURCE_IMAGE_EXTENSIONS = {
    "jpg", "jpeg", "png", "webp", "bmp", "ico", "tiff", "tif", "pdf",
}


def _pixmap_from_data_uri(data_uri: str | None) -> QPixmap | None:
    if not data_uri or "," not in data_uri:
        return None
    try:
        raw = base64.b64decode(data_uri.split(",", 1)[1])
    except (ValueError, TypeError):
        return None
    pixmap = QPixmap()
    return pixmap if pixmap.loadFromData(raw) else None


def _placeholder(color: str = "#2a2e36") -> QPixmap:
    pixmap = QPixmap(THUMB_SIZE)
    pixmap.fill(QColor(color))
    return pixmap


def _fit_thumbnail(pixmap: QPixmap, background: str = "#0e1014") -> QPixmap:
    """
    Вписывает кадр в рамку превью с сохранением пропорций.
    setScaledContents растягивал картинку: вертикальное фото и кадр 21:9
    одинаково превращались в 96x54 и выглядели сплющенными.
    """
    canvas = QPixmap(THUMB_SIZE)
    canvas.fill(QColor(background))
    if pixmap.isNull():
        return canvas

    scaled = pixmap.scaled(THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    painter = QPainter(canvas)
    painter.drawPixmap(
        (THUMB_SIZE.width() - scaled.width()) // 2,
        (THUMB_SIZE.height() - scaled.height()) // 2,
        scaled,
    )
    painter.end()
    return canvas


class TaskCard(QFrame):
    """Карточка одного файла в очереди."""

    remove_requested = Signal(str)

    def __init__(self, item: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        self.task_id = item["id"]
        self.item = item

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        self.thumb = QLabel()
        self.thumb.setFixedSize(THUMB_SIZE)
        source = _pixmap_from_data_uri(item.get("thumbnail"))
        self.thumb.setPixmap(_fit_thumbnail(source) if source else _placeholder())
        layout.addWidget(self.thumb)

        center = QVBoxLayout()
        center.setSpacing(5)

        top = QHBoxLayout()
        self.name = QLabel(item.get("filename", ""))
        self.name.setProperty("heading", "2")
        self.name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top.addWidget(self.name, 1)

        self.badge = QLabel(status_text(item.get("status", "queued")))
        self.badge.setProperty("badge", item.get("status", "queued"))
        top.addWidget(self.badge, 0, Qt.AlignRight)
        center.addLayout(top)

        self.meta = QLabel(self._meta_text(item))
        self.meta.setProperty("mono", "true")
        center.addWidget(self.meta)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        # Пустая полоса у файла, который ещё не обрабатывался, только шумит
        self.progress.setVisible(item.get("status") not in (None, "queued"))
        center.addWidget(self.progress)

        layout.addLayout(center, 1)

        self.btn_remove = QPushButton()
        self.btn_remove.setProperty("variant", "icon")
        self.btn_remove.setToolTip("Убрать из очереди")
        self.btn_remove.setCursor(Qt.PointingHandCursor)
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self.task_id))
        layout.addWidget(self.btn_remove, 0, Qt.AlignTop)

    @staticmethod
    def _meta_text(item: dict) -> str:
        details = item.get("details") or {}
        parts = []
        resolution = details.get("resolution")
        if resolution and resolution != "?":
            parts.append(str(resolution))
        codec = details.get("codec")
        if codec and codec != "?":
            parts.append(str(codec))
        fps = details.get("fps")
        if fps:
            parts.append(f"{fps} fps")
        audio = details.get("audio")
        if audio and audio != "?":
            parts.append(str(audio))
        duration = item.get("duration") or 0
        if duration:
            parts.append(f"{int(duration) // 60:02d}:{int(duration) % 60:02d}")
        if item.get("error"):
            return str(item["error"])
        return "  ·  ".join(parts) if parts else "метаданные недоступны"

    def refresh_icons(self, color: str) -> None:
        self.btn_remove.setIcon(icons.icon("trash", color, 15))

    def set_progress(self, text: str, percent: int, status: str | None = None) -> None:
        self.progress.setValue(max(0, min(100, percent)))
        if status:
            self.set_status(status)

    def set_status(self, status: str) -> None:
        self.item["status"] = status
        self.progress.setVisible(status != "queued")
        self.badge.setText(status_text(status))
        self.badge.setProperty("badge", status)
        self.progress.setProperty("state", status if status in ("done", "error") else "")
        for widget in (self.badge, self.progress):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class SkeletonCard(QFrame):
    """Заглушка, пока читаются метаданные файла."""

    def __init__(self, task_id: str, filename: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        self.task_id = task_id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        thumb = QLabel()
        thumb.setFixedSize(THUMB_SIZE)
        thumb.setPixmap(_placeholder())
        layout.addWidget(thumb)

        center = QVBoxLayout()
        center.setSpacing(5)
        name = QLabel(filename)
        name.setProperty("heading", "2")
        center.addWidget(name)
        hint = QLabel("Чтение метаданных...")
        hint.setProperty("muted", "true")
        center.addWidget(hint)
        bar = QProgressBar()
        bar.setRange(0, 0)          # неопределённый прогресс
        bar.setTextVisible(False)
        center.addWidget(bar)
        layout.addLayout(center, 1)


class ConverterPage(QWidget):
    """Экран конвертера целиком."""

    def __init__(self, converter, channel, parent: QWidget | None = None):
        super().__init__(parent)
        self.converter = converter
        self.channel = channel
        self.cards: dict[str, TaskCard] = {}
        self.skeletons: dict[str, SkeletonCard] = {}
        self._icon_color = "#8b919e"

        self.setAcceptDrops(True)

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(20)

        root.addLayout(self._build_queue_column(), 1)
        root.addWidget(self._build_settings_panel(), 0)

        self._connect_channel()

    # ------------------------------------------------------------------
    # Левая колонка: очередь
    # ------------------------------------------------------------------
    def _build_queue_column(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(t("sections.converter", "Конвертер"))
        title.setProperty("heading", "1")
        header.addWidget(title)
        header.addStretch(1)

        self.btn_add = QPushButton(t("converter.add_files_btn", "  Добавить файлы"))
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self.converter.openFile)
        header.addWidget(self.btn_add)

        self.btn_start = QPushButton(t("converter.btn_convert", "  Начать"))
        self.btn_start.setProperty("variant", "primary")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._on_start)
        header.addWidget(self.btn_start)

        self.btn_stop = QPushButton(t("converter.btn_stop", "  Стоп"))
        self.btn_stop.setProperty("variant", "danger")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.converter.stop_conversion)
        header.addWidget(self.btn_stop)

        column.addLayout(header)

        self.hint = QLabel("Перетащите файлы сюда или нажмите «Добавить файлы»")
        self.hint.setProperty("muted", "true")
        column.addWidget(self.hint)

        # Прокручиваемый список карточек
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.queue_host = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_host)
        self.queue_layout.setContentsMargins(0, 0, 6, 0)
        self.queue_layout.setSpacing(10)
        self.queue_layout.addStretch(1)
        self.scroll.setWidget(self.queue_host)
        column.addWidget(self.scroll, 1)

        # Журнал
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(96)
        self.log_view.setPlaceholderText("Журнал конвертации")
        column.addWidget(self.log_view)

        return column

    # ------------------------------------------------------------------
    # Правая колонка: настройки
    # ------------------------------------------------------------------
    def _build_settings_panel(self) -> QWidget:
        """
        Панель настроек разделена по типам источника.

        Одни настройки на всю очередь не работают: если выбрать MP4, а в
        очереди лежит PNG, картинку невозможно сохранить в видеоконтейнер —
        Pillow падал с KeyError. Поэтому каждый файл получает настройки
        своего раздела, а какой именно — решает его собственное расширение.
        """
        panel = QFrame()
        panel.setProperty("card", "true")
        panel.setFixedWidth(300)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(12)

        heading = QLabel(t("converter.convertion_settings", "Параметры вывода"))
        heading.setProperty("heading", "2")
        layout.addWidget(heading)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_media_tab(), "Медиа")
        self.tabs.addTab(self._build_image_tab(), "Изображения")
        layout.addWidget(self.tabs)

        separator = QFrame()
        separator.setProperty("separator", "true")
        layout.addWidget(separator)

        self.lbl_output = QLabel()
        self.lbl_output.setProperty("muted", "true")
        layout.addWidget(self.lbl_output)

        self.btn_output = QPushButton("  Папка сохранения")
        self.btn_output.setCursor(Qt.PointingHandCursor)
        self.btn_output.clicked.connect(self._choose_output)
        layout.addWidget(self.btn_output)

        layout.addStretch(1)

        self.lbl_encoder_hint = QLabel()
        self.lbl_encoder_hint.setProperty("muted", "true")
        self.lbl_encoder_hint.setWordWrap(True)
        layout.addWidget(self.lbl_encoder_hint)

        self._sync_controls()
        self._refresh_output_label()
        return panel

    def _build_media_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(10)

        grid.addWidget(self._label(t("converter.lbl_format", "Формат")), 0, 0)
        self.cmb_format = QComboBox()
        for label, value in VIDEO_CONTAINERS:
            self.cmb_format.addItem(f"{label} · видео", value)
        self.cmb_format.insertSeparator(self.cmb_format.count())
        for label, value in AUDIO_CONTAINERS:
            self.cmb_format.addItem(f"{label} · аудио", value)
        self.cmb_format.currentIndexChanged.connect(self._sync_controls)
        grid.addWidget(self.cmb_format, 0, 1)

        grid.addWidget(self._label(t("converter.lbl_codec", "Кодек")), 1, 0)
        self.cmb_codec = QComboBox()
        self._fill_codecs()
        grid.addWidget(self.cmb_codec, 1, 1)

        grid.addWidget(self._label(t("converter.lbl_resolution", "Разрешение")), 2, 0)
        self.cmb_resolution = QComboBox()
        for label, value in RESOLUTIONS:
            self.cmb_resolution.addItem(label, value)
        grid.addWidget(self.cmb_resolution, 2, 1)

        layout.addLayout(grid)

        row = QHBoxLayout()
        self.lbl_quality = QLabel(t("converter.lbl_quality", "Качество (CRF)"))
        self.lbl_quality.setProperty("muted", "true")
        row.addWidget(self.lbl_quality)
        row.addStretch(1)
        self.lbl_quality_value = QLabel("23")
        row.addWidget(self.lbl_quality_value)
        layout.addLayout(row)

        self.sld_quality = QSlider(Qt.Horizontal)
        self.sld_quality.setRange(16, 35)
        self.sld_quality.setValue(23)
        self.sld_quality.valueChanged.connect(lambda v: self.lbl_quality_value.setText(str(v)))
        layout.addWidget(self.sld_quality)

        scale = QHBoxLayout()
        better = QLabel(t("converter.val_better", "Лучше"))
        better.setProperty("muted", "true")
        smaller = QLabel(t("converter.val_worse", "Меньше"))
        smaller.setProperty("muted", "true")
        scale.addWidget(better)
        scale.addStretch(1)
        scale.addWidget(smaller)
        layout.addLayout(scale)

        layout.addStretch(1)
        return tab

    def _build_image_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(10)

        grid.addWidget(self._label(t("converter.lbl_format", "Формат")), 0, 0)
        self.cmb_img_format = QComboBox()
        for label, value in IMAGE_CONTAINERS:
            self.cmb_img_format.addItem(label, value)
        grid.addWidget(self.cmb_img_format, 0, 1)

        grid.addWidget(self._label(t("converter.lbl_size", "Размер")), 1, 0)
        self.cmb_img_resize = QComboBox()
        for label, value in IMAGE_RESIZES:
            self.cmb_img_resize.addItem(label, value)
        grid.addWidget(self.cmb_img_resize, 1, 1)

        layout.addLayout(grid)

        row = QHBoxLayout()
        caption = QLabel("Качество (%)")
        caption.setProperty("muted", "true")
        row.addWidget(caption)
        row.addStretch(1)
        self.lbl_img_quality_value = QLabel("90")
        row.addWidget(self.lbl_img_quality_value)
        layout.addLayout(row)

        self.sld_img_quality = QSlider(Qt.Horizontal)
        self.sld_img_quality.setRange(10, 100)
        self.sld_img_quality.setValue(90)
        self.sld_img_quality.valueChanged.connect(
            lambda v: self.lbl_img_quality_value.setText(str(v))
        )
        layout.addWidget(self.sld_img_quality)

        hint = QLabel("Многостраничный PDF раскладывается в папку по страницам.")
        hint.setProperty("muted", "true")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch(1)
        return tab

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("muted", "true")
        return label

    def _fill_codecs(self) -> None:
        """В список попадают только кодировщики, реально доступные в сборке."""
        self.cmb_codec.clear()
        self.cmb_codec.addItem("Автоматически", "auto")

        present = available_encoders()
        friendly = [
            ("H.264 (x264)", "libx264"),
            ("H.265 / HEVC (x265)", "libx265"),
            ("VP9", "libvpx-vp9"),
            ("AV1 (SVT)", "libsvtav1"),
            ("H.264 · NVIDIA NVENC", "h264_nvenc"),
            ("H.265 · NVIDIA NVENC", "hevc_nvenc"),
            ("H.264 · Intel QSV", "h264_qsv"),
            ("H.265 · Intel QSV", "hevc_qsv"),
            ("H.264 · AMD AMF", "h264_amf"),
            ("H.265 · AMD AMF", "hevc_amf"),
        ]
        hardware_found = False
        for label, value in friendly:
            if value in present:
                self.cmb_codec.addItem(label, value)
                if VIDEO_ENCODERS.get(value, {}).get("hardware"):
                    hardware_found = True
        self.cmb_codec.addItem("Без перекодирования (copy)", "copy")
        self._hardware_found = hardware_found

    # ------------------------------------------------------------------
    def _sync_controls(self) -> None:
        """Для аудиоформатов кодек и разрешение смысла не имеют."""
        fmt = self.cmb_format.currentData()
        is_audio = fmt in {v for _, v in AUDIO_CONTAINERS}

        self.cmb_codec.setEnabled(not is_audio)
        self.cmb_resolution.setEnabled(not is_audio)
        self.sld_quality.setEnabled(not is_audio)
        self.lbl_quality.setText(
            "Битрейт задаётся профилем" if is_audio else t("converter.lbl_quality", "Качество (CRF)")
        )

        if getattr(self, "_hardware_found", False):
            self.lbl_encoder_hint.setText(
                "Найдено аппаратное кодирование. «Автоматически» задействует GPU."
            )
        else:
            self.lbl_encoder_hint.setText(
                "Аппаратное кодирование недоступно, используется CPU."
            )

    def _refresh_output_label(self) -> None:
        folder = str(getattr(self.converter.ctx, "converter_folder", "") or "")
        metrics = self.lbl_output.fontMetrics()
        # Длинный путь раньше переносился на пять строк и распирал панель
        elided = metrics.elidedText(folder, Qt.ElideMiddle, 250)
        self.lbl_output.setText("Сохранять в:\n" + elided)
        self.lbl_output.setToolTip(folder)

    def _choose_output(self) -> None:
        folder = self.channel.pick_folder(
            "Папка для сохранения", getattr(self.converter.ctx, "converter_folder", "")
        )
        if folder:
            self.converter.ctx.converter_folder = folder
            self.converter.ctx.update_config_value("Settings", "converter_folder", folder)
            self._refresh_output_label()

    # ------------------------------------------------------------------
    # Запуск
    # ------------------------------------------------------------------
    def _settings_for(self, item: dict) -> dict:
        """Настройки под тип конкретного файла, а не одни на всю очередь."""
        ext = os.path.splitext(item.get("filename", ""))[1].lstrip(".").lower()

        if ext in SOURCE_IMAGE_EXTENSIONS:
            return {
                "type": "image",
                "format": self.cmb_img_format.currentData(),
                "quality": str(self.sld_img_quality.value()),
                "resize": self.cmb_img_resize.currentData(),
            }

        return {
            "type": "video",
            "format": self.cmb_format.currentData(),
            "codec": self.cmb_codec.currentData(),
            "quality": str(self.sld_quality.value()),
            "resolution": self.cmb_resolution.currentData(),
        }

    def _on_start(self) -> None:
        with self.converter._lock:
            items = list(self.converter.queue)
        if not items:
            self.append_log("Очередь пуста", "info")
            return

        settings_map = {item["id"]: self._settings_for(item) for item in items}
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.converter.start_conversion(settings_map)

    # ------------------------------------------------------------------
    # Приём событий из канала
    # ------------------------------------------------------------------
    def _connect_channel(self) -> None:
        signals = self.channel.signals
        signals.converter_skeleton.connect(self.on_skeleton)
        signals.converter_skeleton_removed.connect(self.on_skeleton_removed)
        signals.converter_item_added.connect(self.on_item_added)
        signals.converter_progress.connect(self.on_progress)
        signals.converter_finished.connect(self.on_finished)
        signals.log.connect(self.append_log)

    def _insert_card(self, widget: QWidget) -> None:
        # Перед распоркой в конце layout
        self.queue_layout.insertWidget(self.queue_layout.count() - 1, widget)
        self.hint.setVisible(False)

    def on_skeleton(self, task_id: str, filename: str) -> None:
        card = SkeletonCard(task_id, filename)
        self.skeletons[task_id] = card
        self._insert_card(card)

    def on_skeleton_removed(self, task_id: str) -> None:
        card = self.skeletons.pop(task_id, None)
        if card is not None:
            card.setParent(None)
            card.deleteLater()

    def on_item_added(self, item: dict) -> None:
        self.on_skeleton_removed(item.get("temp_id") or item["id"])
        card = TaskCard(item)
        card.refresh_icons(self._icon_color)
        card.remove_requested.connect(self.on_remove)
        self.cards[item["id"]] = card
        self._insert_card(card)

    def on_remove(self, task_id: str) -> None:
        self.converter.remove_item(task_id)
        card = self.cards.pop(task_id, None)
        if card is not None:
            card.setParent(None)
            card.deleteLater()
        if not self.cards and not self.skeletons:
            self.hint.setVisible(True)

    def on_progress(self, task_id: str, text: str, percent: int) -> None:
        card = self.cards.get(task_id)
        if card is None:
            return
        status = None
        if text == "Done":
            status = "done"
        elif text == "Error":
            status = "error"
        elif text == "Stopped":
            status = "queued"
        elif percent >= 0:
            status = "processing"
        card.set_progress(text, percent, status)

    def on_finished(self) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def append_log(self, message: str, level: str = "info", code: str = "",
                   source: str = "") -> None:
        # Только собственные сообщения — сигнал log общий на приложение
        if source not in ("", "converter"):
            return
        prefix = {"error": "✕", "success": "✓", "warn": "!"}.get(level, "·")
        self.log_view.appendPlainText(f"{prefix} {message}")

    # ------------------------------------------------------------------
    # Перетаскивание файлов
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile() and os.path.isfile(url.toLocalFile())
        ]
        if paths:
            self.converter.add_paths(paths)
            event.acceptProposedAction()

    # ------------------------------------------------------------------
    def apply_palette(self, palette: dict[str, str]) -> None:
        self._icon_color = palette.get("text-secondary", "#8b919e")
        self.btn_add.setIcon(icons.icon("plus", palette.get("text-color", "#e6e8ec"), 15))
        self.btn_start.setIcon(icons.icon("play", "#ffffff", 13))
        self.btn_stop.setIcon(icons.icon("stop", palette.get("danger-color", "#ef4444"), 12))
        self.btn_output.setIcon(icons.icon("folder", palette.get("text-color", "#e6e8ec"), 15))
        for card in self.cards.values():
            card.refresh_icons(self._icon_color)
