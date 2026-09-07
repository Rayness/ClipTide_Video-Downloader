# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Канал «логика -> интерфейс».

Модули (загрузчик, конвертер, редактор, настройки) не трогают виджеты
напрямую. Они зовут именованные методы канала, а конкретная реализация
решает, как это показать:

    UIChannel   — база, ничего не делает (headless, тесты, CLI)
    QtChannel   — нативный интерфейс (app/ui/channel.py)

Такое разделение и позволило заменить интерфейс целиком, не переписывая
логику: раньше модули собирали строки JavaScript и звали evaluate_js.
"""

from __future__ import annotations

from typing import Any


class UIChannel:
    """Базовый канал. Ничего не делает — удобно для тестов и headless-режима."""

    # ------------------------------------------------------------------
    # Общее
    # ------------------------------------------------------------------
    def log(self, message: str, level: str = "info", code: str = "",
            source: str = "") -> None:
        """source — какой модуль пишет: downloader / converter / editor / settings.
        Нужен, чтобы журнал каждого экрана показывал только своё."""
        pass

    def status(self, text: str) -> None:
        pass

    def alert(self, text: str, title: str = "ClipTide", level: str = "info") -> None:
        """Модальное сообщение пользователю."""
        pass

    def call(self, fn: str, *args: Any) -> None:
        """Escape hatch: вызвать произвольную функцию интерфейса."""
        pass

    # ------------------------------------------------------------------
    # Диалоги
    # ------------------------------------------------------------------
    # Выбор файлов — задача интерфейса, а не логики. Раньше конвертер и
    # настройки импортировали webview напрямую и звали create_file_dialog,
    # из-за чего были намертво привязаны к конкретному UI-движку.
    def pick_files(self, title: str, filters: list[tuple[str, str]],
                   multiple: bool = True) -> list[str]:
        """filters: [(описание, 'mp4;mkv;avi'), ...]. Возвращает список путей."""
        return []

    def pick_folder(self, title: str, start: str = "") -> str | None:
        return None

    # ------------------------------------------------------------------
    # Загрузчик
    # ------------------------------------------------------------------
    def downloader_item_added(self, item: dict) -> None:
        pass

    def downloader_item_removed(self, task_id: str) -> None:
        pass

    def downloader_progress(self, task_id: str, percent: float,
                            speed: str = "", eta: str = "") -> None:
        pass

    def downloader_placeholder_removed(self, temp_id: str) -> None:
        pass

    def downloader_playlist_found(self, playlist: dict) -> None:
        pass

    def downloader_finished(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Конвертер
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Редактор
    # ------------------------------------------------------------------
    def editor_file_loaded(self, data: dict) -> None:
        pass

    def editor_trim_started(self) -> None:
        pass

    def editor_trim_progress(self, percent: int, label: str = "") -> None:
        pass

    def editor_trim_done(self, mode: str, folder: str) -> None:
        pass

    def editor_trim_error(self, message: str = "") -> None:
        pass

    def editor_trim_stopped(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Настройки
    # ------------------------------------------------------------------
    def language_changed(self, language: str, translations: dict) -> None:
        pass

    def download_folder_changed(self, path: str) -> None:
        pass

    def converter_folder_changed(self, path: str) -> None:
        pass

    def theme_changed(self, theme: str, style: str) -> None:
        pass

    def themes_reloaded(self, themes: list) -> None:
        pass

    def proxy_check_result(self, state: str, message: str) -> None:
        """state: loading | success | error"""
        pass

    def update_check_result(self, result: dict) -> None:
        pass

    # ------------------------------------------------------------------
    # Уведомления
    # ------------------------------------------------------------------
    def notifications_reloaded(self, notifications: list) -> None:
        pass
