# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Набор иконок, отрисованных кодом.

Прежний интерфейс подключал Font Awesome с cdnjs.cloudflare.com. Это значило
две вещи: без интернета иконки не появлялись вовсе, а с интернетом первый
кадр ждал загрузки внешнего CSS и шрифта (~150 КБ). Здесь иконки рисуются
на QPainter — они локальные, векторные, красятся в цвет темы и ничего
не весят в дистрибутиве.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_RENDER_SCALE = 4  # рисуем крупнее и отдаём как HiDPI-пиксмап


def _pen(color: str, width: float) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _draw_download(p: QPainter, s: float, color: str) -> None:
    p.setPen(_pen(color, s * 0.09))
    p.drawLine(QPointF(s * 0.5, s * 0.14), QPointF(s * 0.5, s * 0.62))
    path = QPainterPath(QPointF(s * 0.30, s * 0.44))
    path.lineTo(s * 0.5, s * 0.64)
    path.lineTo(s * 0.70, s * 0.44)
    p.drawPath(path)
    p.drawLine(QPointF(s * 0.20, s * 0.82), QPointF(s * 0.80, s * 0.82))


def _draw_convert(p: QPainter, s: float, color: str) -> None:
    p.setPen(_pen(color, s * 0.09))
    # Две встречные стрелки
    p.drawLine(QPointF(s * 0.18, s * 0.36), QPointF(s * 0.78, s * 0.36))
    head = QPainterPath(QPointF(s * 0.62, s * 0.20))
    head.lineTo(s * 0.80, s * 0.36)
    head.lineTo(s * 0.62, s * 0.52)
    p.drawPath(head)

    p.drawLine(QPointF(s * 0.82, s * 0.66), QPointF(s * 0.22, s * 0.66))
    head2 = QPainterPath(QPointF(s * 0.38, s * 0.50))
    head2.lineTo(s * 0.20, s * 0.66)
    head2.lineTo(s * 0.38, s * 0.82)
    p.drawPath(head2)


def _draw_editor(p: QPainter, s: float, color: str) -> None:
    # Ножницы
    p.setPen(_pen(color, s * 0.085))
    p.drawLine(QPointF(s * 0.28, s * 0.20), QPointF(s * 0.74, s * 0.72))
    p.drawLine(QPointF(s * 0.72, s * 0.20), QPointF(s * 0.26, s * 0.72))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(s * 0.16, s * 0.68, s * 0.20, s * 0.20))
    p.drawEllipse(QRectF(s * 0.64, s * 0.68, s * 0.20, s * 0.20))


def _draw_store(p: QPainter, s: float, color: str) -> None:
    p.setPen(_pen(color, s * 0.085))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(s * 0.16, s * 0.30, s * 0.68, s * 0.56), s * 0.08, s * 0.08)
    path = QPainterPath(QPointF(s * 0.34, s * 0.36))
    path.lineTo(s * 0.34, s * 0.22)
    path.arcTo(QRectF(s * 0.34, s * 0.10, s * 0.32, s * 0.24), 180, -180)
    path.lineTo(s * 0.66, s * 0.36)
    p.drawPath(path)


def _draw_settings(p: QPainter, s: float, color: str) -> None:
    p.setPen(_pen(color, s * 0.085))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(s * 0.36, s * 0.36, s * 0.28, s * 0.28))
    import math
    for index in range(8):
        angle = math.radians(index * 45)
        cos, sin = math.cos(angle), math.sin(angle)
        p.drawLine(
            QPointF(s * 0.5 + cos * s * 0.24, s * 0.5 + sin * s * 0.24),
            QPointF(s * 0.5 + cos * s * 0.36, s * 0.5 + sin * s * 0.36),
        )


def _draw_bell(p: QPainter, s: float, color: str) -> None:
    p.setPen(_pen(color, s * 0.085))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath(QPointF(s * 0.22, s * 0.68))
    path.lineTo(s * 0.30, s * 0.56)
    path.lineTo(s * 0.30, s * 0.42)
    path.arcTo(QRectF(s * 0.30, s * 0.14, s * 0.40, s * 0.40), 180, -180)
    path.lineTo(s * 0.70, s * 0.56)
    path.lineTo(s * 0.78, s * 0.68)
    path.closeSubpath()
    p.drawPath(path)
    p.drawArc(QRectF(s * 0.40, s * 0.70, s * 0.20, s * 0.16), 0, -180 * 16)


def _draw_folder(p: QPainter, s: float, color: str) -> None:
    p.setPen(_pen(color, s * 0.085))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath(QPointF(s * 0.16, s * 0.76))
    path.lineTo(s * 0.16, s * 0.26)
    path.lineTo(s * 0.42, s * 0.26)
    path.lineTo(s * 0.50, s * 0.38)
    path.lineTo(s * 0.84, s * 0.38)
    path.lineTo(s * 0.84, s * 0.76)
    path.closeSubpath()
    p.drawPath(path)


def _draw_plus(p: QPainter, s: float, color: str) -> None:
    p.setPen(_pen(color, s * 0.10))
    p.drawLine(QPointF(s * 0.5, s * 0.22), QPointF(s * 0.5, s * 0.78))
    p.drawLine(QPointF(s * 0.22, s * 0.5), QPointF(s * 0.78, s * 0.5))


def _draw_trash(p: QPainter, s: float, color: str) -> None:
    p.setPen(_pen(color, s * 0.085))
    p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(s * 0.20, s * 0.30), QPointF(s * 0.80, s * 0.30))
    p.drawLine(QPointF(s * 0.40, s * 0.30), QPointF(s * 0.42, s * 0.20))
    p.drawLine(QPointF(s * 0.60, s * 0.30), QPointF(s * 0.58, s * 0.20))
    path = QPainterPath(QPointF(s * 0.28, s * 0.30))
    path.lineTo(s * 0.33, s * 0.82)
    path.lineTo(s * 0.67, s * 0.82)
    path.lineTo(s * 0.72, s * 0.30)
    p.drawPath(path)


def _draw_play(p: QPainter, s: float, color: str) -> None:
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    path = QPainterPath(QPointF(s * 0.30, s * 0.20))
    path.lineTo(s * 0.80, s * 0.50)
    path.lineTo(s * 0.30, s * 0.80)
    path.closeSubpath()
    p.drawPath(path)


def _draw_stop(p: QPainter, s: float, color: str) -> None:
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(s * 0.26, s * 0.26, s * 0.48, s * 0.48), s * 0.06, s * 0.06)


_PAINTERS = {
    "download": _draw_download,
    "convert": _draw_convert,
    "editor": _draw_editor,
    "store": _draw_store,
    "settings": _draw_settings,
    "bell": _draw_bell,
    "folder": _draw_folder,
    "plus": _draw_plus,
    "trash": _draw_trash,
    "play": _draw_play,
    "stop": _draw_stop,
}

_cache: dict[tuple[str, str, int], QIcon] = {}


def icon(name: str, color: str = "#e6e8ec", size: int = 18) -> QIcon:
    """Иконка по имени, покрашенная в переданный цвет."""
    key = (name, color, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    painter_fn = _PAINTERS.get(name)
    if painter_fn is None:
        return QIcon()

    pixmap = QPixmap(size * _RENDER_SCALE, size * _RENDER_SCALE)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter_fn(painter, float(size * _RENDER_SCALE), color)
    painter.end()

    pixmap.setDevicePixelRatio(_RENDER_SCALE)
    result = QIcon(pixmap)
    _cache[key] = result
    return result


def clear_cache() -> None:
    """Сбрасывает кэш при смене темы — цвета иконок должны обновиться."""
    _cache.clear()
