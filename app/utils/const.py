# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import os
from pathlib import Path

appdata_local = os.path.join(os.environ['LOCALAPPDATA'], 'ClipTide')
os.makedirs(appdata_local, exist_ok=True)

download_dir = Path.home() / 'Downloads' / 'ClipTide'
os.makedirs(download_dir, exist_ok=True)

NOTIFICATION_FILE = os.path.join(appdata_local, "notifications.json")

CONFIG_FILE = os.path.join(appdata_local, "config.ini")

QUEUE_FILE = os.path.join(appdata_local, "queue.json")

COOKIES_FILE = os.path.join(appdata_local, "cookies.txt")

UPDATER = "update.exe"

VERSION_FILE = "./data/version.txt"

GITHUB_REPO = "Rayness/YT-Downloader"

MODAL_CONTENT = os.path.abspath("./data/ui/src/text")

HEADERS = {
    "User-Agent": "Updater-App",
    "Accept": "application/vnd.github.v3+json"
}

MANIFEST_URL = "https://raw.githubusercontent.com/Rayness/ClipTide_Video-Downloader/refs/heads/main/updates.json"
# Путь к папке с переводами
TRANSLATIONS_DIR = os.path.abspath("./data/localization")

# THEME_DIR = os.path.abspath("./data/ui/themes")
THEME_DIR = os.path.join(appdata_local, "themes")

# HTML-контент для отображения в окне
html_file_path = os.path.abspath("./data/ui/index.html")