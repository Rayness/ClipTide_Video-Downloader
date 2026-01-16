 /* Copyright (C) 2025 Rayness */
 /* This program is free software under GPLv3. See LICENSE for details. */

document.getElementById('switch_openDownloadFolder').addEventListener('change', function () {
    const checkbox = document.getElementById('switch_openDownloadFolder');

    if (checkbox.checked) {
        window.pywebview.api.switch_open_folder_dl("dl" ,"True");
    } else {
        window.pywebview.api.switch_open_folder_dl("dl", "False");
    }
});

document.getElementById('switch_openConverterFolder').addEventListener('change', function () {
    const checkbox = document.getElementById('switch_openConverterFolder');

    if (checkbox.checked) {
        window.pywebview.api.switch_open_folder_dl("cv" ,"True");
    } else {
        window.pywebview.api.switch_open_folder_dl("cv", "False");
    }
});

window.loadopenfolders = function(enabled_dl, enabled_cv){
    const checkbox_dl = document.getElementById('switch_openDownloadFolder');
    const checkbox_cv = document.getElementById('switch_openConverterFolder');

    if (enabled_dl == "True") {
        checkbox_dl.checked = true
    } else {
        checkbox_dl.checked = false
    };

    if (enabled_cv == "True") {
        checkbox_cv.checked = true
    } else {
        checkbox_cv.checked = false
    }
}

window.removePreloader = function() {
    const preloader = document.getElementById('app-preloader');
    if (preloader) {
        preloader.classList.add('hidden');
        
        // Удаляем из DOM через секунду, чтобы не мешал
        setTimeout(() => {
            preloader.remove();
        }, 1000);
    }
}

// Загрузка настроек субтитров при старте
window.loadSubtitlesSettings = function(enabled, auto, embed, lang) {
    document.getElementById('switch_subs_enable').checked = (enabled === "True");
    document.getElementById('switch_subs_auto').checked = (auto === "True");
    document.getElementById('switch_subs_embed').checked = (embed === "True");
    document.getElementById('subs_language').value = lang;
    
    // Обновляем кастомный селект, если он инициализирован
    if(typeof refreshCustomSelectOptions === 'function') refreshCustomSelectOptions();
}

// Слушатели
document.getElementById('switch_subs_enable').addEventListener('change', (e) => {
    window.pywebview.api.switch_subs_setting("enabled", e.target.checked ? "True" : "False");
});
document.getElementById('switch_subs_auto').addEventListener('change', (e) => {
    window.pywebview.api.switch_subs_setting("auto", e.target.checked ? "True" : "False");
});
document.getElementById('switch_subs_embed').addEventListener('change', (e) => {
    window.pywebview.api.switch_subs_setting("embed", e.target.checked ? "True" : "False");
});
document.getElementById('subs_language').addEventListener('change', (e) => {
    window.pywebview.api.switch_subs_setting("langs", e.target.value);
});

// Аудио
window.loadAudioSettings = function(lang) {
    document.getElementById('audio_language').value = lang;
    if(typeof refreshCustomSelectOptions === 'function') refreshCustomSelectOptions();
}

document.getElementById('audio_language').addEventListener('change', (e) => {
    window.pywebview.api.switch_audio_setting("lang", e.target.value);
});

// Загрузка
window.loadUpdateSettings = function(channel) {
    const sel = document.getElementById('update_channel');
    if(sel) {
        sel.value = channel;
        if(typeof refreshCustomSelectOptions === 'function') refreshCustomSelectOptions();
    }
}

// Сохранение
document.getElementById('update_channel').addEventListener('change', (e) => {
    // Создай метод switch_update_channel в Python
    window.pywebview.api.switch_update_channel(e.target.value);
});