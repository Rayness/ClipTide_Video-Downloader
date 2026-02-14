# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import json
import os
import threading
import time
import uuid
import subprocess
import platform

from app.utils.const import COOKIES_FILE
from app.utils.queue.queue import save_queue_to_file
from app.utils.notifications.notifications import add_notification
from app.utils.utils import resource_path

# Класс для фильтрации шума в консоли
class YtLogger:
    def __init__(self, downloader_instance):
        self.dl = downloader_instance

    def debug(self, msg):
        # Игнорируем технические дебаги yt-dlp, их слишком много
        if msg.startswith('[debug] '):
            return 
        # Но полезные сообщения (например, про ffmpeg merge) можно оставить как info
        if "[Merger]" in msg or "[ExtractAudio]" in msg:
            self.dl.log(msg, "info")

    def warning(self, msg):
        # Отправляем как WARN (Желтый)
        # Убираем префикс WARNING: если он есть
        clean_msg = msg.replace('WARNING:', '').strip()
        self.dl.log(clean_msg, "warn")

    def error(self, msg):
        # Отправляем как ERROR (Красный)
        clean_msg = msg.replace('ERROR:', '').strip()
        self.dl.log(clean_msg, "error", "YTDLP_ERR")

class Downloader:
    def __init__(self, context):
        self.ctx = context
        self.stop_requested = False
        self.is_running = False 
        self.active_tasks = 0   
        self.max_concurrent = 3
        self.semaphore = threading.Semaphore(self.max_concurrent)

        # Флаги для остановки конкретных задач
        self.interrupt_flags = {}

        # Путь к QuickJS
        self.qjs_path = resource_path(os.path.join("data", "bin", "qjs.exe"))
        
        if not os.path.exists(self.qjs_path):
            print(f"[WARN] QuickJS not found at: {self.qjs_path}")
            self.qjs_path = None
        else:
            print(f"[INFO] QuickJS found: {self.qjs_path}")

    def _js_exec(self, code):
        if self.ctx.window:
            self.ctx.window.evaluate_js(code)

    def get_trans(self, category, key=None, default=""):
        value = self.ctx.translations.get(category)
        if isinstance(value, str): return value
        if isinstance(value, dict) and key: return value.get(key, default or key)
        return default or key or category

    def log(self, message, level="info", code=""):
        """
        level: info, success, warn, error
        code: код ошибки для документации (опционально)
        """
        # Пишем в консоль разработчика для отладки
        prefix = f"[{level.upper()}]"
        print(f"{prefix} {message}")
        
        # Экранируем для JS
        safe_msg = message.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
        
        # Отправляем в UI
        # Обрати внимание: если code None, передаем пустую строку
        code_str = code if code else ""
        self._js_exec(f'addLog("{safe_msg}", "{level}", "{code_str}")')

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
            self.log(f"Error opening folder: {e}", "error", "OPEN_FOLDER_ERR")

    # Вспомогательные методы форматирования
    def _format_size(self, bytes_val):
        if not bytes_val: return "~"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return "~"

    def _format_duration(self, seconds):
        if not seconds: return "--:--"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{int(h)}:{int(m):02d}:{int(s):02d}"
        return f"{int(m)}:{int(s):02d}"

    def addVideoToQueue(self, video_url, selected_format, selectedResolution, temp_id=None):
        task_id = str(uuid.uuid4())
        
        status_pending = self.get_trans('status', 'status_text', 'Pending...')
        self.log(f"{status_pending} ({video_url})", "info")
        
        def _analyze():
            # Ленивый импорт для скорости
            import yt_dlp 

            try:
                # 1. Сначала проверяем, плейлист это или нет (быстро)
                opt = {
                    'proxy': self.ctx.proxy_url if self.ctx.proxy_enabled == "True" else '',
                    'nocheckcertificate': True,
                    'cookies': COOKIES_FILE,
                    'quiet': True,
                    'extract_flat': 'in_playlist', # Не качаем данные каждого видео
                    'logger': YtLogger(self),
                    'extractor_args': {'youtube': {'player_client': ['ios']}} 
                }
                
                if self.qjs_path:
                    opt['extractor_args'] = {"ytdl_js": ["js"]}
                    opt['javascript_executable'] = self.qjs_path

                with yt_dlp.YoutubeDL(opt) as ydl:
                    info = ydl.extract_info(video_url, download=False)

                # === ЭТО ПЛЕЙЛИСТ ===
                if 'entries' in info:
                    self.log(f"Найден плейлист: {info.get('title')}", "info")
                    
                    playlist_data = {
                        "title": info.get('title', 'Playlist'),
                        "items": []
                    }
                    
                    for entry in info['entries']:
                        if entry:
                            playlist_data["items"].append({
                                "url": entry.get('url') or entry.get('webpage_url'),
                                "title": entry.get('title', 'Unknown'),
                                "duration": self._format_duration(entry.get('duration'))
                            })
                    
                    if temp_id: self._js_exec(f'removeLoadingItem("{temp_id}")')
                    
                    self._js_exec(f'openPlaylistModal({json.dumps(playlist_data)})')
                    return 

                # === ЭТО ОДИНОЧНОЕ ВИДЕО ===
                # Перезапускаем анализ без extract_flat, чтобы получить размеры и кодеки
                del opt['extract_flat']
                
                with yt_dlp.YoutubeDL(opt) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    
                    title = info.get('title', 'Unknown').replace('"', "'")
                    thumbnail = info.get('thumbnail', '')
                    
                    # Метаданные
                    duration = self._format_duration(info.get('duration'))
                    filesize = info.get('filesize_approx') or info.get('filesize')
                    size_str = self._format_size(filesize)
                    
                    vcodec = info.get('vcodec', 'N/A')
                    acodec = info.get('acodec', 'N/A')
                    fps = info.get('fps', 0)
                    tbr = info.get('tbr', 0)
                    uploader = info.get('uploader', 'Unknown')

                t_fmt = self.get_trans('status', 'in_format', 'format')
                t_res = self.get_trans('status', 'in_resolution', 'res')
                
                video_data = {
                    "id": task_id,
                    "url": video_url,
                    "title": title,
                    "format": selected_format,
                    "resolution": selectedResolution,
                    "thumbnail": thumbnail,
                    "status": "queued",
                    "fmt_label": t_fmt, 
                    "res_label": t_res,
                    "temp_id": temp_id,
                    "meta": {
                        "duration": duration,
                        "size": size_str,
                        "uploader": uploader,
                        "fps": fps,
                        "vcodec": vcodec,
                        "acodec": acodec,
                        "bitrate": f"{int(tbr)} kbps" if tbr else "N/A"
                    }
                }
                
                self.ctx.download_queue.append(video_data)
                save_queue_to_file(self.ctx.download_queue)

                self._js_exec(f'addVideoToList({json.dumps(video_data)})')
                
                msg_added = self.get_trans('status', 'to_queue', 'Added to queue')
                self.log(f"{msg_added}: {title}", "success")

            except Exception as e:
                err_msg = self.get_trans('status', 'error_adding', 'Error adding')
                self.log(f"{err_msg}: {str(e)}", "error", "DL_GENERIC_ERR")
                if temp_id:
                    self._js_exec(f'removeLoadingItem("{temp_id}")')

        threading.Thread(target=_analyze, daemon=True).start()

    def update_item_settings(self, task_id, new_fmt, new_res):
        found = False
        for item in self.ctx.download_queue:
            if item["id"] == task_id:
                item["format"] = new_fmt
                item["resolution"] = new_res
                # Если была ошибка, даем шанс перезапустить
                if item["status"] == "error":
                    item["status"] = "queued"
                    self._js_exec(f'updateItemProgress("{task_id}", 0, "", "Queued")')
                found = True
                break
        
        if found:
            save_queue_to_file(self.ctx.download_queue)
        else:
            print(f"Video {task_id} not found for update")

    def removeVideoFromQueue(self, task_id):
        self.interrupt_flags[task_id] = True 
        
        title = "Video"
        for v in self.ctx.download_queue:
            if v.get("id") == task_id:
                title = v.get("title", "Video")
                break

        self.ctx.download_queue = [v for v in self.ctx.download_queue if v.get("id") != task_id]
        save_queue_to_file(self.ctx.download_queue)
        
        msg_removed = self.get_trans('status', 'removed_from_queue', 'Removed')
        self.log(f"{msg_removed}: {title}", "success")

    def stop_single_task(self, task_id):
        self.interrupt_flags[task_id] = True
        self.log(f"Stopping task: {task_id}", "info")

    def start_single_task(self, task_id):
        if not self.is_running:
            self.startDownload()
        
        for v in self.ctx.download_queue:
            if v.get("id") == task_id:
                if v.get("status") in ["error", "paused", "stopped"]:
                    v["status"] = "queued"
                    self._js_exec(f'updateItemProgress("{task_id}", 0, "", "Queued")')
                break

    def startDownload(self):
        if not self.ctx.download_queue:
            msg_empty = self.get_trans('status', 'the_queue_is_empty', 'Queue empty')
            self.log(msg_empty, "warn")
            return

        if self.is_running:
            self.log("Download manager is already running.", "warn")
            return

        # Возобновление зависших задач
        resumed_count = 0
        for task in self.ctx.download_queue:
            if task.get("status") == "downloading":
                task["status"] = "queued"
                resumed_count += 1
                self._js_exec(f'updateItemProgress("{task["id"]}", 0, "", "Queued")')
        
        if resumed_count > 0:
            msg = self.get_trans('status', 'resuming', 'Resuming tasks...')
            self.log(f"{msg} ({resumed_count})", "info")

        self.stop_requested = False
        self.is_running = True
        threading.Thread(target=self._download_manager, daemon=True).start()

    def stopDownload(self):
        self.stop_requested = True
        self.is_running = False
        msg = self.get_trans('status', 'stopping', 'Stopping...')
        self.log(msg, "info")

    def _download_manager(self):
        msg_start = self.get_trans('status', 'manager_started', 'Manager Started')
        self.log(msg_start, "info")
        
        while self.is_running and not self.stop_requested:
            queued_tasks = [v for v in self.ctx.download_queue if v.get("status") == "queued"]
            
            if not queued_tasks and self.active_tasks == 0:
                msg_fin = self.get_trans('status', 'queue_finished', 'Queue finished.')
                self.log(msg_fin, "success")
                self.is_running = False
                break

            if not queued_tasks:
                time.sleep(1)
                continue

            for task in queued_tasks:
                if self.stop_requested: break
                
                if self.semaphore.acquire(blocking=False):
                    task["status"] = "downloading"
                    self.active_tasks += 1
                    t = threading.Thread(target=self._download_worker, args=(task,))
                    t.start()
                else:
                    time.sleep(1)
            
            time.sleep(0.5)
        
        if self.stop_requested:
            self.is_running = False
            self.log("Download Manager Stopped.", "info")

    def _download_worker(self, task):
            import yt_dlp 
            
            task_id = task["id"]
            title = task["title"]
            
            if task_id in self.interrupt_flags:
                del self.interrupt_flags[task_id]
            
            # Сбрасываем прогресс
            self.last_video_progress = 0
            
            try:
                msg_start = self.get_trans('status', 'downloading', 'Downloading')
                self.log(f"{msg_start}: {title}", "info")
                
                t_mbs = self.get_trans('mbs', 'MB/s')
                t_sec = self.get_trans('sec', 's')
                t_min = self.get_trans('min', 'm')
                t_done = self.get_trans('status', 'download_success', 'Done')
                
                # Статусы для UI
                t_subs = "Subs..."
                t_proc = "Processing..." 

                def progress_hook(d):
                    if self.stop_requested:
                        raise yt_dlp.utils.DownloadCancelled("Stop requested")
                    if self.interrupt_flags.get(task_id, False):
                        raise yt_dlp.utils.DownloadCancelled("Task stop requested")
                    
                    info = d.get('info_dict', {})
                    filename = d.get('filename', '').lower()
                    
                    # Фильтр субтитров
                    is_subtitle = filename.endswith(('.vtt', '.srt', '.ttml', '.srv3', '.ass'))
                    
                    if d['status'] == 'downloading':
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                        downloaded = d.get('downloaded_bytes', 0)
                        progress = round((downloaded / total) * 100, 1) if total else 0
                        
                        if not is_subtitle:
                            self.last_video_progress = progress
                            speed = d.get('speed', 0) or 0
                            speed_str = f"{speed / 1024 / 1024:.1f} {t_mbs}"
                            
                            eta = d.get('eta', 0)
                            if eta and eta > 60:
                                eta_str = f"{eta // 60}{t_min} {eta % 60}{t_sec}"
                            else:
                                eta_str = f"{eta}{t_sec}" if eta else "..."

                            self._js_exec(f'updateItemProgress("{task_id}", {progress}, "{speed_str}", "{eta_str}")')
                        else:
                            # Для субтитров показываем текст, но прогресс держим от видео
                            self._js_exec(f'updateItemProgress("{task_id}", {self.last_video_progress}, "{t_subs}", "")')

                    elif d['status'] == 'finished':
                        # Никогда не ставим 100% здесь
                        self._js_exec(f'updateItemProgress("{task_id}", 99, "{t_proc}", "")')

                # Путь вывода
                # Используем %(ext)s, чтобы yt-dlp сам подставил расширение (mkv/mp4)
                out_tmpl = os.path.join(self.ctx.download_folder, f"{title}.%(ext)s")
                
                ydl_opts = {
                    'proxy': self.ctx.proxy_url if self.ctx.proxy_enabled == "True" else '',
                    'outtmpl': out_tmpl,
                    'progress_hooks': [progress_hook],
                    'quiet': True,
                    'nocheckcertificate': True,
                    'logger': YtLogger(self),
                    'sleep_interval': 1,
                    'sleep_subtitles': 1,
                    'extractor_args': {'youtube': {'player_client': ['ios']}} 
                }

                # === НАСТРОЙКИ АУДИО ===
                audio_pref = self.ctx.config.get("Audio", "lang", fallback="none")
                
                # Какой контейнер выбрал пользователь (mp4/mkv/webm)
                user_container = task["format"] 
                # Финальный контейнер (может измениться на mkv)
                final_container = user_container

                # Строка выбора видео (с учетом разрешения)
                res = task["resolution"]
                video_sel = f'bestvideo[height<={res}]'

                # 1. Сценарий: Скачать ВСЕ аудиодорожки
                if audio_pref == "all_tracks":
                    self.log(f"Multi-audio mode enabled for {title}", "info")
                    
                    # Включаем поддержку мульти-аудио
                    ydl_opts['audio_multistreams'] = True
                    
                    # Принудительно ставим MKV, так как MP4 плохо клеит много дорожек
                    final_container = 'mkv'
                    
                    # Формула: Видео + (Все аудиодорожки)
                    # mergeall[vcodec=none] выбирает всё, что не является видео (т.е. все аудио)
                    fmt_str = f'{video_sel}+mergeall[vcodec=none]'

                # 2. Сценарий: Скачать конкретный язык (если есть)
                elif audio_pref != "none" and audio_pref != "orig":
                    # Пытаемся найти аудио с нужным языком, если нет - берем лучшее
                    # language^=ru означает "язык начинается с ru"
                    fmt_str = f'{video_sel}+bestaudio[language^={audio_pref}] / {video_sel}+bestaudio'
                
                # 3. Сценарий: По умолчанию (лучшее видео + лучшее аудио)
                else:
                    fmt_str = f'{video_sel}+bestaudio / best[height<={res}]'

                # === НАСТРОЙКИ СУБТИТРОВ ===
                subs_enabled = self.ctx.config.get("Subtitles", "enabled", fallback="False") == "True"
                if subs_enabled:
                    subs_auto = self.ctx.config.get("Subtitles", "auto", fallback="False") == "True"
                    subs_embed = self.ctx.config.get("Subtitles", "embed", fallback="True") == "True"
                    subs_lang = self.ctx.config.get("Subtitles", "langs", fallback="all")
                    
                    ydl_opts['writesubtitles'] = True
                    ydl_opts['writeautomaticsub'] = subs_auto
                    
                    if subs_lang != 'all':
                        ydl_opts['subtitleslangs'] = [subs_lang]
                    else:
                        ydl_opts['subtitleslangs'] = ['all']
                    
                    if subs_embed:
                        ydl_opts['postprocessors'] = ydl_opts.get('postprocessors', [])
                        ydl_opts['postprocessors'].append({'key': 'FFmpegEmbedSubtitle'})

                # JS
                if self.qjs_path:
                    ydl_opts['extractor_args'] = {"ytdl_js": ["js"]}
                    ydl_opts['javascript_executable'] = self.qjs_path

                # === ПРИМЕНЕНИЕ ФОРМАТОВ ===
                if task["format"] == 'mp3':
                    ydl_opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': ydl_opts.get('postprocessors', []) + 
                                        [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
                    })
                    final_container = 'mp3'
                else:
                    ydl_opts.update({
                        'format': fmt_str,
                        'merge_output_format': final_container # Явно указываем контейнер
                    })

                # === ЗАПУСК ===
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([task["url"]])

                # === ФИНАЛ ===
                self.log(f"{t_done}: {title}", "success")
                self._js_exec(f'updateItemProgress("{task_id}", 100, "{t_done}", "")')
                
                # Удаление из очереди
                self.ctx.download_queue = [v for v in self.ctx.download_queue if v["id"] != task_id]
                save_queue_to_file(self.ctx.download_queue)
                time.sleep(1.5) 
                self._js_exec(f'window.removeVideoFromQueue("{task_id}")')
                
                open_dl = self.ctx.config.get("Folders", "dl", fallback="True")
                if open_dl == "True":
                    self.open_dl_folder()

                if self.ctx.config.get("Notifications", "downloads", fallback="True") == "True":
                    history_payload = {
                        "url": task["url"],
                        "thumbnail": task["thumbnail"],
                        "format": final_container, # Пишем реальный формат (напр. mkv вместо mp4)
                        "resolution": task["resolution"],
                        "title": title,
                        "folder": self.ctx.download_folder
                    }
                    import json
                    updated_list = add_notification(t_done, title, "downloader", payload=history_payload)
                    self._js_exec(f'loadNotifications({json.dumps(updated_list)})')

            except yt_dlp.utils.DownloadCancelled:
                t_paused = self.get_trans('status', 'paused', 'Paused')
                self.log(f"{t_paused}: {title}")
                task["status"] = "paused"
                self._js_exec(f'updateItemProgress("{task_id}", 0, "{t_paused}", "")')
                if task_id in self.interrupt_flags:
                    del self.interrupt_flags[task_id]

            except Exception as e:
                t_err = self.get_trans('status', 'error', 'Error')
                self.log(f"{t_err} [{title}]: {str(e)}", "error", "DL_GENERIC_ERR")
                task["status"] = "error" 
                self._js_exec(f'updateItemProgress("{task_id}", 0, "{t_err}", "Failed")')
                
                self._js_exec('openLogsOnError()')
                
            finally:
                self.active_tasks -= 1
                self.semaphore.release()