# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import sys
import os
import subprocess
from pathlib import Path

from app.utils.const import GITHUB_REPO, HEADERS, VERSION_FILE
from app.utils.network import get_session

def unicodefix():
    """
    Переводит вывод в UTF-8, если вывод вообще есть.

    В windowed-сборке PyInstaller sys.stdout и sys.stderr равны None.
    Прежняя версия ловила AttributeError от .reconfigure(), но в обработчике
    сразу обращалась к sys.stdout.buffer — и падала уже там, до создания
    окна. Приложение не запускалось вовсе, показывая диалог PyInstaller
    «Unhandled exception in script».
    """
    if sys.platform != "win32":
        return

    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue                      # windowed-сборка: выводить некуда
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            # Поток есть, но перенастроить нельзя — заворачиваем вручную
            buffer = getattr(stream, "buffer", None)
            if buffer is None:
                continue
            import io
            setattr(sys, name, io.TextIOWrapper(
                buffer, encoding="utf-8", errors="replace"))


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
