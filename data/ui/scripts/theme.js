// Copyright (C) 2025 Rayness
// This program is free software under GPLv3. See LICENSE for details.

// Глобальное хранилище данных о темах
let cachedThemesData = [];

// === ОСНОВНЫЕ ФУНКЦИИ (Работа с CSS) ===

function setTheme(themeName) {
    const themeLink = document.getElementById('theme-link');
    const themeSelect = document.getElementById('theme');
    
    // Меняем CSS файл скина
    themeLink.href = `themes/${themeName}/styles.css`;
    
    // Синхронизируем селект (если смена была программной)
    if (themeSelect.value !== themeName) {
        themeSelect.value = themeName;
    }

    // Загружаем иконки для этой темы
    loadIconsForTheme(themeName);

    if (typeof refreshCustomSelectOptions === 'function') {
        refreshCustomSelectOptions();
    }
}

function setStyle(styleName) {
    // Удаляем старые классы стилей
    document.body.classList.forEach(className => {
        if (className.startsWith('style-')) {
            document.body.classList.remove(className);
        }
    });
    
    // Добавляем новый (если не дефолт)
    if (styleName && styleName !== 'default') {
        document.body.classList.add(`style-${styleName}`);
    }
    
    // Синхронизируем селект
    const styleSelect = document.getElementById('style');
    if (styleSelect.value !== styleName) {
        styleSelect.value = styleName;
    }
}

async function loadIconsForTheme(themeName) {
    const iconNames = [
        'icon-downloader', 'icon-settings', 'icon-converter', 
        'icon-comingSoon', 'icon-donate', 'icon-notifi'
    ];
    
    for (const name of iconNames) {
        try {
            const el = document.getElementById(name);
            if (el) {
                // Пытаемся загрузить из папки темы
                // Если иконки нет, fetch вернет 404, можно обработать
                const res = await fetch(`themes/${themeName}/icons/${name}.svg`);
                if (res.ok) {
                    const svgText = await res.text();
                    el.innerHTML = svgText;
                } else {
                    const svgText = await fetch(`styles/icons/${name}.svg`).then(r => r.text());
                    el.innerHTML = svgText;
                    // Можно загрузить дефолтную, если нужно
                    console.warn(`Icon ${name} not found in theme ${themeName}`);
                }
            }
        } catch (e) {
            console.error(`Error loading icon ${name}:`, e);
        }
    }
}

// === ЛОГИКА UI (Селекты и Списки) ===
function populateStylesSelect(themeId, currentStyle = null) {
    const styleSelect = document.getElementById('style');
    styleSelect.innerHTML = ""; // Очистка

    const themeData = cachedThemesData.find(t => t.id === themeId);

    if (themeData && themeData.styles) {
        themeData.styles.forEach(style => {
            const opt = document.createElement("option");
            opt.value = style;
            opt.textContent = style.charAt(0).toUpperCase() + style.slice(1);
            
            if (style === currentStyle) {
                opt.selected = true;
            }
            styleSelect.appendChild(opt);
        });
        
        // Если текущий стиль не найден в новой теме, выбираем первый
        if (currentStyle && !themeData.styles.includes(currentStyle) && themeData.styles.length > 0) {
            styleSelect.value = themeData.styles[0];
             // Можно вызвать setStyle(themeData.styles[0]) если хотим авто-переключение
        }
    }
}

// --- ИНИЦИАЛИЗАЦИЯ (При старте) ---
function loadTheme(themeName, styleName, themes) {
    cachedThemesData = themes;

    const oldSelect = document.getElementById('theme');
    
    const newSelect = oldSelect.cloneNode(false);
    
    cachedThemesData.forEach(theme => {
        const option = document.createElement("option");
        option.value = theme.id;
        option.textContent = theme.name;
        newSelect.appendChild(option);
    });

    oldSelect.parentNode.replaceChild(newSelect, oldSelect);

    newSelect.value = themeName;

    if (newSelect.value !== themeName && newSelect.options.length > 0) {
        // Если тема не найдена, выбираем первую и сообщаем об этом
        themeName = newSelect.options[0].value;
        newSelect.value = themeName;
    }

    // 6. Заполняем стили и применяем визуал
    populateStylesSelect(themeName, styleName);
    setTheme(themeName);
    setStyle(styleName);

    // 7. Вешаем обработчик
    newSelect.addEventListener("change", (e) => {
        const selectedTheme = e.target.value;
        populateStylesSelect(selectedTheme);
        changeTheme(selectedTheme);
    });
}

// --- ОБНОВЛЕНИЕ (После импорта) ---
window.updateThemeList = function(themes) {
    console.log("Theme list updated:", themes);
    
    // 1. Обновляем глобальные данные!
    cachedThemesData = themes;
    
    const themeSelect = document.getElementById('theme');
    const currentThemeId = themeSelect.value;
    const currentStyleId = document.getElementById('style').value;

    // 2. Перерисовываем список тем
    themeSelect.innerHTML = "";
    cachedThemesData.forEach(theme => {
        const option = document.createElement("option");
        option.value = theme.id;
        option.textContent = theme.name;
        
        // Пытаемся сохранить выбор
        if (theme.id === currentThemeId) {
            option.selected = true;
        }
        themeSelect.appendChild(option);
    });

    // 3. Обновляем стили (потому что в текущей теме могли появиться новые)
    populateStylesSelect(currentThemeId, currentStyleId);
}

// === ВЗАИМОДЕЙСТВИЕ С PYTHON ===

function changeTheme(theme) {
    setTheme(theme);
    // При смене темы стиль сбрасывается на дефолтный или первый доступный
    const styleSelect = document.getElementById('style');
    const firstStyle = styleSelect.options.length > 0 ? styleSelect.options[0].value : 'default';
    
    setStyle(firstStyle); // Применяем стиль визуально
    
    window.pywebview.api.saveTheme(theme);
    window.pywebview.api.saveStyle(firstStyle);
}

function changeStyle(style) {
    setStyle(style);
    window.pywebview.api.saveStyle(style);
}

// Слушатели для UI
document.getElementById("style").addEventListener('change', (e) => {
    changeStyle(e.target.value);
});

// Кнопки открытия папки и импорта
const btnOpenFolder = document.getElementById('open-theme_folder');
if(btnOpenFolder) {
    btnOpenFolder.addEventListener('click', ()=>{
        window.pywebview.api.open_theme_folder();
    });
}

const btnHelp = document.getElementById('help-theme');
if(btnHelp) {
    btnHelp.addEventListener('click', ()=>{
        if(typeof openInfoModal === 'function') openInfoModal('themes');
    });
}

const btnImport = document.getElementById('btn-import-theme');
if (btnImport) {
    btnImport.addEventListener('click', () => {
        window.pywebview.api.import_theme();
    });
}