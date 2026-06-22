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

document.getElementById('switch_openEditorFolder').addEventListener('change', function () {
    const val = this.checked ? "True" : "False";
    window.pywebview.api.switch_open_folder_dl("editor", val);
});

window.loadopenfolders = function(enabled_dl, enabled_cv, enabled_editor){
    const checkbox_dl     = document.getElementById('switch_openDownloadFolder');
    const checkbox_cv     = document.getElementById('switch_openConverterFolder');
    const checkbox_editor = document.getElementById('switch_openEditorFolder');

    if (checkbox_dl)     checkbox_dl.checked     = (enabled_dl     == "True");
    if (checkbox_cv)     checkbox_cv.checked     = (enabled_cv     == "True");
    if (checkbox_editor) checkbox_editor.checked = (enabled_editor == "True");
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

// Загрузка настроек канала обновлений
window.loadUpdateSettings = function(channel) {
    const sel = document.getElementById('update_channel');
    if(sel) {
        sel.value = channel;
        if(typeof refreshCustomSelectOptions === 'function') refreshCustomSelectOptions();
    }
    // При загрузке сразу проверяем обновления для текущего канала
    setTimeout(() => {
        if(window.pywebview && window.pywebview.api && window.pywebview.api.check_update_for_channel) {
            window.pywebview.api.check_update_for_channel(channel);
        }
    }, 500);
}

// Сохранение + проверка обновлений при смене канала
const updateChannel = document.getElementById('update_channel');
if (updateChannel) {
    updateChannel.addEventListener('change', (e) => {
        const channel = e.target.value;
        if(window.pywebview.api.switch_update_channel) {
            window.pywebview.api.switch_update_channel(channel);
        }
        // Сразу проверяем обновления для нового канала
        if(window.pywebview.api.check_update_for_channel) {
            window.pywebview.api.check_update_for_channel(channel);
        }
    });
}

// --- Обработка результатов проверки обновлений по каналу ---

function getUpdatesTranslations() {
    return window.i18n?.settings?.updates || {};
}

window.onChannelCheckStart = function() {
    const spinner = document.getElementById('channel-check-spinner');
    const result = document.getElementById('channel-check-result');
    const loadingText = document.getElementById('channel-check-loading-text');
    const t = getUpdatesTranslations();

    if (loadingText) {
        loadingText.textContent = t.checking_text || 'Checking...';
    }
    if(spinner) spinner.style.display = 'flex';
    if(result) result.style.display = 'none';
}

window.onChannelCheckResult = function(data) {
    const spinner = document.getElementById('channel-check-spinner');
    const resultEl = document.getElementById('channel-check-result');
    const patchnotesContent = document.getElementById('patchnotes-content');

    if(spinner) spinner.style.display = 'none';
    if(!resultEl) return;

    resultEl.style.display = 'block';
    const t = getUpdatesTranslations();

    if(data.error) {
        resultEl.className = 'channel-result channel-result--error';
        resultEl.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> ' +
            '<span>' + (t.check_error_prefix || 'Check error:') + ' ' + data.message + '</span>';
        return;
    }

    if(data.has_update) {
        resultEl.className = 'channel-result channel-result--available';
        resultEl.innerHTML = '<i class="fa-solid fa-circle-up"></i> ' +
            '<span>' + (t.available_prefix || 'Version available') + ' <strong>' + data.latest_version + '</strong> (' + data.channel + ')</span>';
    } else {
        resultEl.className = 'channel-result channel-result--latest';
        resultEl.innerHTML = '<i class="fa-solid fa-circle-check"></i> ' +
            '<span>' + (t.latest_installed || 'Latest version is installed') + ' (' + data.channel + ')</span>';
    }

    // Обновляем патчноут
    if(patchnotesContent && data.description) {
        const lines = data.description.split(/[.;]/).filter(s => s.trim());
        if(lines.length > 1) {
            let html = '<ul class="patchnotes-list">';
            lines.forEach(line => {
                const trimmed = line.trim();
                if(trimmed) html += '<li>' + trimmed + '</li>';
            });
            html += '</ul>';
            patchnotesContent.innerHTML = html;
        } else {
            patchnotesContent.innerHTML = '<p class="patchnotes-text">' + data.description + '</p>';
        }

        // Показываем для какой версии патчноут
        const titleEl = document.getElementById('patchnotes-title');
        if(titleEl) {
            const channelLabel = data.channel === 'dev'
                ? (t.dev_label || 'Dev')
                : (t.stable_label || 'Stable');
            if(data.has_update) {
                titleEl.textContent = (t.patchnotes_title_latest || 'What is new in') + ' ' + data.latest_version + ' (' + channelLabel + ')';
            } else {
                titleEl.textContent = (t.patchnotes_title_current || 'Current version notes') + ' (' + channelLabel + ')';
            }
        }
    }
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

// === Настройки редактора ===

window.loadEditorSettings = function(codec, preset, crf, format, openFolder) {
    const codecSel   = document.getElementById('editor-export-codec');
    const presetSel  = document.getElementById('editor-export-preset');
    const crfSlider  = document.getElementById('editor-export-crf');
    const crfVal     = document.getElementById('editor-crf-val');
    const formatSel  = document.getElementById('editor-export-format');
    const openFolderCb = document.getElementById('switch_openEditorFolder');

    if (codecSel)  codecSel.value  = codec;
    if (presetSel) presetSel.value = preset;
    if (crfSlider) { crfSlider.value = crf; if (crfVal) crfVal.textContent = crf; }
    if (formatSel) formatSel.value = format;
    if (openFolderCb) openFolderCb.checked = (openFolder === "True" || openFolder === true);

    _editorUpdateCodecOptions(codec);
    if (typeof refreshCustomSelectOptions === 'function') refreshCustomSelectOptions();
};

function _editorUpdateCodecOptions(codec) {
    const opts = document.getElementById('editor-codec-options');
    if (opts) opts.style.display = (codec === 'copy') ? 'none' : '';
}

document.addEventListener('DOMContentLoaded', function() {
    const codecSel  = document.getElementById('editor-export-codec');
    const presetSel = document.getElementById('editor-export-preset');
    const crfSlider = document.getElementById('editor-export-crf');
    const formatSel = document.getElementById('editor-export-format');
    const openFolderCb = document.getElementById('switch_openEditorFolder');

    if (codecSel) {
        codecSel.addEventListener('change', function() {
            window.pywebview.api.switch_editor_setting('codec', this.value);
            _editorUpdateCodecOptions(this.value);
        });
    }
    if (presetSel) {
        presetSel.addEventListener('change', function() {
            window.pywebview.api.switch_editor_setting('preset', this.value);
        });
    }
    if (crfSlider) {
        crfSlider.addEventListener('input', function() {
            const val = document.getElementById('editor-crf-val');
            if (val) val.textContent = this.value;
        });
        crfSlider.addEventListener('change', function() {
            window.pywebview.api.switch_editor_setting('crf', this.value);
        });
    }
    if (formatSel) {
        formatSel.addEventListener('change', function() {
            window.pywebview.api.switch_editor_setting('format', this.value);
        });
    }
    if (openFolderCb) {
        openFolderCb.addEventListener('change', function() {
            window.pywebview.api.switch_open_folder_dl('editor', this.checked ? 'True' : 'False');
        });
    }
});