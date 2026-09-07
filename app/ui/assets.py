# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Мелкие растровые элементы для QSS, окрашенные под текущую тему.

Некоторые части QSS умеют только `image: url(...)` и не поддерживают
покраску: стрелка QComboBox, галочка QCheckBox, стрелка QSpinBox. Приём
из веба «нарисовать треугольник прозрачными границами» в Qt не работает —
получается не треугольник, а чёрточка.

Поэтому такие элементы рисуются на QPainter в цвет темы, кладутся в кэш
внутри пользовательских данных и подставляются в шаблон как пути.
Файлы перегенерируются при смене темы; имя включает цвет, так что
разные темы не конфликтуют.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap

from app.utils.paths import USER_DATA_DIR

ASSET_CACHE_DIR = Path(USER_DATA_DIR) / "cache" / "qss"

_SCALE = 3


def _token(color: str, name: str) -> str:
    digest = hashlib.md5(f"{name}:{color}".encode()).hexdigest()[:10]
    return f"{name}-{digest}.png"


def _new_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(size * _SCALE, size * _SCALE)
    pixmap.fill(Qt.transparent)
    return pixmap


def _pen(color: str, width: float) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _render_chevron(color: str, size: int = 10) -> QPixmap:
    pixmap = _new_pixmap(size)
    s = size * _SCALE
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(_pen(color, s * 0.13))
    path = QPainterPath(QPointF(s * 0.22, s * 0.36))
    path.lineTo(s * 0.5, s * 0.66)
    path.lineTo(s * 0.78, s * 0.36)
    painter.drawPath(path)
    painter.end()
    return pixmap


def _render_check(color: str, size: int = 12) -> QPixmap:
    pixmap = _new_pixmap(size)
    s = size * _SCALE
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(_pen(color, s * 0.16))
    path = QPainterPath(QPointF(s * 0.20, s * 0.52))
    path.lineTo(s * 0.42, s * 0.74)
    path.lineTo(s * 0.80, s * 0.28)
    painter.drawPath(path)
    painter.end()
    return pixmap


_RENDERERS = {
    "chevron-down": _render_chevron,
    "check": _render_check,
}


def _ensure(name: str, color: str) -> str:
    """Возвращает путь к PNG, отрисовав его при необходимости."""
    ASSET_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSET_CACHE_DIR / _token(color, name)
    if not path.is_file():
        pixmap = _RENDERERS[name](color)
        pixmap.save(str(path), "PNG")
    # QSS ждёт прямые слэши даже на Windows
    return str(path).replace("\\", "/")


def build_asset_tokens(palette: dict[str, str]) -> dict[str, str]:
    """Токены с путями к иконкам под текущую палитру."""
    secondary = palette.get("text-secondary", "#8b919e")
    return {
        "asset-chevron-down": _ensure("chevron-down", secondary),
        "asset-check": _ensure("check", "#ffffff"),
    }


def clear_cache() -> None:
    """Удаляет накопившиеся PNG (например, после долгой смены тем)."""
    if not ASSET_CACHE_DIR.is_dir():
        return
    for file in ASSET_CACHE_DIR.glob("*.png"):
        try:
            file.unlink()
        except OSError:
            pass
