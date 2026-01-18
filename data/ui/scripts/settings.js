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


// Папка загрузки
const btnChooseDl = document.getElementById("chooseButton");
if (btnChooseDl) {
    btnChooseDl.addEventListener("click", function() {
        window.pywebview.api.choose_folder();
    });
}

const btnDefaultDl = document.getElementById("byDefoult");
if (btnDefaultDl) {
    btnDefaultDl.addEventListener("click", function() {
        window.pywebview.api.switch_download_folder();
    });
}

const btnOpenDl = document.getElementById("openFolder");
if (btnOpenDl) {
    btnOpenDl.addEventListener("click", () =>{
        const el = document.getElementById('folder_path');
        const folder = el ? el.placeholder : "";
        window.pywebview.api.open_folder(folder);
    });
}

// Папка конвертера
const btnChooseCv = document.getElementById("chooseButton-conv");
if (btnChooseCv) {
    btnChooseCv.addEventListener("click", function() {
        window.pywebview.api.choose_converter_folder();
    });
}

const btnDefaultCv = document.getElementById("byDefoult-conv");
if (btnDefaultCv) {
    btnDefaultCv.addEventListener("click", function() {
        window.pywebview.api.switch_converter_folder();
    });
}

const btnOpenCv = document.getElementById("openFolder-conv");
if (btnOpenCv) {
    btnOpenCv.addEventListener("click", () =>{
        const el = document.getElementById('conv_folder_path');
        const folder = el ? el.placeholder : "";
        window.pywebview.api.open_folder(folder);
    });
}


// Обновление
const btnUpdate = document.getElementById("update");
if (btnUpdate) {
    btnUpdate.addEventListener("click", function(){
        window.pywebview.api.launch_update();
    });
}

// Локализация
const langSelect = document.getElementById('language');
if (langSelect) {
    langSelect.addEventListener('change', function() {
        const lang = langSelect.value || 'en';
        window.pywebview.api.switch_language(lang);
    });
}

// --- Глобальные функции (вызываются из Python) ---

window.setLanguage = function(lang) {
    const select = document.getElementById("language");
    if (select) {
        select.value = lang;
        // Обновляем кастомный селект, если он есть
        if (typeof refreshCustomSelectOptions === 'function') {
             // Маленькая задержка, чтобы DOM успел отработать
            setTimeout(refreshCustomSelectOptions, 50);
        }
    }
}

// Открытие папки с переводами
const btnOpenLoc = document.getElementById('open_locale_folder'); // ID поправлен под новый HTML
if (btnOpenLoc) {
    btnOpenLoc.addEventListener('click', () => {
        window.pywebview.api.open_locale_folder();
    });
} else {
    // Фолбек для старого ID, если вдруг остался
    const btnOpenLangFiles = document.getElementById('openLangFiles');
    if (btnOpenLangFiles) {
        btnOpenLangFiles.addEventListener('click', () => {
            window.pywebview.api.open_locale_folder();
        });
    }
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