// Copyright (C) 2025 Rayness
// This program is free software under GPLv3. See LICENSE for details.

window.i18n = {};

updateApp = function(update, translations) {
    update_text = document.getElementById('update__text');
    if (update) {
        safeSetText('update__text', translations.settings.updates.update_text_ready);
        update_text.style.backgroundColor=  "#5d8a51";
    } else if (!update) {
        safeSetText('update__text', translations.settings.updates.update_text_not_ready);
        update_text.style.backgroundColor = "#3e4d3a";
    } else {
        safeSetText('update__text', translations.settings.updates.update_text_error);
        update_text.style.backgroundColor = "#7c363d";
    }
}

function safeSetText(id, text) {
    const el = document.getElementById(id);
    if (el && text) {
        el.innerText = text;
    }
}

// Функция для обновления текста интерфейса
window.updateTranslations = function(translations) {
    if (!translations) return;
    window.i18n = translations;

    const s = translations.settings; // Сокращение
    const sui = translations.settings.settings_ui; // Наша новая секция

    window.i18n = translations;

    // Настройки //
    if (sui) {
        safeSetText('settings-main-title', s.title); // "Настройки"

        // Навигация
        safeSetText('nav-app', sui.nav_app);
        safeSetText('nav-download', sui.nav_download);
        safeSetText('nav-convert', sui.nav_convert);
        safeSetText('nav-proxy', sui.nav_proxy);
        safeSetText('nav-version', sui.nav_version);
        safeSetText('nav-about', sui.nav_about);

        // Заголовки секций
        safeSetText('hdr-appearance', sui.hdr_appearance);
        safeSetText('hdr-download', sui.hdr_download);
        safeSetText('hdr-folders', sui.hdr_folders);
        safeSetText('hdr-convert', sui.hdr_convert);
        
        // Кнопки и описания
        safeSetText('lbl-proxy-string', sui.lbl_proxy_string);
        safeSetText('txt-proxy-check', sui.btn_check);
        safeSetText('txt-proxy-save', sui.btn_save);
        
        safeSetText('desc-about', sui.desc_about);
        safeSetText('hdr-licenses', sui.hdr_licenses);
        safeSetText('txt-licenses', sui.txt_licenses);
        safeSetText('btn-close', sui.btn_close);
    }          
        
    // Язык
    if (s.language) {
        safeSetText('language_title', s.language.language);
        safeSetText('open_locale_folder', s.language.open_folder);
        // Опции
        safeSetText('lang_ru', s.language.russian);
        safeSetText('lang_en', s.language.english);

        safeSetText('lang_ru', translations.settings.language.russian);
        safeSetText('lang_en', translations.settings.language.english);
        safeSetText('lang_pl', translations.settings.language.polish);
        safeSetText('lang_ja', translations.settings.language.japan);
        safeSetText('lang_ua', translations.settings.language.ukraine);
        safeSetText('lang_it', translations.settings.language.italian);
        safeSetText('lang_de', translations.settings.language.german);
        safeSetText('lang_fr', translations.settings.language.french);
        safeSetText('lang_cn', translations.settings.language.chinese);
    }
    // Оформление

    if (s.subtitles) {
        safeSetText('subs-title', s.subtitles.title);
        safeSetText('lbl_subs_enable', s.subtitles.enable);
        safeSetText('lbl_subs_auto', s.subtitles.auto);
        safeSetText('lbl_subs_embed', s.subtitles.embed);
        safeSetText('lbl_subs_lang', s.subtitles.lang);
    }

    if (s.themes) {
        safeSetText('theme-title', s.themes.theme);
        safeSetText('style-title', s.themes.style);
    }

    // Папки 
    if (s.folders) {
        safeSetText('download_folder_title', s.folders.placeholder_download);
        safeSetText('conversion_folder_title', s.folders.placeholder_conversion);
        
        safeSetText('open_folder_download', s.folders.open_download_folder); // Текст свитча
        safeSetText('open_converter_folder', s.folders.open_converter_folder);
    }

    // Уведомления
    if (s.notifications) {
        safeSetText('get_notifi_download', s.notifications.notifi_download);
        safeSetText('get_notifi_conversion', s.notifications.notifi_conversion);
    }

    // Прокси 
    if (s.proxys) {
        safeSetText('proxy-title', s.proxys.title);
        safeSetText('turn_on_proxy', s.proxys.turn_on);
    }

    // Обновления
    if (s.updates) {
        safeSetText('updates-title', s.updates.title);
        safeSetText('txt-btn-update', s.updates.update_button);
    }

    safeSetText('update__text', s.updates.update_text_ready);

    // О приложении
    if (s.about) {
        safeSetText('about-title', s.about.title);
        safeSetText('about-date', s.about.date);
    }

    // Донат
    if (translations.donate) {
        safeSetText('donate-description', translations.donate.description);
    }
    
    // Основной функционал //
    // 
    // Загрузка видео
    
    const vidUrl = document.getElementById('videoUrl');
    if(vidUrl) vidUrl.placeholder = translations.video_URL || 'URL...';
    
    // --- МАГАЗИН ---
    if (translations.store) {
        safeSetText('tab-store-modules', translations.store.tab_modules);
        safeSetText('tab-store-themes', translations.store.tab_themes);
        const btnRefresh = document.getElementById('btn-refresh-store');
        if (btnRefresh) btnRefresh.title = translations.store.btn_refresh;
    }
    
    // Конвертер
    if (translations.converter) {
        // safeSetText('converter_add_video', translations.converter.click_for_add_video);
        // safeSetText('convertion-settings', translations.converter.convertion_settings);
        safeSetText('txt-conv-add', translations.converter.add_files_btn);
        
        // Заголовок сайдбара обновляется динамически, но дефолт зададим
        const headerTitle = document.getElementById('setting-header-title');
        if(headerTitle && headerTitle.innerText.includes("Глобальные")) { 
            headerTitle.innerText = translations.converter.global_settings;
        }
        
        safeSetText('lbl-cv-fmt', translations.converter.lbl_format);
        safeSetText('lbl-cv-codec', translations.converter.lbl_codec);
        safeSetText('lbl-cv-qual', translations.converter.lbl_quality);
        safeSetText('lbl-cv-res', translations.converter.lbl_resolution);
        
        safeSetText('txt-cv-better', translations.converter.val_better);
        safeSetText('txt-cv-worse', translations.converter.val_worse);
        
        safeSetText('txt-btn-conv', translations.converter.btn_convert);
        safeSetText('txt-btn-stop', translations.converter.btn_stop);
        
        safeSetText('cv-res-orig', translations.converter.val_original);
        safeSetText('opt-cv-img-orig', translations.converter.val_original);
        
        safeSetText('lbl-cv-img-fmt', translations.converter.lbl_format);
        safeSetText('lbl-cv-img-qual', translations.converter.lbl_quality);
        safeSetText('lbl-cv-img-size', translations.converter.lbl_size);
        
        safeSetText('txt-cv-img-low', translations.converter.val_low);
        safeSetText('txt-cv-img-high', translations.converter.val_high);
        
    } 
    
    
    // История (Модальное окно)
    if (translations.history) {
        safeSetText('lbl-hist-date', translations.history.date_label);
        safeSetText('lbl-hist-fmt', translations.history.format_label);
        safeSetText('lbl-hist-link', translations.history.link_label);
        safeSetText('txt-hist-dl', translations.history.btn_download_again);
        safeSetText('txt-hist-del', translations.history.btn_delete_record);
        
        // Ссылку "Открыть в браузере" нужно обновлять аккуратно, чтобы не стереть href
        const linkEl = document.getElementById('hist-link');
        if(linkEl && translations.history.open_browser) {
            linkEl.innerText = translations.history.open_browser;
        } else {
            console.warn("Translation section 'history' is missing!");
        }
        
    }
    
    // Логи
    // Если лог пустой (только старт), можно обновить первую запись
    if (translations.logs) {
        safeSetText('event-log-title', translations.logs.tittle);
    }
    const logContainer = document.getElementById("app-logs");
    if (logContainer && logContainer.children.length === 1) {
        safeSetText('log-entry', translations.logs.app_ready);
    }
    
}
    