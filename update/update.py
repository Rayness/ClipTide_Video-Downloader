# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import os
import sys
import shutil
import requests
import zipfile
import time
import subprocess
import threading
import psutil
import webview
import configparser


class UpdaterAPI:
    def __init__(self):
        self._window = None
        self.download_url = None

    def set_window(self, window):
        self._window = window

# Настройки
GITHUB_REPO = "Rayness/YT-Downloader"
APP_EXECUTABLE = "ClipTide.exe"
HEADERS = {"User-Agent": "Updater-App", "Accept": "application/vnd.github.v3+json"}

MANIFEST_URL = "https://raw.githubusercontent.com/Rayness/ClipTide_Video-Downloader/refs/heads/main/updates.json"
CONFIG_PATH = os.path.join(os.environ["LOCALAPPDATA"], "ClipTide", "config.ini")

# Пути
CURRENT_DIR = os.getcwd()
TARGET_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "ClipTide")
TEMP_BASE = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "ClipTideUpdater")
DOWNLOAD_DIR = os.path.join(TEMP_BASE, "download")
EXTRACT_DIR = os.path.join(TEMP_BASE, "extract")
# Путь к HTML (предполагаем, что он лежит рядом, если запускаем как скрипт, или в _MEIPASS)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.getcwd()
HTML_PATH = os.path.join(BASE_DIR, "data", "ui", "updater.html")

class UpdaterAPI:
    def __init__(self):
        # ВАЖНО: Название с нижним подчеркиванием, чтобы pywebview не пытался это экспортировать в JS
        self._window = None
        self.download_url = None

    def set_window(self, window):
        self._window = window

    def log(self, message):
        print(message)
        if self._window:
            safe_msg = message.replace('"', '\\"').replace("'", "\\'")
            self._window.evaluate_js(f'addLog("{safe_msg}")')

    def get_update_channel(self):
        """Читает config.ini основной программы"""
        channel = "stable"
        if os.path.exists(CONFIG_PATH):
            try:
                config = configparser.ConfigParser()
                config.read(CONFIG_PATH, encoding='utf-8')
                channel = config.get("Updates", "channel", fallback="stable")
            except: pass
        return channel

    def set_status(self, text):
        if self._window:
            safe_text = text.replace('"', '\\"')
            self._window.evaluate_js(f'setStatus("{safe_text}")')

    def set_progress(self, percent):
        if self._window:
            self._window.evaluate_js(f'setProgress({percent})')

    def set_ui_state(self, state):
        if self._window:
            self._window.evaluate_js(f'setButtons("{state}")')

    def close(self):
        if self._window:
            self._window.destroy()

    def _get_headers_for_url(self, url):
            """Выбирает заголовки в зависимости от домена"""
            if "github.com" in url or "api.github.com" in url:
                return {
                    "User-Agent": "Updater-App",
                    "Accept": "application/vnd.github.v3+json"
                }
            else:
                # Притворяемся обычным браузером для твоего сайта
                return {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }

    # --- ЛОГИКА ---

    def get_local_version(self):
        v_path = os.path.join(CURRENT_DIR, "data", "version.txt")
        if os.path.exists(v_path):
            try:
                with open(v_path, "r") as file:
                    return file.read().strip()
            except: pass
        return "0.0.0"

    def check_for_updates(self):
        threading.Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self):
        
        self.log(f"Проверка версии...")
        local = self.get_local_version()
        channel = self.get_update_channel()
        
        self.log(f"Канал обновлений: {channel.upper()}")
        
        try:
            # Ссылка на манифест (обычно GitHub RAW)
            # Если MANIFEST_URL ведет на GitHub, функция вернет нужные хедеры
            manifest_headers = self._get_headers_for_url(MANIFEST_URL)
            
            response = requests.get(MANIFEST_URL, headers=manifest_headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 2. Берем данные для выбранного канала
                if channel not in data:
                    self.log(f"Ошибка: канал '{channel}' не найден в манифесте. Переход на stable.")
                    channel = "stable"
                
                channel_data = data.get(channel, {})
                latest = channel_data.get("version", "0.0.0")
                self.download_url = channel_data.get("url")
                description = channel_data.get("description", "")

                if latest != local:
                    self.set_status(f"Доступна версия {latest} ({channel})")
                    self.log(f"Описание: {description}")
                    
                    if not self.download_url:
                        self.log("Ошибка: URL для скачивания не указан в манифесте")
                        self.set_ui_state('no-update')
                    else:
                        self.set_ui_state('ready')
                else:
                    self.set_status(f"У вас последняя версия ({channel})")
                    self.set_ui_state('no-update')
            else:
                self.log(f"Ошибка получения манифеста: {response.status_code}")
                self.set_ui_state('no-update')

        except Exception as e:
            self.log(f"Ошибка: {e}")
            self.set_ui_state('no-update')

    def start_update(self):
        threading.Thread(target=self._update_thread, daemon=True).start()

    def _update_thread(self):
        if not self.download_url:
            self.log("URL не найден")
            return

        if os.path.exists(TEMP_BASE):
            try: shutil.rmtree(TEMP_BASE)
            except: pass
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        os.makedirs(EXTRACT_DIR, exist_ok=True)

        archive_path = os.path.join(DOWNLOAD_DIR, "update.zip")
        self.set_status("Скачивание...")
        
        # Получаем правильные заголовки (если ты внедрил метод _get_headers_for_url)
        # Если нет, используй просто HEADERS
        current_headers = self._get_headers_for_url(self.download_url) if hasattr(self, '_get_headers_for_url') else HEADERS
        
        try:
            self.log(f"Источник: {self.download_url}")
            
            response = requests.get(self.download_url, headers=current_headers, stream=True, timeout=60)
            
            if response.status_code != 200:
                self.log(f"Ошибка сервера: {response.status_code}")
                self.set_ui_state('error')
                return

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(archive_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            self.set_progress(int((downloaded / total_size) * 100))
        except Exception as e:
            self.log(f"Ошибка скачивания: {e}")
            return

        self.set_status("Распаковка...")
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(EXTRACT_DIR)
        except Exception as e:
            self.log(f"Ошибка архива: {e}")
            return

        self.set_status("Закрытие программы...")
        self._terminate_app()

        self.set_status("Установка...")
        try:
            if not os.path.exists(TARGET_DIR):
                os.makedirs(TARGET_DIR, exist_ok=True)

            source_root = EXTRACT_DIR
            items = os.listdir(EXTRACT_DIR)
            if len(items) == 1 and os.path.isdir(os.path.join(EXTRACT_DIR, items[0])):
                source_root = os.path.join(EXTRACT_DIR, items[0])

            # === ЗАМЕНА shutil.copytree НА УМНЫЙ ЦИКЛ ===
            for root, dirs, files in os.walk(source_root):
                rel_dir = os.path.relpath(root, source_root)
                dest_dir = os.path.join(TARGET_DIR, rel_dir)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)

                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dest_dir, file)

                    # Проверка: если файл занят (это мы сами), сохраняем как .new
                    if file.lower() == "updater.exe":
                        dst_file = dst_file + ".new"
                        self.log(f"Отложенное обновление: {file}")

                    # Удаляем старый файл, если он есть (и не занят)
                    if os.path.exists(dst_file):
                        try:
                            os.remove(dst_file)
                        except Exception as e:
                            self.log(f"Пропуск занятого файла {file}: {e}")
                            continue 
                    
                    shutil.copy2(src_file, dst_file)
            
            self.log("Файлы обновлены.")
            # ============================================

        except Exception as e:
            self.log(f"Ошибка копирования: {e}")
            return

        self._create_shortcut()
        self._cleanup_old()
        
        self.set_progress(100)
        self.set_status("Обновление завершено!")
        self.set_ui_state('done')

    def launch_app(self):
        target_exe = os.path.join(TARGET_DIR, APP_EXECUTABLE)
        if os.path.exists(target_exe):
            try:
                subprocess.Popen([target_exe], cwd=TARGET_DIR)
                self.close()
            except Exception as e:
                self.log(f"Ошибка запуска: {e}")
        else:
            self.log("Файл программы не найден")

    def _terminate_app(self):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == APP_EXECUTABLE:
                try: proc.terminate()
                except: pass
        time.sleep(1)

    def _create_shortcut(self):
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        shortcut_path = os.path.join(desktop, "ClipTide.lnk")
        target = os.path.join(TARGET_DIR, APP_EXECUTABLE)
        
        ps_cmd = f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{shortcut_path}");$s.TargetPath="{target}";$s.WorkingDirectory="{TARGET_DIR}";$s.Save()'
        subprocess.run(["powershell", "-Command", ps_cmd], creationflags=subprocess.CREATE_NO_WINDOW)

    def _cleanup_old(self):
        if os.path.normpath(CURRENT_DIR) == os.path.normpath(TARGET_DIR):
            return
        self.log("Удаление старой версии...")
        try:
            old_exe = os.path.join(CURRENT_DIR, APP_EXECUTABLE)
            if os.path.exists(old_exe): os.remove(old_exe)
            old_data = os.path.join(CURRENT_DIR, "data")
            if os.path.exists(old_data): shutil.rmtree(old_data)
        except: pass

def main():
    api = UpdaterAPI()
    
    window = webview.create_window(
        "ClipTide Updater",
        url=HTML_PATH,
        js_api=api,
        width=450,
        height=500,
        resizable=False,
        frameless=True, 
        easy_drag=False 
    )
    
    api.set_window(window)
    webview.start()

if __name__ == "__main__":
    main()