# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Точка входа Qt-интерфейса.

Собирает контекст приложения, канал, окно и страницы. Модули логики
(загрузчик, конвертер, редактор, настройки) переиспользуются как есть —
они общаются с интерфейсом только через UIChannel и не знают, что под ними
именно Qt.
"""

from __future__ import annotations

import sys
import threading

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.context import AppContext
from app.utils.config.config import load_config, update_config
from app.utils.notifications.notifications import load_notifications
from app.utils.paths import resource_path
from app.utils.queue.queue import load_queue_from_file
from app.utils.utils import check_for_update, get_local_version

from .channel import QtChannel
from .i18n import set_language, t
from .theme_manager import ThemeManager
from .widgets.thumbnail import ThumbnailLoader
from .window import MainWindow

#: Порядок разделов в боковой навигации
PAGE_DOWNLOADER = 0
PAGE_CONVERTER = 1
PAGE_EDITOR = 2
PAGE_NOTIFICATIONS = 3
PAGE_SETTINGS = 4


def build_context() -> AppContext:
    """Контекст с настройками приложения."""
    ctx = AppContext()
    ctx.config = load_config()
    update_config(ctx.config)

    ctx.language = ctx.config.get("Settings", "language", fallback="ru")
    # Один и тот же словарь: модулям логики — через контекст,
    # интерфейсу — через хелпер t()
    ctx.translations = set_language(ctx.language)
    ctx.download_folder = ctx.config.get("Settings", "folder_path", fallback="downloads")
    ctx.converter_folder = ctx.config.get(
        "Settings", "converter_folder", fallback=ctx.download_folder
    )
    ctx.theme = ctx.config.get("Themes", "theme", fallback="cliptide")
    ctx.style = ctx.config.get("Themes", "style", fallback="default")
    ctx.proxy_url = ctx.config.get("Proxy", "url", fallback="")
    ctx.proxy_enabled = ctx.config.get("Proxy", "enabled", fallback="False")

    ctx.download_queue = load_queue_from_file()
    ctx.notifications = load_notifications()
    return ctx


class Application:
    """Связывает окно, страницы и модули логики."""

    def __init__(self, argv: list[str] | None = None):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self.app = QApplication(argv if argv is not None else sys.argv)
        self.app.setApplicationName("ClipTide")
        self.app.setOrganizationName("ClipTide")

        self.ctx = build_context()
        self.channel = QtChannel()
        self.ctx.ui = self.channel

        self.version = f"v{get_local_version()}".replace("vv", "v")
        self.window = MainWindow("ClipTide", self.version)
        self.channel.parent = self.window

        self.themes = ThemeManager(self.app, self.ctx.config)
        self.themes.apply(self.ctx.theme, self.ctx.style)

        self.loader = ThumbnailLoader(self.window)
        self.loader.set_proxy(
            self.ctx.proxy_url if self.ctx.proxy_enabled == "True" else None
        )

        self._build_modules()
        self._build_pages()
        self._connect_global_signals()
        self._apply_palette()

        self.window.sidebar.set_footer(f"ClipTide {self.version}")
        self.window.closing.connect(self._on_close)

    # ------------------------------------------------------------------
    def _build_modules(self) -> None:
        from app.modules.converter.converter import Converter
        from app.modules.downloader.downloader import Downloader
        from app.modules.editor.editor import Editor
        from app.modules.settings.settings import SettingsManager
        from app.modules.system.module_manager import ModuleManager

        self.ctx.module_manager = ModuleManager(self.ctx)
        self.downloader = Downloader(self.ctx)
        self.converter = Converter(self.ctx)
        self.editor = Editor(self.ctx)
        self.settings = SettingsManager(self.ctx)

    def _build_pages(self) -> None:
        from .pages.converter_page import ConverterPage
        from .pages.downloader_page import DownloaderPage
        from .pages.editor_page import EditorPage
        from .pages.notifications_page import NotificationsPage
        from .pages.settings_page import SettingsPage

        self.downloader_page = DownloaderPage(self.downloader, self.channel, self.loader)
        self.converter_page = ConverterPage(self.converter, self.channel)
        self.editor_page = EditorPage(self.editor, self.channel)
        self.notifications_page = NotificationsPage(self.channel)
        self.settings_page = SettingsPage(
            self.settings, self.channel, self.themes, self.version,
            on_theme_applied=self._on_theme_applied,
        )

        self.window.add_page(self.downloader_page,
                             t("sections.video_downloader", "Загрузчик"), "download")
        self.window.add_page(self.converter_page,
                             t("sections.converter", "Конвертер"), "convert")
        self.window.add_page(self.editor_page,
                             t("sections.editor", "Редактор"), "editor")
        self.window.add_page(self.notifications_page,
                             t("sections.notifications", "Уведомления"), "bell")
        self.window.add_page(self.settings_page,
                             t("sections.setting", "Настройки"), "settings")

        self.pages = (
            self.downloader_page, self.converter_page, self.editor_page,
            self.notifications_page, self.settings_page,
        )

    # ------------------------------------------------------------------
    def _connect_global_signals(self) -> None:
        signals = self.channel.signals
        signals.status.connect(self.window.set_status)
        signals.alert.connect(self._show_alert)
        signals.log.connect(self._on_log)
        signals.download_folder_changed.connect(self._on_download_folder)
        signals.converter_folder_changed.connect(self._on_converter_folder)

    def _on_log(self, message: str, level: str, code: str, source: str) -> None:
        # Последнее сообщение любого модуля дублируем в строку состояния
        self.window.set_status(message)

    def _on_download_folder(self, path: str) -> None:
        self.ctx.download_folder = path

    def _on_converter_folder(self, path: str) -> None:
        self.ctx.converter_folder = path
        self.converter_page._refresh_output_label()

    def _show_alert(self, text: str, title: str, level: str) -> None:
        icon = {
            "error": QMessageBox.Critical,
            "warn": QMessageBox.Warning,
        }.get(level, QMessageBox.Information)
        box = QMessageBox(icon, title, text, QMessageBox.Ok, self.window)
        box.exec()

    # ------------------------------------------------------------------
    def _on_theme_applied(self, palette: dict) -> None:
        self._apply_palette(palette)

    def _apply_palette(self, palette: dict | None = None) -> None:
        if palette is None:
            palette = self.themes.palette_for(self.ctx.theme, self.ctx.style)
        self.window.apply_palette(palette)
        for page in getattr(self, "pages", ()):
            if hasattr(page, "apply_palette"):
                page.apply_palette(palette)

    # ------------------------------------------------------------------
    def _check_updates_async(self) -> None:
        """Сетевой запрос уводим с пути запуска, чтобы окно открывалось сразу."""
        def worker():
            try:
                if check_for_update():
                    self.channel.status("Доступна новая версия — откройте «Настройки»")
            except Exception as e:
                print(f"[WARN] Проверка обновлений не удалась: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _on_close(self) -> None:
        try:
            self.downloader.stopDownload()
            self.converter.stop_conversion()
            self.editor.stop_trim()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def run(self) -> int:
        icon_path = resource_path("data/ui/src/icon.png")
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            self.window.set_app_icon(
                pixmap.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.app.setWindowIcon(QIcon(pixmap))

        self.window.show()
        self._check_updates_async()
        return self.app.exec()


def main() -> int:
    from app.utils.logs.logs import logs
    from app.utils.utils import ffmpegreg, unicodefix

    unicodefix()
    ffmpegreg()
    logs()
    return Application().run()


if __name__ == "__main__":
    sys.exit(main())
