// data/ui/scripts/downloader.js

// --- Downloader Logic ---

// Кнопка "Добавить в очередь"
document.getElementById('addBtn').addEventListener('click', function() {
    const videoUrl = document.getElementById('videoUrl').value;
    const selectedFormat = document.getElementById('format').value;
    const selectedResolution = document.getElementById('resolution').value;

    if (!videoUrl) return;
    
    const tempId = Date.now().toString();
    createLoadingItem(tempId);

    window.pywebview.api.addVideoToQueue(videoUrl, selectedFormat, selectedResolution, tempId)
        .catch(() => {
            removeLoadingItem(tempId);
            // Можно добавить вывод ошибки в лог
        });
        
    document.getElementById('videoUrl').value = '';
});

// Глобальные кнопки
document.getElementById('startBtn').addEventListener('click', function() {
    window.pywebview.api.startDownload();
});

document.getElementById("stopBtn").addEventListener('click', function() {
    window.pywebview.api.stopDownload();
})

// Блокировка разрешений для аудио
document.getElementById('format').addEventListener('change', ()=> {
    const element = document.getElementById('format');
    const res = document.getElementById('resolution');

    if (['mp3', 'm4a', 'aac', 'flac'].includes(element.value)) {
        res.selectedIndex = -1;
        res.disabled = true;
    } else {
        res.disabled = false;
        res.selectedIndex = 4; // Default 1080p
    }
})

// --- UI Helpers ---

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

// --- Очередь (Queue) ---

// Создает временный блок загрузки
window.createLoadingItem = function(tempId) {
    const queueList = document.getElementById("queue");
    const li = document.createElement("li");
    li.id = `temp-${tempId}`;
    li.className = "queue-item-skeleton";
    
    li.innerHTML = `
        <div class="skeleton-thumb"><div class="mini-spinner"></div></div>
        <div class="skeleton-info">
            <div class="skeleton-line"></div>
            <div class="skeleton-line short"></div>
        </div>
    `;
    queueList.prepend(li);
}

window.removeLoadingItem = function(tempId) {
    const el = document.getElementById(`temp-${tempId}`);
    if (el) el.remove();
}

window.addVideoToList = function(videoData) {
    if (videoData.temp_id) window.removeLoadingItem(videoData.temp_id);
    
    const queueList = document.getElementById("queue");
    if(document.getElementById(`item-${videoData.id}`)) return;

    const listItem = document.createElement("li");
    listItem.id = `item-${videoData.id}`;
    listItem.className = "queue-item"; 

    const thumb = videoData.thumbnail || "src/default_thumbnail.png";
    const meta = videoData.meta || { duration: '--:--', size: '~', uploader: 'Unknown', fps: '-', vcodec: '-', acodec: '-', bitrate: '-' };
    
    const currentFmt = videoData.format;
    const currentRes = videoData.resolution;
    const isAudio = ['mp3', 'm4a', 'aac'].includes(currentFmt);

    const fmtSelect = generateFormatSelect(videoData.id, currentFmt);
    const resSelect = generateResolutionSelect(videoData.id, currentRes, isAudio);
    const txtWait = window.i18n.status?.status_text?.replace('Status: ', '') || 'Waiting...';

    listItem.innerHTML = `
        <div class="queue-item-top">
            <button class="btn-q-expand" onclick="toggleQueueDetails('${videoData.id}')" title="Подробнее">
                <i class="fa-solid fa-chevron-down"></i>
            </button>
            <div class="queue-item-info">
                <div class="queue-thumb-wrapper"><img src="${thumb}" alt="thumb"></div>
                <div class="video-info">
                    <div class="video_queue_text" title="${videoData.title}">${videoData.title}</div>
                    <div class="queue-meta-badges">
                        ${fmtSelect} ${resSelect}
                        <div class="meta-badge" title="Длительность"><i class="fa-regular fa-clock"></i> ${meta.duration}</div>
                        <div class="meta-badge" title="Размер"><i class="fa-solid fa-weight-hanging"></i> ${meta.size}</div>
                    </div>
                </div>
            </div>
            <div class="queue-actions">
                <button class="icon-btn-queue btn-q-start" onclick="startSingleDownload('${videoData.id}')"><i class="fa-solid fa-play"></i></button>
                <button class="icon-btn-queue btn-q-delete" id="btn-del-${videoData.id}" onclick="window.removeVideoFromQueue('${videoData.id}')"><i class="fa-solid fa-trash"></i></button>
                <button class="icon-btn-queue btn-q-stop hidden" id="btn-stop-${videoData.id}" onclick="stopSingleDownload('${videoData.id}')"><i class="fa-solid fa-stop"></i></button>
            </div>
        </div>
        <div class="queue-details">
            <div class="detail-group"><span class="detail-label">Автор</span><span class="detail-value">${meta.uploader}</span></div>
            <div class="detail-group"><span class="detail-label">FPS</span><span class="detail-value">${meta.fps}</span></div>
            <div class="detail-group"><span class="detail-label">V-Codec</span><span class="detail-value">${meta.vcodec}</span></div>
            <div class="detail-group"><span class="detail-label">A-Codec</span><span class="detail-value">${meta.acodec}</span></div>
            <div class="detail-group"><span class="detail-label">Bitrate</span><span class="detail-value">${meta.bitrate}</span></div>
        </div>
        <div class="queue-item-bottom">
            <div class="mini-progress-track"><div class="mini-progress-fill" id="prog-bar-${videoData.id}" style="width: 0%"></div></div>
            <div class="queue-item-stats">
                <span id="status-${videoData.id}">${txtWait}</span>
                <span><span id="speed-${videoData.id}">--</span> | <span id="eta-${videoData.id}">--</span></span>
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
    if (item) item.classList.toggle('expanded');
}

// Запуск/Стоп одного видео
window.startSingleDownload = function(id) {
    if(window.pywebview.api.downloader_start_task) window.pywebview.api.downloader_start_task(id);
    else window.pywebview.api.startDownload(); 
}

window.stopSingleDownload = function(id) {
    if(window.pywebview.api.downloader_stop_task) window.pywebview.api.downloader_stop_task(id);
}

function toggleQueueButtons(id, isDownloading) {
    const btnDel = document.getElementById(`btn-del-${id}`);
    const btnStop = document.getElementById(`btn-stop-${id}`);
    const btnStart = document.querySelector(`#item-${id} .btn-q-start`);
    const selects = document.querySelectorAll(`#item-${id} select`);
    const item = document.getElementById(`item-${id}`);

    if (isDownloading) {
        if(btnDel) btnDel.classList.add('hidden');
        if(btnStop) btnStop.classList.remove('hidden');
        if(btnStart) btnStart.disabled = true;
        if(item) item.classList.add('status-downloading');
        selects.forEach(s => s.disabled = true);
    } else {
        if(btnDel) btnDel.classList.remove('hidden');
        if(btnStop) btnStop.classList.add('hidden');
        if(btnStart) btnStart.disabled = false;
        if(item) item.classList.remove('status-downloading');
        selects.forEach(s => s.disabled = false);
    }
}

// Генераторы селектов
function generateFormatSelect(id, selected) {
    const formats = ['mp4', 'mkv', 'webm', 'avi', 'mp3'];
    let options = '';
    formats.forEach(f => {
        const isSel = f === selected ? 'selected' : '';
        options += `<option value="${f}" ${isSel}>${f.toUpperCase()}</option>`;
    });
    return `<select class="queue-select" id="fmt-${id}" onchange="onQueueSettingsChange('${id}')">${options}</select>`;
}

function generateResolutionSelect(id, selected, disabled) {
    const resolutions = [
        {val: '2160', label: '4K'}, {val: '1440', label: '2K'},
        {val: '1080', label: '1080p'}, {val: '720', label: '720p'},
        {val: '480', label: '480p'}, {val: '360', label: '360p'}
    ];
    let options = '';
    resolutions.forEach(r => {
        const isSel = r.val == selected ? 'selected' : '';
        options += `<option value="${r.val}" ${isSel}>${r.label}</option>`;
    });
    const disAttr = disabled ? 'disabled' : '';
    return `<select class="queue-select" id="res-${id}" ${disAttr} onchange="onQueueSettingsChange('${id}')">${options}</select>`;
}

window.onQueueSettingsChange = function(taskId) {
    const fmtEl = document.getElementById(`fmt-${taskId}`);
    const resEl = document.getElementById(`res-${taskId}`);
    if (!fmtEl || !resEl) return;

    const newFmt = fmtEl.value;
    const newRes = resEl.value;

    if (['mp3', 'aac', 'm4a'].includes(newFmt)) resEl.disabled = true;
    else resEl.disabled = false;

    window.pywebview.api.update_video_settings(taskId, newFmt, newRes);
}

// Обновление прогресса
window.updateItemProgress = function(taskId, progress, speed, eta) {
    const bar = document.getElementById(`prog-bar-${taskId}`);
    const statusText = document.getElementById(`status-${taskId}`);
    const speedText = document.getElementById(`speed-${taskId}`);
    const etaText = document.getElementById(`eta-${taskId}`);

    if (bar) bar.style.width = `${progress}%`;
    if (statusText) statusText.innerText = `${progress}%`;
    if (speedText) speedText.innerText = speed;
    if (etaText) etaText.innerText = eta;
    
    if (progress > 0 && progress < 100) {
        toggleQueueButtons(taskId, true);
    } else {
        toggleQueueButtons(taskId, false);
        if (progress === 0 && speed === "Stopped" && statusText) statusText.innerText = "Paused";
        if (progress >= 100) {
            const item = document.getElementById(`item-${taskId}`);
            if(item) item.classList.add('status-done');
            if(statusText) statusText.innerText = "Done";
        }
    }
}

// Загрузка/Удаление очереди
window.loadQueue = function(queue) {
    const queueList = document.getElementById('queue');
    if (!queueList) return;
    queueList.innerHTML = "";
    queue.forEach(video => {
        // Миграция старого формата
        let vData = video;
        if (Array.isArray(video)) {
            vData = {
                id: "old-" + Math.random().toString(36).substr(2, 9),
                url: video[0], title: video[1], format: video[2],
                resolution: video[3], thumbnail: video[4]
            };
        }
        window.addVideoToList(vData);
    });
};

window.removeVideoFromQueue = function(taskId) {
    const item = document.getElementById(`item-${taskId}`);
    if(item) item.remove();
    window.pywebview.api.removeVideoFromQueue(taskId);
}

// Плейлисты
let currentPlaylistItems = [];

window.openPlaylistModal = function(data) {
    currentPlaylistItems = data.items;
    const modal = document.getElementById('modal-playlist');
    const listContainer = document.getElementById('playlist-items');
    const titleEl = document.getElementById('pl-title');
    const countEl = document.getElementById('pl-count');
    const checkAll = document.getElementById('pl-select-all');
    
    listContainer.innerHTML = "";
    checkAll.checked = true;
    titleEl.innerText = data.title;
    countEl.innerText = `${data.items.length} видео`;

    data.items.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'pl-item';
        div.innerHTML = `
            <label class="checkbox-container" onclick="event.stopPropagation()">
                <input type="checkbox" class="pl-checkbox" data-index="${index}" checked>
                <span class="checkmark"></span>
            </label>
            <div class="pl-info" onclick="togglePlRow(${index})">
                <div class="pl-title" title="${item.title}">${index + 1}. ${item.title}</div>
                <div class="pl-meta"><span><i class="fa-regular fa-clock"></i> ${item.duration}</span></div>
            </div>
        `;
        listContainer.appendChild(div);
    });
    modal.classList.add('show');
}

window.togglePlRow = function(index) {
    const cb = document.querySelector(`.pl-checkbox[data-index="${index}"]`);
    if(cb) { cb.checked = !cb.checked; updateSelectAllState(); }
}

function updateSelectAllState() {
    const checkboxes = document.querySelectorAll('.pl-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    document.getElementById('pl-select-all').checked = allChecked;
}

document.getElementById('pl-select-all').addEventListener('change', (e) => {
    document.querySelectorAll('.pl-checkbox').forEach(cb => cb.checked = e.target.checked);
});

document.getElementById('btn-pl-cancel').addEventListener('click', () => {
    document.getElementById('modal-playlist').classList.remove('show');
});

document.getElementById('btn-pl-add').addEventListener('click', () => {
    const selectedUrls = [];
    document.querySelectorAll('.pl-checkbox').forEach(cb => {
        if (cb.checked) selectedUrls.push(currentPlaylistItems[cb.getAttribute('data-index')].url);
    });
    if (selectedUrls.length === 0) { alert("Выберите видео"); return; }
    document.getElementById('modal-playlist').classList.remove('show');
    const fmt = document.getElementById('format').value;
    const res = document.getElementById('resolution').value;
    window.pywebview.api.add_playlist_videos(selectedUrls, fmt, res);
});

document.getElementById('close-playlist').addEventListener('click', () => {
    document.getElementById('modal-playlist').classList.remove('show');
});