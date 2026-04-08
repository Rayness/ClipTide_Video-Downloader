 /* Copyright (C) 2025 Rayness */
 /* This program is free software under GPLv3. See LICENSE for details. */

// --- CONVERTER LOGIC ---
const FILE_TYPES = {
    VIDEO: ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'],
    AUDIO: ['mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a'],
    IMAGE: ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'ico', 'heic', 'pdf'],
    DOC: ['docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt', 'odt', 'ods', 'odp', 'txt', 'rtf']
};

window.convSettingsMap = {};
let selectedConvId = null;

function getFileType(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (FILE_TYPES.VIDEO.includes(ext) || FILE_TYPES.AUDIO.includes(ext)) return 'video';
    if (FILE_TYPES.IMAGE.includes(ext)) return 'image';
    if (FILE_TYPES.DOC.includes(ext)) return 'document';
    return 'unknown';
}

function getDefaultSettings(type = 'video') {
    if (type === 'image') {
        return {
            type: 'image',
            format: document.getElementById('cv-img-format').value,
            quality: document.getElementById('cv-img-quality').value,
            resize: document.getElementById('cv-img-resize').value
        };
    } else if (type === 'document') {
        return {
            type: 'document',
            doc_format: document.getElementById('cv-doc-format').value
        } 
    } else {
        return {
            type: 'video',
            format: document.getElementById('cv-format').value,
            codec: document.getElementById('cv-codec').value,
            quality: document.getElementById('cv-quality').value,
            resolution: document.getElementById('cv-res').value
        };
    }
}

document.getElementById('dropZoneConv').addEventListener('click', () => {
    window.pywebview.api.converter_add_files();
});

window.createConverterSkeleton = function(tempId, filename) {
    const list = document.getElementById('converter-queue');
    const empty = document.getElementById('conv-empty-state');
    if (empty) empty.style.display = 'none';

    const li = document.createElement('li');
    li.id = `conv-skeleton-${tempId}`;
    li.className = 'conv-item conv-skeleton';
    li.innerHTML = `
        <div class="conv-item-top">
            <div class="skel-box skel-expand"></div>
            <div class="skel-box skel-thumb"></div>
            <div class="conv-info">
                <div class="skel-line skel-name"></div>
                <div class="skel-line skel-meta"></div>
            </div>
            <div class="skel-box skel-status"></div>
        </div>
    `;
    list.appendChild(li);
    updateFileCount();
};

window.removeConverterSkeleton = function(tempId) {
    const el = document.getElementById(`conv-skeleton-${tempId}`);
    if (el) el.remove();
    updateFileCount();
    const remaining = document.querySelectorAll('.conv-item').length;
    const empty = document.getElementById('conv-empty-state');
    if (empty && remaining === 0) empty.style.display = 'flex';
};

const TYPE_META = {
    video:    { icon: 'fa-film',        key: 'type_video',  cls: 'type-video' },
    audio:    { icon: 'fa-music',       key: 'type_audio',  cls: 'type-audio' },
    image:    { icon: 'fa-image',       key: 'type_image',  cls: 'type-image' },
    document: { icon: 'fa-file-lines',  key: 'type_doc',    cls: 'type-doc'   },
    unknown:  { icon: 'fa-file',        key: null,          cls: 'type-doc'   }
};

function updateFileCount() {
    const count = document.querySelectorAll('.conv-item').length;
    const badge = document.getElementById('conv-file-count');
    if (!badge) return;
    if (count === 0) { badge.textContent = ''; return; }
    const c = window.i18n?.converter || {};
    let word;
    if (count === 1) word = c.file_count_1 || 'file';
    else if (count >= 2 && count <= 4) word = c.file_count_234 || c.file_count_many || 'files';
    else word = c.file_count_many || 'files';
    badge.textContent = `${count} ${word}`;
}

window.addConverterItem = function(item) {
    const type = getFileType(item.filename);
    window.convSettingsMap[item.id] = getDefaultSettings(type);

    const t = window.i18n?.converter || {};
    const metaDef = TYPE_META[type] || TYPE_META.unknown;
    const meta = { ...metaDef, label: metaDef.key ? (t[metaDef.key] || metaDef.key) : '?' };

    const list = document.getElementById('converter-queue');

    // Заменяем скелетон, если он есть
    if (item.temp_id) {
        const skeleton = document.getElementById(`conv-skeleton-${item.temp_id}`);
        if (skeleton) skeleton.remove();
    }

    // Убрать пустое состояние при первом файле
    const empty = document.getElementById('conv-empty-state');
    if (empty) empty.style.display = 'none';

    const li = document.createElement('li');
    li.className = 'conv-item';
    li.id = `conv-item-${item.id}`;

    li.onclick = function(e) {
        if (e.target.closest('button')) return;
        selectConverterItem(item.id);
    };

    const thumbSrc = item.thumbnail || "src/default_thumbnail.png";
    const durationStr = item.duration ? formatDuration(item.duration) : '—';
    const d = item.details || {};
    const res = d.resolution && d.resolution !== '?' ? d.resolution : null;
    const codec = d.codec && d.codec !== '?' ? d.codec : null;
    const bitrate = d.bitrate ? d.bitrate + ' kbps' : null;
    const fps = d.fps ? d.fps + ' fps' : null;
    const audio = d.audio && d.audio !== '?' ? d.audio : null;
    const txtQueued = t.status_queued || 'В очереди';

    const ext = item.filename.split('.').pop().toUpperCase();

    li.innerHTML = `
        <div class="conv-item-top">
            <button class="btn-q-expand" onclick="toggleConvDetails('${item.id}')" title="Подробнее">
                <i class="fa-solid fa-chevron-down"></i>
            </button>

            <div class="conv-thumb-wrap">
                <img src="${thumbSrc}" class="conv-thumb" onerror="this.src='src/default_thumbnail.png'">
                <span class="conv-ext-badge">${ext}</span>
            </div>

            <div class="conv-info">
                <div class="conv-filename" title="${item.filename}">${item.filename}</div>
                <div class="conv-meta">
                    ${item.duration ? `<span><i class="fa-regular fa-clock"></i> ${durationStr}</span>` : ''}
                    ${res ? `<span><i class="fa-solid fa-display"></i> ${res}</span>` : ''}
                    <span class="conv-type-badge ${meta.cls}"><i class="fa-solid ${meta.icon}"></i> ${meta.label}</span>
                </div>
            </div>

            <div class="conv-status queued" id="conv-status-${item.id}">${txtQueued}</div>

            <button class="conv-remove-btn" onclick="removeConverterItem('${item.id}')" title="Убрать">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>

        <div class="conv-details">
            ${res     ? `<div class="detail-row"><span class="detail-label"><i class="fa-solid fa-expand"></i> ${t.detail_res || 'Resolution'}</span><span>${res}</span></div>` : ''}
            ${codec   ? `<div class="detail-row"><span class="detail-label"><i class="fa-solid fa-microchip"></i> ${t.detail_codec || 'Codec'}</span><span>${codec}</span></div>` : ''}
            ${bitrate ? `<div class="detail-row"><span class="detail-label"><i class="fa-solid fa-gauge-high"></i> ${t.detail_bitrate || 'Bitrate'}</span><span>${bitrate}</span></div>` : ''}
            ${fps     ? `<div class="detail-row"><span class="detail-label"><i class="fa-solid fa-film"></i> ${t.detail_fps || 'FPS'}</span><span>${fps}</span></div>` : ''}
            ${audio   ? `<div class="detail-row"><span class="detail-label"><i class="fa-solid fa-volume-high"></i> ${t.detail_audio || 'Audio'}</span><span>${audio}</span></div>` : ''}
            ${!res && !codec && !bitrate && !fps && !audio ? `<div class="detail-row" style="color:#666;">${t.no_metadata || 'Metadata unavailable'}</div>` : ''}
        </div>

        <div class="conv-progress-bg">
            <div class="conv-progress-fill" id="conv-prog-${item.id}"></div>
        </div>
    `;
    list.appendChild(li);
    updateFileCount();
}

function selectConverterItem(id) {
    const prev = document.querySelector('.conv-item.selected');
    if (prev) prev.classList.remove('selected');

    if (selectedConvId === id) {
        selectedConvId = null;
        updateSidebarUI(null);
        return;
    }

    selectedConvId = id;
    const curr = document.getElementById(`conv-item-${id}`);
    if (curr) curr.classList.add('selected');

    const settings = window.convSettingsMap[id];
    updateSidebarUI(settings, id);
}

function updateSidebarUI(settings, id) {
    const title = document.getElementById('setting-header-title');
    const btnApplyAll = document.getElementById('btn-apply-all');
    const videoBlock = document.getElementById('settings-video');
    const imageBlock = document.getElementById('settings-image');
    const docBlock = document.getElementById('settings-document');

    if (id && settings) {
        const filename = document.getElementById(`conv-item-${id}`).querySelector('.conv-filename').innerText;
        title.innerText = filename;
        title.title = filename;
        btnApplyAll.style.display = 'block';
        btnApplyAll.title = window.i18n.converter?.apply_all_btn || "Apply to all";
        setInputValues(settings);
    } else {
        title.innerText = window.i18n.converter?.global_settings || "Global settings";
        btnApplyAll.style.display = 'none';
    }

    let type = 'video';
    if (settings && settings.type) type = settings.type;
    else if (id) {
        const filename = document.getElementById(`conv-item-${id}`).querySelector('.conv-filename').innerText;
        type = getFileType(filename);
    }

    videoBlock.style.display = 'none';
    imageBlock.style.display = 'none';
    docBlock.style.display = 'none';

    if (type === 'image') {
        imageBlock.style.display = 'flex'; 
        imageBlock.style.flexDirection = 'column';
        imageBlock.style.gap = '1rem';
        if (settings) setImageInputValues(settings);
    } else if (type === 'document') {
        docBlock.style.display = 'flex';
        docBlock.style.flexDirection = 'column';
        docBlock.style.gap = '1rem';
        if (settings) document.getElementById('cv-doc-format').value = settings.doc_format;
    } else {
        videoBlock.style.display = 'flex';
        videoBlock.style.flexDirection = 'column';
        videoBlock.style.gap = '1rem';
        if (settings) setInputValues(settings);
    }
}

function setInputValues(s) {
    document.getElementById('cv-format').value = s.format;
    document.getElementById('cv-codec').value = s.codec;
    document.getElementById('cv-quality').value = s.quality;
    document.getElementById('cv-quality-val').innerText = s.quality + '%'
    document.getElementById('cv-res').value = s.resolution;
}

function setImageInputValues(s) {
    document.getElementById('cv-img-format').value = s.format;
    document.getElementById('cv-img-quality').value = s.quality;
    document.getElementById('cv-img-quality-val').innerText = s.quality + '%';
    document.getElementById('cv-img-resize').value = s.resize;
}

// Обновление настроек
function updateSettingsInMap(field, value, targetType) {
    if (selectedConvId) {
        window.convSettingsMap[selectedConvId][field] = value;
        if (field === 'doc_format') window.convSettingsMap[selectedConvId].type = 'document';
    } else {
        for (const [id, settings] of Object.entries(window.convSettingsMap)) {
            if (targetType === 'video' && settings.type === 'video') settings[field] = value;
            else if (targetType === 'image' && settings.type === 'image') settings[field] = value;
            else if (targetType === 'document' && settings.type === 'document') settings[field] = value;
        }
    }
}

function getInputValue(id) {
    return document.getElementById(id).value;
}

// Слушатели инпутов
const videoInputs = ['cv-format', 'cv-codec', 'cv-quality', 'cv-res'];
videoInputs.forEach(id => {
    const el = document.getElementById(id);
    if(!el) return;
    
    // Слушаем и change, и input для надежности
    ['input', 'change'].forEach(evtType => {
        el.addEventListener(evtType, (e) => {
            // ВАЖНО: Берем значение напрямую из элемента, а не из ивента
            const val = getInputValue(id);
            const field = id.replace('cv-', '').replace('res', 'resolution');
            
            console.log(`Setting ${field} to ${val}`); // Debug в консоль браузера (F12)
            updateSettingsInMap(field, val, 'video');
        });
    });
});

// Слушатели для ИЗОБРАЖЕНИЙ
const imageInputs = ['cv-img-format', 'cv-img-quality', 'cv-img-resize'];
imageInputs.forEach(id => {
    const el = document.getElementById(id);
    if(!el) return;
    
    ['input', 'change'].forEach(evtType => {
        el.addEventListener(evtType, (e) => {
            const val = getInputValue(id);
            const field = id.replace('cv-img-', '');
            
            console.log(`Setting IMG ${field} to ${val}`);
            updateSettingsInMap(field, val, 'image');
            
            if (id === 'cv-img-quality') {
                document.getElementById('cv-img-quality-val').innerText = val + '%';
            }
        });
    });
});

// Слушатель для ДОКУМЕНТОВ
const docInput = document.getElementById('cv-doc-format');
if(docInput) {
    ['input', 'change'].forEach(evtType => {
        docInput.addEventListener(evtType, (e) => {
            const val = getInputValue('cv-doc-format');
            updateSettingsInMap('doc_format', val, 'document');
        });
    });
}

// Кнопка Применить ко всем
document.getElementById('btn-apply-all').addEventListener('click', () => {
    if (!selectedConvId) return;
    const currentSettings = window.convSettingsMap[selectedConvId];
    const currentType = currentSettings.type;
    for (let key in window.convSettingsMap) {
        if (window.convSettingsMap[key].type === currentType) {
            window.convSettingsMap[key] = { ...currentSettings };
        }
    }
    alert(window.i18n?.converter?.apply_all_toast || "Settings applied");
});

document.getElementById('cv-quality').addEventListener('input', (e) => {
    document.getElementById('cv-quality-val').innerText = e.target.value;
});

// Старт
// Старт конвертации
document.getElementById('btn-convert-start').addEventListener('click', () => {
    const btnStart = document.getElementById('btn-convert-start');
    const btnStop = document.getElementById('btn-convert-stop');
    
    // === FIX: ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ ПЕРЕД СТАРТОМ ===
    // Считываем то, что сейчас реально выбрано в селектах
    const currentVideoSettings = {
        format: document.getElementById('cv-format').value,
        codec: document.getElementById('cv-codec').value,
        quality: document.getElementById('cv-quality').value,
        resolution: document.getElementById('cv-res').value
    };
    
    const currentImageSettings = {
        format: document.getElementById('cv-img-format').value,
        quality: document.getElementById('cv-img-quality').value,
        resize: document.getElementById('cv-img-resize').value
    };

    const currentDocSettings = {
        doc_format: document.getElementById('cv-doc-format') ? document.getElementById('cv-doc-format').value : 'pdf'
    };

    // Применяем эти настройки к файлам
    // Если выбран конкретный файл - обновляем его.
    // Если глобальный режим - обновляем все файлы соответствующего типа.
    
    if (selectedConvId) {
        // Обновляем выделенный файл
        const type = window.convSettingsMap[selectedConvId].type;
        if (type === 'video') Object.assign(window.convSettingsMap[selectedConvId], currentVideoSettings);
        else if (type === 'image') Object.assign(window.convSettingsMap[selectedConvId], currentImageSettings);
        else if (type === 'document') Object.assign(window.convSettingsMap[selectedConvId], currentDocSettings);
    } else {
        // Глобальный режим: обновляем вообще все файлы в очереди согласно их типам
        // Это гарантирует, что настройки применятся, даже если событие change не сработало
        for (const [id, settings] of Object.entries(window.convSettingsMap)) {
            if (settings.type === 'video') {
                Object.assign(settings, currentVideoSettings);
            } else if (settings.type === 'image') {
                Object.assign(settings, currentImageSettings);
            } else if (settings.type === 'document') {
                Object.assign(settings, currentDocSettings);
            }
        }
    }
    // ====================================================

    // Собираем активные настройки (фильтруем удаленные)
    const activeSettings = {};
    document.querySelectorAll('.conv-item').forEach(li => {
        const id = li.id.replace('conv-item-', '');
        if (window.convSettingsMap[id]) {
            activeSettings[id] = window.convSettingsMap[id];
        }
    });

    console.log("Sending settings to Python:", activeSettings); // Для проверки в консоли

    window.pywebview.api.converter_start(activeSettings);
    btnStart.disabled = true;
    btnStop.disabled = false;
});

// Удаление
window.removeConverterItem = function(taskId) {
    const el = document.getElementById(`conv-item-${taskId}`);
    if (el) el.remove();
    delete window.convSettingsMap[taskId];
    if (selectedConvId === taskId) {
        selectedConvId = null;
        updateSidebarUI(null);
    }
    window.pywebview.api.converter_remove_item(taskId);
    updateFileCount();
    const remaining = document.querySelectorAll('.conv-item').length;
    const empty = document.getElementById('conv-empty-state');
    if (empty && remaining === 0) empty.style.display = 'flex';
}

window.toggleConvDetails = function(taskId) {
    const item = document.getElementById(`conv-item-${taskId}`);
    if (item) item.classList.toggle('expanded');
}

window.updateConvStatus = function(taskId, text, percent) {
    const statusEl = document.getElementById(`conv-status-${taskId}`);
    const progEl = document.getElementById(`conv-prog-${taskId}`);
    const item = document.getElementById(`conv-item-${taskId}`);
    if (statusEl) {
        statusEl.innerText = text;
        statusEl.className = 'conv-status';
        if (percent >= 100) {
            statusEl.classList.add('done');
            if (item) item.classList.add('done');
        } else if (percent > 0) {
            statusEl.classList.add('converting');
        } else if (text.toLowerCase().includes('ошибк') || text.toLowerCase().includes('error')) {
            statusEl.classList.add('error');
        } else {
            statusEl.classList.add('queued');
        }
    }
    if (progEl) progEl.style.width = `${percent}%`;
}

document.getElementById('btn-convert-stop').addEventListener('click', () => {
    window.pywebview.api.converter_stop();
});

window.conversionFinished = function() {
    document.getElementById('btn-convert-start').disabled = false;
    document.getElementById('btn-convert-stop').disabled = true;
}

// Видео настройки (блокировка кодеков для аудио)
document.getElementById('cv-format').addEventListener('change', (e) => {
    const fmt = e.target.value;
    const codecSel = document.getElementById('cv-codec');
    const resSel = document.getElementById('cv-res');
    
    if (['mp3', 'aac', 'wav'].includes(fmt)) {
        codecSel.disabled = true;
        resSel.disabled = true;
    } else {
        codecSel.disabled = false;
        resSel.disabled = false;
    }
});