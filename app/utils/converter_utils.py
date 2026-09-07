# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Разбор медиафайлов и генерация превью.

Что изменилось против прежней версии:

* ОДИН ffprobe вместо трёх процессов. Раньше на каждый добавленный файл
  запускались: ffprobe из get_thumbnail_base64, ffmpeg для кадра и ещё один
  ffprobe из print_video_info. Теперь метаданные читаются один раз и
  переиспользуются.
* Превью масштабируется до 160 px. Раньше кадр забирался в исходном
  разрешении и уезжал в интерфейс как base64 — один 4K-кадр это ~1 МБ строки
  в DOM на каждую карточку.
* Кадр берётся на 10% длительности, а не жёстко на 00:00:05. Для роликов
  короче пяти секунд превью просто не получалось.
* fps считается через Fraction. Раньше строка из метаданных файла попадала
  в eval() — то есть медиафайл мог выполнить произвольный код.
* Вызовы идут через app.utils.media: абсолютный путь к ffmpeg и
  CREATE_NO_WINDOW, поэтому не мигает консоль.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
from dataclasses import dataclass, field
from fractions import Fraction

from app.utils.media import popen, run

# Превью в карточке очереди ~120 px; берём 160 с запасом под HiDPI.
THUMBNAIL_MAX_SIDE = 160
THUMBNAIL_JPEG_QUALITY = 6  # шкала mjpeg -q:v, 2 = лучшее, 31 = худшее


def format_duration(seconds) -> str:
    """Секунды -> ЧЧ:ММ:СС."""
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        total = 0
    if total < 0:
        total = 0
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def _parse_fps(value) -> float:
    """
    '30000/1001' -> 29.97. Раньше здесь стоял eval() над строкой из файла.
    Fraction разбирает тот же формат, но ничего не исполняет.
    """
    if not value:
        return 0.0
    try:
        return float(Fraction(str(value)))
    except (ValueError, ZeroDivisionError, TypeError):
        return 0.0


def _to_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


@dataclass
class MediaInfo:
    """Результат одного прогона ffprobe."""
    duration: float = 0.0
    bitrate_kbps: int = 0
    width: int = 0
    height: int = 0
    codec: str = "?"
    fps: float = 0.0
    audio_codec: str = "нет"
    audio_bitrate_kbps: int = 0
    has_attached_pic: bool = False
    has_video: bool = False
    raw: dict = field(default_factory=dict)

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}" if self.width and self.height else "?"

    def as_ui_dict(self) -> dict:
        """Форма, которую ждёт карточка в интерфейсе."""
        return {
            "duration": round(self.duration),
            "bitrate": self.bitrate_kbps,
            "resolution": self.resolution,
            "codec": self.codec,
            "fps": round(self.fps),
            "audio": f"{self.audio_codec} ({self.audio_bitrate_kbps} kbps)",
        }


def probe(file_path: str) -> tuple[MediaInfo | None, str | None]:
    """
    Читает метаданные одним вызовом ffprobe.
    Возвращает (MediaInfo, None) либо (None, "текст ошибки").
    """
    if not os.path.exists(file_path):
        return None, f"Файл не найден: {file_path}"
    if not os.access(file_path, os.R_OK):
        return None, f"Нет прав на чтение файла: {file_path}"

    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        file_path,
    ]
    try:
        result = run(cmd, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return None, "ffprobe не ответил за 30 секунд"
    except Exception as e:
        return None, f"Не удалось запустить ffprobe: {e}"

    if result.returncode != 0:
        stderr = (result.stderr or b"").decode("utf-8", "replace").strip()
        return None, f"Ошибка ffprobe: {stderr or f'код {result.returncode}'}"

    try:
        data = json.loads((result.stdout or b"").decode("utf-8", "replace"))
    except json.JSONDecodeError as e:
        return None, f"Не удалось разобрать ответ ffprobe: {e}"

    streams = data.get("streams", [])
    fmt = data.get("format", {})

    info = MediaInfo(raw=data)
    info.duration = float(fmt.get("duration") or 0.0)
    info.bitrate_kbps = _to_int(fmt.get("bit_rate", 0)) // 1000

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is not None:
        info.has_video = True
        info.width = _to_int(video.get("width"))
        info.height = _to_int(video.get("height"))
        info.codec = video.get("codec_name", "?")
        info.fps = _parse_fps(video.get("avg_frame_rate") or video.get("r_frame_rate"))
        info.has_attached_pic = bool(video.get("disposition", {}).get("attached_pic", 0))

    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if audio is not None:
        info.audio_codec = audio.get("codec_name", "нет")
        info.audio_bitrate_kbps = _to_int(audio.get("bit_rate", 0)) // 1000

    return info, None


def thumbnail_data_uri(
    file_path: str,
    info: MediaInfo | None = None,
    max_side: int = THUMBNAIL_MAX_SIDE,
) -> tuple[str | None, str | None]:
    """
    Кадр-превью как data:URI. Если MediaInfo уже прочитан — передайте его,
    тогда ffprobe второй раз не запускается.
    Возвращает (data_uri, None) либо (None, "текст ошибки").
    """
    if info is None:
        info, error = probe(file_path)
        if info is None:
            return None, error

    if not info.has_video:
        return None, "В файле нет видеопотока"

    # Уменьшаем по большей стороне, сохраняя пропорции и чётность размеров.
    scale = f"scale='if(gt(iw,ih),min({max_side},iw),-2)':'if(gt(iw,ih),-2,min({max_side},ih))'"

    cmd = ["ffmpeg", "-v", "error"]
    if not info.has_attached_pic:
        # Кадр на 10% длительности: не чёрная заставка в начале и не за концом
        # короткого ролика. -ss ДО -i — быстрый seek по ключевым кадрам.
        seek = max(0.0, min(info.duration * 0.10, max(info.duration - 0.5, 0.0)))
        if seek > 0.05:
            cmd += ["-ss", f"{seek:.3f}"]
    cmd += ["-i", file_path]
    cmd += [
        "-map", "v:0",
        "-frames:v", "1",
        "-vf", scale,
        "-q:v", str(THUMBNAIL_JPEG_QUALITY),
        "-f", "image2pipe", "-vcodec", "mjpeg",
        "pipe:1",
    ]

    try:
        result = run(cmd, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return None, "ffmpeg не успел снять превью за 30 секунд"
    except Exception as e:
        return None, f"Не удалось запустить ffmpeg: {e}"

    if result.returncode != 0 or not result.stdout:
        stderr = (result.stderr or b"").decode("utf-8", "replace").strip()
        return None, f"Ошибка FFmpeg: {stderr or 'пустой кадр'}"

    return "data:image/jpeg;base64," + base64.b64encode(result.stdout).decode("ascii"), None


# ---------------------------------------------------------------------------
# Совместимость со старым кодом (editor.py). Оба возвращают то же, что раньше.
# ---------------------------------------------------------------------------

def print_video_info(file_path):
    """Устаревшая форма: кортеж из 8 значений либо строка с ошибкой."""
    info, error = probe(file_path)
    if info is None:
        return error
    if not info.has_video:
        return None
    return (
        round(info.duration), info.bitrate_kbps,
        info.width or "?", info.height or "?",
        info.codec, round(info.fps),
        info.audio_codec, info.audio_bitrate_kbps,
    )


def get_thumbnail_base64(video_path, use_first_frame_if_no_thumbnail=True):
    """Устаревшая форма: (data_uri | None, error | None)."""
    info, error = probe(video_path)
    if info is None:
        return None, error
    if not info.has_attached_pic and not use_first_frame_if_no_thumbnail:
        return None, "Встроенная обложка не найдена"
    return thumbnail_data_uri(video_path, info)
