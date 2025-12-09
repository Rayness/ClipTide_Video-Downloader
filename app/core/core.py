# app/core/core.py

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

    def saveTheme(self, theme):
        self._api.settings.switch_theme(theme)

    def saveStyle(self, style):
        self._api.settings.switch_style(style)
        
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