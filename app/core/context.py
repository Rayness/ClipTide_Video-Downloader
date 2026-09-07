# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Общее состояние приложения.

Контекст держит конфигурацию, кэш часто используемых настроек и канал
в интерфейс. Модули логики получают его в конструкторе и через него же
разговаривают с интерфейсом — напрямую виджеты они не трогают.
"""

from __future__ import annotations

from app.core.ui_channel import UIChannel
from app.utils.config.config import save_config


class AppContext:
    def __init__(self):
        self.config = None

        # Канал «логика -> интерфейс». Подменяется целиком при смене UI-слоя,
        # поэтому модули не знают, что под ними именно Qt.
        self.ui: UIChannel = UIChannel()

        self.translations: dict = {}
        self.notifications: list = []
        self.download_queue: list = []

        # Кэш часто используемых настроек
        self.language = "ru"
        self.download_folder = ""
        self.converter_folder = ""
        self.theme = "cliptide"
        self.style = "default"

        self.proxy_url = ""
        self.proxy_enabled = "False"

        self.module_manager = None

    # ------------------------------------------------------------------
    def update_config_value(self, section: str, key: str, value) -> None:
        """Единая точка сохранения настроек."""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        save_config(self.config)

    def log_status(self, message_key: str, *args) -> None:
        """Строка состояния внизу окна."""
        text = self.translations.get("status", {}).get(message_key, message_key)
        full_text = f"{text}: {' '.join(map(str, args))}" if args else text
        self.ui.status(full_text)
