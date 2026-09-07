# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import os
import json
import threading
import subprocess
import base64
import tempfile
import uuid
import socket as _socket_mod
import time

import bottle as _bottle
from webview.http import ThreadedAdapter as _ThreadedAdapter

from app.utils import media
from app.utils.converter_utils import print_video_info, get_thumbnail_base64

# Минимальный интервал между обновлениями прогресса в интерфейсе.
# Раньше evaluate_js вызывался на каждую строку stderr ffmpeg.
_PROGRESS_INTERVAL_SEC = 0.25


class _VideoBottleServer:
    """Bottle-сервер для стриминга видеофайла. Range-запросы через bottle.static_file."""

    def __init__(self):
        self._port = None
        self._thread = None
        self._app = None
        self._video_dir = ''
        self._video_file = ''

    def start(self, video_path: str) -> str:
        self._video_dir  = os.path.dirname(video_path)
        self._video_file = os.path.basename(video_path)

        if self._app is None:
            self._app = _bottle.Bottle()

            @self._app.route('/video')
            def serve():
                resp = _bottle.static_file(self._video_file, root=self._video_dir)
                resp.headers['Access-Control-Allow-Origin'] = '*'
                return resp

            with _socket_mod.socket() as s:
                s.bind(('127.0.0.1', 0))
                self._port = s.getsockname()[1]

            self._thread = threading.Thread(
                target=lambda: _bottle.run(
                    app=self._app,
                    server=_ThreadedAdapter,
                    host='127.0.0.1',
                    port=self._port,
                    quiet=True,
                ),
                daemon=True,
            )
            self._thread.start()

        return f'http://127.0.0.1:{self._port}/video'


class Editor:
    def __init__(self, context):
        self.ctx = context
        self.is_running = False
        self.stop_requested = False
        self.current_process = None
        self._frame_lock = threading.Lock()
        self._video_server = _VideoBottleServer()

    def _js_exec(self, code):
        if self.ctx.window:
            self.ctx.window.evaluate_js(code)

    def log(self, message, level="info"):
        print(f"[EDITOR {level.upper()}] {message}")
        safe_msg = message.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
        self._js_exec(f'addLog("{safe_msg}", "{level}")')

    def open_folder(self, path):
        import platform, subprocess
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log(f"Ошибка открытия папки: {e}", "error")

    def open_file(self):
        import webview
        file_paths = self.ctx.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=("Video Files (*.mp4;*.mkv;*.avi;*.mov;*.webm)", "All Files (*.*)")
        )
        if not file_paths:
            return

        file_path = file_paths[0]

        def _process():
            try:
                result = print_video_info(file_path)
                if isinstance(result, str):
                    self.log(f"Ошибка чтения файла: {result}", "error")
                    return

                duration, bitrate, width, height, codec, fps, audio_codec, audio_bitrate = result

                thumb, _ = get_thumbnail_base64(file_path)

                file_data = {
                    "path": file_path,
                    "filename": os.path.basename(file_path),
                    "duration": duration,
                    "width": width,
                    "height": height,
                    "codec": codec,
                    "fps": fps,
                    "thumb": thumb or ""
                }

                file_data['video_url'] = self._video_server.start(file_path)

                data_json = json.dumps(file_data)
                safe_json = data_json.replace('\\', '\\\\').replace("'", "\\'")
                self._js_exec(f"editorLoadFile(JSON.parse('{safe_json}'))")

            except Exception as e:
                self.log(f"Ошибка открытия файла: {e}", "error")

        threading.Thread(target=_process, daemon=True).start()

    def get_frame(self, file_path, timestamp_sec):
        """Извлечь кадр по времени, вернуть base64 JPEG.
        Если предыдущий вызов ещё не завершён — пропустить."""
        if not self._frame_lock.acquire(blocking=False):
            return None  # предыдущий вызов ещё работает — скипаем
        try:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(timestamp_sec),
                "-i", file_path,
                "-vframes", "1",
                "-vf", "scale=480:-2",
                "-f", "image2",
                "-vcodec", "mjpeg",
                "pipe:1"
            ]
            # media.run подставляет абсолютный путь к ffmpeg и CREATE_NO_WINDOW:
            # без этого на каждой перемотке таймлайна моргала чёрная консоль.
            result = media.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0 and result.stdout:
                img_b64 = base64.b64encode(result.stdout).decode("utf-8")
                return f"data:image/jpeg;base64,{img_b64}"
        except Exception as e:
            print(f"[EDITOR] get_frame error: {e}")
        finally:
            self._frame_lock.release()
        return None

    def trim_video(self, file_path, segments, mode, output_dir):
        """
        Обрезать видео по сегментам с точным ре-энкодингом.
        segments: [{"start": float, "end": float}, ...]
        mode: "separate" | "merge"
        output_dir: путь к папке назначения
        """
        if self.is_running:
            self.log("Обрезка уже выполняется", "warn")
            return

        self.is_running = True
        self.stop_requested = False

        def _run():
            try:
                self._js_exec("editorTrimStart()")
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                os.makedirs(output_dir, exist_ok=True)

                if mode == "separate":
                    for i, seg in enumerate(segments):
                        if self.stop_requested:
                            break
                        fmt = self.ctx.config.get("Editor", "format", fallback="mp4")
                        out_file = os.path.join(output_dir, f"{base_name}_clip_{i+1}.{fmt}")
                        self._encode_segment(file_path, seg["start"], seg["end"], out_file, i, len(segments))

                    if not self.stop_requested:
                        safe_dir = output_dir.replace('\\', '\\\\')
                        self._js_exec(f'editorTrimDone("separate", "{safe_dir}")')
                        if self.ctx.config.get("Folders", "editor", fallback="True") == "True":
                            self.open_folder(output_dir)

                elif mode == "merge":
                    temp_dir   = tempfile.mkdtemp()
                    temp_files = []
                    concat_list = None

                    for i, seg in enumerate(segments):
                        if self.stop_requested:
                            break
                        temp_file = os.path.join(temp_dir, f"seg_{i}.mp4")
                        self._encode_segment(file_path, seg["start"], seg["end"], temp_file, i, len(segments))
                        if os.path.exists(temp_file):
                            temp_files.append(temp_file)

                    if not self.stop_requested and temp_files:
                        concat_list = os.path.join(temp_dir, "concat.txt")
                        with open(concat_list, "w", encoding="utf-8") as f:
                            for tf in temp_files:
                                f.write(f"file '{tf.replace(chr(39), '')}'\n")

                        merge_fmt = self.ctx.config.get("Editor", "format", fallback="mp4")
                        out_file = os.path.join(output_dir, f"{base_name}_merged.{merge_fmt}")
                        concat_cmd = [
                            "ffmpeg", "-y",
                            "-f", "concat", "-safe", "0",
                            "-i", concat_list,
                            "-c", "copy",
                            out_file
                        ]
                        self._js_exec('editorTrimProgress(90, "Склейка сегментов...")')
                        self.current_process = media.popen(
                            concat_cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        self.current_process.wait()

                    # Очистка временных файлов
                    for tf in temp_files:
                        try: os.remove(tf)
                        except Exception: pass
                    if concat_list:
                        try: os.remove(concat_list)
                        except Exception: pass
                    try: os.rmdir(temp_dir)
                    except Exception: pass

                    if not self.stop_requested:
                        safe_dir = output_dir.replace('\\', '\\\\')
                        self._js_exec(f'editorTrimDone("merge", "{safe_dir}")')
                        if self.ctx.config.get("Folders", "editor", fallback="True") == "True":
                            self.open_folder(output_dir)

            except Exception as e:
                self.log(f"Ошибка при обрезке: {e}", "error")
                self._js_exec("editorTrimError()")
            finally:
                self.is_running = False

        threading.Thread(target=_run, daemon=True).start()

    def _encode_segment(self, file_path, start, end, out_file, idx, total):
        """Кадро-точная обрезка одного сегмента с реальным прогрессом из FFmpeg."""
        duration = end - start
        label = f"Сегмент {idx + 1} из {total}"
        pct_base = int(idx / total * 85)
        pct_end  = int((idx + 1) / total * 85)

        codec  = self.ctx.config.get("Editor", "codec",  fallback="h264")
        preset = self.ctx.config.get("Editor", "preset", fallback="fast")
        crf    = self.ctx.config.get("Editor", "crf",    fallback="18")
        fmt    = self.ctx.config.get("Editor", "format", fallback="mp4")

        codec_map = {"h264": "libx264", "h265": "libx265"}
        vcodec = codec_map.get(codec, codec)

        # Подбираем расширение из настроек (только для separate-режима)
        ext = os.path.splitext(out_file)[1]
        if ext.lower() not in (".mp4", ".mkv"):
            out_file = os.path.splitext(out_file)[0] + "." + fmt

        if codec == "copy":
            video_args = ["-c:v", "copy", "-c:a", "copy"]
        else:
            video_args = ["-c:v", vcodec, "-preset", preset, "-crf", crf, "-c:a", "aac", "-b:a", "192k"]

        cmd = [
            "ffmpeg", "-hide_banner", "-nostdin", "-y",
            "-v", "error",
            # Машиночитаемый прогресс вместо регулярки по человеческому stderr
            "-progress", "pipe:1", "-nostats",
            "-ss", str(start),
            "-i", file_path,
            "-t", str(duration),
            *video_args,
            out_file
        ]

        self._js_exec(f'editorTrimProgress({pct_base}, "{label}")')
        self.log(f"{label}: {start:.1f}s → {end:.1f}s", "info")

        self.current_process = media.popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Разбираем поток -progress: пары ключ=значение, время в микросекундах
        last_pct = -1
        last_emit = 0.0
        for raw in iter(self.current_process.stdout.readline, b''):
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("out_time_us=") and not line.startswith("out_time_ms="):
                continue
            if duration <= 0:
                continue
            try:
                elapsed = float(line.split("=", 1)[1]) / 1_000_000
            except ValueError:
                continue
            frac = min(elapsed / duration, 1.0)
            pct = pct_base + int(frac * (pct_end - pct_base))
            now = time.monotonic()
            if pct != last_pct and now - last_emit >= _PROGRESS_INTERVAL_SEC:
                last_pct, last_emit = pct, now
                self._js_exec(f'editorTrimProgress({pct}, "{label}")')

        self.current_process.wait()

        if self.current_process.returncode != 0:
            err = (self.current_process.stderr.read() or b'').decode("utf-8", "replace")[-300:]
            self.log(f"FFmpeg ошибка (сег. {idx+1}): {err}", "error")

        self._js_exec(f'editorTrimProgress({pct_end}, "{label} готов")')

    def stop_trim(self):
        self.stop_requested = True
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception:
                pass
        self._js_exec("editorTrimStopped()")
