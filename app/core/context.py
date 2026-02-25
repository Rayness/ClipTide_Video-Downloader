# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import json
from app.utils.config.config import save_config

class AppContext:
    def __init__(self):
        self.window = None
        self.config = None
        self.translations = {}
        self.notifications = []
        self.download_queue = []

        # Кэшируем часто используемые пути и настройки для удобства
        self.language = "en"
        self.download_folder = ""
        self.converter_folder = ""
        self.theme = "default"
        self.style = "default"

        # Настройки прокси
        self.proxy_url = ""
        self.proxy_enabled = "False"

        # ClipTide API
        self.cliptide_api = None
        self.cliptide_sync_enabled = False
        self.cliptide_last_sync = None

        self.module_manager = None

    def set_window(self, window):
        print(f"DEBUG: Window установлено в контекст: {window}") # Добавили отладку
        self.window = window

    def update_config_value(self, section, key, value):
        """Единый метод для сохранения настроек"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        save_config(self.config)

    def log_status(self, message_key, *args):
        """Отправка статуса в UI (убираем дублирование кода в модулях)"""
        """Безопасная отправка статуса"""
        if self.window:
            text = self.translations.get('status', {}).get(message_key, message_key)
            full_text = f"{text}: {' '.join(map(str, args))}" if args else text
            safe_text = full_text.replace('"', '\\"').replace("'", "\\'")
            self.window.evaluate_js(f'document.getElementById("status").innerText = "{safe_text}"')
        else:
            print(f"WARNING: Окно не установлено, пропускаем статус: {message_key}")

    def js_exec(self, code):
        """Безопасный вызов JS"""
        if self.window:
            self.window.evaluate_js(code)
        else:
            print(f"WARNING: Окно не установлено, пропускаем JS: {code[:50]}...")

    # === ClipTide API методы ===

    def init_cliptide_api(self):
        """Инициализация ClipTide API клиента из конфигурации"""
        from app.modules.cliptide_api import ClipTideAPIClient

        sync_enabled = self.config.get("ClipTide", "sync_enabled", fallback="False") == "True"
        api_url = self.config.get("ClipTide", "api_url", fallback="production")
        auth_token = self.config.get("ClipTide", "auth_token", fallback="")
        last_sync_str = self.config.get("ClipTide", "last_sync", fallback="")

        self.cliptide_sync_enabled = sync_enabled

        if auth_token:
            use_prod = api_url != "dev"
            self.cliptide_api = ClipTideAPIClient(use_production=use_prod)
            self.cliptide_api.token = auth_token

            if last_sync_str:
                try:
                    from datetime import datetime
                    self.cliptide_last_sync = datetime.fromisoformat(last_sync_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    self.cliptide_last_sync = None
        else:
            self.cliptide_api = None
            self.cliptide_last_sync = None

    def save_cliptide_auth(self, email: str, token: str):
        """Сохранить данные авторизации ClipTide"""
        self.config.set("ClipTide", "auth_token", token)
        self.config.set("ClipTide", "user_email", email)
        save_config(self.config)

    def clear_cliptide_auth(self):
        """Очистить данные авторизации ClipTide"""
        self.config.set("ClipTide", "auth_token", "")
        self.config.set("ClipTide", "user_email", "")
        self.config.set("ClipTide", "last_sync", "")
        self.config.set("ClipTide", "sync_enabled", "False")
        save_config(self.config)
        self.cliptide_api = None
        self.cliptide_sync_enabled = False
        self.cliptide_last_sync = None

    def save_cliptide_last_sync(self, sync_time):
        """Сохранить время последней синхронизации"""
        if sync_time:
            self.config.set("ClipTide", "last_sync", sync_time.isoformat())
            save_config(self.config)
            self.cliptide_last_sync = sync_time

    def is_cliptide_authenticated(self) -> bool:
        """Проверить авторизацию в ClipTide"""
        return self.cliptide_api is not None and self.cliptide_api.is_authenticated()

    def sync_cliptide_downloads(self, downloads: list) -> int:
        """
        Синхронизировать загрузки с ClipTide.

        Args:
            downloads: Список загрузок для синхронизации

        Returns:
            Количество успешно синхронизированных загрузок
        """
        if not self.cliptide_sync_enabled or not self.cliptide_api:
            return 0

        try:
            count = self.cliptide_api.sync_downloads(downloads)
            from datetime import datetime
            self.save_cliptide_last_sync(datetime.utcnow())
            return count
        except Exception as e:
            print(f"ClipTide sync error: {e}")
            return 0