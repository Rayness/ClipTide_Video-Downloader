# app/modules/system/module_manager.py

import os
import json
import shutil
import subprocess
import requests
import zipfile
from app.utils.const import appdata_local

MODULES_DIR = os.path.join(appdata_local, "modules")

class ModuleManager:
    def __init__(self, context):
        self.ctx = context
        self.modules = {} # { "id": {manifest_data} }
        self._ensure_dir()
        self.scan_modules()

    def _ensure_dir(self):
        if not os.path.exists(MODULES_DIR):
            os.makedirs(MODULES_DIR)

    def scan_modules(self):
        """Сканирует папку modules и загружает манифесты"""
        self.modules = {}
        if not os.path.exists(MODULES_DIR): return

        for folder_name in os.listdir(MODULES_DIR):
            manifest_path = os.path.join(MODULES_DIR, folder_name, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Добавляем путь к папке модуля для удобства
                        data["_path"] = os.path.join(MODULES_DIR, folder_name)
                        self.modules[data["id"]] = data
                except Exception as e:
                    print(f"Error loading module {folder_name}: {e}")
        
        print(f"Loaded {len(self.modules)} modules.")

    def get_installed_modules(self):
        """Возвращает список для UI"""
        return list(self.modules.values())

    def install_module(self, url):
        """Скачивает и распаковывает модуль (zip)"""
        # Логика похожа на апдейтер: скачать zip, распаковать в MODULES_DIR
        try:
            zip_path = os.path.join(MODULES_DIR, "temp_module.zip")
            response = requests.get(url, stream=True)
            with open(zip_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Предполагаем, что внутри архива есть корневая папка с именем модуля
                zip_ref.extractall(MODULES_DIR)
            
            os.remove(zip_path)
            self.scan_modules()
            return True, "Модуль установлен"
        except Exception as e:
            return False, str(e)

    def uninstall_module(self, module_id):
        if module_id in self.modules:
            path = self.modules[module_id]["_path"]
            try:
                shutil.rmtree(path)
                del self.modules[module_id]
                return True
            except Exception as e:
                print(e)
        return False

    def get_converter_for_ext(self, extension):
        """Ищет модуль, который поддерживает это расширение"""
        ext = extension.lower().replace('.', '')
        for mod in self.modules.values():
            if mod.get("type") == "converter" and ext in mod.get("supported_extensions", []):
                return mod
        return None

    def run_converter_module(self, module_id, input_path, output_path, settings_json):
        """
        Запускает внешний exe модуля.
        Протокол: converter.exe "input" "output" '{"settings":...}'
        """
        module = self.modules.get(module_id)
        if not module: return False

        exe_path = os.path.join(module["_path"], module["executable"])
        
        # Запуск процесса без окна консоли
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            process = subprocess.Popen(
                [exe_path, input_path, output_path, settings_json],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            
            # Чтение вывода для прогресса (если модуль умеет писать прогресс в stdout)
            for line in process.stdout:
                # Парсинг прогресса, если модуль его шлет
                pass
                
            process.wait()
            return process.returncode == 0
        except Exception as e:
            print(f"Module execution failed: {e}")
            return False