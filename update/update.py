# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Апдейтер ClipTide.

Отдельный исполняемый файл: скачивает архив новой версии, распаковывает его
поверх установленной программы и запускает её заново.

Интерфейс переведён с pywebview на Qt вместе с основным приложением —
иначе зависимость от Edge WebView2 осталась бы через апдейтер.
Логика обновления не менялась.
"""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
import sys
import threading
import time
import zipfile

import psutil
import requests
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

GITHUB_REPO = "Rayness/YT-Downloader"
APP_EXECUTABLE = "ClipTide.exe"
MANIFEST_URL = (
    "https://raw.githubusercontent.com/Rayness/"
    "ClipTide_Video-Downloader/refs/heads/main/updates.json"
)

# --- пути -------------------------------------------------------------
if getattr(sys, "frozen", False):
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    BASE_DIR = sys._MEIPASS
else:
    EXE_DIR = os.getcwd()
    BASE_DIR = os.getcwd()

CURRENT_DIR = EXE_DIR

# Portable-режим: маркерный файл рядом с exe, обновление ставится в ту же папку
IS_PORTABLE = os.path.exists(os.path.join(EXE_DIR, "portable.txt"))

if IS_PORTABLE:
    TARGET_DIR = EXE_DIR
    CONFIG_PATH = os.path.join(EXE_DIR, "userdata", "config.ini")
else:
    TARGET_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "ClipTide")
    CONFIG_PATH = os.path.join(os.environ["LOCALAPPDATA"], "ClipTide", "config.ini")

TEMP_BASE = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "ClipTideUpdater")
DOWNLOAD_DIR = os.path.join(TEMP_BASE, "download")
EXTRACT_DIR = os.path.join(TEMP_BASE, "extract")


class UpdaterSignals(QObject):
    """Логика работает в фоновом потоке; в виджеты идём только сигналами."""

    log = Signal(str)
    status = Signal(str)
    progress = Signal(int)
    state = Signal(str)          # checking | ready | no-update | error | done
    finished = Signal()


class Updater:
    """Вся работа по обновлению. Интерфейс получает события через signals."""

    def __init__(self, signals: UpdaterSignals):
        self.signals = signals
        self.download_url: str | None = None

    # ------------------------------------------------------------------
    def log(self, message: str) -> None:
        print(message)
        self.signals.log.emit(str(message))

    def set_status(self, text: str) -> None:
        self.signals.status.emit(str(text))

    def set_progress(self, percent: int) -> None:
        self.signals.progress.emit(int(percent))

    def set_state(self, state: str) -> None:
        self.signals.state.emit(state)

    # ------------------------------------------------------------------
    @staticmethod
    def _headers_for(url: str) -> dict:
        if "github.com" in url:
            return {"User-Agent": "Updater-App",
                    "Accept": "application/vnd.github.v3+json"}
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }

    def get_update_channel(self) -> str:
        if not os.path.exists(CONFIG_PATH):
            return "stable"
        try:
            config = configparser.ConfigParser()
            config.read(CONFIG_PATH, encoding="utf-8")
            return config.get("Updates", "channel", fallback="stable")
        except Exception:
            return "stable"

    def get_local_version(self) -> str:
        # Старая раскладка: data/ рядом с exe; новая (onedir): data/ в _internal
        for candidate in (
            os.path.join(CURRENT_DIR, "data", "version.txt"),
            os.path.join(CURRENT_DIR, "_internal", "data", "version.txt"),
        ):
            if os.path.exists(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8") as handle:
                        return handle.read().strip()
                except OSError:
                    continue
        return "0.0.0"

    # ------------------------------------------------------------------
    def check_for_updates(self) -> None:
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self) -> None:
        self.set_state("checking")
        self.log("Проверка версии...")
        local = self.get_local_version()
        channel = self.get_update_channel()
        self.log(f"Канал обновлений: {channel.upper()}")

        try:
            response = requests.get(
                MANIFEST_URL, headers=self._headers_for(MANIFEST_URL), timeout=10
            )
            if response.status_code != 200:
                self.log(f"Ошибка получения манифеста: {response.status_code}")
                self.set_state("no-update")
                return

            data = response.json()
            if channel not in data:
                self.log(f"Канал '{channel}' не найден, перехожу на stable")
                channel = "stable"

            channel_data = data.get(channel, {})
            latest = channel_data.get("version", "0.0.0")
            self.download_url = channel_data.get("url")
            description = channel_data.get("description", "")

            if latest == local:
                self.set_status(f"У вас последняя версия ({local})")
                self.set_state("no-update")
                return

            self.set_status(f"Доступна версия {latest}")
            if description:
                self.log(f"Описание: {description}")

            if not self.download_url:
                self.log("В манифесте не указан адрес загрузки")
                self.set_state("no-update")
            else:
                self.set_state("ready")

        except Exception as e:
            self.log(f"Ошибка: {e}")
            self.set_state("error")

    # ------------------------------------------------------------------
    def start_update(self) -> None:
        threading.Thread(target=self._update, daemon=True).start()

    def _update(self) -> None:
        if not self.download_url:
            self.log("Адрес загрузки не найден")
            return

        if os.path.exists(TEMP_BASE):
            shutil.rmtree(TEMP_BASE, ignore_errors=True)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        os.makedirs(EXTRACT_DIR, exist_ok=True)

        archive_path = os.path.join(DOWNLOAD_DIR, "update.zip")
        self.set_status("Скачивание...")
        self.log(f"Источник: {self.download_url}")

        try:
            response = requests.get(
                self.download_url,
                headers=self._headers_for(self.download_url),
                stream=True, timeout=60,
            )
            if response.status_code != 200:
                self.log(f"Ошибка сервера: {response.status_code}")
                self.set_state("error")
                return

            total = int(response.headers.get("content-length", 0))
            downloaded = 0
            last_percent = -1
            with open(archive_path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        percent = int(downloaded / total * 100)
                        if percent != last_percent:
                            last_percent = percent
                            self.set_progress(percent)
        except Exception as e:
            self.log(f"Ошибка скачивания: {e}")
            self.set_state("error")
            return

        self.set_status("Распаковка...")
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(EXTRACT_DIR)
        except Exception as e:
            self.log(f"Ошибка архива: {e}")
            self.set_state("error")
            return

        self.set_status("Закрытие программы...")
        self._terminate_app()

        self.set_status("Установка...")
        try:
            self._install()
        except Exception as e:
            self.log(f"Ошибка копирования: {e}")
            self.set_state("error")
            return

        self._create_shortcut()
        self._cleanup_old()

        self.set_progress(100)
        self.set_status("Обновление завершено")
        self.set_state("done")

    def _install(self) -> None:
        os.makedirs(TARGET_DIR, exist_ok=True)

        source_root = EXTRACT_DIR
        entries = os.listdir(EXTRACT_DIR)
        if len(entries) == 1 and os.path.isdir(os.path.join(EXTRACT_DIR, entries[0])):
            source_root = os.path.join(EXTRACT_DIR, entries[0])

        for root, _dirs, files in os.walk(source_root):
            relative = os.path.relpath(root, source_root)
            destination = os.path.join(TARGET_DIR, relative)
            os.makedirs(destination, exist_ok=True)

            for name in files:
                source = os.path.join(root, name)
                target = os.path.join(destination, name)

                # Себя заменить на ходу нельзя — кладём рядом как .new,
                # основное приложение подменит файл при следующем запуске
                if name.lower() in ("update.exe", "updater.exe"):
                    target += ".new"
                    self.log(f"Отложенное обновление: {name}")

                if os.path.exists(target):
                    try:
                        os.remove(target)
                    except OSError as e:
                        self.log(f"Пропуск занятого файла {name}: {e}")
                        continue

                shutil.copy2(source, target)

        self.log("Файлы обновлены.")

    def launch_app(self) -> bool:
        target = os.path.join(TARGET_DIR, APP_EXECUTABLE)
        if not os.path.exists(target):
            self.log("Файл программы не найден")
            return False
        try:
            subprocess.Popen([target], cwd=TARGET_DIR)
            return True
        except Exception as e:
            self.log(f"Ошибка запуска: {e}")
            return False

    @staticmethod
    def _terminate_app() -> None:
        for process in psutil.process_iter(["name"]):
            if process.info["name"] == APP_EXECUTABLE:
                try:
                    process.terminate()
                except psutil.Error:
                    pass
        time.sleep(1)

    def _create_shortcut(self) -> None:
        if IS_PORTABLE:
            return
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        shortcut = os.path.join(desktop, "ClipTide.lnk")
        target = os.path.join(TARGET_DIR, APP_EXECUTABLE)
        command = (
            f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{shortcut}");'
            f'$s.TargetPath="{target}";$s.WorkingDirectory="{TARGET_DIR}";$s.Save()'
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", command],
                       creationflags=subprocess.CREATE_NO_WINDOW)

    def _cleanup_old(self) -> None:
        if os.path.normpath(CURRENT_DIR) == os.path.normpath(TARGET_DIR):
            return
        self.log("Удаление старой версии...")
        try:
            old_exe = os.path.join(CURRENT_DIR, APP_EXECUTABLE)
            if os.path.exists(old_exe):
                os.remove(old_exe)
            for folder in ("data", "_internal"):
                path = os.path.join(CURRENT_DIR, folder)
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


# ======================================================================
# Интерфейс
# ======================================================================
class UpdaterWindow(QWidget):
    def __init__(self, updater: Updater):
        super().__init__()
        self.updater = updater
        self.setWindowTitle("Обновление ClipTide")
        self.setFixedSize(460, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel("Обновление ClipTide")
        title.setProperty("heading", "1")
        layout.addWidget(title)

        self.status = QLabel("Проверка обновлений...")
        self.status.setProperty("muted", "true")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        separator = QFrame()
        separator.setProperty("separator", "true")
        layout.addWidget(separator)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.btn_update = QPushButton("Обновить")
        self.btn_update.setProperty("variant", "primary")
        self.btn_update.setEnabled(False)
        self.btn_update.clicked.connect(self._on_update)
        buttons.addWidget(self.btn_update)

        self.btn_launch = QPushButton("Запустить ClipTide")
        self.btn_launch.setVisible(False)
        self.btn_launch.clicked.connect(self._on_launch)
        buttons.addWidget(self.btn_launch)

        buttons.addStretch(1)

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.setProperty("variant", "ghost")
        self.btn_close.clicked.connect(self.close)
        buttons.addWidget(self.btn_close)
        layout.addLayout(buttons)

        signals = updater.signals
        signals.log.connect(self._append_log)
        signals.status.connect(self.status.setText)
        signals.progress.connect(self.progress.setValue)
        signals.state.connect(self._on_state)

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _on_state(self, state: str) -> None:
        if state == "ready":
            self.btn_update.setEnabled(True)
        elif state in ("no-update", "error"):
            self.btn_update.setEnabled(False)
        elif state == "done":
            self.btn_update.setEnabled(False)
            self.btn_launch.setVisible(True)

    def _on_update(self) -> None:
        self.btn_update.setEnabled(False)
        self.updater.start_update()

    def _on_launch(self) -> None:
        if self.updater.launch_app():
            self.close()


def _stylesheet() -> str:
    """Тот же QSS, что и у основного приложения, с палитрой по умолчанию."""
    try:
        from app.ui.assets import build_asset_tokens
        from app.ui.qss import render
        from app.ui.tokens import DEFAULT_PALETTE, build_tokens

        tokens = build_tokens(DEFAULT_PALETTE)
        tokens.update(build_asset_tokens(DEFAULT_PALETTE))
        return render(tokens)
    except Exception as e:
        print(f"[updater] стили не загружены: {e}")
        return ""


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ClipTide Updater")
    app.setStyleSheet(_stylesheet())

    signals = UpdaterSignals()
    updater = Updater(signals)
    window = UpdaterWindow(updater)
    window.show()

    updater.check_for_updates()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
