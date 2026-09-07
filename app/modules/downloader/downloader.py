# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Загрузчик: анализ ссылок и параллельное скачивание через yt-dlp.

Исправленное против прежней версии:

* СЕМАФОР НЕ ОСВОБОЖДАЛСЯ. `_download_worker` уменьшал счётчик активных
  задач, но `self.semaphore.release()` не вызывал никогда. После трёх
  скачиваний свободных слотов не оставалось, и менеджер бесконечно крутился
  в цикле, не запуская ничего нового.
* `extractor_args` ЗАТИРАЛСЯ. Сначала ставили
  {'youtube': {'player_client': ['ios']}}, а следом, если найден QuickJS,
  присваивали {'ytdl_js': ['js']} — целиком, вместе с ключом youtube.
  Так как QuickJS есть всегда, настройка player_client не применялась.
  Сам пин на iOS теперь снят: из-за SABR-only этот клиент отдаёт только
  раскадровку, и любая загрузка падала с "Requested format is not available".
* ИМЯ ФАЙЛА НЕ ЭКРАНИРОВАЛОСЬ. Заголовок подставлялся в outtmpl как есть,
  поэтому ролик с «/» или «:» в названии создавал подпапки или ломал путь.
  Теперь имя чистится, а расширение по-прежнему отдаётся yt-dlp.
* ПРОГРЕСС БЫЛ ОБЩИЙ. `self.last_video_progress` — одно поле на все три
  параллельные загрузки, поэтому проценты одной задачи протекали в другую.
  Теперь состояние на задачу.
* Прогресс троттлится: yt-dlp дёргает хук на каждый сетевой блок.
* Очередь защищена локом — её меняли одновременно UI и рабочие потоки.
* Потоки скачивания стали daemon: раньше приложение не закрывалось, пока
  не завершится активная загрузка.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import threading
import time
import uuid

from app.core.ui_channel import UIChannel
from app.utils.const import COOKIES_FILE
from app.utils.notifications.notifications import add_notification
from app.utils.queue.queue import save_queue_to_file
from app.utils.utils import resource_path

#: Минимальный интервал между отправками прогресса в интерфейс
PROGRESS_INTERVAL_SEC = 0.2

#: Символы, запрещённые в именах файлов Windows
_UNSAFE_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

CODEC_FILTERS = {
    "av1": "[vcodec^=av01]",
    "h265": "[vcodec^=hev1]",
    "h264": "[vcodec^=avc1]",
}

AUDIO_ONLY_FORMATS = {"mp3", "m4a", "opus", "aac", "flac", "wav"}


def sanitize_filename(name: str, max_length: int = 150) -> str:
    """Заголовок ролика -> безопасное имя файла."""
    cleaned = _UNSAFE_FILENAME.sub("_", name or "video").strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(" .")
    return cleaned or "video"


class YtLogger:
    """Фильтр шума yt-dlp: дебаг отбрасываем, полезное отдаём в журнал."""

    def __init__(self, downloader):
        self.dl = downloader

    def debug(self, msg):
        if msg.startswith("[debug] "):
            return
        if "[Merger]" in msg or "[ExtractAudio]" in msg:
            self.dl.log(msg, "info")

    def warning(self, msg):
        self.dl.log(msg.replace("WARNING:", "").strip(), "warn")

    def error(self, msg):
        self.dl.log(msg.replace("ERROR:", "").strip(), "error", "YTDLP_ERR")


class _TaskProgress:
    """Троттлинг и состояние прогресса ОДНОЙ задачи."""

    def __init__(self, emit, task_id: str):
        self._emit = emit
        self._task_id = task_id
        self._last_percent = -1.0
        self._last_time = 0.0
        #: последний процент собственно видео — нужен, пока качаются субтитры
        self.video_percent = 0.0

    def update(self, percent: float, speed: str = "", eta: str = "",
               force: bool = False) -> None:
        percent = max(0.0, min(100.0, float(percent)))
        now = time.monotonic()
        if not force and now - self._last_time < PROGRESS_INTERVAL_SEC \
                and abs(percent - self._last_percent) < 1.0:
            return
        self._last_percent = percent
        self._last_time = now
        self._emit(self._task_id, percent, speed, eta)


class Downloader:
    def __init__(self, context):
        self.ctx = context
        self.stop_requested = False
        self.is_running = False
        self.max_concurrent = 3
        self.semaphore = threading.Semaphore(self.max_concurrent)

        self._active_lock = threading.Lock()
        self.active_tasks = 0

        #: Очередь живёт в контексте, но менять её можно только под этим локом
        self._queue_lock = threading.RLock()

        #: Флаги остановки конкретных задач
        self.interrupt_flags: dict[str, bool] = {}

        self.qjs_path = resource_path(os.path.join("data", "bin", "qjs.exe"))
        if not os.path.exists(self.qjs_path):
            print(f"[WARN] QuickJS не найден: {self.qjs_path}")
            self.qjs_path = None

    # ------------------------------------------------------------------
    # Канал в интерфейс
    # ------------------------------------------------------------------
    @property
    def ui(self) -> UIChannel:
        return getattr(self.ctx, "ui", None) or UIChannel()

    def log(self, message, level="info", code=""):
        self.ui.log(str(message), level, code, "downloader")

    def get_trans(self, category, key=None, default=""):
        value = self.ctx.translations.get(category)
        if isinstance(value, str):
            return value
        if isinstance(value, dict) and key:
            return value.get(key, default or key)
        return default or key or category

    def open_dl_folder(self):
        path = self.ctx.download_folder
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log(f"Не удалось открыть папку: {e}", "error", "OPEN_FOLDER_ERR")

    # ------------------------------------------------------------------
    # Форматирование
    # ------------------------------------------------------------------
    @staticmethod
    def _format_size(bytes_val):
        if not bytes_val:
            return "~"
        value = float(bytes_val)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024:
                return f"{value:.1f} {unit}"
            value /= 1024
        return "~"

    @staticmethod
    def _format_duration(seconds):
        if not seconds:
            return "--:--"
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    # ------------------------------------------------------------------
    # Общие опции yt-dlp
    # ------------------------------------------------------------------
    def _base_opts(self) -> dict:
        """
        Базовые опции. extractor_args собирается ОДНИМ словарём: раньше
        второе присваивание стирало настройку player_client целиком.

        player_client НЕ фиксируем. Пин на "ios" ломал скачивание: YouTube
        включил SABR-only, и iOS-клиент перестал отдавать https-ссылки —
        yt-dlp видел только раскадровку и падал с "Requested format is not
        available". Набор клиентов по умолчанию обновляется вместе с yt-dlp,
        поэтому выбор оставлен ему.
        """
        extractor_args: dict[str, object] = {}

        opts: dict = {
            "proxy": self.ctx.proxy_url if self.ctx.proxy_enabled == "True" else "",
            "nocheckcertificate": True,
            "cookies": COOKIES_FILE,
            "quiet": True,
            "logger": YtLogger(self),
            "extractor_args": extractor_args,
        }

        # Движок JS нужен для расшифровки ссылок YouTube. Ключи "ytdl_js" и
        # "javascript_executable" из старых версий yt-dlp больше не читаются:
        # теперь рантаймы задаются через js_runtimes. Из четырёх поддерживаемых
        # (deno, node, quickjs, bun) в комплекте лежит только QuickJS, и его
        # надо перечислить явно — по умолчанию включён один deno.
        if self.qjs_path:
            opts["js_runtimes"] = {"quickjs": {"path": self.qjs_path}}

        return opts

    # ------------------------------------------------------------------
    # Добавление в очередь
    # ------------------------------------------------------------------
    def addVideoToQueue(self, video_url, selected_format, selectedResolution, temp_id=None):
        task_id = str(uuid.uuid4())
        self.log(f"{self.get_trans('status', 'status_text', 'Анализ')} ({video_url})", "info")

        threading.Thread(
            target=self._analyze,
            args=(task_id, video_url, selected_format, selectedResolution, temp_id),
            daemon=True,
        ).start()

    def _analyze(self, task_id, video_url, selected_format, selected_resolution, temp_id):
        import yt_dlp

        try:
            # 1. Быстрая проверка: плейлист или одиночный ролик
            opts = self._base_opts()
            opts["extract_flat"] = "in_playlist"

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

            if "entries" in info:
                self._emit_playlist(info, temp_id)
                return

            # 2. Полный разбор одиночного ролика
            opts = self._base_opts()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

            item = self._build_item(task_id, video_url, info,
                                    selected_format, selected_resolution, temp_id)

            with self._queue_lock:
                self.ctx.download_queue.append(item)
                save_queue_to_file(self.ctx.download_queue)

            self.ui.downloader_item_added(item)
            self.log(f"{self.get_trans('status', 'to_queue', 'Добавлено')}: {item['title']}",
                     "success")

        except Exception as e:
            self.log(f"{self.get_trans('status', 'error_adding', 'Ошибка добавления')}: {e}",
                     "error", "DL_GENERIC_ERR")
            if temp_id:
                self.ui.downloader_placeholder_removed(temp_id)

    def _emit_playlist(self, info: dict, temp_id: str | None) -> None:
        self.log(f"Найден плейлист: {info.get('title')}", "info")
        playlist = {
            "title": info.get("title", "Playlist"),
            "items": [
                {
                    "url": entry.get("url") or entry.get("webpage_url"),
                    "title": entry.get("title", "Без названия"),
                    "duration": self._format_duration(entry.get("duration")),
                }
                for entry in info.get("entries", []) if entry
            ],
        }
        if temp_id:
            self.ui.downloader_placeholder_removed(temp_id)
        self.ui.downloader_playlist_found(playlist)

    def _build_item(self, task_id, video_url, info,
                    selected_format, selected_resolution, temp_id) -> dict:
        title = info.get("title", "Без названия")

        thumbnail = info.get("thumbnail", "")
        if (info.get("extractor", "").lower() == "youtube") and info.get("id"):
            thumbnail = f"https://i.ytimg.com/vi/{info['id']}/maxresdefault.jpg"
        if not thumbnail:
            candidates = [t for t in info.get("thumbnails", []) if t.get("url")]
            if candidates:
                candidates.sort(key=lambda t: t.get("width") or 0)
                thumbnail = candidates[-1]["url"]

        # Какие видеокодеки вообще предлагает источник
        available_codecs = []
        for fmt in info.get("formats", []):
            vcodec = (fmt.get("vcodec") or "").lower()
            if vcodec.startswith("av01") and "av1" not in available_codecs:
                available_codecs.append("av1")
            elif vcodec.startswith(("hev1", "hvc1")) and "h265" not in available_codecs:
                available_codecs.append("h265")
            elif vcodec.startswith("avc1") and "h264" not in available_codecs:
                available_codecs.append("h264")

        tbr = info.get("tbr") or 0
        return {
            "id": task_id,
            "url": video_url,
            "title": title,
            "format": selected_format,
            "resolution": selected_resolution,
            "codec": "auto",
            "available_codecs": available_codecs,
            "thumbnail": thumbnail,
            "status": "queued",
            "temp_id": temp_id,
            "meta": {
                "duration": self._format_duration(info.get("duration")),
                "size": self._format_size(info.get("filesize_approx") or info.get("filesize")),
                "uploader": info.get("uploader", "Неизвестно"),
                "fps": info.get("fps", 0),
                "vcodec": info.get("vcodec", "N/A"),
                "acodec": info.get("acodec", "N/A"),
                "bitrate": f"{int(tbr)} kbps" if tbr else "N/A",
            },
        }

    # ------------------------------------------------------------------
    # Управление очередью
    # ------------------------------------------------------------------
    def update_item_settings(self, task_id, new_fmt, new_res, new_codec="auto"):
        with self._queue_lock:
            for item in self.ctx.download_queue:
                if item["id"] != task_id:
                    continue
                item["format"] = new_fmt
                item["resolution"] = new_res
                item["codec"] = new_codec
                if item["status"] == "error":
                    item["status"] = "queued"
                    self.ui.downloader_progress(task_id, 0, "", "")
                save_queue_to_file(self.ctx.download_queue)
                return
        print(f"Задача {task_id} для обновления не найдена")

    def removeVideoFromQueue(self, task_id):
        self.interrupt_flags[task_id] = True
        with self._queue_lock:
            title = next(
                (v.get("title", "Видео") for v in self.ctx.download_queue
                 if v.get("id") == task_id),
                "Видео",
            )
            self.ctx.download_queue = [
                v for v in self.ctx.download_queue if v.get("id") != task_id
            ]
            save_queue_to_file(self.ctx.download_queue)
        self.ui.downloader_item_removed(task_id)
        self.log(f"{self.get_trans('status', 'removed_from_queue', 'Удалено')}: {title}",
                 "success")

    def stop_single_task(self, task_id):
        self.interrupt_flags[task_id] = True
        self.log("Остановка задачи", "info")

    def start_single_task(self, task_id):
        with self._queue_lock:
            for item in self.ctx.download_queue:
                if item.get("id") == task_id and item.get("status") in (
                    "error", "paused", "stopped"
                ):
                    item["status"] = "queued"
                    self.ui.downloader_progress(task_id, 0, "", "")
                    break
        if not self.is_running:
            self.startDownload()

    # ------------------------------------------------------------------
    # Запуск и остановка
    # ------------------------------------------------------------------
    def startDownload(self):
        if self.is_running:
            self.log("Менеджер загрузок уже запущен", "warn")
            return

        with self._queue_lock:
            if not self.ctx.download_queue:
                self.log(self.get_trans("status", "the_queue_is_empty", "Очередь пуста"), "warn")
                return

            # Возобновляем задачи, зависшие в статусе downloading после падения
            resumed = 0
            for task in self.ctx.download_queue:
                if task.get("status") == "downloading":
                    task["status"] = "queued"
                    resumed += 1
                    self.ui.downloader_progress(task["id"], 0, "", "")

        if resumed:
            self.log(f"{self.get_trans('status', 'resuming', 'Возобновление')} ({resumed})", "info")

        self.stop_requested = False
        self.is_running = True
        threading.Thread(target=self._download_manager, daemon=True).start()

    def stopDownload(self):
        self.stop_requested = True
        self.log(self.get_trans("status", "stopping", "Остановка..."), "info")

    def _download_manager(self):
        self.log(self.get_trans("status", "manager_started", "Менеджер запущен"), "info")

        while self.is_running and not self.stop_requested:
            with self._queue_lock:
                queued = [v for v in self.ctx.download_queue if v.get("status") == "queued"]

            with self._active_lock:
                active = self.active_tasks

            if not queued and active == 0:
                self.log(self.get_trans("status", "queue_finished", "Очередь завершена"),
                         "success")
                break

            if not queued:
                time.sleep(0.5)
                continue

            started_any = False
            for task in queued:
                if self.stop_requested:
                    break
                if not self.semaphore.acquire(blocking=False):
                    break
                with self._queue_lock:
                    task["status"] = "downloading"
                with self._active_lock:
                    self.active_tasks += 1
                started_any = True
                threading.Thread(
                    target=self._download_worker, args=(task,), daemon=True
                ).start()

            if not started_any:
                time.sleep(0.5)

        self.is_running = False
        self.ui.downloader_finished()
        if self.stop_requested:
            self.log("Менеджер загрузок остановлен", "info")

    # ------------------------------------------------------------------
    # Рабочий поток одной загрузки
    # ------------------------------------------------------------------
    def _download_worker(self, task):
        import yt_dlp

        task_id = task["id"]
        title = task["title"]
        self.interrupt_flags.pop(task_id, None)

        progress = _TaskProgress(self.ui.downloader_progress, task_id)

        try:
            self.log(f"{self.get_trans('status', 'downloading', 'Скачивание')}: {title}", "info")
            ydl_opts = self._build_download_opts(task, progress)
            final_container = ydl_opts.pop("_final_container", task["format"])

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([task["url"]])

            self._finish_task(task, final_container)

        except yt_dlp.utils.DownloadCancelled:
            paused = self.get_trans("status", "paused", "Пауза")
            self.log(f"{paused}: {title}", "info")
            with self._queue_lock:
                task["status"] = "paused"
            self.ui.downloader_progress(task_id, 0, paused, "")
            self.interrupt_flags.pop(task_id, None)

        except Exception as e:
            error = self.get_trans("status", "error", "Ошибка")
            self.log(f"{error} [{title}]: {e}", "error", "DL_GENERIC_ERR")
            with self._queue_lock:
                task["status"] = "error"
            self.ui.downloader_progress(task_id, 0, error, "")

        finally:
            with self._active_lock:
                self.active_tasks -= 1
            # Без этого release слоты кончались после max_concurrent задач
            # и менеджер больше ничего не запускал.
            self.semaphore.release()

    def _build_download_opts(self, task, progress: _TaskProgress) -> dict:
        import yt_dlp

        task_id = task["id"]
        subs_label = self.get_trans("status", "subtitles", "Субтитры...")
        processing_label = self.get_trans("status", "processing", "Обработка...")
        mbs = self.get_trans("mbs", None, "МБ/с")
        sec = self.get_trans("sec", None, "с")
        minute = self.get_trans("min", None, "м")

        def progress_hook(d):
            if self.stop_requested or self.interrupt_flags.get(task_id):
                raise yt_dlp.utils.DownloadCancelled("Остановлено пользователем")

            filename = (d.get("filename") or "").lower()
            is_subtitle = filename.endswith((".vtt", ".srt", ".ttml", ".srv3", ".ass"))

            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0.0

                if is_subtitle:
                    # Проценты держим от видео: у дорожки субтитров свой
                    # крошечный размер, и полоса прыгала на 100%
                    progress.update(progress.video_percent, subs_label, "")
                    return

                progress.video_percent = percent
                speed = d.get("speed") or 0
                speed_text = f"{speed / 1048576:.1f} {mbs}" if speed else ""

                eta = d.get("eta") or 0
                if eta > 60:
                    eta_text = f"{eta // 60}{minute} {eta % 60}{sec}"
                elif eta:
                    eta_text = f"{eta}{sec}"
                else:
                    eta_text = ""

                progress.update(percent, speed_text, eta_text)

            elif d["status"] == "finished":
                # 100% ставим только после постобработки (склейка, субтитры)
                progress.update(99, processing_label, "", force=True)

        # Имя файла чистим: заголовок мог содержать / : ? и ломать путь
        safe_title = sanitize_filename(task["title"])
        out_template = os.path.join(self.ctx.download_folder, f"{safe_title}.%(ext)s")

        opts = self._base_opts()
        opts.update({
            "outtmpl": out_template,
            "progress_hooks": [progress_hook],
            "sleep_interval": 1,
            "sleep_subtitles": 1,
        })

        container = task["format"]
        final_container = container

        resolution = task["resolution"]
        codec_filter = CODEC_FILTERS.get(task.get("codec", "auto"), "")
        video_sel = f"bestvideo{codec_filter}[height<={resolution}]"

        audio_pref = self.ctx.config.get("Audio", "lang", fallback="none")

        if audio_pref == "all_tracks":
            self.log(f"Режим всех аудиодорожек: {task['title']}", "info")
            opts["audio_multistreams"] = True
            # MP4 плохо склеивает несколько дорожек — принудительно MKV
            final_container = "mkv"
            fmt_str = f"{video_sel}+mergeall[vcodec=none]"
        elif audio_pref not in ("none", "orig"):
            fmt_str = (f"{video_sel}+bestaudio[language^={audio_pref}] / "
                       f"{video_sel}+bestaudio")
        else:
            fmt_str = f"{video_sel}+bestaudio / best[height<={resolution}]"

        # --- субтитры ---
        if self.ctx.config.get("Subtitles", "enabled", fallback="False") == "True":
            langs = self.ctx.config.get("Subtitles", "langs", fallback="all")
            opts["writesubtitles"] = True
            opts["writeautomaticsub"] = (
                self.ctx.config.get("Subtitles", "auto", fallback="False") == "True"
            )
            opts["subtitleslangs"] = ["all"] if langs == "all" else [langs]
            if self.ctx.config.get("Subtitles", "embed", fallback="True") == "True":
                opts.setdefault("postprocessors", []).append(
                    {"key": "FFmpegEmbedSubtitle"}
                )

        # --- контейнер ---
        if container in AUDIO_ONLY_FORMATS:
            opts["format"] = "bestaudio/best"
            opts.setdefault("postprocessors", []).append(
                {"key": "FFmpegExtractAudio", "preferredcodec": container}
            )
            final_container = container
        else:
            opts["format"] = fmt_str
            opts["merge_output_format"] = final_container

        opts["_final_container"] = final_container
        return opts

    def _finish_task(self, task, final_container: str) -> None:
        task_id = task["id"]
        title = task["title"]
        done = self.get_trans("status", "download_success", "Готово")

        self.log(f"{done}: {title}", "success")
        self.ui.downloader_progress(task_id, 100, done, "")

        with self._queue_lock:
            self.ctx.download_queue = [
                v for v in self.ctx.download_queue if v["id"] != task_id
            ]
            save_queue_to_file(self.ctx.download_queue)

        self.ui.downloader_item_removed(task_id)

        if self.ctx.config.get("Folders", "dl", fallback="True") == "True":
            self.open_dl_folder()

        if self.ctx.config.get("Notifications", "downloads", fallback="True") == "True":
            updated = add_notification(
                done, title, "downloader",
                payload={
                    "url": task["url"],
                    "thumbnail": task.get("thumbnail", ""),
                    "format": final_container,
                    "resolution": task["resolution"],
                    "title": title,
                    "folder": self.ctx.download_folder,
                },
            )
            self.ui.notifications_reloaded(updated)
