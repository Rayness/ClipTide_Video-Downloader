//  Copyright (C) 2025 Rayness
//  This program is free software under GPLv3. See LICENSE for details.

// --- Инициализация и Вкладки ---
document.addEventListener('DOMContentLoaded', function() {
    window.isDomReady = true;
    const buttons = document.querySelectorAll('.tab-btn');
    const blocks = document.querySelectorAll('.content');
    const name = document.getElementById('name');
    
    const stopBtnConv = document.getElementById("stopBtn_conv");
    if(stopBtnConv) stopBtnConv.disabled = true;
    
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            buttons.forEach(btn => btn.classList.remove('active'));
            blocks.forEach(block => block.classList.remove('active'));
            
            this.classList.add('active');
            
            const tabId = this.getAttribute('data-tab');
            const block = document.getElementById(tabId)
            if(block) {
                block.classList.add('active');
                if(name) name.textContent = block.getAttribute('data-status');
            }
        });
    });
    
    if(buttons.length > 0) buttons[0].click();
});



// --- CONVERTER NEW LOGIC ---
const FILE_TYPES = {
    VIDEO: ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'],
    AUDIO: ['mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a'],
    IMAGE: ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'ico', 'heic', 'pdf'],
    DOC: ['docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt', 'odt', 'ods', 'odp', 'txt', 'rtf']
};
// Хранилище индивидуальных настроек: { "task-id": { format: 'mp4', ... } }
window.convSettingsMap = {};

// Текущий выделенный ID (null = глобальный режим)
let selectedConvId = null;

function getFileType(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (FILE_TYPES.VIDEO.includes(ext) || FILE_TYPES.AUDIO.includes(ext)) return 'video';
    if (FILE_TYPES.IMAGE.includes(ext)) return 'image';
    if (FILE_TYPES.DOC.includes(ext)) return 'document';
    return 'unknown';
}


// Дефолтные настройки (значения инпутов при старте)
function getDefaultSettings(type = 'video') {
    if (type === 'image') {
        return {
            type: 'image', // Метка для Python
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
            type: 'video', // Метка для Python
            format: document.getElementById('cv-format').value,
            codec: document.getElementById('cv-codec').value,
            quality: document.getElementById('cv-quality').value,
            resolution: document.getElementById('cv-res').value
        };
    }
}

// 1. Кнопка "Добавить файлы"
document.getElementById('dropZoneConv').addEventListener('click', () => {
    window.pywebview.api.converter_add_files();
});

// 2. Добавление элемента (вызывается из Python)
window.addConverterItem = function(item) {
    // Сохраняем дефолтные настройки для нового файла
    const type = getFileType(item.filename);
    window.convSettingsMap[item.id] = getDefaultSettings(type);

    const list = document.getElementById('converter-queue');
    const li = document.createElement('li');
    li.className = 'conv-item';
    li.id = `conv-item-${item.id}`;
    
    // Добавляем обработчик клика для выделения (кроме кликов по кнопкам внутри)
    li.onclick = function(e) {
        // Если кликнули по кнопке удаления или раскрытия - не выделяем
        if (e.target.closest('button')) return;
        selectConverterItem(item.id);
    };

    let thumbSrc = item.thumbnail || "src/default_thumbnail.png";
    if (type === 'image' && item.thumbnail) {
        thumbSrc = item.thumbnail;
    }
    const durationStr = formatDuration(item.duration);
    const d = item.details || { resolution: '?', codec: '?', bitrate: 0, fps: 0, audio: '?' };
    const txtQueued = window.i18n.converter?.status_queued || 'Queued';

    li.innerHTML = `
        <div class="conv-item-top">
            <button class="btn-expand" onclick="toggleConvDetails('${item.id}')">
                <i class="fa-solid fa-chevron-down"></i>
            </button>
            <img src="${thumbSrc}" class="conv-thumb">
            <div class="conv-info">
                <div class="conv-filename" title="${item.filename}">${item.filename}</div>
                <div class="conv-meta"><i class="fa-regular fa-clock"></i> ${durationStr}</div>
            </div>
            <div class="conv-status" id="conv-status-${item.id}">${txtQueued}</div>
            <button class="delete-button" onclick="removeConverterItem('${item.id}')">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="conv-details">
            <div class="detail-row"><span class="detail-label">Res:</span> <span>${d.resolution}</span></div>
            <div class="detail-row"><span class="detail-label">Codec:</span> <span>${d.codec}</span></div>
            <div class="detail-row"><span class="detail-label">Bitrate:</span> <span>${d.bitrate} kbps</span></div>
            <div class="detail-row" style="grid-column: span 2;">
                <span class="detail-label">Audio:</span> <span>${d.audio}</span>
            </div>
        </div>
        <div class="conv-progress-bg">
            <div class="conv-progress-fill" id="conv-prog-${item.id}"></div>
        </div>
    `;
    list.appendChild(li);
}

// 3. Логика выделения
function selectConverterItem(id) {
    // Снимаем выделение с прошлого
    const prev = document.querySelector('.conv-item.selected');
    if (prev) prev.classList.remove('selected');

    // Если кликнули на тот же самый - снимаем выделение (возврат к глобальным)
    if (selectedConvId === id) {
        selectedConvId = null;
        updateSidebarUI(null);
        return;
    }

    // Выделяем новый
    selectedConvId = id;
    const curr = document.getElementById(`conv-item-${id}`);
    if (curr) curr.classList.add('selected');

    // Загружаем настройки этого файла в сайдбар
    const settings = window.convSettingsMap[id];
    updateSidebarUI(settings, id);
}

// Обновление инпутов сайдбара
function updateSidebarUI(settings, id) {
    const title = document.getElementById('setting-header-title');
    const btnApplyAll = document.getElementById('btn-apply-all');
    const videoBlock = document.getElementById('settings-video');
    const imageBlock = document.getElementById('settings-image');
    const docBlock = document.getElementById('settings-document');

    if (id && settings) {
        // Режим файла
        const filename = document.getElementById(`conv-item-${id}`).querySelector('.conv-filename').innerText;
        title.innerText = filename;
        title.title = filename; // тултип для длинных имен
        btnApplyAll.style.display = 'block'; // Показываем кнопку "Применить ко всем"
        btnApplyAll.title = window.i18n.converter?.apply_all_btn || "Apply to all";

        // Устанавливаем значения
        setInputValues(settings);
    } else {
        // Глобальный режим (показывать текущие значения инпутов или дефолт?)
        // Оставим как есть, просто сменим заголовок
        title.innerText = window.i18n.converter?.global_settings || "Global settings";
        btnApplyAll.style.display = 'none';
    }

    let type = 'video';
    if (settings && settings.type) {
        type = settings.type;
    } else if (id) {
        // Пытаемся определить по файлу
        const filename = document.getElementById(`conv-item-${id}`).querySelector('.conv-filename').innerText;
        type = getFileType(filename);
    }

    videoBlock.style.display = 'none';
    imageBlock.style.display = 'none';
    docBlock.style.display = 'none';

    if (type === 'image') {
        imageBlock.style.display = 'block';
        if (settings) setImageInputValues(settings);
    } else if (type === 'document') {
        docBlock.style.display = 'block';
        if (settings) {
            document.getElementById('cv-doc-format').value = settings.doc_format;
        }
    } else {
        videoBlock.style.display = 'block';
        if (settings) setInputValues(settings); // Старая функция для видео
    }

    // Триггерим событие change для обновления зависимостей (mp3 -> disabled codec)
    document.getElementById('cv-format').dispatchEvent(new Event('change'));
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

document.getElementById('cv-doc-format').addEventListener('input', (e) => {
    if (selectedConvId) {
        window.convSettingsMap[selectedConvId].doc_format = e.target.value;
        window.convSettingsMap[selectedConvId].type = 'document';
    }
});

// 4. Слушатели изменений в инпутах
const inputs = ['cv-format', 'cv-codec', 'cv-quality', 'cv-res'];
inputs.forEach(id => {
    document.getElementById(id).addEventListener('input', (e) => {
        // Если выбран файл - сохраняем в его настройки
        if (selectedConvId) {
            const field = id.replace('cv-', '').replace('res', 'resolution'); // маппинг id -> key
            window.convSettingsMap[selectedConvId][field] = e.target.value;
        } else {
            // Если ничего не выбрано - обновляем все настройки глобально? 
            // Или просто оставляем инпуты как "шаблон" для новых файлов.
            // Давай сделаем так: изменение глобальных настроек НЕ меняет уже добавленные файлы,
            // но меняет "шаблон" для будущих.
        }
    });
});

// Слушатели для НОВЫХ инпутов
['cv-img-format', 'cv-img-quality', 'cv-img-resize'].forEach(id => {
    document.getElementById(id).addEventListener('input', (e) => {
        if (selectedConvId) {
            // Убираем префикс cv-img-
            const field = id.replace('cv-img-', '');
            window.convSettingsMap[selectedConvId][field] = e.target.value;
            // Не забываем обновить тип, если вдруг он потерялся
            window.convSettingsMap[selectedConvId].type = 'image';
        }
        
        // Обновляем текст ползунка
        if (id === 'cv-img-quality') {
            document.getElementById('cv-img-quality-val').innerText = e.target.value + '%';
        }
    });
});

// Ползунок качества (визуал)
document.getElementById('cv-quality').addEventListener('input', (e) => {
    document.getElementById('cv-quality-val').innerText = e.target.value;
});

// Кнопка "Применить ко всем"
document.getElementById('btn-apply-all').addEventListener('click', () => {
    if (!selectedConvId) return;
    const currentSettings = window.convSettingsMap[selectedConvId];
    
    // Копируем во все остальные
    for (let key in window.convSettingsMap) {
        window.convSettingsMap[key] = { ...currentSettings };
    }
    alert("Настройки применены ко всем файлам в очереди");
});

// 5. Старт конвертации
document.getElementById('btn-convert-start').addEventListener('click', () => {
    const btnStart = document.getElementById('btn-convert-start');
    const btnStop = document.getElementById('btn-convert-stop');
    
    // Собираем карту настроек, но фильтруем удаленные файлы
    // (на случай если в map остались мусорные данные)
    const activeSettings = {};
    const listItems = document.querySelectorAll('.conv-item');
    listItems.forEach(li => {
        const id = li.id.replace('conv-item-', '');
        if (window.convSettingsMap[id]) {
            activeSettings[id] = window.convSettingsMap[id];
        }
    });

    // Отправляем ВСЮ карту настроек в Python
    // Python должен обновить свою очередь
    window.pywebview.api.converter_start(activeSettings);

    btnStart.disabled = true;
    btnStop.disabled = false;
});

// 6. Удаление
window.removeConverterItem = function(taskId) {
    const el = document.getElementById(`conv-item-${taskId}`);
    if(el) el.remove();
    delete window.convSettingsMap[taskId]; // Чистим память
    
    if (selectedConvId === taskId) {
        selectedConvId = null;
        updateSidebarUI(null);
    }
    
    window.pywebview.api.converter_remove_item(taskId);
}

// ... Оставляем toggleConvDetails и updateConvStatus из прошлого ответа ...
window.toggleConvDetails = function(taskId) {
    const item = document.getElementById(`conv-item-${taskId}`);
    if (item) item.classList.toggle('expanded');
}

window.updateConvStatus = function(taskId, text, percent) {
    const statusEl = document.getElementById(`conv-status-${taskId}`);
    const progEl = document.getElementById(`conv-prog-${taskId}`);
    if(statusEl) statusEl.innerText = text;
    if(progEl) progEl.style.width = `${percent}%`;
}

document.getElementById('btn-convert-stop').addEventListener('click', () => {
    window.pywebview.api.converter_stop();
});

window.conversionFinished = function() {
    document.getElementById('btn-convert-start').disabled = false;
    document.getElementById('btn-convert-stop').disabled = true;
}

// Блокировка форматов
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




// --- Downloader Logic ---

// Кнопка "Добавить в очередь"
document.getElementById('addBtn').addEventListener('click', function() {
    const videoUrl = document.getElementById('videoUrl').value;
    const selectedFormat = document.getElementById('format').value;
    const selectedResolution = document.getElementById('resolution').value;

    if (!videoUrl) {
        // Желательно добавить красивый тост/алерт
        return;
    }
    
    // Генерируем временный ID
    const tempId = Date.now().toString();
    
    // 1. Сразу показываем заглушку
    createLoadingItem(tempId);

    // 2. Отправляем запрос в Python (вместе с tempId)
    // Обрати внимание: теперь 4 аргумента
    window.pywebview.api.addVideoToQueue(videoUrl, selectedFormat, selectedResolution, tempId)
        .catch(() => {
            // Если сам вызов API упал
            removeLoadingItem(tempId);
            document.getElementById('status').innerHTML = 'API Error';
        });
        
    document.getElementById('videoUrl').value = '';
});


// Кнопка "Начать загрузку"
document.getElementById('startBtn').addEventListener('click', function() {
    window.pywebview.api.startDownload();
});

// Кнопка "Остановить загрузку"
document.getElementById("stopBtn").addEventListener('click', function() {
    window.pywebview.api.stopDownload();
})

// Управление форматами (блокировка разрешения для mp3)
document.getElementById('format').addEventListener('change', ()=> {
    const element = document.getElementById('format');
    const res = document.getElementById('resolution');

    if (element.value === 'mp3') {
        res.selectedIndex = -1;
        res.disabled = true;
    } else {
        res.disabled = false;
        res.selectedIndex = 4; // Default 1080p?
    }
})

// --- UI Helpers (Вызываются из Python) ---

window.showSpinner = function() {
    const spinner = document.getElementById('loading-spinner');
    if(spinner) spinner.style.display = 'block';
    
    toggleButtons(true);
}

window.hideSpinner = function() {
    const spinner = document.getElementById('loading-spinner');
    if(spinner) spinner.style.display = 'none'; 
    
    toggleButtons(false);
}

function toggleButtons(disabled) {
    const ids = ['addBtn', 'startBtn', 'convert_btn'];
    ids.forEach(id => {
        const btn = document.getElementById(id);
        if(btn) btn.disabled = disabled;
    });
}

// Универсальная функция обновления прогресса (для Python)
window.updateProgressBar = function(progress, speed, eta) {
    // Прогресс
    if (progress !== undefined && progress !== "") {
        const pText = document.getElementById("progress");
        const pFill = document.getElementById("progress-fill");
        // Пытаемся сохранить префикс "Progress" если он есть в тексте, или просто число
        // Но лучше, чтобы Python просто слал числа, а JS добавлял текст.
        // Сейчас Python шлет вызовы updateProgressBar(50, "2 MB/s", "1 min")
        
        // Для упрощения, предположим, что мы просто обновляем цифры, 
        // а слова "Speed", "ETA" уже есть в span или добавляются тут.
        // В твоем коде Python в downloader.py сам формирует строки "Speed: ...".
        
        // Если Python прислал просто число:
        if (typeof progress === 'number') {
            if(pText) pText.innerText = `Progress ${progress}%`;
            if(pFill) pFill.style.width = `${progress}%`;
        }
    }

    // Скорость (если передана строка уже с единицами)
    if (speed) {
        const sEl = document.getElementById("speed");
        if(sEl) sEl.innerText = speed.includes("Speed") ? speed : `Speed ${speed}`;
    }

    // ETA
    if (eta) {
        const eEl = document.getElementById("eta");
        if(eEl) eEl.innerText = eta.includes("ETA") ? eta : `ETA ${eta}`;
    }
}

// --- Очередь (Queue) ---

// Создает временный блок загрузки
// Создает временный блок загрузки
function createLoadingItem(tempId) {
    const queueList = document.getElementById("queue");
    const li = document.createElement("li");
    li.id = `temp-${tempId}`;
    li.className = "queue-item-skeleton"; // Класс из CSS выше
    
    li.innerHTML = `
        <div class="skeleton-thumb">
            <div class="mini-spinner"></div>
        </div>
        <div class="skeleton-info">
            <div class="skeleton-line"></div>
            <div class="skeleton-line short"></div>
        </div>
    `;
    
    // Вставляем В НАЧАЛО списка (перед первым элементом)
    queueList.prepend(li);
}

// Удаляет временный блок (вызывается из Python при ошибке или JS при успехе)
window.removeLoadingItem = function(tempId) {
    const el = document.getElementById(`temp-${tempId}`);
    if (el) el.remove();
}


// Функция принимает объект videoData из Python
window.addVideoToList = function(videoData) {
    if (videoData.temp_id) window.removeLoadingItem(videoData.temp_id);
    const queueList = document.getElementById("queue");
    if(document.getElementById(`item-${videoData.id}`)) return;

    const listItem = document.createElement("li");
    listItem.id = `item-${videoData.id}`;
    listItem.className = "queue-item"; 

    // Данные (с фолбеками, если это старая запись из JSON без меты)
    const thumb = videoData.thumbnail || "src/default_thumbnail.png";
    const meta = videoData.meta || { duration: '--:--', size: '~', uploader: 'Unknown', fps: '-', vcodec: '-', acodec: '-', bitrate: '-' };
    
    // Селекты
    const currentFmt = videoData.format;
    const currentRes = videoData.resolution;
    const isAudio = ['mp3', 'm4a', 'aac'].includes(currentFmt);
    const fmtSelect = generateFormatSelect(videoData.id, currentFmt);
    const resSelect = generateResolutionSelect(videoData.id, currentRes, isAudio);
    
    const txtWait = window.i18n.status?.status_text?.replace('Status: ', '') || 'Waiting...';

    listItem.innerHTML = `
        <div class="queue-item-top">
            <!-- Кнопка раскрытия (слева) -->
            <button class="btn-q-expand" onclick="toggleQueueDetails('${videoData.id}')" title="Подробнее">
                <i class="fa-solid fa-chevron-down"></i>
            </button>

            <div class="queue-item-info">
                <div class="queue-thumb-wrapper">
                    <img src="${thumb}" alt="thumb">
                </div>
                <div class="video-info">
                    <div class="video_queue_text" title="${videoData.title}">${videoData.title}</div>
                
                    <!-- Бейджики с информацией и селекты -->
                    <div class="queue-meta-badges">
                        ${fmtSelect}
                        ${resSelect}
                        <div class="meta-badge" title="Длительность">
                            <i class="fa-regular fa-clock"></i> ${meta.duration}
                        </div>
                        <div class="meta-badge" title="Примерный размер">
                            <i class="fa-solid fa-weight-hanging"></i> ${meta.size}
                        </div>
                    </div>

                    </div>
            </div>
            
            <!-- Кнопки действий -->
            <div class="queue-actions">
                <button class="icon-btn-queue btn-q-start" onclick="startSingleDownload('${videoData.id}')">
                    <i class="fa-solid fa-play"></i>
                </button>
                <button class="icon-btn-queue btn-q-delete" id="btn-del-${videoData.id}" onclick="window.removeVideoFromQueue('${videoData.id}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
                <button class="icon-btn-queue btn-q-stop hidden" id="btn-stop-${videoData.id}" onclick="stopSingleDownload('${videoData.id}')">
                    <i class="fa-solid fa-stop"></i>
                </button>
            </div>
        </div>
        
        <!-- Скрытые детали -->
        <div class="queue-details">
            <div class="detail-group">
                <span class="detail-label">Автор</span>
                <span class="detail-value">${meta.uploader}</span>
            </div>
            <div class="detail-group">
                <span class="detail-label">FPS</span>
                <span class="detail-value">${meta.fps}</span>
            </div>
            <div class="detail-group">
                <span class="detail-label">Видео кодек</span>
                <span class="detail-value">${meta.vcodec}</span>
            </div>
            <div class="detail-group">
                <span class="detail-label">Аудио кодек</span>
                <span class="detail-value">${meta.acodec}</span>
            </div>
            <div class="detail-group">
                <span class="detail-label">Битрейт</span>
                <span class="detail-value">${meta.bitrate}</span>
            </div>
        </div>
        
        <div class="queue-item-bottom">
            <div class="mini-progress-track">
                <div class="mini-progress-fill" id="prog-bar-${videoData.id}" style="width: 0%"></div>
            </div>
            <div class="queue-item-stats">
                <span id="status-${videoData.id}">${txtWait}</span>
                <span>
                    <span id="speed-${videoData.id}">--</span> | 
                    <span id="eta-${videoData.id}">--</span>
                </span>
            </div>
        </div>
    `;

    queueList.insertBefore(listItem, queueList.firstChild);
    
    if (videoData.status === 'downloading') {
        toggleQueueButtons(videoData.id, true);
    }
}

window.toggleQueueDetails = function(taskId) {
    const item = document.getElementById(`item-${taskId}`);
    if (item) {
        item.classList.toggle('expanded');
    }
}

// Запуск одного видео (через API)
window.startSingleDownload = function(id) {
    if(window.pywebview.api.downloader_start_task) {
        window.pywebview.api.downloader_start_task(id);
    } else {
        // Фолбек, если метод не реализован в API
        window.pywebview.api.startDownload(); 
    }
}

// Остановка одного видео (через API)
window.stopSingleDownload = function(id) {
    if(window.pywebview.api.downloader_stop_task) {
        window.pywebview.api.downloader_stop_task(id);
    }
}

// Функция переключения кнопок (Удалить <-> Стоп) и блокировки селектов
function toggleQueueButtons(id, isDownloading) {
    const btnDel = document.getElementById(`btn-del-${id}`);
    const btnStop = document.getElementById(`btn-stop-${id}`);
    const btnStart = document.querySelector(`#item-${id} .btn-q-start`);
    const selects = document.querySelectorAll(`#item-${id} select`);
    const item = document.getElementById(`item-${id}`);

    if (isDownloading) {
        // Режим загрузки
        if(btnDel) btnDel.classList.add('hidden');
        if(btnStop) btnStop.classList.remove('hidden');
        if(btnStart) btnStart.disabled = true; // Блокируем Play
        if(item) item.classList.add('status-downloading');
        // Блокируем выбор качества
        selects.forEach(s => s.disabled = true);
    } else {
        // Режим ожидания/паузы
        if(btnDel) btnDel.classList.remove('hidden');
        if(btnStop) btnStop.classList.add('hidden');
        if(btnStart) btnStart.disabled = false;
        if(item) item.classList.remove('status-downloading');
        selects.forEach(s => s.disabled = false);
    }
}


// Генератор HTML для селекта форматов
function generateFormatSelect(id, selected) {
    const formats = ['mp4', 'mkv', 'webm', 'avi', 'mp3'];
    let options = '';
    formats.forEach(f => {
        const isSel = f === selected ? 'selected' : '';
        options += `<option value="${f}" ${isSel}>${f.toUpperCase()}</option>`;
    });
    // Добавляем onchange прямо здесь
    return `<select class="queue-select" id="fmt-${id}" onchange="onQueueSettingsChange('${id}')">${options}</select>`;
}

// Генератор HTML для селекта разрешений
function generateResolutionSelect(id, selected, disabled) {
    const resolutions = [
        // {val: '4320', label: '8K'},
        {val: '2160', label: '4K'},
        {val: '1440', label: '2K'},
        {val: '1080', label: '1080p'},
        {val: '720', label: '720p'},
        {val: '480', label: '480p'},
        {val: '360', label: '360p'}
    ];
    
    let options = '';
    resolutions.forEach(r => {
        const isSel = r.val == selected ? 'selected' : '';
        options += `<option value="${r.val}" ${isSel}>${r.label}</option>`;
    });
    
    const disAttr = disabled ? 'disabled' : '';
    return `<select class="queue-select" id="res-${id}" ${disAttr} onchange="onQueueSettingsChange('${id}')">${options}</select>`;
}

// Обработчик изменений
window.onQueueSettingsChange = function(taskId) {
    const fmtEl = document.getElementById(`fmt-${taskId}`);
    const resEl = document.getElementById(`res-${taskId}`);
    
    if (!fmtEl || !resEl) return;

    const newFmt = fmtEl.value;
    const newRes = resEl.value;

    // Логика блокировки разрешения для аудио
    if (['mp3', 'aac', 'm4a'].includes(newFmt)) {
        resEl.disabled = true;
    } else {
        resEl.disabled = false;
    }

    // Отправляем в Python
    window.pywebview.api.update_video_settings(taskId, newFmt, newRes);
}


// Загрузка очереди при старте
window.loadQueue = function(queue) {
    const queueList = document.getElementById('queue');
    if (!queueList) return;
    queueList.innerHTML = "";
    
    // Теперь queue это список словарей, а не кортежей (мы изменили это в downloader.py)
    // Но если старый файл queue.json содержит списки, надо проверить.
    
    queue.forEach(video => {
        // Проверка совместимости (если вдруг загрузили старый json)
        let vData = video;
        if (Array.isArray(video)) {
             // Конвертация старого формата [url, title, fmt, res, thumb]
             // Генерируем фейковый ID для старых записей
            vData = {
                id: "old-" + Math.random().toString(36).substr(2, 9),
                url: video[0],
                title: video[1],
                format: video[2],
                resolution: video[3],
                thumbnail: video[4]
            };
        }
        window.addVideoToList(vData);
    });
};

// Удаление
window.removeVideoFromQueue = function(taskId) {
    // Удаляем визуально
    const item = document.getElementById(`item-${taskId}`);
    if(item) item.remove();
    
    // Удаляем логически
    window.pywebview.api.removeVideoFromQueue(taskId);
}

window.removeVideoFromList = function(videoTitle) {
    const queueList = document.getElementById("queue");
    const items = queueList.getElementsByTagName("li");

    for (let i = 0; i < items.length; i++) {
        // Простая проверка на вхождение подстроки
        if (items[i].innerText.includes(videoTitle)) {
            queueList.removeChild(items[i]);
            break;
        }
    }
}

// Обновление прогресса конкретного видео
window.updateItemProgress = function(taskId, progress, speed, eta) {
    const bar = document.getElementById(`prog-bar-${taskId}`);
    const statusText = document.getElementById(`status-${taskId}`);
    const speedText = document.getElementById(`speed-${taskId}`);
    const etaText = document.getElementById(`eta-${taskId}`);

    if (bar) bar.style.width = `${progress}%`;
    if (statusText) statusText.innerText = `${progress}%`;
    if (speedText) speedText.innerText = speed;
    if (etaText) etaText.innerText = eta;
    
    // ЛОГИКА ПЕРЕКЛЮЧЕНИЯ
    // Если прогресс идет (>0 и <100), значит качается
    if (progress > 0 && progress < 100) {
        toggleQueueButtons(taskId, true);
    } else {
        // Если 0 (ошибка/пауза) или 100 (готово) - разблокируем
        toggleQueueButtons(taskId, false);
        
        // Если остановлено вручную
        if (progress === 0 && speed === "Stopped") {
            if (statusText) statusText.innerText = "Paused";
        }
        
        // Если готово
        if (progress >= 100) {
            const item = document.getElementById(`item-${taskId}`);
            if(item) item.classList.add('status-done');
            if(statusText) statusText.innerText = "Done";
        }
    }
}


// --- Настройки и Папки (Settings) ---

window.updateDownloadFolder = function(folder_path) {
    const el = document.getElementById('folder_path');
    if(el) el.placeholder = folder_path;
}

window.updateConvertFolder = function(folder_path) {
    const el = document.getElementById('conv_folder_path');
    if(el) el.placeholder = folder_path;
}

document.getElementById("chooseButton").addEventListener("click", function() {
    window.pywebview.api.choose_folder();
});
document.getElementById("byDefoult").addEventListener("click", function() {
    window.pywebview.api.switch_download_folder();
});
document.getElementById("openFolder").addEventListener("click", () =>{
    const folder = document.getElementById('folder_path').placeholder;
    window.pywebview.api.open_folder(folder);
});

// Converter Settings
document.getElementById("chooseButton-conv").addEventListener("click", function() {
    window.pywebview.api.choose_converter_folder();
});
document.getElementById("byDefoult-conv").addEventListener("click", function() {
    window.pywebview.api.switch_converter_folder();
});
document.getElementById("openFolder-conv").addEventListener("click", () =>{
    const folder = document.getElementById('conv_folder_path').placeholder;
    window.pywebview.api.open_folder(folder);
});



// --- Прочее ---

document.getElementById("update").addEventListener("click", function(){
    window.pywebview.api.launch_update();
});

document.getElementById('language').addEventListener('change', function() {
    const lang = document.getElementById('language').value || 'en'; // Исправил English на код en
    window.pywebview.api.switch_language(lang);
});

window.setLanguage = function(lang) {
    const select = document.getElementById("language");
    if (select) select.value = lang;
}

// Вспомогательная функция времени
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}


// --- Логирование ---
window.addLog = function(message) {
    const logContainer = document.getElementById("app-logs");
    if (!logContainer) return;

    const entry = document.createElement("div");
    entry.className = "log-entry";
    
    // Время
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    entry.innerText = `[${timeStr}] ${message}`;
    
    // Добавляем в начало (или конец, если flex-direction: column-reverse)
    logContainer.prepend(entry); // prepend добавляет сверху (визуально снизу из-за стилей)
}


let currentPlaylistItems = []; // Храним данные текущего открытого плейлиста

window.openPlaylistModal = function(data) {
    currentPlaylistItems = data.items;
    
    const modal = document.getElementById('modal-playlist');
    const listContainer = document.getElementById('playlist-items');
    const titleEl = document.getElementById('pl-title');
    const countEl = document.getElementById('pl-count');
    const checkAll = document.getElementById('pl-select-all');
    
    // Сброс
    listContainer.innerHTML = "";
    checkAll.checked = true;
    titleEl.innerText = data.title;
    countEl.innerText = `${data.items.length} видео`;

    // Рендер списка
    data.items.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'pl-item';
        // Используем data-index для связи
        div.innerHTML = `
            <label class="checkbox-container" onclick="event.stopPropagation()">
                <input type="checkbox" class="pl-checkbox" data-index="${index}" checked>
                <span class="checkmark"></span>
            </label>
            <div class="pl-info" onclick="togglePlRow(${index})">
                <div class="pl-title" title="${item.title}">${index + 1}. ${item.title}</div>
                <div class="pl-meta">
                    <span><i class="fa-regular fa-clock"></i> ${item.duration}</span>
                </div>
            </div>
        `;
        listContainer.appendChild(div);
    });

    modal.classList.add('show');
}

// Клик по строке переключает чекбокс
window.togglePlRow = function(index) {
    const cb = document.querySelector(`.pl-checkbox[data-index="${index}"]`);
    if(cb) {
        cb.checked = !cb.checked;
        updateSelectAllState();
    }
}

// "Выбрать все"
document.getElementById('pl-select-all').addEventListener('change', (e) => {
    const checkboxes = document.querySelectorAll('.pl-checkbox');
    checkboxes.forEach(cb => cb.checked = e.target.checked);
});

// Слушаем изменения чекбоксов для обновления состояния "Выбрать все"
function updateSelectAllState() {
    const checkboxes = document.querySelectorAll('.pl-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    document.getElementById('pl-select-all').checked = allChecked;
}

// Кнопка "Отмена"
document.getElementById('btn-pl-cancel').addEventListener('click', () => {
    document.getElementById('modal-playlist').classList.remove('show');
});

// Кнопка "Добавить"
document.getElementById('btn-pl-add').addEventListener('click', () => {
    const selectedUrls = [];
    
    const checkboxes = document.querySelectorAll('.pl-checkbox');
    checkboxes.forEach(cb => {
        if (cb.checked) {
            const index = cb.getAttribute('data-index');
            selectedUrls.push(currentPlaylistItems[index].url);
        }
    });

    if (selectedUrls.length === 0) {
        alert("Выберите хотя бы одно видео");
        return;
    }

    // Закрываем окно
    document.getElementById('modal-playlist').classList.remove('show');

    // Берем текущие настройки формата/качества из главной панели
    const fmt = document.getElementById('format').value;
    const res = document.getElementById('resolution').value;

    // Отправляем массив URL в Python
    window.pywebview.api.add_playlist_videos(selectedUrls, fmt, res);
});

// Закрытие по крестику
document.getElementById('close-playlist').addEventListener('click', () => {
    document.getElementById('modal-playlist').classList.remove('show');
});

// --- STORE TABS ---
document.querySelectorAll('.store-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // 1. Убираем класс active у всех кнопок-табов
        document.querySelectorAll('.store-tab').forEach(t => t.classList.remove('active'));
        
        // 2. Скрываем все секции контента
        document.querySelectorAll('.store-section').forEach(s => s.classList.remove('active'));
        
        // 3. Активируем нажатую кнопку
        tab.classList.add('active');
        
        // 4. Показываем нужную секцию (по ID из data-target)
        const targetId = tab.getAttribute('data-target');
        const targetSection = document.getElementById(targetId);
        if (targetSection) {
            targetSection.classList.add('active');
            
            // Опционально: если открыли "Темы", а там пусто - загрузим их
            if (targetId === 'store-themes') {
                const list = document.getElementById('themes-list');
                // Простая проверка: если нет карточек, грузим
                if (!list.querySelector('.theme-card')) {
                    list.innerHTML = '<div style="text-align: center; color: #666; margin-top: 2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Загрузка тем...</div>';
                    window.pywebview.api.store_fetch_themes();
                }
            }
        }
    });
});
// --- MODULES STORE LOGIC ---

// Обновление кнопки "Refresh" (чтобы обновляла текущую открытую вкладку)
document.getElementById('btn-refresh-store').addEventListener('click', () => {
    const activeSection = document.querySelector('.store-section.active');
    
    if (activeSection && activeSection.id === 'store-themes') {
        // Обновляем темы
        document.getElementById('themes-list').innerHTML = '...';
        window.pywebview.api.store_fetch_themes();
    } else {
        // Обновляем модули
        document.getElementById('modules-list').innerHTML = '...';
        window.pywebview.api.store_fetch_data();
    }
});

// Клик по табу "Store" (id=3) должен триггерить загрузку
document.getElementById('coming-soon').addEventListener('click', () => { // id кнопки таба
    // Если список пуст, загружаем
    const list = document.getElementById('modules-list');
    if (!list.querySelector('.module-card')) {
        window.pywebview.api.store_fetch_data();
    }
});

// Функция обновления списка (вызывается из Python)
window.updateStoreList = function(available, installedIds) {
    const container = document.getElementById('modules-list');
    container.innerHTML = "";

    if (!available || available.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666;">Каталог пуст или недоступен</div>';
        return;
    }

    available.forEach(mod => {
        const isInstalled = installedIds.includes(mod.id);
        const btnClass = isInstalled ? 'btn-store uninstall' : 'btn-store install';
        const btnText = isInstalled ? '<i class="fa-solid fa-trash"></i> Удалить' : '<i class="fa-solid fa-download"></i> Скачать';
        const btnAction = isInstalled ? `uninstallModule('${mod.id}')` : `installModule('${mod.id}')`;
        
        // Иконка (если есть URL, иначе дефолт)
        // Для простоты пока используем FontAwesome иконку из JSON, если она там есть текстом,
        // или картинку
        let iconHtml = '<i class="fa-solid fa-cube"></i>';
        if (mod.icon && mod.icon.endsWith('.svg')) {
             // Можно добавить поддержку url картинок
            iconHtml = `<img src="src/${mod.icon}" style="width:24px;">`; 
        }

        const card = document.createElement('div');
        card.className = 'module-card';
        card.id = `mod-card-${mod.id}`;
        
        card.innerHTML = `
            <div class="mod-header">
                <div class="mod-icon">${iconHtml}</div>
                <div class="mod-info">
                    <h4>${mod.name}</h4>
                    <div class="mod-version">v${mod.version}</div>
                </div>
            </div>
            <div class="mod-desc">${mod.description}</div>
            <div class="mod-footer">
                <div class="mod-status" id="mod-status-${mod.id}"></div>
                <button class="${btnClass}" id="btn-mod-${mod.id}" onclick="${btnAction}">
                    ${btnText}
                </button>
            </div>
            <div class="mod-progress" id="prog-mod-${mod.id}"></div>
        `;
        container.appendChild(card);
    });
}

// Действия
window.installModule = function(id) {
    const btn = document.getElementById(`btn-mod-${id}`);
    btn.disabled = true;
    btn.innerText = "Ожидание...";
    window.pywebview.api.store_install_module(id);
}

window.uninstallModule = function(id) {
    if(!confirm("Удалить этот модуль?")) return;
    window.pywebview.api.store_uninstall_module(id);
}

// Обновление прогресса установки (вызывается из Python)
window.updateStoreProgress = function(id, percent, status) {
    const bar = document.getElementById(`prog-mod-${id}`);
    const btn = document.getElementById(`btn-mod-${id}`);
    const statusText = document.getElementById(`mod-status-${id}`);

    if (bar) bar.style.width = `${percent}%`;
    
    if (status === 'downloading') {
        btn.innerText = `${percent}%`;
    } else if (status === 'extracting') {
        btn.innerText = "Распаковка...";
    } else if (status === 'done') {
        // Меняем кнопку на "Удалить"
        btn.className = 'btn-store uninstall';
        btn.innerHTML = '<i class="fa-solid fa-trash"></i> Удалить';
        btn.disabled = false;
        btn.onclick = function() { uninstallModule(id); };
        if(bar) setTimeout(() => bar.style.width = '0%', 1000);
    } else if (status === 'error') {
        btn.innerText = "Ошибка";
        btn.disabled = false;
        if(bar) bar.style.background = 'var(--danger-color)';
    }
}

window.updateThemesStoreList = function(available, installedIds) {
    const container = document.getElementById('themes-list');
    container.innerHTML = "";

    if (!available || available.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #666;">Каталог пуст</div>';
        return;
    }

    available.forEach(theme => {
        const isInstalled = installedIds.includes(theme.id);
        const btnClass = isInstalled ? 'btn-store uninstall' : 'btn-store install';
        const btnText = isInstalled ? 'Удалить' : 'Установить';
        
        // Для удаления не нужен URL, для установки нужен
        const btnAction = isInstalled 
            ? `deleteTheme('${theme.id}')` 
            : `installTheme('${theme.id}', '${theme.download_url}')`;

        const card = document.createElement('div');
        card.className = 'store-card theme-card';
        card.id = `theme-card-${theme.id}`;
        
        // Превью темы (картинка или цвет)
        // Если preview это url картинки - ставим img, иначе градиент
        let previewStyle = '';
        if (theme.preview && (theme.preview.startsWith('http') || theme.preview.startsWith('data:'))) {
            previewStyle = `background-image: url('${theme.preview}');`;
        } else {
            // Фолбек - случайный градиент или цвет из JSON
            previewStyle = `background: ${theme.color || 'linear-gradient(45deg, #333, #555)'};`;
        }

        card.innerHTML = `
            <div class="theme-preview" style="${previewStyle}"></div>
            <div class="card-content">
                <h4>${theme.name}</h4>
                <p>${theme.description || 'No description'}</p>
                <div class="card-meta">Author: ${theme.author || 'Unknown'}</div>
            </div>
            <div class="mod-footer" style="padding: 0 0.8rem 0.8rem 0.8rem;">
                <div class="mod-status" id="theme-status-${theme.id}"></div>
                <button class="${btnClass}" id="btn-theme-${theme.id}" onclick="${btnAction}">
                    ${btnText}
                </button>
            </div>
            <div class="mod-progress" id="prog-theme-${theme.id}"></div>
        `;
        container.appendChild(card);
    });
}

// Действия с темами
window.installTheme = function(id, url) {
    const btn = document.getElementById(`btn-theme-${id}`);
    btn.disabled = true;
    btn.innerText = "Скачивание...";
    window.pywebview.api.store_install_theme(id, url);
}

window.deleteTheme = function(id) {
    if(id === 'cliptide') { alert("Нельзя удалить стандартную тему"); return; }
    if(!confirm("Удалить эту тему?")) return;
    window.pywebview.api.store_delete_theme(id);
}

// Прогресс бар для тем
window.updateThemeProgress = function(id, percent, status) {
    const bar = document.getElementById(`prog-theme-${id}`);
    const btn = document.getElementById(`btn-theme-${id}`);
    
    if (bar) bar.style.width = `${percent}%`;

    if (status === 'downloading') {
        btn.innerText = `${percent}%`;
    } else if (status === 'extracting') {
        btn.innerText = "Установка...";
    } else if (status === 'done') {
        btn.className = 'btn-store uninstall';
        btn.innerHTML = 'Удалить';
        btn.disabled = false;
        // Обновляем onclick на удаление (немного костыльно, лучше перерисовать)
        btn.onclick = function() { deleteTheme(id); };
        if(bar) setTimeout(() => bar.style.width = '0%', 1000);
    } else if (status === 'error') {
        btn.innerText = "Ошибка";
        btn.disabled = false;
        if(bar) bar.style.background = 'var(--danger-color)';
    }
}