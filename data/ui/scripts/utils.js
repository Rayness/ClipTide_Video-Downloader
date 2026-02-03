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
const updateChannel = document.getElementById('update_channel');
if (updateChannel) {
    updateChannel.addEventListener('change', (e) => {
        if(window.pywebview.api.switch_update_channel) {
            window.pywebview.api.switch_update_channel(e.target.value);
        }
    });
}

function resizeWindow(event, direction) {
    // 1. Запрещаем браузеру выделять текст или тащить картинки
    event.preventDefault();
    
    // 2. Вызываем Python
    window.pywebview.api.resize_window(direction);
}

// === Настройки отображения ===

// Применение масштаба интерфейса с адаптацией скролла
window.applyUIScale = function(scale) {
    // Сохраняем позиции скролла всех скроллируемых контейнеров
    const scrollContainers = [
        document.querySelector('.settings-scroll-view'),
        document.querySelector('.queue-container'),
        document.querySelector('.converter-list'),
        document.getElementById('app-logs')
    ].filter(el => el);
    
    const scrollPositions = scrollContainers.map(el => ({
        element: el,
        scrollTop: el.scrollTop,
        scrollHeight: el.scrollHeight
    }));
    
    // Применяем zoom
    document.body.style.zoom = scale;
    
    // Восстанавливаем позиции скролла (пропорционально)
    requestAnimationFrame(() => {
        scrollPositions.forEach(({element, scrollTop, scrollHeight}) => {
            if (scrollHeight > 0) {
                const ratio = scrollTop / scrollHeight;
                element.scrollTop = ratio * element.scrollHeight;
            }
        });
    });
    
    // Сохраняем в localStorage для быстрого применения при старте
    localStorage.setItem('ui_scale', scale);
}

// Загрузка настроек отображения при старте
window.loadDisplaySettings = function(windowSize, uiScale) {
    // Размер окна
    const sizeSelect = document.getElementById('window-size');
    if (sizeSelect && windowSize) {
        sizeSelect.value = windowSize;
    }
    
    // Масштаб интерфейса
    const scaleSelect = document.getElementById('ui-scale');
    if (scaleSelect && uiScale) {
        scaleSelect.value = uiScale;
        applyUIScale(uiScale);
    }
    
    // Обновляем кастомные селекты если они инициализированы
    if (typeof refreshCustomSelectOptions === 'function') {
        refreshCustomSelectOptions();
    }
}

// Обработчики изменения настроек отображения
document.addEventListener('DOMContentLoaded', function() {
    const windowSizeSelect = document.getElementById('window-size');
    if (windowSizeSelect) {
        windowSizeSelect.addEventListener('change', function(e) {
            window.pywebview.api.switch_window_size(e.target.value);
        });
    }
    
    const uiScaleSelect = document.getElementById('ui-scale');
    if (uiScaleSelect) {
        uiScaleSelect.addEventListener('change', function(e) {
            window.pywebview.api.switch_ui_scale(e.target.value);
        });
    }
});

// Быстрое применение масштаба из localStorage (до загрузки Python)
(function() {
    const savedScale = localStorage.getItem('ui_scale');
    if (savedScale) {
        document.body.style.zoom = savedScale;
    }
})();