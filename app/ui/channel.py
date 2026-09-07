# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Реализация UIChannel поверх Qt.

Загрузчик, конвертер и редактор работают в фоновых потоках и зовут методы
канала оттуда. Qt запрещает трогать виджеты не из главного потока, поэтому
каждый вызов превращается в сигнал: соединение через Qt.QueuedConnection
само перекладывает вызов в очередь событий главного потока.

Это тот же контракт, что у WebViewChannel, — модули логики не знают,
какой интерфейс под ними.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.core.ui_channel import UIChannel


class QtSignals(QObject):
    """Сигналы канала. Отдельный QObject, чтобы UIChannel остался обычным классом."""

    # --- общее ---
    log = Signal(str, str, str, str)             # message, level, code, source
    status = Signal(str)
    alert = Signal(str, str, str)                # text, title, level
    generic = Signal(str, tuple)                 # имя, аргументы

    # --- загрузчик ---
    downloader_item_added = Signal(dict)
    downloader_item_removed = Signal(str)
    downloader_progress = Signal(str, float, str, str)   # id, %, скорость, ETA
    downloader_placeholder_removed = Signal(str)
    downloader_playlist_found = Signal(dict)
    downloader_finished = Signal()

    # --- конвертер ---
    converter_skeleton = Signal(str, str)
    converter_skeleton_removed = Signal(str)
    converter_item_added = Signal(dict)
    converter_progress = Signal(str, str, int)
    converter_finished = Signal()

    # --- редактор ---
    editor_file_loaded = Signal(dict)
    editor_trim_started = Signal()
    editor_trim_progress = Signal(int, str)
    editor_trim_done = Signal(str, str)
    editor_trim_error = Signal(str)
    editor_trim_stopped = Signal()

    # --- настройки ---
    language_changed = Signal(str, dict)
    download_folder_changed = Signal(str)
    converter_folder_changed = Signal(str)
    theme_changed = Signal(str, str)
    themes_reloaded = Signal(list)
    proxy_check_result = Signal(str, str)
    update_check_result = Signal(dict)
    self_update_progress = Signal(str, int, str)

    # --- уведомления ---
    notifications_reloaded = Signal(list)


class QtChannel(UIChannel):
    """Канал в Qt-интерфейс. Потокобезопасен: всё уходит через сигналы."""

    def __init__(self, parent=None):
        self.signals = QtSignals()
        # Родитель для модальных диалогов; ставится после создания окна
        self.parent = parent

    # ------------------------------------------------------------------
    # Общее
    # ------------------------------------------------------------------
    def log(self, message: str, level: str = "info", code: str = "",
            source: str = "") -> None:
        print(f"[{level.upper()}] {message}")
        self.signals.log.emit(str(message), str(level), str(code), str(source))

    def status(self, text: str) -> None:
        self.signals.status.emit(str(text))

    def alert(self, text: str, title: str = "ClipTide", level: str = "info") -> None:
        self.signals.alert.emit(str(text), str(title), str(level))

    def call(self, fn: str, *args) -> None:
        self.signals.generic.emit(fn, tuple(args))

    # ------------------------------------------------------------------
    # Диалоги
    # ------------------------------------------------------------------
    # Зовутся из главного потока (обработчик нажатия), поэтому QFileDialog
    # можно открывать напрямую.
    def pick_files(self, title: str, filters: list[tuple[str, str]],
                   multiple: bool = True) -> list[str]:
        from PySide6.QtWidgets import QFileDialog

        pattern = ";;".join(
            f"{label} ({' '.join('*.' + e for e in exts.split(';'))})"
            for label, exts in filters
        )
        if multiple:
            paths, _ = QFileDialog.getOpenFileNames(self.parent, title, "", pattern)
            return list(paths)
        path, _ = QFileDialog.getOpenFileName(self.parent, title, "", pattern)
        return [path] if path else []

    def pick_folder(self, title: str, start: str = "") -> str | None:
        from PySide6.QtWidgets import QFileDialog

        path = QFileDialog.getExistingDirectory(self.parent, title, start or "")
        return path or None

    # ------------------------------------------------------------------
    # Загрузчик
    # ------------------------------------------------------------------
    def downloader_item_added(self, item: dict) -> None:
        self.signals.downloader_item_added.emit(dict(item))

    def downloader_item_removed(self, task_id: str) -> None:
        self.signals.downloader_item_removed.emit(str(task_id))

    def downloader_progress(self, task_id: str, percent: float,
                            speed: str = "", eta: str = "") -> None:
        self.signals.downloader_progress.emit(str(task_id), float(percent), str(speed), str(eta))

    def downloader_placeholder_removed(self, temp_id: str) -> None:
        self.signals.downloader_placeholder_removed.emit(str(temp_id))

    def downloader_playlist_found(self, playlist: dict) -> None:
        self.signals.downloader_playlist_found.emit(dict(playlist))

    def downloader_finished(self) -> None:
        self.signals.downloader_finished.emit()

    # ------------------------------------------------------------------
    # Конвертер
    # ------------------------------------------------------------------
    def converter_skeleton(self, task_id: str, filename: str) -> None:
        self.signals.converter_skeleton.emit(task_id, filename)

    def converter_skeleton_removed(self, task_id: str) -> None:
        self.signals.converter_skeleton_removed.emit(task_id)

    def converter_item_added(self, item: dict) -> None:
        self.signals.converter_item_added.emit(dict(item))

    def converter_progress(self, task_id: str, text: str, percent: int) -> None:
        self.signals.converter_progress.emit(task_id, str(text), int(percent))

    def converter_finished(self) -> None:
        self.signals.converter_finished.emit()

    # ------------------------------------------------------------------
    # Редактор
    # ------------------------------------------------------------------
    def editor_file_loaded(self, data: dict) -> None:
        self.signals.editor_file_loaded.emit(dict(data))

    def editor_trim_started(self) -> None:
        self.signals.editor_trim_started.emit()

    def editor_trim_progress(self, percent: int, label: str = "") -> None:
        self.signals.editor_trim_progress.emit(int(percent), str(label))

    def editor_trim_done(self, mode: str, folder: str) -> None:
        self.signals.editor_trim_done.emit(str(mode), str(folder))

    def editor_trim_error(self, message: str = "") -> None:
        self.signals.editor_trim_error.emit(str(message))

    def editor_trim_stopped(self) -> None:
        self.signals.editor_trim_stopped.emit()

    # ------------------------------------------------------------------
    # Настройки
    # ------------------------------------------------------------------
    def language_changed(self, language: str, translations: dict) -> None:
        self.signals.language_changed.emit(str(language), dict(translations))

    def download_folder_changed(self, path: str) -> None:
        self.signals.download_folder_changed.emit(str(path))

    def converter_folder_changed(self, path: str) -> None:
        self.signals.converter_folder_changed.emit(str(path))

    def theme_changed(self, theme: str, style: str) -> None:
        self.signals.theme_changed.emit(str(theme), str(style))

    def themes_reloaded(self, themes: list) -> None:
        self.signals.themes_reloaded.emit(list(themes))

    def proxy_check_result(self, state: str, message: str) -> None:
        self.signals.proxy_check_result.emit(str(state), str(message))

    def update_check_result(self, result: dict) -> None:
        self.signals.update_check_result.emit(dict(result))

    def self_update_progress(self, state: str, percent: int,
                             message: str) -> None:
        self.signals.self_update_progress.emit(str(state), int(percent), str(message))

    # ------------------------------------------------------------------
    # Уведомления
    # ------------------------------------------------------------------
    def notifications_reloaded(self, notifications: list) -> None:
        self.signals.notifications_reloaded.emit(list(notifications))
