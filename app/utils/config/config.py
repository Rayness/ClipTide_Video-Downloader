# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import os
import configparser
from app.utils.const import download_dir, CONFIG_FILE
from app.utils.utils import restart_app

# Настройки по умолчанию
DEFAULT_CONFIG_SETTINGS = {
    "language": "ru",
    "folder_path": f"{download_dir}",
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
    "dl" : "True",
    "cv" : "True"
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

def update_config(config):
    if config.has_section('Proxy'):
        print("Конфиг актуальный", config)
    else:
        print("Конфиг не актуальный")
        create_default_config()
        restart_app()

def create_default_config():
    config = configparser.ConfigParser()
    config["Settings"] = DEFAULT_CONFIG_SETTINGS
    config["Subtitles"] = DEFAULT_CONFIG_SUBS
    config["Audio"] = DEFAULT_CONFIG_AUDIO
    config["Proxy"] = DEFAULT_CONFIG_PROXY
    config["Themes"] = DEFAULT_CONFIG_THEMES
    config["Notifications"] = DEFAULT_CONFIG_NOTIFICATIONS
    config["Folders"] = DEFAULT_CONFIG_FOLDERS
    save_config(config)
    return config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            config.write(file)
            print("Конфигурация сохранена.")
    except Exception as e:
        print(f"Ошибка при сохранении конфигурации: {e}")

