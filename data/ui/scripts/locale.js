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



// Функция для обновления текста интерфейса
window.updateTranslations = function(translations) {
    if (!translations) return; 

    window.i18n = translations;
    if (translations.settings) {
        // safeSetText('update__text', translations.settings.updates.update_text_ready);

        // safeSetText('10', translations.sections.setting);

        // Настройки //

        // Язык
        if (translations.settings.language) {
            safeSetText('language_settings_title', translations.settings.language.title);
            safeSetText('language_title', translations.settings.language.language);
            safeSetText('lang_ru', translations.settings.language.russian);
            safeSetText('lang_en', translations.settings.language.english);
            safeSetText('lang_pl', translations.settings.language.polish);
            safeSetText('lang_ja', translations.settings.language.japan);
            safeSetText('lang_ua', translations.settings.language.ukraine);
            safeSetText('lang_it', translations.settings.language.italian);
            safeSetText('lang_de', translations.settings.language.german);
            safeSetText('lang_fr', translations.settings.language.french);
            safeSetText('lang_cn', translations.settings.language.chinese);
            safeSetText('open_locale_folder', translations.settings.language.open_folder);
        }
        // Оформление

        if (translations.settings.subtitles) {
            safeSetText('subs-title', translations.settings.subtitles.title);
            safeSetText('lbl_subs_enable', translations.settings.subtitles.enable);
            safeSetText('lbl_subs_auto', translations.settings.subtitles.auto);
            safeSetText('lbl_subs_embed', translations.settings.subtitles.embed);
            safeSetText('lbl_subs_lang', translations.settings.subtitles.lang);
        }

        if (translations.settings.themes) {
            safeSetText('decorations-title', translations.settings.themes.decoration);
            safeSetText('theme-title', translations.settings.themes.theme);
            safeSetText('style-title', translations.settings.themes.style);
            safeSetText('themes-tooltip-open', translations.settings.themes.open_folder);
        }

        // Папки 
        if (translations.settings.folders) {
            safeSetText('folders-title', translations.settings.folders.title);
            safeSetText('download_folder_title', translations.settings.folders.placeholder_download);
            safeSetText('conversion_folder_title', translations.settings.folders.placeholder_conversion);

            safeSetText('download_tooltip_defoult', translations.settings.folders.by_defoult);
            safeSetText('download_tooltip_choose', translations.settings.folders.choose_download_folder);
            safeSetText('download_tooltip_open', translations.settings.folders.open_download_folder);

            safeSetText('conversion-tooltip_defoult', translations.settings.folders.by_defoult);
            safeSetText('conversion-tooltip_choose', translations.settings.folders.choose_converter_folder);
            safeSetText('conversion-tooltip_open', translations.settings.folders.open_converter_folder);
        }

        // Уведомления
        if (translations.settings.notifications) {
            safeSetText('notification-title', translations.settings.notifications.title);
            safeSetText('get_notifi_download', translations.settings.notifications.notifi_download);
            safeSetText('get_notifi_conversion', translations.settings.notifications.notifi_conversion);
        }

        // Прокси 
        if (translations.settings.proxys) {
            safeSetText('proxy-title', translations.settings.proxys.title);
            safeSetText('turn_on_proxy', translations.settings.proxys.turn_on);
        }

        // Обновления
        if (translations.settings.updates) {
            safeSetText('updates-title', translations.settings.updates.title);
            safeSetText('update', translations.settings.updates.update_button);
        }

        // О приложении
        if (translations.settings.about) {
            safeSetText('about-title', translations.settings.about.title);
            safeSetText('about-version', translations.settings.about.version);
            safeSetText('about-date', translations.settings.about.date);
        }

    }
        // Донат
        if (translations.donate) {
            safeSetText('donate-description', translations.donate.description);
        }

        // Основной функционал //
        // 
        // Загрузка видео

        const vidUrl = document.getElementById('videoUrl');
        if(vidUrl) vidUrl.placeholder = translations.video_URL || 'Enter video URL';

        // Конвертер
        if (translations.converter) {
            safeSetText('converter_add_video', translations.converter.click_for_add_video);
            safeSetText('convertion-settings', translations.converter.convertion_settings);
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

            safeSetText('cv-res-orig', translations.converter.cv_res_orig);
        
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
            }
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
};

function safeSetText(id, text) {
    const el = document.getElementById(id);
    if (el && text) el.innerText = text;
}

// Оставляем слушатель
const openLangBtn = document.getElementById('openLangFiles');
if(openLangBtn) {
    openLangBtn.addEventListener('click', ()=>{
        window.pywebview.api.open_locale_folder()
    });
}