// data/ui/scripts/store.js

// --- 1. ЛОГИКА ТАБОВ (Модули <-> Темы) ---
// Используем делегирование или безопасный поиск
const storeTabs = document.querySelectorAll('.store-tab');

if (storeTabs.length > 0) {
    storeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Убираем актив у всех кнопок
            storeTabs.forEach(t => t.classList.remove('active'));
            // Убираем актив у всех секций
            document.querySelectorAll('.store-section').forEach(s => s.classList.remove('active'));
            
            // Активируем нажатую
            tab.classList.add('active');
            
            // Показываем секцию
            const targetId = tab.getAttribute('data-target');
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.classList.add('active');
                
                // АВТОЗАГРУЗКА: Если переключились на Темы и там пусто — грузим
                if (targetId === 'store-themes') {
                    const list = document.getElementById('themes-list');
                    // Если внутри нет карточек, значит пусто
                    if (list && !list.querySelector('.store-card')) {
                        loadThemesData();
                    }
                }
                // АВТОЗАГРУЗКА: То же для Модулей
                if (targetId === 'store-modules') {
                    const list = document.getElementById('modules-list');
                    if (list && !list.querySelector('.store-card')) {
                        loadModulesData();
                    }
                }
            }
        });
    });
}

// --- 2. ФУНКЦИИ ЗАГРУЗКИ (Обертки) ---

function loadModulesData() {
    const list = document.getElementById('modules-list');
    if (list) list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666; margin-top: 2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Загрузка модулей...</div>';
    
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.store_fetch_data();
    }
}

function loadThemesData() {
    const list = document.getElementById('themes-list');
    if (list) list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666; margin-top: 2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Загрузка тем...</div>';
    
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.store_fetch_themes();
    }
}

// --- 3. КНОПКИ УПРАВЛЕНИЯ ---

// Кнопка обновления (круговая стрелка в заголовке магазина)
const btnRefreshStore = document.getElementById('btn-refresh-store');
if (btnRefreshStore) {
    btnRefreshStore.addEventListener('click', () => {
        const activeSection = document.querySelector('.store-section.active');
        
        if (activeSection && activeSection.id === 'store-themes') {
            loadThemesData();
        } else {
            loadModulesData();
        }
    });
}

// Клик по кнопке "Магазин" в левом меню (ID="coming-soon")
const btnOpenStore = document.getElementById('coming-soon');
if (btnOpenStore) {
    btnOpenStore.addEventListener('click', () => {
        // Проверяем, пусто ли в модулях. Если да — грузим.
        const list = document.getElementById('modules-list');
        if (list && !list.querySelector('.store-card')) {
            loadModulesData();
        }
    });
}


// --- 4. РЕНДЕР МОДУЛЕЙ (Вызывается из Python) ---

window.updateStoreList = function(available, installedIds) {
    const container = document.getElementById('modules-list');
    if (!container) return;
    container.innerHTML = "";

    if (!available || available.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666;">Каталог пуст или недоступен</div>';
        return;
    }

    available.forEach(mod => {
        const isInstalled = installedIds.includes(mod.id);
        
        // Локализация кнопок
        const t = window.i18n?.store || {};
        const btnTextDownload = t.btn_download || 'Download';
        const btnTextUninstall = t.btn_uninstall || 'Uninstall';
        const btnTextInstall = t.btn_install || 'Install';

        const btnClass = isInstalled ? 'btn-store uninstall' : 'btn-store install';
        // Если установлено - текст "Удалить", если нет - "Скачать"
        const btnText = isInstalled 
            ? `<i class="fa-solid fa-trash"></i> ${btnTextUninstall}` 
            : `<i class="fa-solid fa-download"></i> ${btnTextDownload}`;
            
        const btnAction = isInstalled ? `uninstallModule('${mod.id}')` : `installModule('${mod.id}')`;
        
        // Иконка
        let iconHtml = '<i class="fa-solid fa-cube"></i>';
        if (mod.icon && (mod.icon.endsWith('.svg') || mod.icon.endsWith('.png'))) {
             // Можно добавить обработку URL
             iconHtml = `<img src="src/${mod.icon}" style="width:32px; height:32px;">`; 
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

// --- 5. РЕНДЕР ТЕМ (Вызывается из Python) ---

window.updateThemesStoreList = function(available, installedIds) {
    const container = document.getElementById('themes-list');
    if (!container) return;
    container.innerHTML = "";

    if (!available || available.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666;">Каталог пуст</div>';
        return;
    }

    const t = window.i18n?.store || {};

    available.forEach(theme => {
        const isInstalled = installedIds.includes(theme.id);
        const btnClass = isInstalled ? 'btn-store uninstall' : 'btn-store install';
        const btnText = isInstalled 
            ? `<i class="fa-solid fa-trash"></i> ${t.btn_uninstall || 'Uninstall'}` 
            : `<i class="fa-solid fa-download"></i> ${t.btn_install || 'Install'}`;
            
        // Для удаления не нужен URL, для установки нужен
        // Экранируем кавычки в URL
        const rawUrl = theme.download_url || "";
        const safeUrl = rawUrl.replace(/'/g, "\\'");
        const btnAction = isInstalled 
            ? `deleteTheme('${theme.id}')` 
            : `installTheme('${theme.id}', '${safeUrl}')`;

        const card = document.createElement('div');
        card.className = 'store-card theme-card';
        card.id = `theme-card-${theme.id}`;
        
        let previewStyle = '';
        if (theme.preview && (theme.preview.startsWith('http') || theme.preview.startsWith('data:'))) {
            previewStyle = `background-image: url('${theme.preview}');`;
        } else {
            // Фолбек - цвет из JSON
            previewStyle = `background: ${theme.color || 'linear-gradient(45deg, #333, #555)'};`;
        }

        card.innerHTML = `
            <div class="theme-preview" style="${previewStyle}"></div>
            <div class="card-content">
                <h4>${theme.name}</h4>
                <p>${theme.description || 'No description'}</p>
                <div class="card-meta">${t.author || 'Author'}: ${theme.author || 'Unknown'}</div>
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


// --- 6. ДЕЙСТВИЯ (Install / Uninstall) ---

window.installModule = function(id) {
    const btn = document.getElementById(`btn-mod-${id}`);
    if(btn) {
        btn.disabled = true;
        btn.innerText = "...";
    }
    window.pywebview.api.store_install_module(id);
}

window.uninstallModule = function(id) {
    if(!confirm("Удалить этот модуль?")) return;
    window.pywebview.api.store_uninstall_module(id);
}

window.installTheme = function(id, url) {
    const btn = document.getElementById(`btn-theme-${id}`);
    if(btn) {
        btn.disabled = true;
        btn.innerText = "...";
    }
    window.pywebview.api.store_install_theme(id, url);
}

window.deleteTheme = function(id) {
    if(id === 'cliptide') { alert("Нельзя удалить стандартную тему"); return; }
    if(!confirm("Удалить эту тему?")) return;
    window.pywebview.api.store_delete_theme(id);
}


// --- 7. ПРОГРЕСС БАРЫ ---

window.updateStoreProgress = function(id, percent, status) {
    const bar = document.getElementById(`prog-mod-${id}`);
    const btn = document.getElementById(`btn-mod-${id}`);
    const t = window.i18n?.store || {};

    if (bar) bar.style.width = `${percent}%`;
    
    if(btn) {
        if (status === 'downloading') btn.innerText = `${percent}%`;
        else if (status === 'extracting') btn.innerText = t.status_extracting || "Unpacking...";
        else if (status === 'done') {
            btn.className = 'btn-store uninstall';
            btn.innerHTML = `<i class="fa-solid fa-trash"></i> ${t.btn_uninstall || 'Delete'}`;
            btn.disabled = false;
            btn.onclick = function() { uninstallModule(id); };
            if(bar) setTimeout(() => bar.style.width = '0%', 1000);
        } else if (status === 'error') {
            btn.innerText = t.status_error || "Error";
            btn.disabled = false;
            if(bar) bar.style.background = 'var(--danger-color)';
        }
    }
}

window.updateThemeProgress = function(id, percent, status) {
    const bar = document.getElementById(`prog-theme-${id}`);
    const btn = document.getElementById(`btn-theme-${id}`);
    const t = window.i18n?.store || {};

    if (bar) bar.style.width = `${percent}%`;

    if(btn) {
        if (status === 'downloading') btn.innerText = `${percent}%`;
        else if (status === 'extracting') btn.innerText = t.status_extracting || "Unpacking...";
        else if (status === 'done') {
            btn.className = 'btn-store uninstall';
            btn.innerHTML = `<i class="fa-solid fa-trash"></i> ${t.btn_uninstall || 'Delete'}`;
            btn.disabled = false;
            btn.onclick = function() { deleteTheme(id); };
            if(bar) setTimeout(() => bar.style.width = '0%', 1000);
        } else if (status === 'error') {
            btn.innerText = t.status_error || "Error";
            btn.disabled = false;
            if(bar) bar.style.background = 'var(--danger-color)';
        }
    }
}