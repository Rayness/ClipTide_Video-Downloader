# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Единая точка вычисления всех путей приложения.

Режимы работы:
 - Установленная версия: пользовательские данные в %LOCALAPPDATA%/ClipTide
 - Portable-версия: рядом с ClipTide.exe лежит файл portable.txt,
   все данные хранятся в <папка приложения>/userdata
"""

import os
import sys
from pathlib import Path

APP_NAME = 'ClipTide'

IS_FROZEN = getattr(sys, 'frozen', False)

# Папка, где лежит exe (или корень проекта в dev-режиме)
if IS_FROZEN:
    APP_DIR = Path(sys.executable).resolve().parent
else:
    # app/utils/paths.py -> app/utils -> app -> корень проекта
    APP_DIR = Path(__file__).resolve().parents[2]

# Папка с ресурсами (data, ffmpeg): _MEIPASS у PyInstaller (_internal в onedir),
# в dev-режиме — корень проекта
RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', APP_DIR))

# Portable-режим: маркерный файл рядом с exe
PORTABLE_MARKER = APP_DIR / 'portable.txt'
IS_PORTABLE = PORTABLE_MARKER.exists()

if IS_PORTABLE:
    USER_DATA_DIR = APP_DIR / 'userdata'
    DEFAULT_DOWNLOAD_DIR = APP_DIR / 'downloads'
else:
    _local = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~/.config')
    USER_DATA_DIR = Path(_local) / APP_NAME
    DEFAULT_DOWNLOAD_DIR = Path.home() / 'Downloads' / APP_NAME

LOGS_DIR = USER_DATA_DIR / 'Logs'

# Профиль WebView2 (cookies, localStorage). В portable-режиме остаётся в папке программы.
WEBVIEW_PROFILE_DIR = USER_DATA_DIR / 'WebViewProfile'

# Опциональный WebView2 Fixed Version Runtime, лежащий рядом с exe.
# Если папка существует — приложение не зависит от установленного в системе WebView2.
FIXED_WEBVIEW2_DIR = APP_DIR / 'WebView2'

os.makedirs(USER_DATA_DIR, exist_ok=True)


def resource_path(relative_path) -> str:
    """Абсолютный путь к ресурсу (data/..., ffmpeg/...) независимо от CWD и способа запуска."""
    return str(RESOURCE_DIR / relative_path)
