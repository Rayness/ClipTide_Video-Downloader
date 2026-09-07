# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Профили кодировщиков и сборка команд ffmpeg.

Вынесено из converter.py, где команда собиралась инлайн и имела несколько
проблем:

* `-crf` подставлялся любому кодеку. Аппаратные кодировщики (NVENC, QSV, AMF)
  этот флаг не понимают — у них своя шкала (-cq / -global_quality / -qp),
  и попытка перекодировать через них просто падала.
* `-preset medium` был захардкожен, хотя пресеты у libx264 и NVENC называются
  по-разному, а в настройках приложения пресет уже есть.
* Значения разрешений из интерфейса ('4K', '2K') уезжали в фильтр как есть,
  давая `scale=-2:4K` — невалидный фильтр и падение конвертации.
* Для mp4 не выставлялся +faststart, поэтому файл нельзя было начать смотреть
  до полной загрузки.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.utils.media import run

# --------------------------------------------------------------------------
# Разрешения
# --------------------------------------------------------------------------
# Ключи — ровно те value, что стоят в <select id="cv-res"> в интерфейсе.
RESOLUTION_HEIGHTS = {
    "original": None,
    "4K": 2160,
    "2K": 1440,
    "1080": 1080,
    "720": 720,
    "480": 480,
    "360": 360,
}


def resolution_filter(value: str | None) -> str | None:
    """'720' -> 'scale=-2:720'. Апскейл не делаем — только уменьшаем."""
    if not value:
        return None
    height = RESOLUTION_HEIGHTS.get(str(value))
    if height is None:
        # Пользователь мог задать число напрямую
        try:
            height = int(str(value).rstrip("p"))
        except ValueError:
            return None
    # min(ih,H) не даёт растянуть 480p до 4K; -2 держит чётную ширину.
    return f"scale=-2:'min({height},ih)'"


# --------------------------------------------------------------------------
# Кодировщики
# --------------------------------------------------------------------------
# rate_flag  — каким флагом задаётся качество у этого семейства
# presets    — допустимые пресеты, от быстрого к качественному
# hardware   — требует поддержки со стороны GPU/драйвера
VIDEO_ENCODERS = {
    "libx264":     {"rate_flag": "-crf", "presets": ("ultrafast", "veryfast", "fast", "medium", "slow"), "hardware": False, "family": "h264"},
    "libx265":     {"rate_flag": "-crf", "presets": ("ultrafast", "veryfast", "fast", "medium", "slow"), "hardware": False, "family": "hevc"},
    "libvpx-vp9":  {"rate_flag": "-crf", "presets": (), "hardware": False, "family": "vp9"},
    "libsvtav1":   {"rate_flag": "-crf", "presets": (), "hardware": False, "family": "av1"},
    "h264_nvenc":  {"rate_flag": "-cq",  "presets": ("p1", "p4", "p7"), "hardware": True, "family": "h264"},
    "hevc_nvenc":  {"rate_flag": "-cq",  "presets": ("p1", "p4", "p7"), "hardware": True, "family": "hevc"},
    "av1_nvenc":   {"rate_flag": "-cq",  "presets": ("p1", "p4", "p7"), "hardware": True, "family": "av1"},
    "h264_qsv":    {"rate_flag": "-global_quality", "presets": ("veryfast", "medium", "slow"), "hardware": True, "family": "h264"},
    "hevc_qsv":    {"rate_flag": "-global_quality", "presets": ("veryfast", "medium", "slow"), "hardware": True, "family": "hevc"},
    "h264_amf":    {"rate_flag": "-qp_i", "presets": ("speed", "balanced", "quality"), "hardware": True, "family": "h264"},
    "hevc_amf":    {"rate_flag": "-qp_i", "presets": ("speed", "balanced", "quality"), "hardware": True, "family": "hevc"},
}

# Что предпочитаем, когда пользователь выбрал 'auto': сначала железо, потом CPU.
_AUTO_PREFERENCE = {
    "h264": ("h264_nvenc", "h264_qsv", "h264_amf", "libx264"),
    "hevc": ("hevc_nvenc", "hevc_qsv", "hevc_amf", "libx265"),
}

# Контейнер -> семейство кодека по умолчанию
CONTAINER_DEFAULT_FAMILY = {
    "mp4": "h264", "mov": "h264", "mkv": "h264", "avi": "h264", "webm": "vp9",
}

AUDIO_ONLY_FORMATS = {"mp3", "aac", "wav", "flac", "opus", "m4a", "ogg"}

# Аудио-настройки для режима «только звук»
_AUDIO_PROFILES = {
    "mp3":  ["-c:a", "libmp3lame", "-q:a", "2"],
    "aac":  ["-c:a", "aac", "-b:a", "192k"],
    "m4a":  ["-c:a", "aac", "-b:a", "192k"],
    "wav":  ["-c:a", "pcm_s16le"],
    "flac": ["-c:a", "flac"],
    "opus": ["-c:a", "libopus", "-b:a", "128k"],
    "ogg":  ["-c:a", "libvorbis", "-q:a", "5"],
}


@lru_cache(maxsize=1)
def available_encoders() -> frozenset[str]:
    """
    Кодировщики, которые реально собраны в нашем ffmpeg.
    Один запуск `ffmpeg -encoders`, результат кэшируется на всё время работы.
    """
    try:
        result = run(["ffmpeg", "-hide_banner", "-v", "error", "-encoders"],
                     capture_output=True, timeout=15)
    except Exception:
        return frozenset()
    text = (result.stdout or b"").decode("utf-8", "replace")
    # Строки вида: " V....D h264_nvenc           NVIDIA NVENC H.264 encoder"
    return frozenset(re.findall(r"^\s*[VAS][.A-Z]{5}\s+(\S+)", text, re.MULTILINE))


@lru_cache(maxsize=8)
def _encoder_works(name: str) -> bool:
    """
    Наличие кодировщика в сборке ещё не значит, что он запустится: у NVENC
    может не быть видеокарты, у QSV — драйвера. Проверяем пробным кадром.
    """
    if name not in available_encoders():
        return False
    try:
        result = run(
            ["ffmpeg", "-hide_banner", "-v", "error", "-f", "lavfi",
             "-i", "nullsrc=s=256x256:d=0.1", "-c:v", name,
             "-frames:v", "1", "-f", "null", "-"],
            capture_output=True, timeout=25,
        )
    except Exception:
        return False
    return result.returncode == 0


def resolve_encoder(codec: str, container: str) -> str:
    """
    Приводит выбор пользователя к реальному имени кодировщика.
    'auto' -> лучший доступный для контейнера, с проверкой железа.
    """
    codec = (codec or "auto").strip()

    if codec in ("copy",):
        return "copy"

    if codec == "auto":
        family = CONTAINER_DEFAULT_FAMILY.get(container, "h264")
        for candidate in _AUTO_PREFERENCE.get(family, ("libx264",)):
            spec = VIDEO_ENCODERS.get(candidate, {})
            if spec.get("hardware"):
                if _encoder_works(candidate):
                    return candidate
            elif candidate in available_encoders():
                return candidate
        return "libx264"

    # Явно выбранный аппаратный кодировщик, которого нет — мягко откатываемся
    spec = VIDEO_ENCODERS.get(codec)
    if spec and spec["hardware"] and not _encoder_works(codec):
        fallback = "libx265" if spec["family"] == "hevc" else "libx264"
        return fallback

    if codec not in available_encoders() and codec in VIDEO_ENCODERS:
        return "libx264"

    return codec


def _clamp_preset(encoder: str, preset: str | None) -> str | None:
    """Пресет из настроек может не подходить кодировщику — подбираем ближайший."""
    spec = VIDEO_ENCODERS.get(encoder)
    if not spec or not spec["presets"]:
        return None
    presets = spec["presets"]
    if preset in presets:
        return preset
    # Универсальный маппинг «быстро / нормально / качественно»
    bucket = {
        "ultrafast": 0, "superfast": 0, "veryfast": 0, "faster": 0, "fast": 0, "p1": 0, "speed": 0,
        "medium": 1, "balanced": 1, "p4": 1,
        "slow": 2, "slower": 2, "veryslow": 2, "p7": 2, "quality": 2,
    }.get((preset or "medium").lower(), 1)
    # 0 = самый быстрый пресет, 1 = середина шкалы, 2 = самый качественный
    return presets[{0: 0, 1: len(presets) // 2, 2: len(presets) - 1}[bucket]]


def build_video_command(
    input_path: str,
    output_path: str,
    container: str,
    codec: str = "auto",
    quality: str | int = 23,
    resolution: str | None = "original",
    preset: str | None = "medium",
    audio_bitrate: str = "160k",
) -> tuple[list[str], str]:
    """
    Возвращает (argv, фактический_кодировщик).
    argv уже содержит -progress pipe:1 для машиночитаемого прогресса.
    """
    container = (container or "mp4").lower()

    cmd = [
        "ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-v", "error",
        # Машиночитаемый прогресс в stdout вместо парсинга человеческого stderr
        "-progress", "pipe:1", "-nostats",
        "-i", input_path,
    ]

    # ---- только звук -------------------------------------------------
    if container in AUDIO_ONLY_FORMATS:
        cmd += ["-vn"]
        cmd += _AUDIO_PROFILES.get(container, ["-c:a", "aac", "-b:a", "192k"])
        cmd += [output_path]
        return cmd, "audio"

    # ---- видео -------------------------------------------------------
    encoder = resolve_encoder(codec, container)

    if encoder == "copy":
        cmd += ["-c", "copy"]
    else:
        spec = VIDEO_ENCODERS.get(encoder, VIDEO_ENCODERS["libx264"])

        vf = resolution_filter(resolution if resolution != "original" else None)
        if vf:
            cmd += ["-vf", vf]

        cmd += ["-c:v", encoder]

        chosen_preset = _clamp_preset(encoder, preset)
        if chosen_preset:
            cmd += ["-preset", chosen_preset]

        cmd += [spec["rate_flag"], str(quality)]

        # AMF задаёт качество тремя флагами сразу
        if encoder.endswith("_amf"):
            cmd += ["-qp_p", str(quality), "-qp_b", str(quality)]

        # Совместимость с бытовыми плеерами
        cmd += ["-pix_fmt", "yuv420p"]

        cmd += ["-c:a", "aac", "-b:a", audio_bitrate]

    # Метаданные исходника (название, дата) не теряем
    cmd += ["-map_metadata", "0"]

    if container in ("mp4", "mov", "m4a"):
        # Индекс в начало файла: воспроизведение стартует без полной загрузки
        cmd += ["-movflags", "+faststart"]

    cmd += [output_path]
    return cmd, encoder
