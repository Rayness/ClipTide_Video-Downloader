# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Пакетный конвертер: видео/аудио через ffmpeg, изображения и PDF своими силами,
офисные форматы — через внешние модули.

Основные отличия от прежней версии:

* Прогресс читается из `-progress pipe:1` (машиночитаемые пары ключ=значение),
  а не выковыривается регуляркой из человекочитаемого stderr. Старый разбор
  ломался, как только ffmpeg менял формат строки или писал не на английском.
* Обновления интерфейса троттлятся. Раньше evaluate_js дёргался на каждую
  строку вывода ffmpeg — сотни вызовов в секунду на один файл.
* Очередь защищена локом: её меняли одновременно поток UI (добавление,
  удаление) и рабочий поток конвертации.
* PyMuPDF (AGPL, 37 МБ) заменён на pypdfium2 (BSD, 4 МБ).
* Выходной файл больше не затирает существующий молча и не может совпасть
  с исходным.
* Оборванный или остановленный файл удаляется, а не остаётся битым огрызком.
* На каждый добавленный файл теперь два процесса ffmpeg вместо трёх.
"""

from __future__ import annotations

import base64
import io
import os
import subprocess
import threading
import time
import uuid

from PIL import Image

from app.modules.converter.encoders import (
    AUDIO_ONLY_FORMATS,
    build_video_command,
)
from app.modules.settings.settings import open_folder
from app.utils import media
from app.utils.converter_utils import probe, thumbnail_data_uri

# Форматы, которые обрабатываем сами через Pillow/pypdfium2
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "ico", "tiff", "tif"}
PDF_EXTENSIONS = {"pdf"}

# Как часто отдавать прогресс в интерфейс
PROGRESS_INTERVAL_SEC = 0.25

# Разрешение рендера страниц PDF при конвертации в картинки
PDF_RENDER_DPI = 200

_PIL_FORMAT_ALIASES = {"jpg": "JPEG", "jpeg": "JPEG", "tif": "TIFF"}

# Форматы, в которые умеем сохранять изображения. Раньше сюда мог прийти
# видеоконтейнер (например mp4, если в интерфейсе выбран общий формат),
# и Pillow падал с KeyError: 'MP4' — сообщение, которое ничего не объясняет.
IMAGE_OUTPUT_FORMATS = {"jpg", "jpeg", "png", "webp", "bmp", "ico", "tiff", "tif", "pdf"}


def _unique_path(path: str) -> str:
    """Добавляет ' (2)', ' (3)'... вместо молчаливой перезаписи."""
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    counter = 2
    while os.path.exists(f"{root} ({counter}){ext}"):
        counter += 1
    return f"{root} ({counter}){ext}"


class _Progress:
    """Троттлинг обновлений прогресса: не чаще раза в PROGRESS_INTERVAL_SEC."""

    def __init__(self, emit, task_id: str):
        self._emit = emit
        self._task_id = task_id
        self._last_percent = -1
        self._last_time = 0.0

    def update(self, percent: int, force: bool = False) -> None:
        percent = max(0, min(100, int(percent)))
        now = time.monotonic()
        if not force and (
            percent == self._last_percent
            or now - self._last_time < PROGRESS_INTERVAL_SEC
        ):
            return
        self._last_percent = percent
        self._last_time = now
        self._emit(self._task_id, f"{percent}%", percent)


class Converter:
    def __init__(self, context):
        self.ctx = context
        self.queue: list[dict] = []
        self._lock = threading.RLock()
        self.is_running = False
        self.stop_requested = False
        self.current_process: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    # Канал в интерфейс
    # ------------------------------------------------------------------
    @property
    def ui(self):
        """Канал берём у контекста; если его нет — молчаливая заглушка."""
        channel = getattr(self.ctx, "ui", None)
        if channel is None:
            from app.core.ui_channel import UIChannel
            channel = UIChannel()
        return channel

    def log(self, message: str, level: str = "info", code: str = "") -> None:
        self.ui.log(message, level, code)

    # ------------------------------------------------------------------
    # Добавление файлов
    # ------------------------------------------------------------------
    #: Фильтры файлового диалога — общие для любого интерфейса
    FILE_FILTERS = [
        ("Медиафайлы", "mp4;avi;mkv;mov;webm;mp3;wav;flac;m4a;ogg;opus"),
        ("Изображения", "jpg;jpeg;png;webp;bmp;tiff;ico;heic"),
        ("PDF", "pdf"),
        ("Документы Word", "docx;doc"),
        ("Таблицы Excel", "xlsx;xls"),
        ("Презентации PowerPoint", "pptx;ppt"),
        ("Все файлы", "*"),
    ]

    def openFile(self):
        file_paths = self.ui.pick_files(
            "Выберите файлы для конвертации", self.FILE_FILTERS, multiple=True
        )
        self.add_paths(file_paths)

    def add_paths(self, paths) -> None:
        """Добавляет файлы в очередь (используется и диалогом, и drag-and-drop)."""
        paths = [p for p in (paths or []) if p]
        if not paths:
            return
        threading.Thread(
            target=self._add_files, args=(list(paths),), daemon=True
        ).start()

    def _add_files(self, paths: list[str]) -> None:
        for path in paths:
            task_id = str(uuid.uuid4())
            filename = os.path.basename(path)

            # Скелетон показываем до тяжёлой работы, чтобы карточка появилась сразу
            self.ui.converter_skeleton(task_id, filename)
            try:
                item = self._build_item(task_id, path, filename)
            except Exception as e:
                self.ui.converter_skeleton_removed(task_id)
                self.log(f"Ошибка добавления {filename}: {e}", "error", "ADD_FILE_ERROR")
                continue

            with self._lock:
                self.queue.append(item)

            self.ui.converter_item_added({**item, "temp_id": task_id})
            self.log(f"Добавлен: {filename}", "success")

    def _build_item(self, task_id: str, path: str, filename: str) -> dict:
        ext = os.path.splitext(filename)[1].lstrip(".").lower()
        meta = {"duration": 0, "bitrate": 0, "resolution": "?",
                "codec": "?", "fps": 0, "audio": "?"}
        thumb = None
        error = None

        if ext in IMAGE_EXTENSIONS or ext in PDF_EXTENSIONS:
            thumb, meta_patch, error = self._preview_document(path, ext)
            meta.update(meta_patch)
        else:
            # Один ffprobe, результат переиспользуется для превью
            info, error = probe(path)
            if info is not None:
                meta.update(info.as_ui_dict())
                if info.has_video:
                    thumb, thumb_error = thumbnail_data_uri(path, info)
                    error = error or thumb_error

        return {
            "id": task_id,
            "path": path,
            "filename": filename,
            "thumbnail": thumb,
            "duration": meta["duration"],
            "status": "queued",
            "error": error,
            "details": meta,
        }

    def _preview_document(self, path: str, ext: str) -> tuple[str | None, dict, str | None]:
        """Превью для картинки или первой страницы PDF."""
        try:
            if ext in PDF_EXTENSIONS:
                image = self._render_pdf_page(path, 0, dpi=72)
                patch = {"resolution": f"{image.width}x{image.height}",
                         "codec": "PDF Document"}
            else:
                image = Image.open(path)
                patch = {"resolution": f"{image.width}x{image.height}",
                         "codec": image.format or ext.upper()}

            with image:
                preview = image.convert("RGB") if image.mode in ("RGBA", "LA", "P") else image
                preview.thumbnail((160, 160))
                buffer = io.BytesIO()
                preview.save(buffer, format="JPEG", quality=70)

            data_uri = "data:image/jpeg;base64," + base64.b64encode(
                buffer.getvalue()
            ).decode("ascii")
            return data_uri, patch, None
        except Exception as e:
            return None, {}, f"Не удалось создать превью: {e}"

    @staticmethod
    def _render_pdf_page(path: str, index: int, dpi: int) -> Image.Image:
        """Страница PDF как PIL-изображение (pypdfium2, пришёл на смену fitz)."""
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(path)
        try:
            page = document[index]
            return page.render(scale=dpi / 72).to_pil()
        finally:
            document.close()

    @staticmethod
    def _pdf_page_count(path: str) -> int:
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(path)
        try:
            return len(document)
        finally:
            document.close()

    # ------------------------------------------------------------------
    # Управление очередью
    # ------------------------------------------------------------------
    def remove_item(self, task_id: str) -> None:
        with self._lock:
            self.queue = [x for x in self.queue if x["id"] != task_id]
        self.log("Файл удалён из очереди", "info")

    def start_conversion(self, settings_map: dict) -> None:
        if self.is_running:
            self.log("Конвертация уже идёт", "info")
            return

        default_settings = {"type": "video", "format": "mp4", "codec": "auto",
                            "quality": "23", "resolution": "original"}
        with self._lock:
            if not self.queue:
                self.log("Очередь пуста", "info")
                return
            for item in self.queue:
                item["settings"] = settings_map.get(item["id"], default_settings)
            pending = [x for x in self.queue if x["status"] != "done"]

        if not pending:
            self.log("Все файлы уже сконвертированы", "info")
            return

        self.stop_requested = False
        self.is_running = True
        threading.Thread(target=self._conversion_loop, daemon=True).start()

    def stop_conversion(self) -> None:
        self.stop_requested = True
        process = self.current_process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        self.log("Остановка конвертации...", "info")

    # ------------------------------------------------------------------
    # Основной цикл
    # ------------------------------------------------------------------
    def _conversion_loop(self) -> None:
        out_folder = self.ctx.converter_folder
        try:
            os.makedirs(out_folder, exist_ok=True)
        except OSError as e:
            self.log(f"Не удалось создать папку {out_folder}: {e}", "error", "OUTPUT_DIR")
            self.is_running = False
            self.ui.converter_finished()
            return

        self.log("Старт пакетной конвертации", "info")

        with self._lock:
            batch = list(self.queue)

        for item in batch:
            if self.stop_requested:
                break
            if item["status"] == "done":
                continue

            task_id = item["id"]
            item["status"] = "processing"
            self.ui.converter_progress(task_id, "Converting...", 0)

            try:
                self._convert_one(item, out_folder)
            except Exception as e:
                item["status"] = "error"
                self.log(f"{item['filename']}: {e}", "error", "CONVERSION_ERROR")
                self.ui.converter_progress(task_id, "Error", 0)

        self.is_running = False
        self.current_process = None
        self.ui.converter_finished()

        if self.ctx.config.get("Folders", "cv", fallback="True") == "True" and not self.stop_requested:
            open_folder(out_folder)

    def _convert_one(self, item: dict, out_folder: str) -> None:
        settings = item.get("settings", {})
        task_id = item["id"]
        source = item["path"]
        base_name = os.path.splitext(item["filename"])[0]
        input_ext = os.path.splitext(source)[1].lstrip(".").lower()
        file_type = settings.get("type", "video")

        is_native = (
            file_type == "image"
            or input_ext in IMAGE_EXTENSIONS
            or input_ext in PDF_EXTENSIONS
        )

        external_module = None
        if not is_native and file_type != "video":
            manager = getattr(self.ctx, "module_manager", None)
            if manager is not None:
                external_module = manager.get_converter_module(input_ext)

        if external_module is not None:
            self._convert_via_module(item, external_module, out_folder)
        elif is_native:
            self._convert_image(item, out_folder, base_name, input_ext)
        else:
            self._convert_media(item, out_folder, base_name)

        if item["status"] == "done":
            self.ui.converter_progress(task_id, "Done", 100)

    # ---- сценарий 1: внешний модуль ----------------------------------
    def _convert_via_module(self, item: dict, module: dict, out_folder: str) -> None:
        task_id = item["id"]
        settings = item.get("settings", {})
        doc_format = settings.get("doc_format", "pdf")

        self.log(f"Модуль {module['name']}: {item['filename']}", "info")
        progress = _Progress(self.ui.converter_progress, task_id)

        success = self.ctx.module_manager.run_converter(
            module["id"], item["path"], out_folder,
            extra_args={"format": doc_format},
            progress_callback=progress.update,
            stop_callback=lambda: self.stop_requested,
        )

        if not success:
            if self.stop_requested:
                item["status"] = "queued"
                self.log("Остановлено пользователем", "info")
                self.ui.converter_progress(task_id, "Stopped", 0)
                return
            raise RuntimeError("модуль конвертации вернул ошибку")

        item["status"] = "done"
        self.log(f"Успешно: {item['filename']}", "success")
        self._notify_done(item, doc_format.upper(), out_folder)

    # ---- сценарий 2: изображения и PDF -------------------------------
    def _convert_image(self, item: dict, out_folder: str, base_name: str, input_ext: str) -> None:
        settings = item.get("settings", {})
        task_id = item["id"]
        out_fmt = (settings.get("format") or "jpg").lower()
        if out_fmt not in IMAGE_OUTPUT_FORMATS:
            raise RuntimeError(
                f"в «{out_fmt}» изображение сохранить нельзя; "
                f"доступны: {', '.join(sorted(IMAGE_OUTPUT_FORMATS))}"
            )
        quality = int(settings.get("quality", 90))
        resize = settings.get("resize", "original")
        pil_format = _PIL_FORMAT_ALIASES.get(out_fmt, out_fmt.upper())

        if input_ext in PDF_EXTENSIONS and out_fmt != "pdf":
            # Каждая страница -> отдельная картинка в папке с именем документа
            self.log(f"PDF -> {out_fmt.upper()}: {item['filename']}", "info")
            page_dir = _unique_path(os.path.join(out_folder, base_name))
            os.makedirs(page_dir, exist_ok=True)

            total = self._pdf_page_count(item["path"])
            progress = _Progress(self.ui.converter_progress, task_id)

            for index in range(total):
                if self.stop_requested:
                    item["status"] = "queued"
                    self.ui.converter_progress(task_id, "Stopped", 0)
                    return
                image = self._render_pdf_page(item["path"], index, PDF_RENDER_DPI)
                with image:
                    self._save_image(
                        image, os.path.join(page_dir, f"Page_{index + 1}.{out_fmt}"),
                        pil_format, out_fmt, quality, resize,
                    )
                progress.update(int((index + 1) / total * 100))

            item["status"] = "done"
            self._notify_done(item, out_fmt.upper(), page_dir)
            return

        self.log(f"Изображение -> {out_fmt.upper()}: {item['filename']}", "info")
        # _unique_path всегда возвращает несуществующий путь, поэтому перезаписать
        # исходник невозможно даже при совпадении имени и расширения.
        out_path = _unique_path(os.path.join(out_folder, f"{base_name}.{out_fmt}"))

        source = (
            self._render_pdf_page(item["path"], 0, PDF_RENDER_DPI)
            if input_ext in PDF_EXTENSIONS
            else Image.open(item["path"])
        )
        with source:
            self._save_image(source, out_path, pil_format, out_fmt, quality, resize)

        item["status"] = "done"
        self._notify_done(item, out_fmt.upper(), out_folder)

    @staticmethod
    def _save_image(image: Image.Image, save_path: str, pil_format: str,
                    out_fmt: str, quality: int, resize: str) -> None:
        # JPEG и PDF не умеют альфа-канал — подкладываем белый фон
        if out_fmt in ("jpg", "jpeg", "pdf") and image.mode in ("RGBA", "LA", "P"):
            if image.mode == "P":
                image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            mask = image.split()[-1] if "A" in image.mode else None
            background.paste(image, mask=mask)
            image = background
        elif image.mode == "P":
            image = image.convert("RGB")

        if resize and resize != "original":
            width, height = image.size
            if resize.endswith("%"):
                factor = int(resize.rstrip("%")) / 100
                new_size = (max(1, int(width * factor)), max(1, int(height * factor)))
            elif resize.isdigit():
                max_dim = int(resize)
                ratio = min(max_dim / width, max_dim / height, 1.0)
                new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
            else:
                new_size = (width, height)
            if new_size != image.size:
                image = image.resize(new_size, Image.Resampling.LANCZOS)

        save_args = {}
        if out_fmt in ("jpg", "jpeg", "webp"):
            save_args["quality"] = quality
        if out_fmt in ("jpg", "jpeg"):
            save_args["optimize"] = True
            save_args["progressive"] = True
        if out_fmt == "ico" and max(image.size) > 256:
            image = image.resize((256, 256), Image.Resampling.LANCZOS)

        image.save(save_path, format=pil_format, **save_args)

    # ---- сценарий 3: видео и аудио -----------------------------------
    def _convert_media(self, item: dict, out_folder: str, base_name: str) -> None:
        settings = item.get("settings", {})
        task_id = item["id"]
        out_fmt = (settings.get("format") or "mp4").lower()

        out_path = _unique_path(os.path.join(out_folder, f"{base_name}.{out_fmt}"))

        preset = self.ctx.config.get("Editor", "preset", fallback="medium")
        command, encoder = build_video_command(
            item["path"], out_path, out_fmt,
            codec=settings.get("codec", "auto"),
            quality=settings.get("quality", 23),
            resolution=settings.get("resolution", "original"),
            preset=preset,
        )

        if out_fmt in AUDIO_ONLY_FORMATS:
            self.log(f"FFmpeg (аудио {out_fmt}): {item['filename']}", "info")
        else:
            self.log(f"FFmpeg [{encoder}]: {item['filename']}", "info")

        duration = float(item.get("duration") or 0)
        progress = _Progress(self.ui.converter_progress, task_id)

        self.current_process = media.popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        process = self.current_process

        try:
            self._pump_progress(process, duration, progress)
            process.wait()
        finally:
            self.current_process = None

        if self.stop_requested:
            item["status"] = "queued"
            self.ui.converter_progress(task_id, "Stopped", 0)
            self._remove_partial(out_path)
            return

        if process.returncode != 0:
            stderr = (process.stderr.read() or "").strip() if process.stderr else ""
            self._remove_partial(out_path)
            raise RuntimeError(stderr.splitlines()[-1] if stderr else f"ffmpeg код {process.returncode}")

        item["status"] = "done"
        self._notify_done(item, out_fmt.upper(), out_folder)

    @staticmethod
    def _pump_progress(process: subprocess.Popen, duration: float, progress: _Progress) -> None:
        """
        Читает поток `-progress pipe:1`. Формат — пары ключ=значение по строке,
        блок закрывается строкой progress=continue или progress=end.
        """
        if process.stdout is None:
            return
        for line in process.stdout:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key == "out_time_us" or key == "out_time_ms":
                if duration <= 0:
                    continue
                try:
                    micros = float(value)
                except ValueError:
                    continue
                # out_time_ms в ffmpeg фактически тоже в микросекундах
                seconds = micros / 1_000_000
                progress.update(min(int(seconds / duration * 100), 99))
            elif key == "progress" and value == "end":
                progress.update(100, force=True)

    @staticmethod
    def _remove_partial(path: str) -> None:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    # ------------------------------------------------------------------
    def _notify_done(self, item: dict, fmt: str, folder: str) -> None:
        if self.ctx.config.get("Notifications", "conversion", fallback="True") != "True":
            return
        from app.utils.notifications.notifications import add_notification

        updated = add_notification(
            "Конвертация завершена", item["filename"], "converter",
            payload={"title": item["filename"], "thumbnail": None,
                     "format": fmt, "folder": folder},
        )
        self.ui.notifications_reloaded(updated)
