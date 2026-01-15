# app/modules/system/module_manager.py

import os
import json
import shutil
import subprocess
import requests
import zipfile
import threading
from app.utils.const import appdata_local

MODULES_DIR = os.path.join(appdata_local, "modules")
# Ссылка на твой файл каталога (замени на реальную Raw ссылку)
CATALOG_URL = "https://raw.githubusercontent.com/Rayness/YT-Downloader/main/data/modules_catalog.json"

class ModuleManager:
    def __init__(self, context):
        self.ctx = context
        self.installed_modules = {} 
        self.available_modules = [] # Данные из магазина
        self._ensure_dir()
        self.scan_installed_modules()

    def _ensure_dir(self):
        if not os.path.exists(MODULES_DIR):
            os.makedirs(MODULES_DIR)

    def _js_exec(self, code):
        if self.ctx.window:
            self.ctx.window.evaluate_js(code)

    def scan_installed_modules(self):
        """Сканирует папку modules"""
        self.installed_modules = {}
        if not os.path.exists(MODULES_DIR): return

        for folder_name in os.listdir(MODULES_DIR):
            manifest_path = os.path.join(MODULES_DIR, folder_name, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["_path"] = os.path.join(MODULES_DIR, folder_name)
                        self.installed_modules[data["id"]] = data
                except Exception as e:
                    print(f"Error loading module {folder_name}: {e}")

    # --- API МАГАЗИНА ---

    def fetch_store_data(self):
        """Загружает список модулей с GitHub"""
        def worker():
            try:
                response = requests.get(CATALOG_URL, timeout=5)
                if response.status_code == 200:
                    self.available_modules = response.json()
                    # Отправляем в UI
                    import json
                    self._js_exec(f'updateStoreList({json.dumps(self.available_modules)}, {json.dumps(list(self.installed_modules.keys()))})')
                else:
                    print("Store fetch error:", response.status_code)
            except Exception as e:
                print("Store connection error:", e)
        
        threading.Thread(target=worker, daemon=True).start()

    def install_module(self, module_id):
        """Скачивание и установка модуля"""
        # Ищем URL в загруженном каталоге
        module_info = next((m for m in self.available_modules if m["id"] == module_id), None)
        if not module_info:
            print("Module info not found")
            return

        def worker():
            url = module_info["download_url"]
            self._js_exec(f'updateStoreProgress("{module_id}", 0, "starting")')
            
            try:
                zip_path = os.path.join(MODULES_DIR, "temp.zip")
                
                # Скачивание с прогрессом
                response = requests.get(url, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = int((downloaded / total_size) * 100)
                                self._js_exec(f'updateStoreProgress("{module_id}", {percent}, "downloading")')

                # Распаковка
                self._js_exec(f'updateStoreProgress("{module_id}", 100, "extracting")')
                
                # Создаем папку для модуля
                mod_path = os.path.join(MODULES_DIR, module_id)
                if os.path.exists(mod_path): shutil.rmtree(mod_path)
                os.makedirs(mod_path)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(mod_path)
                
                os.remove(zip_path)
                
                self.scan_installed_modules()
                
                # Обновляем UI (говорим что установлено)
                self._js_exec(f'updateStoreProgress("{module_id}", 100, "done")')
                
            except Exception as e:
                print(f"Install error: {e}")
                self._js_exec(f'updateStoreProgress("{module_id}", 0, "error")')

        threading.Thread(target=worker, daemon=True).start()

    def uninstall_module(self, module_id):
        if module_id in self.installed_modules:
            path = self.installed_modules[module_id]["_path"]
            try:
                shutil.rmtree(path)
                del self.installed_modules[module_id]
                # Обновляем UI магазина
                self.fetch_store_data()
                return True
            except Exception as e:
                print(f"Uninstall error: {e}")
        return False

    # --- ЗАПУСК КОНВЕРТАЦИИ ---

    def get_converter_module(self, extension):
        ext = extension.lower().replace('.', '')
        for mod in self.installed_modules.values():
            if mod.get("type") == "converter" and ext in mod.get("supported_extensions", []):
                return mod
        return None

    def run_converter(self, module_id, input_path, output_dir):
        """
        Запускает команду из манифеста.
        Шаблон: "arguments": "--headless --convert-to pdf \"{input}\" --outdir \"{outdir}\""
        """
        module = self.installed_modules.get(module_id)
        if not module: return False

        exe_path = os.path.join(module["_path"], module["executable"])
        args_template = module.get("arguments", "")
        
        # Формируем команду
        # ВАЖНО: input_path и output_dir должны быть абсолютными
        cmd_args = args_template.format(
            input=os.path.abspath(input_path),
            outdir=os.path.abspath(output_dir)
        )
        
        full_cmd = f'"{exe_path}" {cmd_args}'
        print(f"Running module: {full_cmd}")

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            process = subprocess.Popen(
                full_cmd,
                shell=True, # Нужно для запуска сложных команд
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(f"Module stderr: {stderr}")
                
            return process.returncode == 0
        except Exception as e:
            print(f"Module execution failed: {e}")
            return False