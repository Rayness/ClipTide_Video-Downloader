# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import os
import configparser
from app.utils.const import download_dir, CONFIG_FILE

# Настройки по умолчанию
DEFAULT_CONFIG_SETTINGS = {
    "language": "ru",
    "folder_path": f"{download_dir}",
    "converter_folder": f"{download_dir}",
    "auto_update": "False",
}

DEFAULT_CONFIG_PROXY = {
    "enabled" : "False",
    "url" : "http://185.10.129.14:3128"
}

DEFAULT_CONFIG_THEMES = {
    "theme" : "cliptide",
    "style" : "default"
}

DEFAULT_CONFIG_NOTIFICATIONS = {
    "conversion" : "True",
    "downloads" : "True"
}

DEFAULT_CONFIG_FOLDERS = {
    "dl"     : "True",
    "cv"     : "True",
    "editor" : "True"
}

DEFAULT_CONFIG_SUBS = {
    "enabled": "False",
    "auto": "False",
    "embed": "True",
    "langs": "all"
}

DEFAULT_CONFIG_AUDIO = {
    "lang": "none"
}

DEFAULT_CONFIG_UPDATES = {
    "auto_update": "False",
    "channel": "stable"  # stable / dev
}

DEFAULT_CONFIG_DISPLAY = {
    "window_size": "1200x780",
    "ui_scale": "1",
}

DEFAULT_CONFIG_EDITOR = {
    "codec":  "h264",   # h264 | h265 | copy
    "preset": "fast",   # ultrafast | faster | fast | medium | slow
    "crf":    "18",     # 0-51
    "format": "mp4",    # mp4 | mkv
}

def load_config():
    config = configparser.ConfigParser()
    
    # Создаем дефолтную конфигурацию, если файла нет
    if not os.path.exists(CONFIG_FILE):
        print("Файл конфигурации не найден. Создаю новый...")
        return create_default_config()
    
    try:
        # Читаем файл с явным указанием кодировки
        with open(CONFIG_FILE, 'r', encoding='utf-8') as configfile:
            config.read_file(configfile)
        return config
    except UnicodeDecodeError:
        # Пробуем альтернативную кодировку, если utf-8 не сработала
        try:
            with open(CONFIG_FILE, 'r', encoding='cp1251') as configfile:
                config.read_file(configfile)
            print("")
            return config
        except Exception as e:
            print(f"ERROR: {e}")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Если все попытки чтения провалились, создаем дефолтную конфиг
    return create_default_config()

#: Все секции конфигурации и их значения по умолчанию
DEFAULT_SECTIONS = {
    "Settings":      DEFAULT_CONFIG_SETTINGS,
    "Subtitles":     DEFAULT_CONFIG_SUBS,
    "Audio":         DEFAULT_CONFIG_AUDIO,
    "Proxy":         DEFAULT_CONFIG_PROXY,
    "Themes":        DEFAULT_CONFIG_THEMES,
    "Notifications": DEFAULT_CONFIG_NOTIFICATIONS,
    "Folders":       DEFAULT_CONFIG_FOLDERS,
    "Updates":       DEFAULT_CONFIG_UPDATES,
    "Editor":        DEFAULT_CONFIG_EDITOR,
    "Display":       DEFAULT_CONFIG_DISPLAY,
}


def update_config(config):
    """
    Дополняет конфиг недостающими секциями и ключами.

    Раньше отсутствие секции Proxy приводило к пересозданию конфига с нуля
    и перезапуску приложения через restart_app(): пользователь молча терял
    все настройки, а при неудачном стечении обстоятельств получал цикл
    перезапусков. Теперь недостающее просто дописывается.
    """
    changed = False
    for section, defaults in DEFAULT_SECTIONS.items():
        if not config.has_section(section):
            config.add_section(section)
            changed = True
        for key, value in defaults.items():
            if not config.has_option(section, key):
                config.set(section, key, str(value))
                changed = True

    if changed:
        print("Конфигурация дополнена недостающими параметрами")
        save_config(config)
    return config

def create_default_config():
    config = configparser.ConfigParser()
    config["Settings"] = DEFAULT_CONFIG_SETTINGS
    config["Subtitles"] = DEFAULT_CONFIG_SUBS
    config["Audio"] = DEFAULT_CONFIG_AUDIO
    config["Proxy"] = DEFAULT_CONFIG_PROXY
    config["Themes"] = DEFAULT_CONFIG_THEMES
    config["Notifications"] = DEFAULT_CONFIG_NOTIFICATIONS
    config["Folders"] = DEFAULT_CONFIG_FOLDERS
    config["Updates"] = DEFAULT_CONFIG_UPDATES
    config["Editor"] = DEFAULT_CONFIG_EDITOR
    config["Display"] = DEFAULT_CONFIG_DISPLAY
    save_config(config)
    return config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            config.write(file)
            print("Конфигурация сохранена.")
    except Exception as e:
        print(f"Ошибка при сохранении конфигурации: {e}")

