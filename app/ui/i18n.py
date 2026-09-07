# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Переводы интерфейса.

Формат словарей не менялся — это те же data/localization/<код>.json, что
использовал прежний интерфейс, с вложенными разделами. Доступ идёт по
точечному пути:

    t("sections.converter", "Конвертер")
    t("downloader.btn_stop", "Остановить")

Если ключа нет ни в выбранном языке, ни в резервном, возвращается default.
Благодаря этому новые строки Qt-интерфейса можно добавлять сразу, не
дожидаясь перевода на все девять языков: пока ключа нет, показывается
значение по умолчанию.
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.utils.const import TRANSLATIONS_DIR

#: Цепочка запасных языков. Если ключа нет в выбранном языке, берём из
#: английского, затем из русского — он самый полный. Показывать немцу
#: русскую строку раньше английской было бы странно.
FALLBACK_LANGUAGES = ("en", "ru")

_chain: list[dict] = []
_language = "ru"


def _load(language: str) -> dict:
    path = os.path.join(TRANSLATIONS_DIR, f"{language}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[i18n] {path}: {e}")
        return {}


def set_language(language: str) -> dict:
    """Загружает словарь языка и цепочку запасных. Возвращает основной словарь."""
    global _chain, _language
    _language = language or FALLBACK_LANGUAGES[-1]

    current = _load(_language)
    _chain = [current]
    for code in FALLBACK_LANGUAGES:
        if code != _language:
            _chain.append(_load(code))
    return current


def language() -> str:
    return _language


def _lookup(source: dict, path: str) -> Any:
    node: Any = source
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def t(path: str, default: str = "") -> str:
    """Строка перевода по точечному пути; default — если ключа нигде нет."""
    for source in _chain:
        value = _lookup(source, path)
        if isinstance(value, str) and value:
            return value
    return default or path


def section(path: str) -> dict:
    """Вложенный раздел словаря (или пустой, если его нет)."""
    for source in _chain:
        value = _lookup(source, path)
        if isinstance(value, dict):
            return value
    return {}
