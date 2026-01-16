 /* Copyright (C) 2025 Rayness */
 /* This program is free software under GPLv3. See LICENSE for details. */

let modalContentData = {};

// Вызывается из Python при старте (загружает modals.json)
function loadData(data) {
    // data может быть массивом с одним объектом (как у тебя было раньше) или сразу объектом
    if (Array.isArray(data) && data.length > 0) {
        modalContentData = data[0].content;
    } else {
        modalContentData = data.content || data;
    }
    console.log("Modal data loaded", modalContentData);
};

// Функция открытия окна по ключу (theme, proxy и т.д.)
function openInfoModal(key) {
    const modal = document.getElementById('modal-info');
    const titleEl = document.getElementById('info-modal-title');
    const bodyEl = document.getElementById('info-modal-content');
    
    // Получаем текущий язык из селекта
    const currentLang = document.getElementById('language').value || 'en';
    
    // Пытаемся добраться до данных
    // Структура JSON: settings -> [key] -> language -> [lang]
    try {
        const section = modalContentData.settings[key];
        const langData = section.language[currentLang] || section.language['en']; // Фолбек на EN
        
        if (langData) {
            titleEl.innerHTML = langData.title;
            bodyEl.innerHTML = langData.content; // Вставляем как HTML
            modal.classList.add('show');
        } else {
            console.error("No data found for key:", key, "lang:", currentLang);
        }
    } catch (e) {
        console.error("Error parsing modal data:", e);
    }
}

// --- Обработчики событий ---

// Кнопка "?" возле Тем
document.getElementById('help-theme').addEventListener('click', () => {
    openInfoModal('themes');
});

// Кнопка "?" возле Прокси
const proxyHelpBtn = document.getElementById('help-proxy');
if (proxyHelpBtn) {
    proxyHelpBtn.addEventListener('click', () => {
        openInfoModal('proxy');
    });
}

// Закрытие (Крестик)
document.getElementById('close-info-modal').addEventListener('click', () => {
    document.getElementById('modal-info').classList.remove('show');
});

// Закрытие (Кнопка "Понятно")
document.getElementById('btn-info-close').addEventListener('click', () => {
    document.getElementById('modal-info').classList.remove('show');
});

// Закрытие по клику на фон
document.getElementById('modal-info').addEventListener('click', (e) => {
    if (e.target === document.getElementById('modal-info')) {
        document.getElementById('modal-info').classList.remove('show');
    }
});