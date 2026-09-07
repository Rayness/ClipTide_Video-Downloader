# Copyright (C) 2025 Rayness

# This program is free software under GPLv3. See LICENSE for details.

"""
Дизайн-токены интерфейса.

Темы приложения исторически лежат в виде CSS: файл styles.css с блоком
:root { --bg-color: ...; } и опциональным body.style-light для светлого
варианта. Пользователи ставят такие темы из стора и пишут свои.

Чтобы переход на Qt не обнулил эту экосистему, палитра читается прямо
из тех же CSS-файлов, а дальше подставляется в QSS-шаблон. Селекторы,
которые тема могла переопределять помимо :root, при этом игнорируются —
в QSS их перенести нельзя, и это единственное, что теряется.

Отдельно от цветов живёт ГЕОМЕТРИЯ (скругления, границы, интервалы,
типографика). Раньше она была в base.css как единый «строгий» слой поверх
любой темы — здесь та же роль у GEOMETRY.
"""

from __future__ import annotations

import re
from pathlib import Path

# --------------------------------------------------------------------------
# Геометрия и типографика: одна шкала на все темы.
# Тема задаёт цвет, приложение задаёт форму.
# --------------------------------------------------------------------------
GEOMETRY: dict[str, str] = {
    # Скругления — компактные и дисциплинированные
    "radius-sm": "4",
    "radius-md": "6",
    "radius-lg": "10",

    # Шаг сетки отступов (4px). Всё в интерфейсе кратно ему.
    "space-1": "4",
    "space-2": "8",
    "space-3": "12",
    "space-4": "16",
    "space-5": "24",
    "space-6": "32",

    # Типографика
    "font-family": '"Segoe UI Variable Display", "Segoe UI", "Inter", system-ui, sans-serif',
    "font-mono": '"Cascadia Mono", "Consolas", monospace',
    "font-size-xs": "11",
    "font-size-sm": "12",
    "font-size-md": "13",
    "font-size-lg": "15",
    "font-size-xl": "19",

    # Высоты управляющих элементов — единая вертикальная ритмика
    "control-height": "32",
    "control-height-sm": "26",
    "titlebar-height": "38",
    "sidebar-width": "212",
    "sidebar-width-collapsed": "56",

    "border-width": "1",
}

# --------------------------------------------------------------------------
# Палитра по умолчанию (графит) — используется, если тема не найдена
# или в ней нет какого-то токена.
# --------------------------------------------------------------------------
DEFAULT_PALETTE: dict[str, str] = {
    "bg-color": "#15171c",
    "dark-bg": "#101217",
    "card-bg": "#1d2026",
    "input-bg": "#0e1014",

    "text-color": "#e6e8ec",
    "text-secondary": "#8b919e",

    "border-color": "rgba(255, 255, 255, 0.07)",
    "border-strong": "rgba(255, 255, 255, 0.13)",

    "accent-color": "#3b82f6",
    "accent-dark": "#2f6fe0",
    "accent-color-transparent": "rgba(59, 130, 246, 0.16)",
    "accent-dark-transparent": "rgba(59, 130, 246, 0.08)",

    "accent-cyan": "#38bdf8",
    "accent-pink": "#818cf8",
    "accent-purple": "#6366f1",

    "btn-bg": "rgba(59, 130, 246, 0.12)",

    "danger-color": "#ef4444",
    "danger-dark": "#dc2626",
    "success-color": "#22c55e",
    "warning-color": "#f59e0b",

    "titlebar-bg": "#101217",
    "titlebar-text": "#e6e8ec",
    "titlebar-btn-hover": "#1d2026",

    "progress-gradient": "linear-gradient(90deg, #3b82f6, #38bdf8)",
    "main-gradient": "linear-gradient(135deg, rgba(59,130,246,0.10), rgba(59,130,246,0.04))",
}

# Токены, значение которых — градиент и требует перевода в синтаксис Qt
GRADIENT_TOKENS = frozenset({
    "progress-gradient", "main-gradient", "accent-gradient",
    "accent-gradient-text",
})

_VAR_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);", re.IGNORECASE)
_BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.MULTILINE)

# linear-gradient(<угол>deg, c1, c2, ...) — берём угол и список цветов
_LINEAR_RE = re.compile(r"linear-gradient\(\s*([^,]+?)\s*,\s*(.+)\s*\)$", re.IGNORECASE)


def _split_colors(text: str) -> list[str]:
    """Разбивает список цветов по запятым верхнего уровня (rgba(...) не рвём)."""
    parts, depth, current = [], 0, []
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def _angle_to_points(angle_text: str) -> tuple[float, float, float, float]:
    """
    CSS-угол -> координаты x1,y1,x2,y2 для qlineargradient.
    В CSS 0deg — снизу вверх, 90deg — слева направо.
    """
    text = angle_text.strip().lower()
    named = {"to right": 0.0, "to left": 180.0, "to bottom": 180.0, "to top": 0.0}
    if text in named:
        angle = 90.0 if text == "to right" else (270.0 if text == "to left" else named[text])
    else:
        try:
            angle = float(text.replace("deg", "").strip())
        except ValueError:
            angle = 90.0

    import math
    # Переводим в вектор направления в системе координат Qt (y растёт вниз)
    radians = math.radians(angle)
    dx, dy = math.sin(radians), -math.cos(radians)
    # Приводим к отрезку внутри единичного квадрата
    x1, y1 = (0.5 - dx / 2), (0.5 - dy / 2)
    x2, y2 = (0.5 + dx / 2), (0.5 + dy / 2)
    return round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3)


def css_gradient_to_qss(value: str) -> str:
    """
    'linear-gradient(90deg, #a, #b)' -> 'qlineargradient(...)'.
    Qt не понимает CSS-градиенты; если распарсить не вышло — отдаём первый
    цвет как заливку, это всегда лучше пустой строки.
    """
    value = value.strip()
    match = _LINEAR_RE.match(value)
    if not match:
        return value

    angle_text, colors_text = match.group(1), match.group(2)
    colors = _split_colors(colors_text)
    if not colors:
        return value
    if len(colors) == 1:
        return colors[0]

    x1, y1, x2, y2 = _angle_to_points(angle_text)
    stops = ", ".join(
        f"stop:{round(i / (len(colors) - 1), 3)} {color}"
        for i, color in enumerate(colors)
    )
    return f"qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, {stops})"


def parse_css_variables(css: str) -> dict[str, dict[str, str]]:
    """
    Достаёт кастомные свойства из CSS, сгруппированные по селектору.
    Возвращает {'селектор': {'имя-токена': 'значение'}}.
    """
    result: dict[str, dict[str, str]] = {}
    for selector, body in _BLOCK_RE.findall(css):
        variables = {
            name.lower(): val.strip()
            for name, val in _VAR_RE.findall(body)
        }
        if variables:
            result.setdefault(selector.strip().lower(), {}).update(variables)
    return result


def palette_from_css(path: str | Path, style: str = "dark") -> dict[str, str]:
    """
    Палитра темы из её styles.css.
    style='light' дополнительно накладывает блок body.style-light.
    Недостающие токены берутся из DEFAULT_PALETTE.
    """
    palette = dict(DEFAULT_PALETTE)

    try:
        css = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return palette

    blocks = parse_css_variables(css)

    for selector, variables in blocks.items():
        if ":root" in selector or selector == "html" or selector == "body":
            palette.update(variables)

    if style == "light":
        for selector, variables in blocks.items():
            if "style-light" in selector:
                palette.update(variables)

    # Градиенты переводим в синтаксис Qt один раз, на этапе загрузки темы
    for token in GRADIENT_TOKENS:
        if token in palette:
            palette[token] = css_gradient_to_qss(palette[token])

    return palette


def build_tokens(palette: dict[str, str]) -> dict[str, str]:
    """Полный набор подстановок для QSS-шаблона: цвета темы + общая геометрия."""
    tokens = dict(GEOMETRY)
    tokens.update(palette)
    return tokens
