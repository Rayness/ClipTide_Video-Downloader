# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import ctypes
from ctypes import windll

from app.modules.downloader.downloader import Downloader
from app.modules.converter.converter import Converter
from app.modules.settings.settings import SettingsManager, open_folder
from app.utils.const import THEME_DIR, TRANSLATIONS_DIR

class WebViewApi:
    def __init__(self, context):
        self.ctx = context
        self.downloader = Downloader(context)
        self.converter = Converter(context)
        self.settings = SettingsManager(context)

    def set_window(self, window):
        # ОЧЕНЬ ВАЖНО: передаем окно в контекст
        self.ctx.set_window(window)
        
    def resize_window(self, direction):
        """Изменение размера окна через Windows API (как в стандартных приложениях)"""
        if not self.ctx.window: 
            return
        
        # HT-коды для non-client hit test (используются с WM_NCLBUTTONDOWN)
        # Эти коды говорят Windows "пользователь нажал на границу окна"
        mapping = {
            "left": 10,        # HTLEFT
            "right": 11,       # HTRIGHT
            "top": 12,         # HTTOP
            "top-left": 13,    # HTTOPLEFT
            "top-right": 14,   # HTTOPRIGHT
            "bottom": 15,      # HTBOTTOM
            "bottom-left": 16, # HTBOTTOMLEFT
            "bottom-right": 17 # HTBOTTOMRIGHT
        }
        
        if direction in mapping:
            try:
                window = self.ctx.window
                
                # Получаем hwnd по заголовку окна
                hwnd = None
                if hasattr(window, 'title'):
                    hwnd = ctypes.windll.user32.FindWindowW(None, window.title)
                
                if not hwnd:
                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                
                if not hwnd:
                    print("Could not get window hwnd")
                    return
                
                # WM_NCLBUTTONDOWN = 0x00A1
                # Это сообщение говорит "левая кнопка мыши нажата в non-client области"
                # Windows сама обрабатывает интерактивный resize
                WM_NCLBUTTONDOWN = 0x00A1
                ht_code = mapping[direction]
                
                ctypes.windll.user32.ReleaseCapture()
                ctypes.windll.user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, ht_code, 0)
                
            except Exception as e:
                print(f"Resize error: {e}")

class PublicWebViewApi:
    def __init__(self, real_api):
        self._api = real_api

    # ... твои остальные методы ...
    # Убедись, что методы ниже вызывают self._api...
    
    def addVideoToQueue(self, url, fmt, res, temp_id=None):
        # Передаем temp_id дальше в downloader
        self._api.downloader.addVideoToQueue(url, fmt, res, temp_id)
        
    def update_video_settings(self, task_id, fmt, res):
        self._api.downloader.update_item_settings(task_id, fmt, res)

    def startDownload(self):
        self._api.downloader.startDownload()

    def stopDownload(self):
        self._api.downloader.stopDownload()

    def removeVideoFromQueue(self, task_id): # Аргумент теперь task_id
        self._api.downloader.removeVideoFromQueue(task_id)

    def converter_add_files(self): # Переименовал для ясности, или оставь openFile
        self._api.converter.openFile()

    def converter_remove_item(self, task_id):
        self._api.converter.remove_item(task_id)

    def converter_start(self, settings):
        # settings приходит как словарь из JS
        self._api.converter.start_conversion(settings)

    def converter_stop(self):
        self._api.converter.stop_conversion()
        
    def choose_folder(self):
        self._api.settings.choose_folder()

    def switch_download_folder(self):
        self._api.settings.switch_download_folder()
    
    def switch_update_setting(self, key, value):
        self._api.settings.swith_update_setting(key, value)
    
    def choose_converter_folder(self):
        self._api.settings.choose_converter_folder()

    def switch_converter_folder(self):
        self._api.settings.switch_converter_folder()

    def open_folder(self, folder):
        open_folder(folder)

    def open_theme_folder(self):
        open_folder(THEME_DIR)

    def open_locale_folder(self):
        open_folder(TRANSLATIONS_DIR)

    def launch_update(self):
        self._api.settings.launch_update()

    def switch_language(self, lang_code):
        self._api.settings.switch_language(lang_code)

    def minimize(self):
        if self._api.ctx.window: self._api.ctx.window.minimize()

    def toggle_fullscreen(self):
        if self._api.ctx.window: self._api.ctx.window.toggle_fullscreen()

    def close(self):
        if self._api.ctx.window: self._api.ctx.window.destroy()
    
    def resize_window(self, direction):
        """Изменение размера окна перетаскиванием границ"""
        self._api.resize_window(direction)

    def saveTheme(self, theme):
        self._api.settings.switch_theme(theme)

    def saveStyle(self, style):
        self._api.settings.switch_style(style)

    def switch_window_size(self, size):
        """Изменение размера окна"""
        self._api.settings.switch_window_size(size)

    def switch_ui_scale(self, scale):
        """Изменение масштаба интерфейса"""
        self._api.settings.switch_ui_scale(scale)
        
    def get_themes(self):
        from app.utils.ui.themes import get_themes
        return get_themes()

    def switch_proxy_url(self, proxy):
        self._api.settings.switch_proxy_url(proxy)

    def switch_proxy(self, enabled):
        self._api.settings.switch_proxy(enabled)

    def switch_notifi(self, type, enabled):
        self._api.settings.switch_notifi(type, enabled)

    def switch_open_folder_dl(self, type, enabled):
        self._api.settings.switch_open_folder_dl(type, enabled)
    
    # Методы уведомлений
    def save_notifications(self, notifications):
        from app.utils.notifications.notifications import save_notifications
        self._api.ctx.notifications = notifications
        save_notifications(notifications)

    def delete_notification(self, id):
        from app.utils.notifications.notifications import delete_notification
        delete_notification(id)

    def mark_notification_as_read(self, id):
        from app.utils.notifications.notifications import mark_notification_as_read
        self._api.ctx.notifications = mark_notification_as_read(id)
        
    def import_theme(self):
        self._api.settings.import_theme_from_zip()
        
    def test_proxy(self, proxy_url):
        self._api.settings.test_user_proxy(proxy_url)
        
    def downloader_stop_task(self, task_id):
        self._api.downloader.stop_single_task(task_id)
        
    def downloader_start_task(self, task_id):
        self._api.downloader.start_single_task(task_id)
        
    def open_path(self, path):
        from app.modules.settings.settings import open_folder
        open_folder(path)
        
    def add_playlist_videos(self, videos_list, fmt, res):
        """
        videos_list: список URL-адресов
        """
        # Запускаем в отдельном потоке, чтобы не вешать UI циклом
        import threading
        def worker():
            for url in videos_list:
                self._api.downloader.addVideoToQueue(url, fmt, res)
                # Небольшая пауза, чтобы интерфейс успевал отрисовывать карточки плавно
                import time
                time.sleep(0.1) 
        
        threading.Thread(target=worker, daemon=True).start()
        
    def switch_subs_setting(self, key, value):
        self._api.settings.switch_subs_setting(key, value)
        
    def switch_audio_setting(self, key, value):
        self._api.settings.switch_audio_setting(key, value)
        
    def store_fetch_data(self):
        """Запросить обновление списка модулей"""
        if self._api.ctx.module_manager:
            self._api.ctx.module_manager.fetch_store_data()

    def store_install_module(self, module_id):
        if self._api.ctx.module_manager:
            self._api.ctx.module_manager.install_module(module_id)

    def store_uninstall_module(self, module_id):
        if self._api.ctx.module_manager:
            self._api.ctx.module_manager.uninstall_module(module_id)
            
    def store_fetch_themes(self):
        if self._api.ctx.module_manager:
            self._api.ctx.module_manager.fetch_themes_catalog()

    def store_install_theme(self, theme_id, url):
        if self._api.ctx.module_manager:
            self._api.ctx.module_manager.install_theme_from_store(theme_id, url)

    def store_delete_theme(self, theme_id):
        if self._api.ctx.module_manager:
            self._api.ctx.module_manager.delete_theme(theme_id)