# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Точка входа Qt-интерфейса.

Собирает контекст приложения, канал, окно и страницы. Логика (загрузчик,
конвертер, редактор, настройки) переиспользуется как есть — она общается
с интерфейсом только через UIChannel.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from app.core.context import AppContext
from app.utils.config.config import load_config
from app.utils.locale.translations import load_translations
from app.utils.notifications.notifications import load_notifications
from app.utils.paths import resource_path
from app.utils.queue.queue import load_queue_from_file
from app.utils.utils import get_local_version

from .channel import QtChannel
from .theme_manager import ThemeManager
from .window import MainWindow


def _placeholder_page(title: str, note: str) -> QWidget:
    """Временная страница для разделов, ещё не перенесённых на Qt."""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(8)

    heading = QLabel(title)
    heading.setProperty("heading", "1")
    layout.addWidget(heading)

    hint = QLabel(note)
    hint.setProperty("muted", "true")
    hint.setWordWrap(True)
    layout.addWidget(hint)

    layout.addStretch(1)
    return page


def build_context() -> AppContext:
    """Контекст с настройками — тот же, что использует прежний интерфейс."""
    ctx = AppContext()
    ctx.config = load_config()

    ctx.language = ctx.config.get("Settings", "language", fallback="ru")
    ctx.translations = load_translations(ctx.language)
    ctx.download_folder = ctx.config.get("Settings", "folder_path", fallback="downloads")
    ctx.converter_folder = ctx.config.get("Settings", "converter_folder",
                                          fallback=ctx.download_folder)
    ctx.theme = ctx.config.get("Themes", "theme", fallback="cliptide")
    ctx.style = ctx.config.get("Themes", "style", fallback="default")
    ctx.proxy_url = ctx.config.get("Proxy", "url", fallback="")
    ctx.proxy_enabled = ctx.config.get("Proxy", "enabled", fallback="False")

    ctx.download_queue = load_queue_from_file()
    ctx.notifications = load_notifications()
    return ctx


def create_application(argv: list[str] | None = None) -> tuple[QApplication, MainWindow, AppContext]:
    """Создаёт QApplication, окно и все страницы. Возвращает их, но не запускает цикл."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("ClipTide")

    ctx = build_context()

    channel = QtChannel()
    ctx.ui = channel

    version = f"v{get_local_version()}".replace("vv", "v")
    window = MainWindow("ClipTide", version)
    channel.parent = window

    icon_path = resource_path("data/ui/src/icon.png")
    pixmap = QPixmap(icon_path)
    if not pixmap.isNull():
        window.set_app_icon(pixmap.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        app.setWindowIcon(QIcon(pixmap))

    # --- тема ---
    themes = ThemeManager(app, ctx.config)
    themes.apply(ctx.theme, ctx.style)
    palette = themes.palette_for(ctx.theme, ctx.style)

    # --- модули логики ---
    from app.modules.converter.converter import Converter
    converter = Converter(ctx)

    # --- страницы ---
    from .pages.converter_page import ConverterPage

    window.add_page(
        _placeholder_page("Загрузчик", "Раздел ещё не перенесён на Qt."),
        "Загрузчик", "download",
    )
    converter_page = ConverterPage(converter, channel)
    window.add_page(converter_page, "Конвертер", "convert")
    window.add_page(
        _placeholder_page("Редактор", "Раздел ещё не перенесён на Qt."),
        "Редактор", "editor",
    )
    window.add_page(
        _placeholder_page("Настройки", "Раздел ещё не перенесён на Qt."),
        "Настройки", "settings",
    )

    window.sidebar.set_footer(f"ClipTide {version}")
    window.apply_palette(palette)
    converter_page.apply_palette(palette)

    channel.signals.status.connect(window.set_status)

    window.themes = themes
    window.ctx = ctx
    window.converter_page = converter_page
    return app, window, ctx


def main() -> int:
    from app.utils.utils import ffmpegreg, unicodefix
    from app.utils.logs.logs import logs

    unicodefix()
    ffmpegreg()
    logs()

    app, window, _ctx = create_application()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
