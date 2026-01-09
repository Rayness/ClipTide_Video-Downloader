# app/modules/settings/settings.py

import json
import subprocess
import platform
import threading
from app.utils.const import download_dir, UPDATER, THEME_DIR
from app.utils.locale.translations import load_translations
from app.utils.network import check_proxy_connection

# Эту функцию можно оставить здесь или вынести в utils.py
def open_folder(folder_path):
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", folder_path])
        else:
            subprocess.run(['xdg-open', folder_path])
    except Exception as e:
        print(f"Ошибка при открытии папки: {e}")

class SettingsManager:
    def __init__(self, context):
        self.ctx = context # Вся сила теперь здесь

    def launch_update(self):
        try:
            subprocess.run(["powershell", "Start-Process", UPDATER, "-Verb", "runAs"], shell=True)
        except Exception as e:
            print(f"Ошибка при запуске апдейтера: {str(e)}")

    def switch_language(self, language):
        self.ctx.language = language
        self.ctx.translations = load_translations(language)
        self.ctx.update_config_value("Settings", "language", language)
        
        # Обновляем UI
        # Предполагаем, что updateApp и updateTranslations делают одно и то же, упрощаем:
        self.ctx.js_exec(f'window.updateTranslations({json.dumps(self.ctx.translations)})')
        self.ctx.js_exec(f'setLanguage("{language}")')
        return self.ctx.translations

    def switch_subs_setting(self, key, value):
        self.ctx.update_config_value("Subtitles", key, value)

    def switch_audio_setting(self, key, value):
        self.ctx.update_config_value("Audio", key, value)

    def switch_theme(self, theme):
        self.ctx.theme = theme
        self.ctx.update_config_value("Themes", "theme", theme)

    def switch_style(self, style):
        self.ctx.style = style
        self.ctx.update_config_value("Themes", "style", style)

    def switch_proxy_url(self, proxy):
        self.ctx.proxy_url = proxy
        self.ctx.update_config_value("Proxy", "url", proxy)

    def switch_proxy(self, enabled):
        self.ctx.proxy_enabled = enabled
        self.ctx.update_config_value("Proxy", "enabled", enabled)

    def switch_notifi(self, n_type, enabled):
        self.ctx.update_config_value("Notifications", n_type, enabled)

    def switch_open_folder_dl(self, f_type, enabled):
        self.ctx.update_config_value("Folders", f_type, enabled)

    def switch_download_folder(self, folder_path=None):
        raw_path = folder_path if folder_path else download_dir
        path = str(raw_path)
        self.ctx.download_folder = path
        self.ctx.update_config_value("Settings", "folder_path", path)
        self.ctx.js_exec(f'updateDownloadFolder({json.dumps(path)})')

    def switch_converter_folder(self, folder_path=None):
        raw_path = folder_path if folder_path else download_dir
        path = str(raw_path)
        self.ctx.converter_folder = path
        self.ctx.update_config_value("Settings", "converter_folder", path)
        self.ctx.js_exec(f'updateConvertFolder({json.dumps(path)})')

    def choose_folder(self):
        import webview
        folder_path = self.ctx.window.create_file_dialog(
            webview.FOLDER_DIALOG,
            allow_multiple=False
        )
        
        # Метод возвращает кортеж или None
        if folder_path and len(folder_path) > 0:
            path = folder_path[0] # Берем первый путь
            self.switch_download_folder(path)

    def choose_converter_folder(self):
        import webview
        folder_path = self.ctx.window.create_file_dialog(
            webview.FOLDER_DIALOG,
            allow_multiple=False
        )
        
        if folder_path and len(folder_path) > 0:
            path = folder_path[0]
            self.switch_converter_folder(path)

    def test_user_proxy(self, proxy_url):
        """Запускает проверку прокси в отдельном потоке"""
        
        # Колбэк, который выполнится в потоке
        def run_check():
            self.ctx.js_exec('setProxyCheckStatus("loading", "Проверка...")')
            
            success, message = check_proxy_connection(proxy_url)
            
            if success:
                self.ctx.js_exec(f'setProxyCheckStatus("success", "{message}")')
            else:
                # Экранируем кавычки на всякий случай
                safe_msg = message.replace('"', "'")
                self.ctx.js_exec(f'setProxyCheckStatus("error", "{safe_msg}")')

        threading.Thread(target=run_check, daemon=True).start()

    def import_theme_from_zip(self):
        import os
        import zipfile
        import shutil
        import webview
        
        # 1. Открываем диалог выбора файла
        file_types = ("Zip Archives (*.zip)", "All files (*.*)")
        result = self.ctx.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=file_types
        )
        
        if not result:
            return

        zip_path = result[0]
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 2. Проверяем, есть ли там config.json
                file_list = zip_ref.namelist()
                
                # Ищем config.json (он может быть в корне архива или в папке)
                config_file = next((f for f in file_list if f.endswith('config.json')), None)
                
                if not config_file:
                    self.ctx.js_exec('alert("Ошибка: В архиве нет config.json")')
                    return

                # Определяем имя папки темы
                # Если config лежит в "MyTheme/config.json", берем "MyTheme"
                # Если просто "config.json", берем имя архива
                if '/' in config_file:
                    theme_folder_name = config_file.split('/')[0]
                else:
                    theme_folder_name = os.path.splitext(os.path.basename(zip_path))[0]

                target_dir = os.path.join(THEME_DIR, theme_folder_name)
                
                # 3. Распаковка
                if os.path.exists(target_dir):
                    # Если тема уже есть - спрашиваем или удаляем (тут просто перезапишем)
                    shutil.rmtree(target_dir)
                
                os.makedirs(target_dir)
                
                # Извлекаем аккуратно
                for member in file_list:
                    # Защита от Zip Slip уязвимости (выход за пределы папки)
                    if ".." in member or member.startswith("/") or member.startswith("\\"):
                        continue
                        
                    # Если файлы в архиве лежат в папке, извлекаем содержимое папки в корень темы
                    # Или просто извлекаем как есть, если структура правильная.
                    # Для простоты: извлекаем всё в target_dir
                    zip_ref.extract(member, THEME_DIR)

            # 4. Обновляем список тем в UI
            from app.utils.ui.themes import get_themes
            themes = get_themes()
            self.ctx.js_exec(f'updateThemeList({json.dumps(themes)})')
            self.ctx.js_exec('alert("Тема успешно импортирована!")')

        except Exception as e:
            print(f"Import error: {e}")
            self.ctx.js_exec(f'alert("Ошибка импорта: {str(e)}")')