# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import json
import webview
import time
from app.core.context import AppContext
from app.core.core import PublicWebViewApi, WebViewApi
from app.utils.config.config import load_config, update_config
from app.utils.notifications.notifications import load_notifications
from app.utils.ui.themes import get_themes
from app.utils.locale.translations import load_translations
from app.utils.utils import check_for_update, get_local_version, unicodefix, ffmpegreg, load_modal_content
from app.utils.logs.logs import logs
from app.utils.const import html_file_path
from app.utils.queue.queue import load_queue_from_file
from app.modules.system.module_manager import ModuleManager

def startApp():
    # 1. Создаем контекст
    ctx = AppContext()
    
    # 2. Загружаем конфигурацию
    ctx.config = load_config()
    update_config(ctx.config) # Проверка валидности

    # 3. Наполняем контекст данными
    ctx.language = ctx.config.get("Settings", "language", fallback="en")
    ctx.translations = load_translations(ctx.language)
    ctx.download_folder = ctx.config.get("Settings", "folder_path", fallback="downloads")
    ctx.converter_folder = ctx.config.get("Settings", "converter_folder", fallback="downloads")
    
    ctx.theme = ctx.config.get("Themes", "theme", fallback="default")
    ctx.style = ctx.config.get("Themes", "style", fallback="default")
    
    ctx.proxy_url = ctx.config.get("Proxy", "url", fallback="")
    ctx.proxy_enabled = ctx.config.get("Proxy", "enabled", fallback="False")
    
    ctx.download_queue = load_queue_from_file()
    ctx.notifications = load_notifications()
    
    ctx.module_manager = ModuleManager(ctx)
    
    version = str(get_local_version()).lower()
    update_status = str(check_for_update()).lower()
    themes = get_themes()
    modal_content = load_modal_content()
    
    # Флаги настроек (можно читать напрямую из ctx.config в модулях, но для кэша ок)
    dl_open = ctx.config.get("Folders", "dl", fallback="True")
    cv_open = ctx.config.get("Folders", "cv", fallback="True")
    notif_dl = ctx.config.get("Notifications", "downloads", fallback="True")
    notif_cv = ctx.config.get("Notifications", "conversion", fallback="True")

    # 4. Инициализация API
    real_api = WebViewApi(ctx)
    public_api = PublicWebViewApi(real_api)

    # 5. Создание окна
    window = webview.create_window(
        f'ClipTide {version}',
        html_file_path,
        js_api=public_api,
        height=780,
        width=1200,
        resizable=True,
        text_select=True,
        frameless=True,
    )
    real_api.set_window(window)
    print("Window object passed to API") # Добавь этот принт для проверки

    # 6. Загрузка данных в UI при старте
    def on_loaded():
        # Вместо 20 вызовов evaluate_js, передаем данные пачками
        # Но пока сохраним совместимость с твоим JS:
        
        subs_en = ctx.config.get("Subtitles", "enabled", fallback="False")
        subs_auto = ctx.config.get("Subtitles", "auto", fallback="False")
        subs_embed = ctx.config.get("Subtitles", "embed", fallback="True")
        subs_lang = ctx.config.get("Subtitles", "langs", fallback="all")
        
        audio_lang = ctx.config.get("Audio", "lang", fallback="none")
        
        cmds = [
            f'updateDownloadFolder({json.dumps(ctx.download_folder)})',
            f'updateConvertFolder({json.dumps(ctx.converter_folder)})',
            f'loadSubtitlesSettings("{subs_en}", "{subs_auto}", "{subs_embed}", "{subs_lang}")',
            f'loadAudioSettings("{audio_lang}")',
            f'updateTranslations({json.dumps(ctx.translations)})',
            f'window.loadQueue({json.dumps(ctx.download_queue)})',
            f'updateApp({update_status}, {json.dumps(ctx.translations)})',
            f'setLanguage("{ctx.language}")',
            f'loadNotifications({json.dumps(ctx.notifications)})',
            f'loadproxy("{ctx.proxy_url}", {json.dumps(ctx.proxy_enabled)})',
            f'loadopenfolders({json.dumps(dl_open)}, {json.dumps(cv_open)})',
            f'load_settingsNotificatios("{notif_dl}","{notif_cv}")',
            f'loadTheme("{ctx.theme}", "{ctx.style}", {themes})',
            f'get_version("{version}")',
            f'loadData({json.dumps(modal_content)})'
        ]
        
        for cmd in cmds:
            window.evaluate_js(cmd)
        
        print("Initialization complete. Removing preloader.")
        
        time.sleep(0.5) 
        
        window.evaluate_js('window.removePreloader()')

    window.events.loaded += on_loaded
    webview.start(debug=True)

def main():
    unicodefix()
    ffmpegreg()
    logs()
    startApp()

if __name__ == "__main__":
    main()