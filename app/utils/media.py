# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Единая точка доступа к ffmpeg/ffprobe.

Зачем отдельный модуль:
 * раньше модули вызывали ffmpeg по имени (`["ffmpeg", ...]`), полагаясь на то,
   что `ffmpegreg()` допишет папку в конец PATH. Из-за дописывания *в конец*
   системный ffmpeg (если он есть у пользователя) выигрывал у встроенного,
   и поведение приложения зависело от машины;
 * часть вызовов создавалась без CREATE_NO_WINDOW и мигала чёрной консолью;
 * путь к бинарям был захардкожен как ffmpeg/ffmpeg-7.1-essentials_build/bin,
   то есть привязан к конкретной версии сборки ffmpeg.

Теперь путь ищется среди нескольких кандидатов, вычисляется один раз и
раздаётся как абсолютный — PATH перестаёт влиять на результат.
"""

from __future__ import annotations

import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from app.utils.paths import RESOURCE_DIR, USER_DATA_DIR

# Флаг «не показывать окно консоли». На не-Windows его не существует.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""

# Кандидаты на папку с бинарями, в порядке приоритета.
# Первый — новая плоская раскладка, второй — историческая (версия в имени),
# третий — ffmpeg, докинутый пользователем рядом с данными приложения.
_BIN_DIR_CANDIDATES = (
    RESOURCE_DIR / "ffmpeg" / "bin",
    RESOURCE_DIR / "ffmpeg" / "ffmpeg-7.1-essentials_build" / "bin",
    RESOURCE_DIR / "ffmpeg",
    USER_DATA_DIR / "ffmpeg" / "bin",
)


@lru_cache(maxsize=1)
def ffmpeg_bin_dir() -> Path | None:
    """Папка со встроенными ffmpeg.exe/ffprobe.exe, либо None если её нет."""
    for candidate in _BIN_DIR_CANDIDATES:
        if (candidate / f"ffmpeg{_EXE_SUFFIX}").is_file():
            return candidate
    return None


@lru_cache(maxsize=2)
def _tool(name: str) -> str:
    """Абсолютный путь к ffmpeg/ffprobe; фолбэк — голое имя (системный PATH)."""
    bin_dir = ffmpeg_bin_dir()
    if bin_dir is not None:
        exe = bin_dir / f"{name}{_EXE_SUFFIX}"
        if exe.is_file():
            return str(exe)
    return name


def ffmpeg_exe() -> str:
    return _tool("ffmpeg")


def ffprobe_exe() -> str:
    return _tool("ffprobe")


def register_ffmpeg_path() -> None:
    """
    Пробрасывает встроенный ffmpeg в PATH — *в начало*, чтобы он имел приоритет
    над системным. Нужен для сторонних библиотек (ffmpeg-python, yt-dlp),
    которые ищут бинарь сами и не принимают абсолютный путь.
    """
    bin_dir = ffmpeg_bin_dir()
    if bin_dir is None:
        return
    bin_str = str(bin_dir)
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep) if current else []
    if bin_str in parts:
        return
    os.environ["PATH"] = os.pathsep.join([bin_str, *parts]) if parts else bin_str


def popen(args, **kwargs) -> subprocess.Popen:
    """subprocess.Popen с подавлением консольного окна и абсолютным ffmpeg."""
    kwargs.setdefault("creationflags", NO_WINDOW)
    return subprocess.Popen(_resolve_argv(args), **kwargs)


def run(args, **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run с подавлением консольного окна и абсолютным ffmpeg."""
    kwargs.setdefault("creationflags", NO_WINDOW)
    return subprocess.run(_resolve_argv(args), **kwargs)


def _resolve_argv(args):
    """Подменяет argv[0] == 'ffmpeg'/'ffprobe' на абсолютный путь."""
    if not args:
        return args
    head = args[0]
    if head == "ffmpeg":
        return [ffmpeg_exe(), *args[1:]]
    if head == "ffprobe":
        return [ffprobe_exe(), *args[1:]]
    return args
