# app/modules/converter/converter.py

import json
import os
import threading
import time
import uuid
import subprocess
import ffmpeg
import io 
from PIL import Image
import fitz
from app.utils.converter_utils import get_thumbnail_base64, print_video_info
from app.modules.settings.settings import open_folder

class Converter:
    def __init__(self, context):
        self.ctx = context
        self.queue = []         # Очередь файлов
        self.is_running = False
        self.stop_requested = False
        self.current_process = None

    def _js_exec(self, code):
        if self.ctx.window:
            self.ctx.window.evaluate_js(code)

    def log(self, message):
        safe_msg = message.replace('"', '\\"').replace("'", "\\'")
        self._js_exec(f'addLog("[CONV] {safe_msg}")')

    def openFile(self):
        import webview
        # Заменяем Tkinter на pywebview
        ft =  ("Media Files (*.mp4;*.avi;*.mkv;*.mov;*.mp3;*.wav)", "Image Files (*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.tiff;*.ico;*.heic)", "PDF Files (*.pdf)", "All Files (*.*)")
        file_paths = self.ctx.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=ft
        )
        # root.destroy()

        if not file_paths:
            return

        self._js_exec('showSpinner()')
        
        # Обрабатываем файлы в потоке, чтобы не вешать UI при генерации превью
        def _process_add():
            for path in file_paths:
                try:
                    task_id = str(uuid.uuid4())
                    filename = os.path.basename(path)
                    ext = filename.split('.')[-1].lower()
                    
                    thumb = None
                    error = None
                    
                    # Дефолтные метаданные
                    meta_data = {
                        "duration": 0, "bitrate": 0, "resolution": "?", 
                        "codec": "?", "fps": 0, "audio": "?"
                    }

                    # --- ЛОГИКА ГЕНЕРАЦИИ ПРЕВЬЮ ---
                    
                    # 1. Изображения и PDF
                    if ext in ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'ico', 'pdf']:
                        try:
                            img = None
                            import base64
                            # Если PDF - рендерим первую страницу
                            if ext == 'pdf':
                                doc = fitz.open(path)
                                page = doc.load_page(0)
                                pix = page.get_pixmap(alpha=False)
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                doc.close()
                                meta_data["resolution"] = f"{pix.width}x{pix.height}"
                                meta_data["codec"] = "PDF Document"
                            
                            # Если Картинка - открываем Pillow
                            else:
                                img = Image.open(path)
                                meta_data["resolution"] = f"{img.width}x{img.height}"
                                meta_data["codec"] = img.format

                            if img:
                                # Конвертируем в RGB (убираем прозрачность для превью)
                                if img.mode in ('RGBA', 'LA', 'P'):
                                    img = img.convert('RGB')
                                
                                # Создаем миниатюру (быстро)
                                img.thumbnail((120, 120))
                                
                                # Сохраняем в память
                                buffer = io.BytesIO()
                                img.save(buffer, format="JPEG", quality=70)
                                
                                b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
                                thumb = f"data:image/jpeg;base64,{b64_str}"
                                
                        except Exception as e:
                            print(f"[Thumb Error] Не удалось создать превью для {filename}: {e}")
                            thumb = None # Будет дефолтная заглушка

                    # 2. Видео и Аудио (через FFmpeg)
                    else:
                        thumb, error = get_thumbnail_base64(path)
                        
                        # Получаем метаданные видео
                        meta = print_video_info(path)
                        if meta and isinstance(meta, tuple) and len(meta) >= 8:
                            meta_data["duration"] = meta[0]
                            meta_data["bitrate"] = meta[1]
                            meta_data["resolution"] = f"{meta[2]}x{meta[3]}" if meta[2] != "?" else "?"
                            meta_data["codec"] = meta[4]
                            meta_data["fps"] = meta[5]
                            meta_data["audio"] = f"{meta[6]} ({meta[7]} kbps)"

                    # --- ФОРМИРОВАНИЕ ОБЪЕКТА ---
                    item = {
                        "id": task_id,
                        "path": path,
                        "filename": filename,
                        "thumbnail": thumb, # Если None, JS поставит дефолтную
                        "duration": meta_data["duration"],
                        "status": "queued",
                        "error": error,
                        "details": meta_data
                    }
                    
                    self.queue.append(item)
                    
                    # Отправляем в JS
                    json_item = json.dumps(item)
                    self._js_exec(f'addConverterItem({json_item})')
                    
                    self.log(f"Добавлен: {filename}")
                    
                except Exception as e:
                    self.log(f"Критическая ошибка добавления {path}: {e}")
            
            self._js_exec('hideSpinner()')

        threading.Thread(target=_process_add, daemon=True).start()

    def remove_item(self, task_id):
        self.queue = [x for x in self.queue if x["id"] != task_id]
        self.log("Файл удален из очереди")

    def start_conversion(self, settings_map):
        """
        settings_map: Словарь { "task_id": {format:..., codec:...}, ... }
        Приходит из JS.
        """
        if self.is_running: return

        # 1. Обновляем настройки в очереди (в Python) данными из JS
        for item in self.queue:
            t_id = item["id"]
            if t_id in settings_map:
                item["settings"] = settings_map[t_id]
            else:
                # Фолбек, если вдруг чего-то нет (хотя не должно быть)
                item["settings"] = {
                    'format': 'mp4', 'codec': 'libx264', 
                    'quality': '23', 'resolution': 'original'
                }

        self.stop_requested = False
        self.is_running = True
        
        threading.Thread(target=self._conversion_loop, daemon=True).start()

    def stop_conversion(self):
        self.stop_requested = True
        if self.current_process:
            self.current_process.terminate()
        self.log("Остановка конвертации...")

    def _conversion_loop(self):
            self.log("Старт пакетной конвертации")
            
            out_folder = self.ctx.converter_folder
            if not os.path.exists(out_folder):
                os.makedirs(out_folder)

            for item in self.queue:
                if self.stop_requested: break
                if item["status"] == "done": continue

                s = item.get("settings", {})
                file_type = s.get("type", "video")
                
                # Общие настройки
                out_fmt = s.get('format', 'mp4')
                
                item["status"] = "processing"
                task_id = item["id"]
                self._js_exec(f'updateConvStatus("{task_id}", "Converting...", 0)')

                try:
                    base_name = os.path.splitext(item["filename"])[0]
                    
                    # ==========================================
                    # ЛОГИКА ДЛЯ ИЗОБРАЖЕНИЙ И PDF
                    # ==========================================
                    if file_type == 'image':
                        import PIL
                        from PIL import Image
                        
                        quality = int(s.get('quality', 90))
                        resize = s.get('resize', 'original')
                        
                        if out_fmt == 'jpg': pil_fmt = 'JPEG'
                        elif out_fmt == 'webp': pil_fmt = 'WEBP'
                        elif out_fmt == 'png': pil_fmt = 'PNG'
                        elif out_fmt == 'ico': pil_fmt = 'ICO'
                        elif out_fmt == 'pdf': pil_fmt = 'PDF'
                        else: pil_fmt = out_fmt.upper()

                        # Функция сохранения (определена 1 раз для использования ниже)
                        def process_and_save_image(pil_img, save_path):
                            if out_fmt in ['jpg', 'pdf'] and pil_img.mode in ('RGBA', 'LA', 'P'):
                                if pil_img.mode == 'P': pil_img = pil_img.convert('RGBA')
                                background = Image.new('RGB', pil_img.size, (255, 255, 255))
                                background.paste(pil_img, mask=pil_img.split()[-1] if 'A' in pil_img.mode else None)
                                pil_img = background.convert('RGB')
                            
                            if resize != 'original':
                                w, h = pil_img.size
                                if resize.endswith('%'):
                                    factor = int(resize.strip('%')) / 100
                                    new_size = (int(w * factor), int(h * factor))
                                elif resize.isdigit():
                                    max_dim = int(resize)
                                    ratio = min(max_dim / w, max_dim / h)
                                    new_size = (int(w * ratio), int(h * ratio))
                                else:
                                    new_size = (w, h)
                                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

                            save_args = {}
                            if out_fmt in ['jpg', 'webp']:
                                save_args['quality'] = quality
                            if out_fmt == 'ico':
                                if pil_img.size[0] > 256 or pil_img.size[1] > 256:
                                    pil_img = pil_img.resize((256, 256), Image.Resampling.LANCZOS)

                            pil_img.save(save_path, format=pil_fmt, **save_args)

                        input_ext = item["path"].split('.')[-1].lower()
                        
                        # --- ЕСЛИ PDF ---
                        if input_ext == 'pdf':
                            self.log(f"Обработка PDF: {item['filename']}")
                            pdf_folder = os.path.join(out_folder, base_name)
                            if not os.path.exists(pdf_folder): os.makedirs(pdf_folder)
                            
                            import fitz 
                            doc = fitz.open(item["path"])
                            total_pages = len(doc)
                            
                            for i, page in enumerate(doc):
                                if self.stop_requested: break
                                pix = page.get_pixmap(dpi=300, alpha=False)
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                
                                page_name = f"Page_{i+1}.{out_fmt}"
                                process_and_save_image(img, os.path.join(pdf_folder, page_name))
                                
                                percent = int(((i + 1) / total_pages) * 100)
                                self._js_exec(f'updateConvStatus("{task_id}", "{percent}%", {percent})')
                            doc.close()

                        # --- ЕСЛИ КАРТИНКА ---
                        else:
                            out_path = os.path.join(out_folder, f"conv_{base_name}.{out_fmt}")
                            self.log(f"Конвертация IMG: {item['filename']}")
                            with Image.open(item["path"]) as img:
                                process_and_save_image(img, out_path)
                        
                        item["status"] = "done"
                        self._js_exec(f'updateConvStatus("{item["id"]}", "Done", 100)')

                    # ==========================================
                    # ЛОГИКА ДЛЯ ВИДЕО / АУДИО (FFmpeg)
                    # ==========================================
                    else:
                        codec = s.get('codec', 'libx264')
                        crf = s.get('quality', '23')
                        res = s.get('resolution', 'original')
                        
                        output_path = os.path.join(out_folder, f"conv_{base_name}.{out_fmt}")
                        command = ['ffmpeg', '-y', '-i', item["path"]]
                        
                        if out_fmt in ['mp3', 'aac', 'wav']:
                            command.extend(['-vn'])
                            if out_fmt == 'mp3': command.extend(['-c:a', 'libmp3lame', '-q:a', '2'])
                            elif out_fmt == 'aac': command.extend(['-c:a', 'aac', '-b:a', '192k'])
                        else:
                            if codec == 'copy':
                                command.extend(['-c', 'copy'])
                            else:
                                command.extend(['-c:v', codec, '-preset', 'medium', '-crf', crf])
                                command.extend(['-c:a', 'aac', '-b:a', '128k'])
                                if res != 'original':
                                    command.extend(['-vf', f'scale=-2:{res}'])

                        command.append(output_path)
                        self.log(f"FFmpeg: {item['filename']}")
                        
                        self.current_process = subprocess.Popen(
                            command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            universal_newlines=True,
                            encoding='utf-8',
                            errors='ignore',
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )

                        duration = item.get("duration", 0)
                        for line in self.current_process.stdout:
                            if "time=" in line:
                                try:
                                    time_str = line.split("time=")[1].split()[0]
                                    h, m, s = map(float, time_str.split(":"))
                                    curr = h*3600 + m*60 + s
                                    if duration > 0:
                                        percent = min(round((curr / duration) * 100), 99)
                                        self._js_exec(f'updateConvStatus("{task_id}", "{percent}%", {percent})')
                                except: pass
                        
                        self.current_process.wait()

                        if self.current_process.returncode == 0:
                            item["status"] = "done"
                            self._js_exec(f'updateConvStatus("{task_id}", "Done", 100)')
                        else:
                            item["status"] = "error"
                            self._js_exec(f'updateConvStatus("{task_id}", "Error", 0)')

                except Exception as e:
                    self.log(f"Error: {e}")
                    item["status"] = "error"
                    self._js_exec(f'updateConvStatus("{task_id}", "Error", 0)')

            self.is_running = False
            self.current_process = None
            self._js_exec('conversionFinished()')
            
            open_cv = self.ctx.config.get("Folders", "cv", fallback="True")
            if open_cv == "True":
                open_folder(out_folder)