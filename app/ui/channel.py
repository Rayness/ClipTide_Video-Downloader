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

    log = Signal(str, str, str)              # message, level, code
    status = Signal(str)                     # текст строки состояния

    converter_skeleton = Signal(str, str)    # task_id, filename
    converter_skeleton_removed = Signal(str)
    converter_item_added = Signal(dict)
    converter_progress = Signal(str, str, int)   # task_id, text, percent
    converter_finished = Signal()

    notifications_reloaded = Signal(list)

    # Общий канал для вызовов, которым пока не завели именованный сигнал
    generic = Signal(str, tuple)


class QtChannel(UIChannel):
    """Канал в Qt-интерфейс. Потокобезопасен: всё уходит через сигналы."""

    def __init__(self, parent=None):
        self.signals = QtSignals()
        # Родитель для модальных диалогов; ставится после создания окна
        self.parent = parent

    # --- общее ---------------------------------------------------------
    def log(self, message: str, level: str = "info", code: str = "") -> None:
        print(f"[{level.upper()}] {message}")
        self.signals.log.emit(str(message), str(level), str(code))

    def status(self, text: str) -> None:
        self.signals.status.emit(str(text))

    def call(self, fn: str, *args) -> None:
        self.signals.generic.emit(fn, tuple(args))

    # --- диалоги --------------------------------------------------------
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

    # --- конвертер -----------------------------------------------------
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

    # --- уведомления ----------------------------------------------------
    def notifications_reloaded(self, notifications: list) -> None:
        self.signals.notifications_reloaded.emit(list(notifications))
