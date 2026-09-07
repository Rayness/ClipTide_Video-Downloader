# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Канал «логика -> интерфейс».

Модули (загрузчик, конвертер, редактор) больше не собирают строки JavaScript
руками. Они зовут именованные методы канала, а конкретная реализация решает,
как это показать. Сейчас реализация одна — WebViewChannel; когда интерфейс
переедет на Qt, добавится QtChannel, и логику трогать не придётся.

Побочно чинится давняя ошибка экранирования. Раньше писали так:

    safe = message.replace('"', '\\\\"').replace("'", "\\\\'")
    window.evaluate_js(f'addLog("{safe}")')

Такой «эскейпинг» ломается на любом windows-пути: в строке C:\\Users\\new
последовательности \\U и \\n JavaScript трактует как escape-последовательности,
и сообщение либо искажается, либо валит парсер. Здесь каждый аргумент
проходит через json.dumps, который даёт валидный JS-литерал всегда.
"""

from __future__ import annotations

import json
from typing import Any


class UIChannel:
    """Базовый канал. Ничего не делает — удобно для тестов и headless-режима."""

    # --- общее ---------------------------------------------------------
    def log(self, message: str, level: str = "info", code: str = "") -> None:
        pass

    def status(self, text: str) -> None:
        pass

    def call(self, fn: str, *args: Any) -> None:
        """Escape hatch: вызвать произвольную функцию интерфейса."""
        pass

    # --- диалоги -------------------------------------------------------
    # Выбор файлов — задача интерфейса, а не логики. Раньше конвертер
    # импортировал webview напрямую и звал window.create_file_dialog, из-за
    # чего был намертво привязан к конкретному UI-движку.
    def pick_files(self, title: str, filters: list[tuple[str, str]],
                   multiple: bool = True) -> list[str]:
        """filters: [(описание, 'mp4;mkv;avi'), ...]. Возвращает список путей."""
        return []

    def pick_folder(self, title: str, start: str = "") -> str | None:
        return None

    # --- конвертер -----------------------------------------------------
    def converter_skeleton(self, task_id: str, filename: str) -> None:
        pass

    def converter_skeleton_removed(self, task_id: str) -> None:
        pass

    def converter_item_added(self, item: dict) -> None:
        pass

    def converter_progress(self, task_id: str, text: str, percent: int) -> None:
        pass

    def converter_finished(self) -> None:
        pass

    # --- уведомления ---------------------------------------------------
    def notifications_reloaded(self, notifications: list) -> None:
        pass


class WebViewChannel(UIChannel):
    """Реализация поверх pywebview: вызовы транслируются в evaluate_js."""

    def __init__(self, context):
        self.ctx = context

    # -- низкий уровень --------------------------------------------------
    def _eval(self, fn: str, *args: Any) -> None:
        window = getattr(self.ctx, "window", None)
        if window is None:
            print(f"[UI] окно ещё не создано, пропускаем {fn}()")
            return
        payload = ", ".join(json.dumps(a, ensure_ascii=False) for a in args)
        try:
            window.evaluate_js(f"{fn}({payload})")
        except Exception as e:  # окно могли закрыть прямо во время вызова
            print(f"[UI] {fn}() не выполнен: {e}")

    # -- общее -----------------------------------------------------------
    def log(self, message: str, level: str = "info", code: str = "") -> None:
        print(f"[{level.upper()}] {message}")
        self._eval("addLog", message, level, code)

    def status(self, text: str) -> None:
        window = getattr(self.ctx, "window", None)
        if window is None:
            return
        literal = json.dumps(text, ensure_ascii=False)
        try:
            window.evaluate_js(
                f'var _s=document.getElementById("status"); if(_s) _s.innerText={literal};'
            )
        except Exception as e:
            print(f"[UI] status() не выполнен: {e}")

    def call(self, fn: str, *args: Any) -> None:
        self._eval(fn, *args)

    # -- диалоги ---------------------------------------------------------
    def pick_files(self, title: str, filters: list[tuple[str, str]],
                   multiple: bool = True) -> list[str]:
        import webview

        window = getattr(self.ctx, "window", None)
        if window is None:
            return []
        types = tuple(
            f"{label} ({';'.join('*.' + e for e in exts.split(';'))})"
            for label, exts in filters
        )
        result = window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=multiple, file_types=types
        )
        return list(result) if result else []

    def pick_folder(self, title: str, start: str = "") -> str | None:
        import webview

        window = getattr(self.ctx, "window", None)
        if window is None:
            return None
        result = window.create_file_dialog(webview.FOLDER_DIALOG, directory=start or "")
        return result[0] if result else None

    # -- конвертер --------------------------------------------------------
    def converter_skeleton(self, task_id: str, filename: str) -> None:
        self._eval("createConverterSkeleton", task_id, filename)

    def converter_skeleton_removed(self, task_id: str) -> None:
        self._eval("removeConverterSkeleton", task_id)

    def converter_item_added(self, item: dict) -> None:
        self._eval("addConverterItem", item)

    def converter_progress(self, task_id: str, text: str, percent: int) -> None:
        self._eval("updateConvStatus", task_id, text, percent)

    def converter_finished(self) -> None:
        self._eval("conversionFinished")

    # -- уведомления -------------------------------------------------------
    def notifications_reloaded(self, notifications: list) -> None:
        self._eval("loadNotifications", notifications)
