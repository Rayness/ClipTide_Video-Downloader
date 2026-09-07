# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import json
import sys
import os
import subprocess
from pathlib import Path

from app.utils.const import GITHUB_REPO, HEADERS, VERSION_FILE, MODAL_CONTENT
from app.utils.network import get_session

def unicodefix():
    if sys.platform == "win32":
        try:
            # Способ 1 (Python 3.7+)
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except AttributeError:
            # Способ 2 (для старых версий Python)
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)  # 65001 = UTF-8
            # Альтернатива через io
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def resource_path(relative_path):
    """ Возвращает корректный путь для доступа к ресурсам после упаковки PyInstaller """
    from app.utils.paths import resource_path as _resource_path
    return _resource_path(relative_path)

def ffmpegreg():
    """Регистрирует встроенный ffmpeg. Логика живёт в app.utils.media."""
    from app.utils.media import register_ffmpeg_path
    register_ffmpeg_path()

def get_latest_version():
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        # verify=False убран намеренно: проверка TLS-сертификата обязательна,
        # иначе ответ об обновлении можно подменить по пути.
        response = get_session().get(api_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json().get("tag_name", "0.0.0")
        print(f"[WARN] GitHub API answered {response.status_code}")
    except Exception as e:
        print(f"[WARN] Failed to check for updates: {e}")
    return "0.0.0"

def get_local_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as file:
            return file.read().strip()
    return "0.0.0"

def check_for_update():
    local = get_local_version()
    latest = get_latest_version()

    if local != latest:
        return True
    else:
        return False
    
def restart_app():
    if getattr(sys, 'frozen', False):
        # В собранном виде sys.executable — это сам ClipTide.exe
        subprocess.Popen([sys.executable])
    else:
        subprocess.Popen([sys.executable] + sys.argv)
    sys.exit(0)  # Корректно закрываем текущий процесс

def get_appdata_path(app_name: str, roaming: bool = False) -> Path:
    """Возвращает путь к папке приложения в AppData"""
    appdata = os.getenv('APPDATA' if roaming else 'LOCALAPPDATA')
    if not appdata:  # Для Linux/Mac
        appdata = os.path.expanduser('~/.config')
    path = Path(appdata) / app_name
    path.mkdir(parents=True, exist_ok=True)
    return path

def load_modal_content():
    file_path = os.path.join(MODAL_CONTENT, "modals.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                print(file)
                return json.load(file)
        except Exception as e:
            print(f"Ошибка при загрузке модального контента: {e}")
    print("Не получилось загрузить JSON файлы")
    return {}


