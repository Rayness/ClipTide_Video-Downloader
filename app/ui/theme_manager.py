# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Поиск, загрузка и применение тем в Qt-интерфейсе.

Формат тем не меняется: папка с config.json и styles.css. Благодаря этому
темы, уже установленные пользователями из стора, продолжают работать —
из их CSS читается палитра, а форма приходит из GEOMETRY.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from app.utils.const import THEME_DIR
from app.utils.paths import resource_path

from .assets import build_asset_tokens
from .qss import render
from .tokens import DEFAULT_PALETTE, build_tokens, palette_from_css

BUILTIN_THEMES_DIR = Path(resource_path("data/ui/themes"))
USER_THEMES_DIR = Path(THEME_DIR)

FALLBACK_THEME_ID = "cliptide"


@dataclass
class Theme:
    id: str
    name: str
    path: Path
    styles: list[str] = field(default_factory=list)
    author: str = ""
    version: str = ""
    builtin: bool = True

    @property
    def stylesheet_path(self) -> Path:
        return self.path / "styles.css"


def _load_theme_dir(directory: Path, builtin: bool) -> Theme | None:
    config_path = directory / "config.json"
    if not config_path.is_file():
        return None
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[theme] {config_path}: {e}")
        return None
    return Theme(
        id=directory.name,
        name=config.get("title", directory.name),
        path=directory,
        styles=list(config.get("styles", [])),
        author=config.get("author", ""),
        version=str(config.get("version", "")),
        builtin=builtin,
    )


def discover_themes() -> dict[str, Theme]:
    """Все доступные темы: встроенные плюс установленные пользователем."""
    themes: dict[str, Theme] = {}
    for base, builtin in ((BUILTIN_THEMES_DIR, True), (USER_THEMES_DIR, False)):
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if not entry.is_dir():
                continue
            theme = _load_theme_dir(entry, builtin)
            if theme is not None:
                # Пользовательская тема с тем же id перекрывает встроенную
                themes[theme.id] = theme
    return themes


class ThemeManager:
    """Держит текущую тему и умеет применять её ко всему приложению."""

    def __init__(self, app, config=None):
        self._app = app
        self._config = config
        self.themes = discover_themes()
        self.current_id = FALLBACK_THEME_ID
        self.current_style = "default"

    # ------------------------------------------------------------------
    def reload(self) -> None:
        """Перечитать список тем (после установки новой из стора)."""
        self.themes = discover_themes()

    def resolve(self, theme_id: str) -> Theme | None:
        if theme_id in self.themes:
            return self.themes[theme_id]
        if FALLBACK_THEME_ID in self.themes:
            print(f"[theme] '{theme_id}' не найдена, беру {FALLBACK_THEME_ID}")
            return self.themes[FALLBACK_THEME_ID]
        return None

    def palette_for(self, theme_id: str, style: str = "default") -> dict[str, str]:
        theme = self.resolve(theme_id)
        if theme is None:
            return dict(DEFAULT_PALETTE)
        return palette_from_css(theme.stylesheet_path, style=style)

    def stylesheet_for(self, theme_id: str, style: str = "default") -> str:
        palette = self.palette_for(theme_id, style)
        tokens = build_tokens(palette)
        # Пути к PNG-иконкам, окрашенным под эту же палитру
        tokens.update(build_asset_tokens(palette))
        return render(tokens)

    # ------------------------------------------------------------------
    def apply(self, theme_id: str, style: str = "default") -> None:
        """Применяет тему ко всему QApplication."""
        self.current_id = theme_id
        self.current_style = style
        self._app.setStyleSheet(self.stylesheet_for(theme_id, style))

    def apply_from_config(self, config) -> None:
        theme_id = config.get("Themes", "theme", fallback=FALLBACK_THEME_ID)
        style = config.get("Themes", "style", fallback="default")
        self.apply(theme_id, style)

    def as_ui_list(self) -> list[dict]:
        """Список тем для экрана настроек."""
        return [
            {
                "id": theme.id,
                "name": theme.name,
                "styles": theme.styles,
                "author": theme.author,
                "version": theme.version,
                "builtin": theme.builtin,
            }
            for theme in self.themes.values()
        ]
