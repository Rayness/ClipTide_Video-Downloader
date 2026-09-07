# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import os

from app.utils.paths import (
    USER_DATA_DIR,
    DEFAULT_DOWNLOAD_DIR,
    resource_path,
)

appdata_local = str(USER_DATA_DIR)

download_dir = DEFAULT_DOWNLOAD_DIR
os.makedirs(download_dir, exist_ok=True)

NOTIFICATION_FILE = os.path.join(appdata_local, "notifications.json")

CONFIG_FILE = os.path.join(appdata_local, "config.ini")

QUEUE_FILE = os.path.join(appdata_local, "queue.json")

COOKIES_FILE = os.path.join(appdata_local, "cookies.txt")

UPDATER = "update.exe"

VERSION_FILE = resource_path("data/version.txt")

GITHUB_REPO = "Rayness/YT-Downloader"

HEADERS = {
    "User-Agent": "Updater-App",
    "Accept": "application/vnd.github.v3+json"
}

MANIFEST_URL = "https://raw.githubusercontent.com/Rayness/ClipTide_Video-Downloader/refs/heads/main/updates.json"
# Путь к папке с переводами
TRANSLATIONS_DIR = resource_path("data/localization")

THEME_DIR = os.path.join(appdata_local, "themes")

