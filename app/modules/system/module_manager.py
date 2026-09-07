# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Внешние модули конвертации (например, LibreOffice для DOCX/XLSX/PPTX -> PDF).

Магазин модулей и тем удалён: сетевые каталоги, установка и удаление из
стора больше не поддерживаются. Осталось только то, что нужно конвертеру —
найти установленный модуль и запустить его.

Модули лежат в %LOCALAPPDATA%/ClipTide/modules/<id>/ и описываются
manifest.json:

    {
      "id": "office_converter",
      "type": "converter",
      "supported_extensions": ["docx", "xlsx", "pptx"],
      "executable": "LibreOffice/App/libreoffice/program/soffice.exe",
      "arguments": "--headless --convert-to {format} --outdir \\"{outdir}\\" \\"{input}\\""
    }

Запуск больше не идёт через shell: строка аргументов разбирается shlex и
передаётся списком, поэтому имя файла с кавычками или амперсандом не может
превратиться в отдельную команду.
"""

from __future__ import annotations

import json
import math
import os
import shlex
import subprocess
import time

import psutil

from app.utils.const import appdata_local

MODULES_DIR = os.path.join(appdata_local, "modules")

#: Сколько ждать появления выходного файла, прежде чем считать это провалом
CONVERSION_TIMEOUT_SEC = 600


class ModuleManager:
    def __init__(self, context):
        self.ctx = context
        self.installed_modules: dict[str, dict] = {}
        os.makedirs(MODULES_DIR, exist_ok=True)
        self.scan_installed_modules()

    # ------------------------------------------------------------------
    def scan_installed_modules(self) -> None:
        """Читает манифесты модулей из локальной папки."""
        self.installed_modules = {}
        if not os.path.isdir(MODULES_DIR):
            return

        for folder_name in os.listdir(MODULES_DIR):
            manifest_path = os.path.join(MODULES_DIR, folder_name, "manifest.json")
            if not os.path.exists(manifest_path):
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                data["_path"] = os.path.join(MODULES_DIR, folder_name)
                self.installed_modules[data["id"]] = data
            except Exception as e:
                print(f"[modules] {folder_name}: {e}")

        if self.installed_modules:
            print(f"[modules] загружены: {', '.join(self.installed_modules)}")

    def get_converter_module(self, extension: str) -> dict | None:
        ext = extension.lower().lstrip(".")
        for module in self.installed_modules.values():
            if module.get("type") == "converter" and ext in module.get(
                "supported_extensions", []
            ):
                return module
        return None

    # ------------------------------------------------------------------
    @staticmethod
    def _kill_process_tree(pid: int) -> None:
        """LibreOffice плодит soffice.bin — гасим всё дерево."""
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except psutil.Error:
                    pass
            parent.kill()
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            print(f"[modules] не удалось завершить процесс: {e}")

    def run_converter(self, module_id, input_path, output_dir, extra_args=None,
                      progress_callback=None, stop_callback=None) -> bool:
        module = self.installed_modules.get(module_id)
        if module is None:
            return False

        exe_path = os.path.join(module["_path"], module["executable"])
        if not os.path.isfile(exe_path):
            print(f"[modules] исполняемый файл не найден: {exe_path}")
            return False

        params = {
            "input": os.path.abspath(input_path),
            "outdir": os.path.abspath(output_dir),
        }
        if extra_args:
            params.update(extra_args)

        # LibreOffice кладёт результат рядом, меняя только расширение
        target_ext = (extra_args or {}).get("format", "pdf")
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        expected_output = os.path.join(output_dir, f"{base_name}.{target_ext}")

        # Старый файл убираем, иначе примем его за свежий результат
        if os.path.exists(expected_output):
            try:
                os.remove(expected_output)
            except OSError as e:
                print(f"[modules] не удалось удалить старый результат: {e}")

        try:
            # Шаблон разбираем ДО подстановки: так путь с пробелами остаётся
            # одним аргументом, а спецсимволы в имени файла не попадают в shell
            argv = [exe_path]
            for token in shlex.split(module.get("arguments", ""), posix=False):
                argv.append(token.strip('"').format(**params))
        except KeyError as e:
            print(f"[modules] в шаблоне аргументов нет параметра {e}")
            return False

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        process = None
        try:
            start_time = time.time()
            size_mb = os.path.getsize(input_path) / (1024 * 1024)
            estimated = 2.0 + size_mb * 1.5

            process = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            while process.poll() is None:
                if stop_callback and stop_callback():
                    self._kill_process_tree(process.pid)
                    return False

                # LibreOffice в headless-режиме часто не завершается сам,
                # поэтому ждём появления готового файла
                if os.path.exists(expected_output) and os.path.getsize(expected_output) > 0:
                    time.sleep(1.0)   # даём дописать буферы
                    self._kill_process_tree(process.pid)
                    return True

                elapsed = time.time() - start_time
                if elapsed > CONVERSION_TIMEOUT_SEC:
                    print("[modules] превышено время конвертации")
                    self._kill_process_tree(process.pid)
                    return False

                if progress_callback:
                    # Асимптотический «псевдопрогресс»: модуль своего не отдаёт
                    progress_callback(max(1, int(95 * (1 - math.exp(-elapsed / estimated)))))

                time.sleep(0.5)

            return process.returncode == 0

        except Exception as e:
            print(f"[modules] запуск не удался: {e}")
            return False

        finally:
            if process is not None:
                self._kill_process_tree(process.pid)
