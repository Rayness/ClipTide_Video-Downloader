 /* Copyright (C) 2025 Rayness */
 /* This program is free software under GPLv3. See LICENSE for details. */

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

document.getElementById("update").addEventListener("click", function(){
    window.pywebview.api.launch_update();
});

document.getElementById('language').addEventListener('change', function() {
    const lang = document.getElementById('language').value || 'en';
    window.pywebview.api.switch_language(lang);
});

window.setLanguage = function(lang) {
    const select = document.getElementById("language");
    if (select) select.value = lang;
}

// --- ЛОГИКА НОВЫХ НАСТРОЕК (MODAL) ---

const settingsModal = document.getElementById('settings-modal');
const btnOpenSettings = document.getElementById('btn-open-settings');
const btnCloseSettings = document.getElementById('btn-close-settings');

// Открытие
if (btnOpenSettings) {
    btnOpenSettings.addEventListener('click', () => {
        settingsModal.classList.add('show');
        // Обновляем состояние Custom Selects внутри модалки (если нужно)
        if(typeof refreshCustomSelectOptions === 'function') refreshCustomSelectOptions();
    });
}

// Закрытие
if (btnCloseSettings) {
    btnCloseSettings.addEventListener('click', () => {
        settingsModal.classList.remove('show');
    });
}

// Закрытие по ESC
document.addEventListener('keydown', (e) => {
    if (e.key === "Escape" && settingsModal.classList.contains('show')) {
        settingsModal.classList.remove('show');
    }
});

// Переключение табов настроек
document.querySelectorAll('.sett-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Убираем актив у кнопок
        document.querySelectorAll('.sett-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Скрываем секции
        document.querySelectorAll('.sett-section').forEach(s => s.classList.remove('active'));
        
        // Показываем нужную
        const targetId = btn.getAttribute('data-target');
        document.getElementById(targetId).classList.add('active');
    });
});