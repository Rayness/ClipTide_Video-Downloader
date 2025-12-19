# app/modules/downloader/downloader.py

import json
import os
import threading
import time
import uuid
import subprocess
import platform
import yt_dlp

from app.utils.const import COOKIES_FILE
from app.utils.queue.queue import save_queue_to_file
from app.utils.notifications.notifications import add_notification
# Импортируем resource_path для поиска qjs.exe
from app.utils.utils import resource_path 

# Класс для фильтрации шума в консоли
class YtLogger:
    def debug(self, msg):
        # Игнорируем отладочные сообщения
        pass

    def warning(self, msg):
        # Игнорируем предупреждения о JS и Safari, если они не критичны
        # Но если хочешь видеть их - раскомментируй print
        print(f"[YTDLP WARN] {msg}") 
        pass

    def error(self, msg):
        print(f"[YTDLP ERROR] {msg}")

class Downloader:
    def __init__(self, context):
        self.ctx = context
        self.stop_requested = False
        self.is_running = False 
        self.active_tasks = 0   
        self.max_concurrent = 3
        self.semaphore = threading.Semaphore(self.max_concurrent)
        self.interrupt_flags = {}

        # Определяем путь к JS движку один раз при инициализации
        self.qjs_path = resource_path(os.path.join("data", "bin", "qjs.exe"))
        if not os.path.exists(self.qjs_path):
            print(f"WARNING: QuickJS not found at {self.qjs_path}. YouTube downloads might be slow.")
            self.qjs_path = None

    def _js_exec(self, code):
        if self.ctx.window:
            self.ctx.window.evaluate_js(code)

    def get_trans(self, category, key=None, default=""):
        value = self.ctx.translations.get(category)
        if isinstance(value, str): return value
        if isinstance(value, dict) and key: return value.get(key, default or key)
        return default or key or category

    def log(self, message):
        print(f"[LOG] {message}")
        safe_msg = message.replace('"', '\\"').replace("'", "\\'")
        self._js_exec(f'addLog("{safe_msg}")')

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
            self.log(f"Error opening folder: {e}")

    def addVideoToQueue(self, video_url, selected_format, selectedResolution, temp_id=None):
        task_id = str(uuid.uuid4())
        status_pending = self.get_trans('status', 'status_text', 'Pending...')
        self.log(f"{status_pending} ({video_url})")
        
        def _analyze():
            try:
                # Настройки для анализа
                opt = {
                    'proxy': self.ctx.proxy_url if self.ctx.proxy_enabled == "True" else '',
                    'nocheckcertificate': True,
                    'cookies': COOKIES_FILE,
                    'quiet': True,
                    'extract_flat': True,
                    'logger': YtLogger() # Подключаем наш тихий логгер
                }
                
                # Если qjs.exe найден, подключаем его
                if self.qjs_path:
                    opt['extractor_args'] = {"ytdl_js": ["js"]}
                    opt['javascript_executable'] = self.qjs_path

                with yt_dlp.YoutubeDL(opt) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    title = info.get('title', 'Unknown').replace('"', "'")
                    thumbnail = info.get('thumbnail', '')

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
                    "temp_id": temp_id
                }
                
                self.ctx.download_queue.append(video_data)
                save_queue_to_file(self.ctx.download_queue)
                self._js_exec(f'addVideoToList({video_data})')
                
                msg_added = self.get_trans('status', 'to_queue', 'Added to queue')
                self.log(f"{msg_added}: {title}")

            except Exception as e:
                err_msg = self.get_trans('status', 'error_adding', 'Error adding')
                self.log(f"{err_msg}: {str(e)}")
                if temp_id:
                    self._js_exec(f'removeLoadingItem("{temp_id}")')

        threading.Thread(target=_analyze, daemon=True).start()

    def update_item_settings(self, task_id, new_fmt, new_res):
        found = False
        for item in self.ctx.download_queue:
            if item["id"] == task_id:
                item["format"] = new_fmt
                item["resolution"] = new_res
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
        self.log(f"{msg_removed}: {title}")

    def stop_single_task(self, task_id):
        self.interrupt_flags[task_id] = True
        self.log(f"Stopping task: {task_id}")

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
            self.log(msg_empty)
            return

        if self.is_running:
            self.log("Download manager is already running.")
            return

        resumed_count = 0
        for task in self.ctx.download_queue:
            if task.get("status") == "downloading":
                task["status"] = "queued"
                resumed_count += 1
                self._js_exec(f'updateItemProgress("{task["id"]}", 0, "", "Queued")')
        
        if resumed_count > 0:
            msg = self.get_trans('status', 'resuming', 'Resuming tasks...')
            self.log(f"{msg} ({resumed_count})")

        self.stop_requested = False
        self.is_running = True
        threading.Thread(target=self._download_manager, daemon=True).start()

    def stopDownload(self):
        self.stop_requested = True
        self.is_running = False
        msg = self.get_trans('status', 'stopping', 'Stopping...')
        self.log(msg)

    def _download_manager(self):
        msg_start = self.get_trans('status', 'manager_started', 'Manager Started')
        self.log(msg_start)
        
        while self.is_running and not self.stop_requested:
            queued_tasks = [v for v in self.ctx.download_queue if v.get("status") == "queued"]
            
            if not queued_tasks and self.active_tasks == 0:
                msg_fin = self.get_trans('status', 'queue_finished', 'Queue finished.')
                self.log(msg_fin)
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
            self.log("Download Manager Stopped.")

    def _download_worker(self, task):
        task_id = task["id"]
        title = task["title"]
        
        if task_id in self.interrupt_flags:
            del self.interrupt_flags[task_id]
        
        try:
            msg_start = self.get_trans('status', 'downloading', 'Downloading')
            self.log(f"{msg_start}: {title}")
            
            t_mbs = self.get_trans('mbs', 'MB/s')
            t_sec = self.get_trans('sec', 's')
            t_min = self.get_trans('min', 'm')
            t_done = self.get_trans('status', 'download_success', 'Done')

            def progress_hook(d):
                if self.stop_requested:
                    raise yt_dlp.utils.DownloadCancelled("Stop requested")
                
                if self.interrupt_flags.get(task_id, False):
                    raise yt_dlp.utils.DownloadCancelled("Task stop requested")
                
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                    downloaded = d.get('downloaded_bytes', 0)
                    progress = round((downloaded / total) * 100, 1) if total else 0
                    speed = d.get('speed', 0) or 0
                    speed_str = f"{speed / 1024 / 1024:.1f} {t_mbs}"
                    eta = d.get('eta', 0)
                    if eta and eta > 60:
                        eta_str = f"{eta // 60}{t_min} {eta % 60}{t_sec}"
                    else:
                        eta_str = f"{eta}{t_sec}" if eta else "..."

                    self._js_exec(f'updateItemProgress("{task_id}", {progress}, "{speed_str}", "{eta_str}")')

            out_tmpl = os.path.join(self.ctx.download_folder, f"{title}.%(ext)s")
            
            # Базовые опции
            ydl_opts = {
                'proxy': self.ctx.proxy_url if self.ctx.proxy_enabled == "True" else '',
                'outtmpl': out_tmpl,
                'progress_hooks': [progress_hook],
                'quiet': True,
                'nocheckcertificate': True,
                'logger': YtLogger() # Подключаем логгер
            }

            # Подключаем QuickJS если нашли его
            if self.qjs_path:
                ydl_opts['extractor_args'] = {"ytdl_js": ["js"]}
                ydl_opts['javascript_executable'] = self.qjs_path

            if task["format"] == 'mp3':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
                })
            else:
                res = task["resolution"]
                ydl_opts.update({
                    'format': f'bestvideo[height<={res}]+bestaudio/best[height<={res}]',
                    'merge_output_format': task["format"]
                })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([task["url"]])

            self.log(f"{t_done}: {title}")
            self._js_exec(f'updateItemProgress("{task_id}", 100, "{t_done}", "")')
            
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
                    "format": task["format"],
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
            self.log(f"{t_err} [{title}]: {str(e)}")
            task["status"] = "error" 
            self._js_exec(f'updateItemProgress("{task_id}", 0, "{t_err}", "Failed")')
            
        finally:
            self.active_tasks -= 1
            self.semaphore.release()