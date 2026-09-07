# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""Экран редактора: предпросмотр кадра, сегменты и обрезка."""

from __future__ import annotations

import os

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..i18n import t
from ..widgets import icons
from ..widgets.thumbnail import fit, pixmap_from_data_uri

PREVIEW_SIZE = QSize(640, 360)

#: Пауза после последнего движения ползунка, прежде чем запрашивать кадр.
#: Без неё каждый пиксель перемотки порождал запуск ffmpeg.
SCRUB_DEBOUNCE_MS = 120


def format_timecode(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    millis = int((seconds - total) * 1000)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}.{millis:03d}"
    return f"{minutes:02d}:{secs:02d}.{millis:03d}"


class _FrameSignals(QObject):
    ready = Signal(float, str)      # timestamp, data-uri


class _FrameTask(QRunnable):
    """Забирает кадр в фоне: ffmpeg занимает ~100 мс, главный поток блокировать нельзя."""

    def __init__(self, editor, path: str, timestamp: float, signals: _FrameSignals):
        super().__init__()
        self.editor = editor
        self.path = path
        self.timestamp = timestamp
        self.signals = signals

    def run(self) -> None:
        data_uri = self.editor.get_frame(self.path, self.timestamp)
        if data_uri:
            self.signals.ready.emit(self.timestamp, data_uri)


class EditorPage(QWidget):
    def __init__(self, editor, channel, parent: QWidget | None = None):
        super().__init__(parent)
        self.editor = editor
        self.channel = channel

        self.file_path: str | None = None
        self.duration: float = 0.0
        self.segments: list[dict] = []
        self._pending_timestamp = 0.0
        self._icon_color = "#8b919e"

        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)     # кадры нужны по очереди, не пачкой
        self._frame_signals = _FrameSignals()
        self._frame_signals.ready.connect(self._on_frame_ready)

        self._scrub_timer = QTimer(self)
        self._scrub_timer.setSingleShot(True)
        self._scrub_timer.setInterval(SCRUB_DEBOUNCE_MS)
        self._scrub_timer.timeout.connect(self._request_frame)

        self.setAcceptDrops(True)

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(20)
        root.addLayout(self._build_preview_column(), 1)
        root.addWidget(self._build_side_panel(), 0)

        self._connect_channel()
        self._update_enabled()

    # ------------------------------------------------------------------
    def _build_preview_column(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(t("sections.editor", "Редактор"))
        title.setProperty("heading", "1")
        header.addWidget(title)
        header.addStretch(1)

        self.btn_open = QPushButton("  Открыть видео")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self.editor.open_file)
        header.addWidget(self.btn_open)
        column.addLayout(header)

        self.file_label = QLabel("Файл не выбран — откройте видео или перетащите его сюда")
        self.file_label.setProperty("muted", "true")
        column.addWidget(self.file_label)

        self.preview = QLabel()
        self.preview.setObjectName("DropZone")
        self.preview.setMinimumSize(PREVIEW_SIZE)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setText("Кадр появится после открытия файла")
        column.addWidget(self.preview, 1)

        # --- таймлайн ---
        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setRange(0, 1000)
        self.timeline.valueChanged.connect(self._on_scrub)
        column.addWidget(self.timeline)

        times = QHBoxLayout()
        self.lbl_position = QLabel("00:00.000")
        self.lbl_position.setProperty("mono", "true")
        times.addWidget(self.lbl_position)
        times.addStretch(1)
        self.lbl_duration = QLabel("00:00.000")
        self.lbl_duration.setProperty("mono", "true")
        times.addWidget(self.lbl_duration)
        column.addLayout(times)

        marks = QHBoxLayout()
        marks.setSpacing(8)
        self.btn_mark_in = QPushButton("Отметить начало")
        self.btn_mark_in.clicked.connect(self._mark_in)
        marks.addWidget(self.btn_mark_in)

        self.btn_mark_out = QPushButton("Отметить конец")
        self.btn_mark_out.clicked.connect(self._mark_out)
        marks.addWidget(self.btn_mark_out)

        self.lbl_pending = QLabel("")
        self.lbl_pending.setProperty("muted", "true")
        marks.addWidget(self.lbl_pending)
        marks.addStretch(1)
        column.addLayout(marks)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        column.addWidget(self.progress)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setProperty("muted", "true")
        self.lbl_progress.setVisible(False)
        column.addWidget(self.lbl_progress)

        return column

    def _build_side_panel(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("card", "true")
        panel.setFixedWidth(320)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        heading = QLabel("Сегменты")
        heading.setProperty("heading", "2")
        layout.addWidget(heading)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Начало", "Конец", "Длина"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_remove_segment = QPushButton("Удалить")
        self.btn_remove_segment.setProperty("variant", "danger")
        self.btn_remove_segment.clicked.connect(self._remove_selected_segment)
        row.addWidget(self.btn_remove_segment)

        self.btn_clear_segments = QPushButton("Очистить")
        self.btn_clear_segments.setProperty("variant", "ghost")
        self.btn_clear_segments.clicked.connect(self._clear_segments)
        row.addWidget(self.btn_clear_segments)
        layout.addLayout(row)

        separator = QFrame()
        separator.setProperty("separator", "true")
        layout.addWidget(separator)

        mode_label = QLabel("Результат")
        mode_label.setProperty("muted", "true")
        layout.addWidget(mode_label)

        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem("Отдельными файлами", "separate")
        self.cmb_mode.addItem("Склеить в один файл", "merge")
        layout.addWidget(self.cmb_mode)

        codec_label = QLabel("Кодек")
        codec_label.setProperty("muted", "true")
        layout.addWidget(codec_label)

        self.cmb_codec = QComboBox()
        self.cmb_codec.addItem("H.264", "h264")
        self.cmb_codec.addItem("H.265 / HEVC", "h265")
        self.cmb_codec.addItem("Без перекодирования (быстро)", "copy")
        self.cmb_codec.currentIndexChanged.connect(self._save_codec)
        layout.addWidget(self.cmb_codec)

        self.lbl_output = QLabel()
        self.lbl_output.setProperty("muted", "true")
        layout.addWidget(self.lbl_output)

        self.btn_output = QPushButton("  Папка сохранения")
        self.btn_output.clicked.connect(self._choose_output)
        layout.addWidget(self.btn_output)

        layout.addStretch(1)

        self.btn_trim = QPushButton("  Обрезать")
        self.btn_trim.setProperty("variant", "primary")
        self.btn_trim.clicked.connect(self._start_trim)
        layout.addWidget(self.btn_trim)

        self.btn_stop = QPushButton("  Остановить")
        self.btn_stop.setProperty("variant", "danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.editor.stop_trim)
        layout.addWidget(self.btn_stop)

        self.output_dir = str(getattr(self.editor.ctx, "download_folder", "") or "")
        self._refresh_output_label()
        self._load_codec()
        return panel

    # ------------------------------------------------------------------
    # Файл
    # ------------------------------------------------------------------
    def _connect_channel(self) -> None:
        signals = self.channel.signals
        signals.editor_file_loaded.connect(self.on_file_loaded)
        signals.editor_trim_started.connect(self.on_trim_started)
        signals.editor_trim_progress.connect(self.on_trim_progress)
        signals.editor_trim_done.connect(self.on_trim_done)
        signals.editor_trim_error.connect(self.on_trim_error)
        signals.editor_trim_stopped.connect(self.on_trim_stopped)

    def on_file_loaded(self, data: dict) -> None:
        self.file_path = data["path"]
        self.duration = float(data.get("duration") or 0)
        self.segments.clear()
        self._refresh_table()

        details = [
            f"{data.get('width')}x{data.get('height')}",
            str(data.get("codec", "")),
            f"{data.get('fps', 0):g} fps",
            format_timecode(self.duration),
        ]
        self.file_label.setText(f"{data['filename']}   ·   " + "  ·  ".join(details))
        self.lbl_duration.setText(format_timecode(self.duration))

        thumb = pixmap_from_data_uri(data.get("thumb"))
        if thumb is not None:
            self._set_preview(thumb)

        self.timeline.setValue(0)
        self._update_enabled()
        self._request_frame()

    # ------------------------------------------------------------------
    # Перемотка
    # ------------------------------------------------------------------
    def _current_time(self) -> float:
        if self.duration <= 0:
            return 0.0
        return self.timeline.value() / 1000 * self.duration

    def _on_scrub(self) -> None:
        self.lbl_position.setText(format_timecode(self._current_time()))
        # Ждём, пока пользователь остановится: иначе на каждый шаг ползунка
        # запускался бы отдельный ffmpeg
        self._scrub_timer.start()

    def _request_frame(self) -> None:
        if not self.file_path:
            return
        timestamp = self._current_time()
        self._pending_timestamp = timestamp
        self._pool.start(_FrameTask(self.editor, self.file_path, timestamp,
                                    self._frame_signals))

    def _on_frame_ready(self, timestamp: float, data_uri: str) -> None:
        # Кадр мог прийти уже неактуальным, если пользователь продолжил мотать
        if abs(timestamp - self._pending_timestamp) > 1e-6:
            return
        pixmap = pixmap_from_data_uri(data_uri)
        if pixmap is not None:
            self._set_preview(pixmap)

    def _set_preview(self, pixmap) -> None:
        self.preview.setPixmap(fit(pixmap, PREVIEW_SIZE))
        self.preview.setProperty("filled", "true")
        self.preview.style().unpolish(self.preview)
        self.preview.style().polish(self.preview)

    # ------------------------------------------------------------------
    # Сегменты
    # ------------------------------------------------------------------
    def _mark_in(self) -> None:
        self._pending_start = self._current_time()
        self.lbl_pending.setText(f"Начало: {format_timecode(self._pending_start)}")

    def _mark_out(self) -> None:
        start = getattr(self, "_pending_start", None)
        if start is None:
            self.lbl_pending.setText("Сначала отметьте начало")
            return
        end = self._current_time()
        if end <= start:
            self.lbl_pending.setText("Конец должен быть позже начала")
            return
        self.segments.append({"start": start, "end": end})
        self._pending_start = None
        self.lbl_pending.setText("")
        self._refresh_table()
        self._update_enabled()

    def _remove_selected_segment(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.segments):
            self.segments.pop(row)
            self._refresh_table()
            self._update_enabled()

    def _clear_segments(self) -> None:
        self.segments.clear()
        self._refresh_table()
        self._update_enabled()

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self.segments))
        for row, segment in enumerate(self.segments):
            length = segment["end"] - segment["start"]
            for column, value in enumerate((
                format_timecode(segment["start"]),
                format_timecode(segment["end"]),
                format_timecode(length),
            )):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, cell)

    # ------------------------------------------------------------------
    # Настройки и запуск
    # ------------------------------------------------------------------
    def _load_codec(self) -> None:
        codec = self.editor.ctx.config.get("Editor", "codec", fallback="h264")
        index = self.cmb_codec.findData(codec)
        if index >= 0:
            self.cmb_codec.setCurrentIndex(index)

    def _save_codec(self) -> None:
        self.editor.ctx.update_config_value("Editor", "codec", self.cmb_codec.currentData())

    def _refresh_output_label(self) -> None:
        metrics = self.lbl_output.fontMetrics()
        elided = metrics.elidedText(self.output_dir, Qt.ElideMiddle, 270)
        self.lbl_output.setText(f"Сохранять в:\n{elided}")
        self.lbl_output.setToolTip(self.output_dir)

    def _choose_output(self) -> None:
        folder = self.channel.pick_folder("Папка для результата", self.output_dir)
        if folder:
            self.output_dir = folder
            self._refresh_output_label()

    def _update_enabled(self) -> None:
        has_file = bool(self.file_path)
        has_segments = bool(self.segments)
        for widget in (self.timeline, self.btn_mark_in, self.btn_mark_out):
            widget.setEnabled(has_file)
        self.btn_trim.setEnabled(has_file and has_segments)
        self.btn_remove_segment.setEnabled(has_segments)
        self.btn_clear_segments.setEnabled(has_segments)

    def _start_trim(self) -> None:
        if not self.file_path or not self.segments:
            return
        self.editor.trim_video(
            self.file_path, list(self.segments),
            self.cmb_mode.currentData(), self.output_dir,
        )

    # ------------------------------------------------------------------
    # События обрезки
    # ------------------------------------------------------------------
    def on_trim_started(self) -> None:
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.lbl_progress.setVisible(True)
        self.btn_trim.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def on_trim_progress(self, percent: int, label: str) -> None:
        self.progress.setValue(percent)
        self.lbl_progress.setText(label)

    def on_trim_done(self, mode: str, folder: str) -> None:
        self.progress.setValue(100)
        self.lbl_progress.setText(f"Готово · {folder}")
        self._reset_buttons()

    def on_trim_error(self, message: str) -> None:
        self.lbl_progress.setText(f"Ошибка: {message}" if message else "Ошибка обрезки")
        self.progress.setProperty("state", "error")
        self.progress.style().unpolish(self.progress)
        self.progress.style().polish(self.progress)
        self._reset_buttons()

    def on_trim_stopped(self) -> None:
        self.lbl_progress.setText("Остановлено")
        self._reset_buttons()

    def _reset_buttons(self) -> None:
        self.btn_stop.setEnabled(False)
        self._update_enabled()

    # ------------------------------------------------------------------
    # Перетаскивание
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.preview.setProperty("hover", "true")
            self.preview.style().unpolish(self.preview)
            self.preview.style().polish(self.preview)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.preview.setProperty("hover", "")
        self.preview.style().unpolish(self.preview)
        self.preview.style().polish(self.preview)

    def dropEvent(self, event):
        self.dragLeaveEvent(event)
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if url.isLocalFile() and os.path.isfile(path):
                self.editor.load_file(path)
                event.acceptProposedAction()
                return

    # ------------------------------------------------------------------
    def apply_palette(self, palette: dict[str, str]) -> None:
        self._icon_color = palette.get("text-secondary", "#8b919e")
        text = palette.get("text-color", "#e6e8ec")
        self.btn_open.setIcon(icons.icon("folder", text, 15))
        self.btn_output.setIcon(icons.icon("folder", text, 15))
        self.btn_trim.setIcon(icons.icon("editor", "#ffffff", 15))
        self.btn_stop.setIcon(icons.icon("stop", palette.get("danger-color", "#ef4444"), 12))
