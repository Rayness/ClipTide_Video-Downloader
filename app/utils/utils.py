# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import sys
import os
import subprocess
from pathlib import Path


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
