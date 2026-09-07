# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Разовая уборка после перехода с onedir на onefile.

Пользователь 1.7.x обновляется старым update.exe: тот распаковывает архив
поверх установленной папки, кладёт новый ClipTide.exe — и на этом всё. Он
умеет только добавлять файлы, поэтому рядом навсегда остаются папка
_internal от прошлой сборки (сотни мегабайт) и сам update.exe, которому
больше нечего делать. Подчищаем это при первом запуске новой версии.

Работает только в onefile-сборке: там ресурсы распакованы во временную
папку, а рядом с exe не должно быть ни _internal, ни апдейтера. В onedir
_internal — рабочий каталог, трогать его нельзя, поэтому режим проверяется
явно, а не по одному лишь наличию папки.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.utils.paths import APP_DIR, IS_ONEFILE

#: Файлы старого апдейтера. update.exe.new — его собственное отложенное
#: обновление, которое так и не научились применять.
_LEGACY_FILES = ("update.exe", "update.exe.new")

#: По этим признакам отличаем свой _internal от чужой папки с таким именем
_PAYLOAD_MARKERS = ("base_library.zip", "data/version.txt")


def _looks_like_payload(folder: Path) -> bool:
    """Проверяет, что это действительно _internal от прошлой сборки."""
    return any((folder / marker).exists() for marker in _PAYLOAD_MARKERS)


def cleanup_legacy_install() -> int:
    """
    Удаляет остатки onedir-раскладки рядом с exe.

    Возвращает число освобождённых байт (0, если убирать нечего). Любая
    ошибка доступа просто пропускается: это уборка, а не необходимая работа.
    """
    if not IS_ONEFILE:
        return 0

    freed = 0

    payload = APP_DIR / "_internal"
    if payload.is_dir() and _looks_like_payload(payload):
        try:
            freed += sum(p.stat().st_size for p in payload.rglob("*") if p.is_file())
        except OSError:
            pass
        shutil.rmtree(payload, ignore_errors=True)

    for name in _LEGACY_FILES:
        leftover = APP_DIR / name
        if not leftover.is_file():
            continue
        try:
            size = leftover.stat().st_size
            leftover.unlink()
            freed += size
        except OSError:
            continue                      # занят или нет прав — не беда

    return freed
