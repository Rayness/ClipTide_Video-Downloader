# app/core/context.py

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