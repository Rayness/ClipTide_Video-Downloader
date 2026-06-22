/* Copyright (C) 2025 Rayness */
/* This program is free software under GPLv3. See LICENSE for details. */

// --- EDITOR ---

let editorFile       = null;   // { path, filename, duration, width, height, codec, fps, video_url }
let editorSegments   = [];     // [{ id, start, end }]
let editorDragging   = null;   // { segId, handle, startX, origStart, origEnd }
let editorPlayheadPos = 0;
let editorPlaySegEnd  = null;  // секунда остановки при воспроизведении сегмента

// ─── DOM-хелперы ────────────────────────────────────────────────────────────
const elTimeline      = () => document.getElementById('editor-timeline');
const elRuler         = () => document.getElementById('editor-timeline-ruler');
const elPlayhead      = () => document.getElementById('editor-playhead');
const elVideo         = () => document.getElementById('editor-video');
const elTimeBadge     = () => document.getElementById('editor-time-badge');
const elCurrentTime   = () => document.getElementById('editor-current-time');
const elTotalTime     = () => document.getElementById('editor-total-time');
const elPlayIcon      = () => document.getElementById('editor-play-icon');
const elSegments      = () => document.getElementById('editor-segments');
const elMain          = () => document.getElementById('editor-main');
const elEmpty         = () => document.getElementById('editor-empty');
const elFileInfo      = () => document.getElementById('editor-file-info');
const elFilename      = () => document.getElementById('editor-filename');
const elMeta          = () => document.getElementById('editor-meta');
const elProgressWrap  = () => document.getElementById('editor-progress-wrap');
const elProgressFill  = () => document.getElementById('editor-progress-fill');
const elProgressLabel = () => document.getElementById('editor-progress-label');

// ─── Утилиты ────────────────────────────────────────────────────────────────
function fmtTime(sec) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = (sec % 60).toFixed(1);
    if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(4,'0')}`;
    return `${m}:${String(s).padStart(4,'0')}`;
}

function secToPercent(sec) {
    if (!editorFile || editorFile.duration <= 0) return 0;
    return (sec / editorFile.duration) * 100;
}

function percentToSec(pct) {
    if (!editorFile) return 0;
    return Math.max(0, Math.min(editorFile.duration, (pct / 100) * editorFile.duration));
}

function timelineXToSec(clientX) {
    const tl = elTimeline();
    if (!tl) return 0;
    const rect = tl.getBoundingClientRect();
    const pct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
    return percentToSec(pct);
}

// ─── Загрузка файла (вызывается из Python) ──────────────────────────────────
window.editorLoadFile = function(data) {
    editorFile     = data;
    editorSegments = [];
    editorPlaySegEnd = null;

    elFilename().textContent = data.filename;
    elMeta().textContent = `${data.width}×${data.height} · ${data.codec} · ${data.fps}fps · ${fmtTime(data.duration)}`;
    elFileInfo().style.display = 'flex';
    elEmpty().style.display    = 'none';
    elMain().style.display     = 'flex';

    // Загружаем видео
    const video = elVideo();
    if (video) {
        video.src = data.video_url;
        video.load();
        video.currentTime = 0;
    }

    elTotalTime().textContent   = fmtTime(data.duration);
    elCurrentTime().textContent = '0:00.0';

    renderRuler();
    renderTimeline();
    renderSegmentList();
    movePlayhead(0, false);
};

// ─── Линейка времени ─────────────────────────────────────────────────────────
function renderRuler() {
    const ruler = elRuler();
    if (!ruler || !editorFile) return;
    ruler.innerHTML = '';

    const duration = editorFile.duration;
    let step = 1;
    if (duration > 3600)      step = 600;
    else if (duration > 600)  step = 60;
    else if (duration > 120)  step = 15;
    else if (duration > 30)   step = 5;

    for (let t = 0; t <= duration; t += step) {
        const mark = document.createElement('span');
        mark.className = 'ruler-mark';
        mark.style.left = secToPercent(t) + '%';
        mark.textContent = fmtTime(t);
        ruler.appendChild(mark);
    }
}

// ─── Таймлайн ────────────────────────────────────────────────────────────────
function renderTimeline() {
    const tl = elTimeline();
    if (!tl) return;

    tl.querySelectorAll('.editor-segment').forEach(el => el.remove());

    editorSegments.forEach(seg => {
        const el = document.createElement('div');
        el.className = 'editor-segment';
        el.dataset.id = seg.id;
        el.style.left  = secToPercent(seg.start) + '%';
        el.style.width = secToPercent(seg.end - seg.start) + '%';

        el.innerHTML = `
            <div class="seg-handle seg-handle-left"  data-id="${seg.id}" data-handle="left"></div>
            <div class="seg-label">${fmtTime(seg.start)} – ${fmtTime(seg.end)}</div>
            <div class="seg-handle seg-handle-right" data-id="${seg.id}" data-handle="right"></div>
        `;

        el.addEventListener('mousedown', e => {
            if (e.target.classList.contains('seg-handle')) return;
            startDrag(e, seg.id, 'body');
        });

        tl.appendChild(el);
    });

    const ph = elPlayhead();
    if (ph) tl.appendChild(ph);

    tl.onclick = e => {
        if (e.target.classList.contains('seg-handle') || editorDragging) return;
        if (e.detail > 1) return;
        movePlayhead(timelineXToSec(e.clientX), false);
    };
}

// ─── Playhead ────────────────────────────────────────────────────────────────
function movePlayhead(sec, keepPlaying = true) {
    editorPlayheadPos = sec;
    const ph = elPlayhead();
    if (ph) ph.style.left = secToPercent(sec) + '%';
    elTimeBadge().textContent   = fmtTime(sec);
    elCurrentTime().textContent = fmtTime(sec);

    const video = elVideo();
    if (video && editorFile) {
        const wasPlaying = !video.paused;
        video.currentTime = sec;
        if (!keepPlaying && wasPlaying) video.pause();
    }
}

// ─── Транспорт: воспроизведение ──────────────────────────────────────────────
function togglePlay() {
    const video = elVideo();
    if (!video || !editorFile) return;
    if (video.paused) {
        video.play();
    } else {
        video.pause();
    }
}

function skipBy(deltaSec) {
    const video = elVideo();
    if (!video || !editorFile) return;
    const t = Math.max(0, Math.min(editorFile.duration, video.currentTime + deltaSec));
    movePlayhead(t, true);
}

function updateVolumeIcon(volume, muted) {
    const icon = document.getElementById('editor-volume-icon');
    if (!icon) return;
    if (muted || volume === 0)     icon.className = 'fa-solid fa-volume-xmark';
    else if (volume < 0.5)         icon.className = 'fa-solid fa-volume-low';
    else                           icon.className = 'fa-solid fa-volume-high';
}

function playSegment(seg) {
    const video = elVideo();
    if (!video || !editorFile) return;
    editorPlaySegEnd = seg.end;
    video.currentTime = seg.start;
    movePlayhead(seg.start, false);
    video.play();
}

// ─── Видео-события ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const video = elVideo();
    if (!video) return;

    video.addEventListener('timeupdate', () => {
        const t = video.currentTime;
        editorPlayheadPos = t;
        const ph = elPlayhead();
        if (ph) ph.style.left = secToPercent(t) + '%';
        elTimeBadge().textContent   = fmtTime(t);
        elCurrentTime().textContent = fmtTime(t);

        // Авто-стоп в конце сегмента
        if (editorPlaySegEnd !== null && t >= editorPlaySegEnd) {
            video.pause();
            video.currentTime = editorPlaySegEnd;
            editorPlaySegEnd = null;
        }
    });

    video.addEventListener('play', () => {
        const icon = elPlayIcon();
        if (icon) icon.className = 'fa-solid fa-pause';
    });

    video.addEventListener('pause', () => {
        const icon = elPlayIcon();
        if (icon) icon.className = 'fa-solid fa-play';
    });

    video.addEventListener('ended', () => {
        editorPlaySegEnd = null;
        const icon = elPlayIcon();
        if (icon) icon.className = 'fa-solid fa-play';
    });
});

// ─── Drag & Drop сегментов ───────────────────────────────────────────────────
function startDrag(e, segId, handle) {
    e.preventDefault();
    const seg = editorSegments.find(s => s.id === segId);
    if (!seg) return;
    editorDragging = { segId, handle, startX: e.clientX, origStart: seg.start, origEnd: seg.end };
}

document.addEventListener('mousemove', e => {
    if (!editorDragging || !editorFile) return;
    const tl = elTimeline();
    if (!tl) return;

    const rect = tl.getBoundingClientRect();
    const dx   = e.clientX - editorDragging.startX;
    const dSec = (dx / rect.width) * editorFile.duration;
    const seg  = editorSegments.find(s => s.id === editorDragging.segId);
    if (!seg) return;

    const minLen = 0.5;

    if (editorDragging.handle === 'left') {
        seg.start = Math.max(0, Math.min(editorDragging.origStart + dSec, seg.end - minLen));
        editorPlayheadPos = seg.start;
    } else if (editorDragging.handle === 'right') {
        seg.end = Math.min(editorFile.duration, Math.max(editorDragging.origEnd + dSec, seg.start + minLen));
        editorPlayheadPos = seg.end;
    } else {
        const len = editorDragging.origEnd - editorDragging.origStart;
        seg.start = Math.max(0, Math.min(editorDragging.origStart + dSec, editorFile.duration - len));
        seg.end   = seg.start + len;
        editorPlayheadPos = seg.start + len / 2;
    }

    const ph = elPlayhead();
    if (ph) ph.style.left = secToPercent(editorPlayheadPos) + '%';
    elTimeBadge().textContent   = fmtTime(editorPlayheadPos);
    elCurrentTime().textContent = fmtTime(editorPlayheadPos);

    updateSegmentEl(seg);
    updateSegmentListItem(seg);
});

document.addEventListener('mouseup', () => {
    if (editorDragging) {
        // Синхронизируем видео только при отпускании
        const video = elVideo();
        if (video && editorFile) video.currentTime = editorPlayheadPos;
    }
    editorDragging = null;
});

document.addEventListener('mousedown', e => {
    const handle = e.target.closest('.seg-handle');
    if (!handle) return;
    startDrag(e, handle.dataset.id, handle.dataset.handle);
});

function updateSegmentEl(seg) {
    const tl = elTimeline();
    if (!tl) return;
    const el = tl.querySelector(`.editor-segment[data-id="${seg.id}"]`);
    if (!el) return;
    el.style.left  = secToPercent(seg.start) + '%';
    el.style.width = secToPercent(seg.end - seg.start) + '%';
    const lbl = el.querySelector('.seg-label');
    if (lbl) lbl.textContent = `${fmtTime(seg.start)} – ${fmtTime(seg.end)}`;
}

function updateSegmentListItem(seg) {
    const row = document.querySelector(`.seg-row[data-id="${seg.id}"]`);
    if (!row) return;
    const s = row.querySelector('.seg-row-start');
    const e = row.querySelector('.seg-row-end');
    const d = row.querySelector('.seg-row-dur');
    if (s) s.textContent = fmtTime(seg.start);
    if (e) e.textContent = fmtTime(seg.end);
    if (d) d.textContent = fmtTime(seg.end - seg.start);
}

// ─── Добавить сегмент ────────────────────────────────────────────────────────
function addSegment() {
    if (!editorFile) return;
    const duration = editorFile.duration;
    let start = editorPlayheadPos;
    let end   = Math.min(duration, start + Math.max(10, duration * 0.1));
    if (end - start < 1) start = Math.max(0, end - 10);

    const seg = { id: 'seg_' + Date.now(), start, end };
    editorSegments.push(seg);
    renderTimeline();
    renderSegmentList();
    movePlayhead(start, false);
}

// ─── Список сегментов ────────────────────────────────────────────────────────
function renderSegmentList() {
    const container = elSegments();
    if (!container) return;
    container.innerHTML = '';

    if (editorSegments.length === 0) {
        container.innerHTML = '<div class="seg-empty-hint">Нет сегментов. Нажмите «Добавить сегмент».</div>';
        return;
    }

    editorSegments.forEach((seg, idx) => {
        const row = document.createElement('div');
        row.className = 'seg-row';
        row.dataset.id = seg.id;
        row.innerHTML = `
            <span class="seg-row-num">${idx + 1}</span>
            <span class="seg-row-time">
                <span class="seg-row-start">${fmtTime(seg.start)}</span>
                <i class="fa-solid fa-arrow-right seg-row-arrow"></i>
                <span class="seg-row-end">${fmtTime(seg.end)}</span>
            </span>
            <span class="seg-row-dur">${fmtTime(seg.end - seg.start)}</span>
            <button class="icon-btn small seg-row-play" data-id="${seg.id}" title="Воспроизвести сегмент">
                <i class="fa-solid fa-play"></i>
            </button>
            <button class="icon-btn small seg-row-del" data-id="${seg.id}" title="Удалить">
                <i class="fa-solid fa-trash"></i>
            </button>
        `;

        row.addEventListener('click', e => {
            if (e.target.closest('.seg-row-del') || e.target.closest('.seg-row-play')) return;
            movePlayhead(seg.start, false);
        });

        row.querySelector('.seg-row-play').addEventListener('click', () => playSegment(seg));
        row.querySelector('.seg-row-del').addEventListener('click', () => {
            editorSegments = editorSegments.filter(s => s.id !== seg.id);
            renderTimeline();
            renderSegmentList();
        });

        container.appendChild(row);
    });
}

// ─── Экспорт ─────────────────────────────────────────────────────────────────
function startExport() {
    if (!editorFile || editorSegments.length === 0) {
        addLog('Нет сегментов для экспорта', 'warn');
        return;
    }

    const mode = document.querySelector('input[name="editor-mode"]:checked')?.value || 'separate';
    const outputDir = editorFile.path.substring(0, Math.max(
        editorFile.path.lastIndexOf('\\'),
        editorFile.path.lastIndexOf('/')
    ) + 1);

    const segments = editorSegments.map(s => ({ start: s.start, end: s.end }));

    document.getElementById('editor-export-btn').style.display = 'none';
    document.getElementById('editor-stop-btn').style.display   = '';
    elProgressWrap().style.display = 'flex';

    window.pywebview.api.editor_trim_video(editorFile.path, segments, mode, outputDir)
        .catch(err => addLog('Ошибка экспорта: ' + err, 'error'));
}

// ─── Колбэки из Python ───────────────────────────────────────────────────────
window.editorTrimStart = function() {
    elProgressFill().style.width    = '0%';
    elProgressLabel().textContent   = 'Начало обработки...';
};

window.editorTrimProgress = function(percent, label) {
    elProgressFill().style.width  = percent + '%';
    elProgressLabel().textContent = label;
};

window.editorTrimDone = function(mode, outputDir) {
    elProgressFill().style.width  = '100%';
    elProgressLabel().textContent = mode === 'merge' ? 'Готово: файлы склеены!' : 'Готово: файлы сохранены!';
    document.getElementById('editor-export-btn').style.display = '';
    document.getElementById('editor-stop-btn').style.display   = 'none';
    addLog('Экспорт завершён: ' + outputDir, 'success');
    setTimeout(() => { elProgressWrap().style.display = 'none'; }, 3000);
};

window.editorTrimError = function() {
    elProgressLabel().textContent = 'Ошибка при экспорте';
    document.getElementById('editor-export-btn').style.display = '';
    document.getElementById('editor-stop-btn').style.display   = 'none';
};

window.editorTrimStopped = function() {
    elProgressLabel().textContent = 'Остановлено';
    document.getElementById('editor-export-btn').style.display = '';
    document.getElementById('editor-stop-btn').style.display   = 'none';
    setTimeout(() => { elProgressWrap().style.display = 'none'; }, 2000);
};

// ─── Инициализация кнопок ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('editor-open-btn')?.addEventListener('click', () => {
        window.pywebview.api.editor_open_file();
    });

    document.getElementById('editor-add-seg-btn')?.addEventListener('click', addSegment);
    document.getElementById('editor-export-btn')?.addEventListener('click', startExport);

    document.getElementById('editor-play-btn')?.addEventListener('click', togglePlay);
    document.getElementById('editor-skip-back-btn')?.addEventListener('click', () => skipBy(-5));
    document.getElementById('editor-skip-fwd-btn')?.addEventListener('click',  () => skipBy(5));

    // Громкость
    const volSlider = document.getElementById('editor-volume-slider');
    const muteBtn   = document.getElementById('editor-mute-btn');

    volSlider?.addEventListener('input', () => {
        const video = elVideo();
        if (!video) return;
        video.volume = parseFloat(volSlider.value);
        video.muted  = video.volume === 0;
        updateVolumeIcon(video.volume, video.muted);
    });

    muteBtn?.addEventListener('click', () => {
        const video = elVideo();
        if (!video) return;
        video.muted = !video.muted;
        if (!video.muted && video.volume === 0) {
            video.volume = 0.5;
            volSlider.value = 0.5;
        }
        updateVolumeIcon(video.volume, video.muted);
    });

    document.getElementById('editor-stop-btn')?.addEventListener('click', () => {
        window.pywebview.api.editor_stop_trim();
    });
});
