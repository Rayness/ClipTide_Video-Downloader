# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Редактор: покадровое превью и обрезка видео по сегментам.

Изменения против прежней версии:

* Убран встроенный HTTP-сервер на bottle. Он существовал только чтобы
  скармливать файл HTML-тегу <video> с поддержкой Range-запросов. Нативному
  интерфейсу это не нужно — вместе с ним уходит зависимость bottle и импорт
  webview.http.
* Все вызовы ffmpeg идут через app.utils.media: абсолютный путь и
  CREATE_NO_WINDOW. Раньше при каждой перемотке таймлайна мигала консоль.
* Прогресс читается из `-progress pipe:1`, а не регуляркой по stderr,
  и троттлится (было — обновление интерфейса на каждую строку вывода).
* В списке для concat апостроф в пути экранируется, а не вырезается.
* Общение с интерфейсом — через UIChannel, без сборки строк JavaScript.
"""

from __future__ import annotations

import base64
import os
import platform
import subprocess
import tempfile
import threading
import time

from app.core.ui_channel import UIChannel
from app.utils import media
from app.utils.converter_utils import probe, thumbnail_data_uri

#: Минимальный интервал между обновлениями прогресса в интерфейсе
PROGRESS_INTERVAL_SEC = 0.25

#: Ширина кадра предпросмотра
PREVIEW_WIDTH = 480

FILE_FILTERS = [
    ("Видеофайлы", "mp4;mkv;avi;mov;webm;m4v;flv;wmv"),
    ("Все файлы", "*"),
]

CODEC_MAP = {"h264": "libx264", "h265": "libx265"}


class Editor:
    def __init__(self, context):
        self.ctx = context
        self.is_running = False
        self.stop_requested = False
        self.current_process: subprocess.Popen | None = None
        self._frame_lock = threading.Lock()

    # ------------------------------------------------------------------
    @property
    def ui(self) -> UIChannel:
        return getattr(self.ctx, "ui", None) or UIChannel()

    def log(self, message, level="info"):
        self.ui.log(str(message), level, "", "editor")

    def open_folder(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log(f"Не удалось открыть папку: {e}", "error")

    # ------------------------------------------------------------------
    # Открытие файла
    # ------------------------------------------------------------------
    def open_file(self):
        paths = self.ui.pick_files("Выберите видео", FILE_FILTERS, multiple=False)
        if paths:
            self.load_file(paths[0])

    def load_file(self, file_path: str) -> None:
        threading.Thread(target=self._load_file, args=(file_path,), daemon=True).start()

    def _load_file(self, file_path: str) -> None:
        try:
            info, error = probe(file_path)
            if info is None:
                self.log(f"Не удалось прочитать файл: {error}", "error")
                return
            if not info.has_video:
                self.log("В файле нет видеопотока", "error")
                return

            thumb, _ = thumbnail_data_uri(file_path, info)

            self.ui.editor_file_loaded({
                "path": file_path,
                "filename": os.path.basename(file_path),
                "duration": round(info.duration, 3),
                "width": info.width,
                "height": info.height,
                "codec": info.codec,
                "fps": round(info.fps, 3),
                "audio": info.audio_codec,
                "thumb": thumb or "",
            })
        except Exception as e:
            self.log(f"Ошибка открытия файла: {e}", "error")

    # ------------------------------------------------------------------
    # Кадр по времени
    # ------------------------------------------------------------------
    def get_frame(self, file_path: str, timestamp_sec) -> str | None:
        """
        Кадр в момент timestamp_sec как data:URI.
        Если предыдущий запрос ещё выполняется — пропускаем: при быстрой
        перемотке таймлайна иначе копится очередь процессов ffmpeg.
        """
        if not self._frame_lock.acquire(blocking=False):
            return None
        try:
            cmd = [
                "ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-y",
                "-ss", str(timestamp_sec),
                "-i", file_path,
                "-frames:v", "1",
                "-vf", f"scale={PREVIEW_WIDTH}:-2",
                "-f", "image2pipe", "-vcodec", "mjpeg",
                "pipe:1",
            ]
            # media.run подставляет абсолютный путь к ffmpeg и CREATE_NO_WINDOW:
            # без этого на каждой перемотке моргала чёрная консоль.
            result = media.run(cmd, capture_output=True, timeout=10)
            if result.returncode == 0 and result.stdout:
                encoded = base64.b64encode(result.stdout).decode("ascii")
                return f"data:image/jpeg;base64,{encoded}"
        except Exception as e:
            print(f"[EDITOR] get_frame: {e}")
        finally:
            self._frame_lock.release()
        return None

    # ------------------------------------------------------------------
    # Обрезка
    # ------------------------------------------------------------------
    def trim_video(self, file_path, segments, mode, output_dir):
        """
        segments: [{"start": float, "end": float}, ...]
        mode: "separate" (каждый сегмент отдельным файлом) | "merge" (склеить)
        """
        if self.is_running:
            self.log("Обрезка уже выполняется", "warn")
            return
        if not segments:
            self.log("Не задано ни одного сегмента", "warn")
            return

        self.is_running = True
        self.stop_requested = False
        threading.Thread(
            target=self._trim_worker,
            args=(file_path, list(segments), mode, output_dir),
            daemon=True,
        ).start()

    def stop_trim(self):
        self.stop_requested = True
        process = self.current_process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        self.ui.editor_trim_stopped()

    def _trim_worker(self, file_path, segments, mode, output_dir):
        try:
            self.ui.editor_trim_started()
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            os.makedirs(output_dir, exist_ok=True)

            if mode == "separate":
                self._trim_separate(file_path, segments, output_dir, base_name)
            else:
                self._trim_merge(file_path, segments, output_dir, base_name)

        except Exception as e:
            self.log(f"Ошибка при обрезке: {e}", "error")
            self.ui.editor_trim_error(str(e))
        finally:
            self.is_running = False
            self.current_process = None

    def _trim_separate(self, file_path, segments, output_dir, base_name):
        container = self.ctx.config.get("Editor", "format", fallback="mp4")
        for index, segment in enumerate(segments):
            if self.stop_requested:
                return
            out_file = os.path.join(output_dir, f"{base_name}_clip_{index + 1}.{container}")
            self._encode_segment(file_path, segment["start"], segment["end"],
                                 out_file, index, len(segments))

        if not self.stop_requested:
            self.ui.editor_trim_done("separate", output_dir)
            if self.ctx.config.get("Folders", "editor", fallback="True") == "True":
                self.open_folder(output_dir)

    def _trim_merge(self, file_path, segments, output_dir, base_name):
        temp_dir = tempfile.mkdtemp(prefix="cliptide_trim_")
        temp_files: list[str] = []
        concat_list = None

        try:
            for index, segment in enumerate(segments):
                if self.stop_requested:
                    return
                temp_file = os.path.join(temp_dir, f"seg_{index}.mp4")
                self._encode_segment(file_path, segment["start"], segment["end"],
                                     temp_file, index, len(segments))
                if os.path.exists(temp_file):
                    temp_files.append(temp_file)

            if self.stop_requested or not temp_files:
                return

            concat_list = os.path.join(temp_dir, "concat.txt")
            with open(concat_list, "w", encoding="utf-8") as handle:
                for path in temp_files:
                    # ffmpeg concat: одинарная кавычка экранируется как '\'' —
                    # раньше её просто вырезали, ломая путь с апострофом
                    escaped = path.replace("'", "'\\''")
                    handle.write(f"file '{escaped}'\n")

            container = self.ctx.config.get("Editor", "format", fallback="mp4")
            out_file = os.path.join(output_dir, f"{base_name}_merged.{container}")

            self.ui.editor_trim_progress(90, "Склейка сегментов...")
            self.current_process = media.popen(
                ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-y",
                 "-f", "concat", "-safe", "0", "-i", concat_list,
                 "-c", "copy", out_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            self.current_process.wait()

            if not self.stop_requested:
                self.ui.editor_trim_progress(100, "Готово")
                self.ui.editor_trim_done("merge", output_dir)
                if self.ctx.config.get("Folders", "editor", fallback="True") == "True":
                    self.open_folder(output_dir)

        finally:
            for path in temp_files:
                try:
                    os.remove(path)
                except OSError:
                    pass
            if concat_list:
                try:
                    os.remove(concat_list)
                except OSError:
                    pass
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass

    def _encode_segment(self, file_path, start, end, out_file, index, total):
        """Кадро-точная обрезка одного сегмента с реальным прогрессом ffmpeg."""
        duration = float(end) - float(start)
        if duration <= 0:
            raise ValueError(f"сегмент {index + 1}: конец раньше начала")

        label = f"Сегмент {index + 1} из {total}"
        pct_base = int(index / total * 85)
        pct_end = int((index + 1) / total * 85)

        codec = self.ctx.config.get("Editor", "codec", fallback="h264")
        preset = self.ctx.config.get("Editor", "preset", fallback="fast")
        crf = self.ctx.config.get("Editor", "crf", fallback="18")

        if codec == "copy":
            codec_args = ["-c:v", "copy", "-c:a", "copy"]
        else:
            codec_args = [
                "-c:v", CODEC_MAP.get(codec, codec),
                "-preset", preset, "-crf", crf,
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
            ]

        cmd = [
            "ffmpeg", "-hide_banner", "-nostdin", "-y", "-v", "error",
            # Машиночитаемый прогресс вместо регулярки по человеческому stderr
            "-progress", "pipe:1", "-nostats",
            "-ss", str(start),
            "-i", file_path,
            "-t", str(duration),
            *codec_args,
            out_file,
        ]

        self.ui.editor_trim_progress(pct_base, label)
        self.log(f"{label}: {float(start):.1f}s -> {float(end):.1f}s", "info")

        self.current_process = media.popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        last_percent = -1
        last_emit = 0.0
        for raw in iter(self.current_process.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith(("out_time_us=", "out_time_ms=")):
                continue
            try:
                elapsed = float(line.split("=", 1)[1]) / 1_000_000
            except ValueError:
                continue
            fraction = min(elapsed / duration, 1.0)
            percent = pct_base + int(fraction * (pct_end - pct_base))
            now = time.monotonic()
            if percent != last_percent and now - last_emit >= PROGRESS_INTERVAL_SEC:
                last_percent, last_emit = percent, now
                self.ui.editor_trim_progress(percent, label)

        self.current_process.wait()

        if self.current_process.returncode != 0 and not self.stop_requested:
            stderr = (self.current_process.stderr.read() or b"").decode("utf-8", "replace")
            raise RuntimeError(stderr.strip().splitlines()[-1] if stderr.strip()
                               else f"ffmpeg код {self.current_process.returncode}")

        self.ui.editor_trim_progress(pct_end, f"{label} готов")
