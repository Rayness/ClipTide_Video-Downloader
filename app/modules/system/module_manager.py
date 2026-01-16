# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import os
import json
import shutil
import subprocess
import requests
import zipfile
import threading
import time
import math
import psutil
from app.utils.const import appdata_local, THEME_DIR
from app.utils.ui.themes import get_themes

MODULES_DIR = os.path.join(appdata_local, "modules")
CACHE_FILE = os.path.join(appdata_local, "catalog_cache.json")

# Ссылки (Замени на свои реальные RAW ссылки)
MODULES_CATALOG_URL = "https://cliptide.ru/data/modules_catalog.json"
THEMES_CATALOG_URL = "https://cliptide.ru/data/themes.json"



class ModuleManager:
    def __init__(self, context):
        self.ctx = context
        self.installed_modules = {} 
        self.available_modules = [] 
        self._ensure_dir()
        self.scan_installed_modules()

    def _kill_process_tree(self, pid):
        try:
            parent = psutil.Process(pid)
            # Убиваем всех детей (soffice.bin)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except: pass
            # Убиваем родителя (soffice.exe)
            parent.kill()
        except psutil.NoSuchProcess:
            pass # Процесс уже мертв, всё ок
        except Exception as e:
            print(f"Error killing process: {e}")

    def _ensure_dir(self):
        if not os.path.exists(MODULES_DIR):
            os.makedirs(MODULES_DIR)

    def _js_exec(self, code):
        if self.ctx.window:
            self.ctx.window.evaluate_js(code)

    def scan_installed_modules(self):
        """Сканирует локальную папку modules и читает манифесты"""
        self.installed_modules = {}
        if not os.path.exists(MODULES_DIR): return

        for folder_name in os.listdir(MODULES_DIR):
            manifest_path = os.path.join(MODULES_DIR, folder_name, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["_path"] = os.path.join(MODULES_DIR, folder_name)
                        # Помечаем, что это локальная версия
                        data["is_local"] = True
                        self.installed_modules[data["id"]] = data
                except Exception as e:
                    print(f"Error loading module {folder_name}: {e}")
        
        print(f"Local modules loaded: {list(self.installed_modules.keys())}")

    # --- API МАГАЗИНА ---

    def fetch_store_data(self):
        """
        Умная загрузка: Сеть -> Кэш -> Локальные установленные
        """
        def worker():
            catalog = []
            source = "network"

            # 1. Пробуем скачать из интернета
            try:
                print("Fetching modules catalog...")
                response = requests.get(MODULES_CATALOG_URL, timeout=5)
                if response.status_code == 200:
                    catalog = response.json()
                    # Сохраняем в кэш
                    with open(CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(catalog, f, ensure_ascii=False)
                else:
                    raise Exception(f"HTTP {response.status_code}")
            
            except Exception as e:
                print(f"Network failed ({e}), trying cache...")
                source = "cache"
                # 2. Если нет интернета, читаем кэш
                if os.path.exists(CACHE_FILE):
                    try:
                        with open(CACHE_FILE, "r", encoding="utf-8") as f:
                            catalog = json.load(f)
                    except: pass
            
            # 3. Объединяем с установленными (Merge)
            # Мы должны показать ВСЕ установленные модули, даже если их нет в каталоге
            
            # Создаем словарь для быстрого поиска по ID из каталога
            combined_map = {item["id"]: item for item in catalog}
            
            # Проходимся по локально установленным
            for mod_id, mod_data in self.installed_modules.items():
                if mod_id in combined_map:
                    # Модуль есть и там и там. Можно проверить версию (для апдейта),
                    # но пока просто помечаем как установленный в JS.
                    pass 
                else:
                    # Модуль установлен, но его нет в каталоге (удален автором или кастомный)
                    # Добавляем его в список отображения
                    combined_map[mod_id] = mod_data
            
            # Превращаем обратно в список
            final_list = list(combined_map.values())
            self.available_modules = final_list # Сохраняем в память
            
            # Отправляем в UI
            import json
            installed_ids = list(self.installed_modules.keys())
            
            # Если список пуст и source=cache, значит вообще ничего нет
            if not final_list:
                print("No modules found anywhere.")
            
            self._js_exec(f'updateStoreList({json.dumps(final_list)}, {json.dumps(installed_ids)})')

        threading.Thread(target=worker, daemon=True).start()

    def install_module(self, module_id):
        """Скачивание и установка модуля"""
        # Ищем в загруженном списке (он теперь полный)
        module_info = next((m for m in self.available_modules if m["id"] == module_id), None)
        
        if not module_info:
            print("Module info not found")
            return
            
        if "download_url" not in module_info:
            print("No download URL (maybe local only module?)")
            return

        def worker():
            url = module_info["download_url"]
            self._js_exec(f'updateStoreProgress("{module_id}", 0, "starting")')
            
            zip_path = os.path.join(MODULES_DIR, "temp.zip")
            
            try:
                print(f"Downloading {module_id}...")
                response = requests.get(url, stream=True, allow_redirects=True)
                if response.status_code != 200: raise Exception(f"HTTP {response.status_code}")

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

                if not zipfile.is_zipfile(zip_path):
                    raise Exception("Invalid ZIP file")

                self._js_exec(f'updateStoreProgress("{module_id}", 100, "extracting")')
                
                # Чистим старую папку
                mod_path = os.path.join(MODULES_DIR, module_id)
                if os.path.exists(mod_path): shutil.rmtree(mod_path)
                os.makedirs(mod_path)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(mod_path)
                
                os.remove(zip_path)
                
                # Пересканируем установленные
                self.scan_installed_modules()
                self._js_exec(f'updateStoreProgress("{module_id}", 100, "done")')
                
            except Exception as e:
                print(f"Install error: {e}")
                self._js_exec(f'updateStoreProgress("{module_id}", 0, "error")')
                if os.path.exists(zip_path): os.remove(zip_path)

        threading.Thread(target=worker, daemon=True).start()

    def uninstall_module(self, module_id):
        if module_id in self.installed_modules:
            path = self.installed_modules[module_id]["_path"]
            try:
                shutil.rmtree(path)
                del self.installed_modules[module_id]
                # Обновляем UI (перерисовываем список, кнопка станет "Скачать")
                self.fetch_store_data()
                return True
            except Exception as e:
                print(f"Uninstall error: {e}")
        return False

    # --- ТЕМЫ (Упрощенно, по той же логике можно сделать кэш) ---
    def fetch_themes_catalog(self):
        def worker():
            try:
                response = requests.get(THEMES_CATALOG_URL, timeout=10)
                available_themes = []
                if response.status_code == 200:
                    available_themes = response.json()
                
                installed_ids = [t['id'] for t in get_themes()]
                
                import json
                self._js_exec(f'updateThemesStoreList({json.dumps(available_themes)}, {json.dumps(installed_ids)})')
            except Exception as e:
                print(e)
        threading.Thread(target=worker, daemon=True).start()

    # (Остальные методы: install_theme, delete_theme, get_converter_module, run_converter 
    # оставь без изменений из прошлого кода, они не влияют на список)
    
    # ... (код run_converter и прочее) ...
    def get_converter_module(self, extension):
        ext = extension.lower().replace('.', '')
        for mod in self.installed_modules.values():
            if mod.get("type") == "converter" and ext in mod.get("supported_extensions", []):
                return mod
        return None

    def run_converter(self, module_id, input_path, output_dir, extra_args=None, progress_callback=None, stop_callback=None):
        module = self.installed_modules.get(module_id)
        if not module: return False

        exe_path = os.path.join(module["_path"], module["executable"])
        args_template = module.get("arguments", "")
        
        params = {
            "input": os.path.abspath(input_path),
            "outdir": os.path.abspath(output_dir)
        }
        if extra_args: params.update(extra_args)
        
        # === 1. ВЫЧИСЛЯЕМ ОЖИДАЕМЫЙ ВЫХОДНОЙ ФАЙЛ ===
        # LibreOffice сохраняет имя файла, меняя расширение
        target_ext = extra_args.get('format', 'pdf') if extra_args else 'pdf'
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        expected_output = os.path.join(output_dir, f"{base_name}.{target_ext}")
        
        # === 2. ЧИСТИМ СТАРЫЙ ФАЙЛ (чтобы не обмануться) ===
        if os.path.exists(expected_output):
            try:
                os.remove(expected_output)
            except Exception as e:
                print(f"Warning: Cannot delete old output file: {e}")
        # ===================================================

        try:
            cmd_args = args_template.format(**params)
        except KeyError as e:
            return False
        
        full_cmd = f'"{exe_path}" {cmd_args}'
        print(f"Running (Watcher Mode): {full_cmd}")

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        process = None
        try:
            start_time = time.time()
            file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
            estimated_time = 2.0 + (file_size_mb * 1.5)

            process = subprocess.Popen(
                full_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            
            # 3. Цикл ожидания
            while process.poll() is None:
                # А. Проверка Стопа
                if stop_callback and stop_callback():
                    self._kill_process_tree(process.pid)
                    return False

                # Б. FILE WATCHER (НАШ НОВЫЙ ФИКС)
                if os.path.exists(expected_output):
                    # Проверяем, что файл не пустой (на всякий случай)
                    if os.path.getsize(expected_output) > 0:
                        print("Output file detected! Killing process...")
                        # Даем секунду на "дописывание" буферов
                        time.sleep(1.0)
                        
                        # Принудительно завершаем (считаем это успехом)
                        self._kill_process_tree(process.pid)
                        return True

                # В. Фейковый прогресс (чтобы пользователю не было скучно)
                if progress_callback:
                    elapsed = time.time() - start_time
                    percent = int(95 * (1 - math.exp(-elapsed / estimated_time)))
                    percent = max(1, percent)
                    progress_callback(percent)
                
                time.sleep(0.5) # Проверяем каждые полсекунды
            
            # Если процесс закрылся сам (редкость для LO, но вдруг)
            return process.returncode == 0
            
        except Exception as e:
            print(f"Execution failed: {e}")
            return False
            
        finally:
            if process:
                self._kill_process_tree(process.pid)
    
    def fetch_themes_catalog(self):
        """Загружает список тем с сайта"""
        def worker():
            try:
                # Качаем JSON
                response = requests.get(THEMES_CATALOG_URL, timeout=10)
                
                if response.status_code == 200:
                    available_themes = response.json()
                    
                    # Получаем список ID установленных тем
                    installed_themes = get_themes()
                    installed_ids = [t['id'] for t in installed_themes]
                    
                    import json
                    self._js_exec(f'updateThemesStoreList({json.dumps(available_themes)}, {json.dumps(installed_ids)})')
                else:
                    print(f"Themes fetch error: {response.status_code}")
                    self._js_exec('alert("Не удалось загрузить каталог тем")')
                    
            except Exception as e:
                print(f"Themes connection error: {e}")
                self._js_exec('alert("Ошибка соединения с магазином тем")')
        
        threading.Thread(target=worker, daemon=True).start()

    def install_theme_from_store(self, theme_id, download_url):
        """Скачивает тему и устанавливает её"""
        
        def worker():
            self._js_exec(f'updateThemeProgress("{theme_id}", 0, "starting")')
            
            try:
                # Временный архив
                zip_path = os.path.join(appdata_local, "temp_theme.zip")
                
                # Скачивание
                response = requests.get(download_url, stream=True, timeout=30)
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = int((downloaded / total_size) * 100)
                                self._js_exec(f'updateThemeProgress("{theme_id}", {percent}, "downloading")')

                # Распаковка
                self._js_exec(f'updateThemeProgress("{theme_id}", 100, "extracting")')
                
                # Целевая папка: data/ui/themes/{theme_id}
                target_dir = os.path.join(THEME_DIR, theme_id)
                
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                os.makedirs(target_dir, exist_ok=True)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Извлекаем. Если внутри zip есть папка - извлекаем содержимое,
                    # если файлы в корне - кидаем в target_dir.
                    # Для надежности просто распакуем всё в target_dir
                    zip_ref.extractall(target_dir)
                    
                    # ПРОВЕРКА: Часто темы пакуют как Folder/styles.css.
                    # Если после распаковки в target_dir лежит одна папка, поднимем файлы на уровень выше.
                    items = os.listdir(target_dir)
                    if len(items) == 1 and os.path.isdir(os.path.join(target_dir, items[0])):
                        subdir = os.path.join(target_dir, items[0])
                        for f in os.listdir(subdir):
                            shutil.move(os.path.join(subdir, f), target_dir)
                        os.rmdir(subdir)

                os.remove(zip_path)
                
                # Обновляем список тем в настройках (функция из settings/themes)
                themes = get_themes()
                import json
                self._js_exec(f'updateThemeList({json.dumps(themes)})')
                
                # Готово
                self._js_exec(f'updateThemeProgress("{theme_id}", 100, "done")')
                
            except Exception as e:
                print(f"Theme install error: {e}")
                self._js_exec(f'updateThemeProgress("{theme_id}", 0, "error")')

        threading.Thread(target=worker, daemon=True).start()
    
    def delete_theme(self, theme_id):
        # Запрещаем удалять дефолтную
        if theme_id == 'cliptide': 
            return

        target_dir = os.path.join(THEME_DIR, theme_id)
        if os.path.exists(target_dir):
            try:
                shutil.rmtree(target_dir)
                # Обновляем UI магазина и настроек
                themes = get_themes()
                import json
                self._js_exec(f'updateThemeList({json.dumps(themes)})')
                # Перезагружаем список магазина, чтобы кнопка стала "Скачать"
                self.fetch_themes_catalog()
            except Exception as e:
                print(e)