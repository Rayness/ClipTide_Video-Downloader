# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

import os
import json

from app.utils.paths import resource_path

def get_themes():
    themes_path = resource_path('data/ui/themes')
    themes = []
    if not os.path.isdir(themes_path):
        return themes
    for theme_name in os.listdir(themes_path):
        theme_dir = os.path.join(themes_path, theme_name)
        config_path = os.path.join(theme_dir, 'config.json')

        if os.path.isdir(theme_dir) and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                try:
                    config = json.load(f)
                    themes.append({
                        'id': theme_name,        
                        'name': config.get('title', theme_name), 
                        'styles': config.get('styles', [])       
                    })
                except Exception as e:
                    print(f'Ошибка в {config_path}: {e}')
    
    print("ТЕМЫ: ", themes)
    return themes
