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
import webbrowser
import zipfile

from app.core.ui_channel import UIChannel
from app.utils.const import THEME_DIR, download_dir
from app.utils.locale.translations import load_translations
from app.utils.network import check_proxy_connection
from app.utils.updates import check as check_updates, release_page_url


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
        self._self_updater = None

    @property
    def ui(self) -> UIChannel:
        return getattr(self.ctx, "ui", None) or UIChannel()

    # ------------------------------------------------------------------
    # Обновления
    # ------------------------------------------------------------------
    def open_release_page(self, url: str = "") -> None:
        """
        Открывает страницу загрузки в браузере.

        Скачиванием и установкой приложение не занимается: обновление ставится
        вручную поверх старой версии. Подробности — в app/utils/updates.py.
        """
        try:
            webbrowser.open(url or release_page_url())
        except Exception as e:
            self.ui.log(f"Не удалось открыть страницу загрузки: {e}", "error")

    # --- самообновление ---
    @property
    def self_updater(self):
        if self._self_updater is None:
            from app.modules.updater.updater import SelfUpdater
            self._self_updater = SelfUpdater(self.ctx)
        return self._self_updater

    def self_update_available(self) -> bool:
        """Есть ли самообновление в этой сборке (только onefile)."""
        from app.modules.updater.updater import self_update_supported
        return self_update_supported()

    def start_self_update(self, entry: dict) -> None:
        self.self_updater.start(entry)

    def restart_after_update(self) -> None:
        self.self_updater.restart()

    def switch_update_setting(self, key, value):
        self.ctx.update_config_value("Updates", key, value)

    def switch_update_channel(self, channel):
        self.ctx.update_config_value("Updates", "channel", channel)

    def check_update_for_channel(self, channel):
        """Проверяет обновление для канала (stable/dev) и отдаёт результат в UI."""
        def _check():
            self.ui.update_check_result(check_updates(channel))

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
