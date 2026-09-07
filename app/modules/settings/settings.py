# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Настройки приложения.

Модуль не знает, какой интерфейс сверху: диалоги и обратная связь идут
через UIChannel. Раньше здесь напрямую импортировался webview и собирались
строки JavaScript.

Заодно исправлено имя switch_update_setting — метод назывался
`swith_update_setting`, а вызывался как `switch_update_setting`, то есть
сохранение настроек обновлений падало с AttributeError.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import threading
import zipfile

from app.core.ui_channel import UIChannel
from app.utils.const import MANIFEST_URL, THEME_DIR, UPDATER, VERSION_FILE, download_dir
from app.utils.locale.translations import load_translations
from app.utils.network import check_proxy_connection, get_session


def open_folder(folder_path):
    """Открыть папку в системном файловом менеджере."""
    try:
        path = str(folder_path)
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"Ошибка при открытии папки: {e}")


class SettingsManager:
    def __init__(self, context):
        self.ctx = context

    @property
    def ui(self) -> UIChannel:
        return getattr(self.ctx, "ui", None) or UIChannel()

    # ------------------------------------------------------------------
    # Обновления
    # ------------------------------------------------------------------
    def launch_update(self):
        try:
            from app.utils.paths import APP_DIR
            updater_path = os.path.join(str(APP_DIR), UPDATER)
            subprocess.Popen([updater_path], cwd=str(APP_DIR))
        except Exception as e:
            self.ui.log(f"Не удалось запустить апдейтер: {e}", "error")

    def switch_update_setting(self, key, value):
        self.ctx.update_config_value("Updates", key, value)

    def switch_update_channel(self, channel):
        self.ctx.update_config_value("Updates", "channel", channel)

    def check_update_for_channel(self, channel):
        """Проверяет обновление для канала (stable/dev) и отдаёт результат в UI."""
        def _check():
            try:
                local = "0.0.0"
                if os.path.exists(VERSION_FILE):
                    with open(VERSION_FILE, "r", encoding="utf-8") as f:
                        local = f.read().strip()

                response = get_session().get(
                    MANIFEST_URL,
                    headers={"User-Agent": "ClipTide-App", "Accept": "application/json"},
                    timeout=10,
                )
                if response.status_code != 200:
                    self.ui.update_check_result(
                        {"error": True, "message": f"HTTP {response.status_code}"}
                    )
                    return

                data = response.json()
                if channel not in data:
                    self.ui.update_check_result(
                        {"error": True, "message": "Канал не найден"}
                    )
                    return

                channel_data = data[channel]
                latest = channel_data.get("version", "0.0.0")
                self.ui.update_check_result({
                    "error": False,
                    "has_update": latest != local,
                    "latest_version": latest,
                    "current_version": local,
                    "description": channel_data.get("description", ""),
                    "channel": channel,
                })
            except Exception as e:
                self.ui.update_check_result({"error": True, "message": str(e)})

        threading.Thread(target=_check, daemon=True).start()

    # ------------------------------------------------------------------
    # Язык и тема
    # ------------------------------------------------------------------
    def switch_language(self, language):
        self.ctx.language = language
        self.ctx.translations = load_translations(language)
        self.ctx.update_config_value("Settings", "language", language)
        self.ui.language_changed(language, self.ctx.translations)
        return self.ctx.translations

    def switch_theme(self, theme):
        self.ctx.theme = theme
        self.ctx.update_config_value("Themes", "theme", theme)
        self.ui.theme_changed(theme, self.ctx.style)

    def switch_style(self, style):
        self.ctx.style = style
        self.ctx.update_config_value("Themes", "style", style)
        self.ui.theme_changed(self.ctx.theme, style)

    # ------------------------------------------------------------------
    # Простые переключатели
    # ------------------------------------------------------------------
    def switch_subs_setting(self, key, value):
        self.ctx.update_config_value("Subtitles", key, value)

    def switch_audio_setting(self, key, value):
        self.ctx.update_config_value("Audio", key, value)

    def switch_editor_setting(self, key, value):
        self.ctx.update_config_value("Editor", key, value)

    def switch_notifi(self, n_type, enabled):
        self.ctx.update_config_value("Notifications", n_type, enabled)

    def switch_open_folder_dl(self, f_type, enabled):
        self.ctx.update_config_value("Folders", f_type, enabled)

    def switch_window_size(self, size):
        self.ctx.update_config_value("Display", "window_size", size)

    def switch_ui_scale(self, scale):
        self.ctx.update_config_value("Display", "ui_scale", scale)

    # ------------------------------------------------------------------
    # Прокси
    # ------------------------------------------------------------------
    def switch_proxy_url(self, proxy):
        self.ctx.proxy_url = proxy
        self.ctx.update_config_value("Proxy", "url", proxy)

    def switch_proxy(self, enabled):
        self.ctx.proxy_enabled = enabled
        self.ctx.update_config_value("Proxy", "enabled", enabled)

    def test_user_proxy(self, proxy_url):
        def _check():
            self.ui.proxy_check_result("loading", "Проверка...")
            success, message = check_proxy_connection(proxy_url)
            self.ui.proxy_check_result("success" if success else "error", message)

        threading.Thread(target=_check, daemon=True).start()

    # ------------------------------------------------------------------
    # Папки
    # ------------------------------------------------------------------
    def switch_download_folder(self, folder_path=None):
        path = str(folder_path if folder_path else download_dir)
        self.ctx.download_folder = path
        self.ctx.update_config_value("Settings", "folder_path", path)
        self.ui.download_folder_changed(path)

    def switch_converter_folder(self, folder_path=None):
        path = str(folder_path if folder_path else download_dir)
        self.ctx.converter_folder = path
        self.ctx.update_config_value("Settings", "converter_folder", path)
        self.ui.converter_folder_changed(path)

    def choose_folder(self):
        path = self.ui.pick_folder("Папка для загрузок", self.ctx.download_folder)
        if path:
            self.switch_download_folder(path)

    def choose_converter_folder(self):
        path = self.ui.pick_folder("Папка для конвертации", self.ctx.converter_folder)
        if path:
            self.switch_converter_folder(path)

    # ------------------------------------------------------------------
    # Импорт тем
    # ------------------------------------------------------------------
    def import_theme_from_zip(self):
        paths = self.ui.pick_files(
            "Выберите архив с темой",
            [("ZIP-архивы", "zip"), ("Все файлы", "*")],
            multiple=False,
        )
        if not paths:
            return

        zip_path = paths[0]
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                names = archive.namelist()
                config_entry = next((n for n in names if n.endswith("config.json")), None)
                if config_entry is None:
                    self.ui.alert("В архиве нет config.json — это не тема ClipTide",
                                  "Импорт темы", "error")
                    return

                if "/" in config_entry:
                    theme_name = config_entry.split("/")[0]
                else:
                    theme_name = os.path.splitext(os.path.basename(zip_path))[0]

                target_dir = os.path.join(THEME_DIR, theme_name)
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                os.makedirs(target_dir, exist_ok=True)

                # ZipFile.extract сам отбрасывает абсолютные пути и '..',
                # поэтому выхода за пределы THEME_DIR быть не может
                archive.extractall(THEME_DIR)

            self.ui.themes_reloaded(self.list_themes())
            self.ui.alert(f"Тема «{theme_name}» установлена", "Импорт темы", "info")

        except Exception as e:
            self.ui.alert(f"Ошибка импорта: {e}", "Импорт темы", "error")

    @staticmethod
    def list_themes() -> list:
        from app.utils.ui.themes import get_themes
        return get_themes()

    def delete_theme(self, theme_id: str) -> bool:
        """Удаляет установленную пользователем тему."""
        target = os.path.join(THEME_DIR, theme_id)
        if not os.path.isdir(target):
            self.ui.alert("Эту тему нельзя удалить: она встроенная",
                          "Темы", "error")
            return False
        try:
            shutil.rmtree(target)
        except OSError as e:
            self.ui.alert(f"Не удалось удалить тему: {e}", "Темы", "error")
            return False
        self.ui.themes_reloaded(self.list_themes())
        return True
