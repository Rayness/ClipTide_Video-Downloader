 /* Copyright (C) 2025 Rayness */
 /* This program is free software under GPLv3. See LICENSE for details. */

// --- STORE TABS (ВОССТАНОВЛЕНО!) ---
document.querySelectorAll('.store-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // 1. Убираем класс active у всех кнопок
        document.querySelectorAll('.store-tab').forEach(t => t.classList.remove('active'));
        // 2. Скрываем все секции
        document.querySelectorAll('.store-section').forEach(s => s.classList.remove('active'));
        
        // 3. Активируем нажатую
        tab.classList.add('active');
        
        // 4. Показываем нужную секцию
        const targetId = tab.getAttribute('data-target');
        const targetSection = document.getElementById(targetId);
        if (targetSection) {
            targetSection.classList.add('active');
            
            // Автозагрузка тем при переключении
            if (targetId === 'store-themes') {
                const list = document.getElementById('themes-list');
                if (!list.querySelector('.theme-card')) {
                    list.innerHTML = '<div style="text-align: center; color: #666; margin-top: 2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Загрузка тем...</div>';
                    window.pywebview.api.store_fetch_themes();
                }
            }
        }
    });
});

// Кнопка обновления
document.getElementById('btn-refresh-store').addEventListener('click', () => {
    const activeSection = document.querySelector('.store-section.active');
    
    if (activeSection && activeSection.id === 'store-themes') {
        document.getElementById('themes-list').innerHTML = '...';
        window.pywebview.api.store_fetch_themes();
    } else {
        document.getElementById('modules-list').innerHTML = '...';
        window.pywebview.api.store_fetch_data();
    }
});

// Автозагрузка при входе в "Store"
document.getElementById('coming-soon').addEventListener('click', () => { // id кнопки таба в меню
    const list = document.getElementById('modules-list');
    if (!list.querySelector('.module-card')) {
        window.pywebview.api.store_fetch_data();
    }
});

// --- MODULES ---
window.updateStoreList = function(available, installedIds) {
    const container = document.getElementById('modules-list');
    container.innerHTML = "";

    const t = window.i18n.store || {};

    if (!available || available.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #666;">Каталог пуст</div>';
        return;
    }

    available.forEach(mod => {
        const isInstalled = installedIds.includes(mod.id);
        const btnClass = isInstalled ? 'btn-store uninstall' : 'btn-store install';
        const btnText = isInstalled 
            ? `<i class="fa-solid fa-trash"></i> ${t.btn_uninstall || 'Uninstall'}` 
            : `<i class="fa-solid fa-download"></i> ${t.btn_download || 'Download'}`;
        const btnAction = isInstalled ? `uninstallModule('${mod.id}')` : `installModule('${mod.id}')`;
        
        let iconHtml = '<i class="fa-solid fa-cube"></i>';
        if (mod.icon && mod.icon.endsWith('.svg')) {
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
                <button class="${btnClass}" id="btn-mod-${mod.id}" onclick="${btnAction}">${btnText}</button>
            </div>
            <div class="mod-progress" id="prog-mod-${mod.id}"></div>
        `;
        container.appendChild(card);
    });
}

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

window.updateStoreProgress = function(id, percent, status) {
    const bar = document.getElementById(`prog-mod-${id}`);
    const btn = document.getElementById(`btn-mod-${id}`);

    const t = window.i18n.store || {};

    if (bar) bar.style.width = `${percent}%`;
    
    if (status === 'downloading') btn.innerText = t.status_downloading || `${percent}%`;
    else if (status === 'extracting') btn.innerText = t.status_extracting || "Extracting...";
    else if (status === 'done') {
        btn.className = 'btn-store uninstall';
        btn.innerHTML = `<i class="fa-solid fa-trash"></i> ${t.btn_uninstall || 'Uninstall'}`;
        btn.disabled = false;
        btn.onclick = function() { uninstallModule(id); };
        if(bar) setTimeout(() => bar.style.width = '0%', 1000);
    } else if (status === 'error') {
        btn.innerText = "Ошибка";
        btn.disabled = false;
        if(bar) bar.style.background = 'var(--danger-color)';
    }
}

// --- THEMES ---
window.updateThemesStoreList = function(available, installedIds) {
    const container = document.getElementById('themes-list');
    container.innerHTML = "";

    const t = window.i18n.store || {};

    if (!available || available.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #666;">Каталог пуст</div>';
        return;
    }

    available.forEach(theme => {
        const isInstalled = installedIds.includes(theme.id);
        const btnClass = isInstalled ? 'btn-store uninstall' : 'btn-store install';
        const btnText = isInstalled 
            ? `<i class="fa-solid fa-trash"></i> ${t.btn_uninstall || 'Uninstall'}` 
            : `<i class="fa-solid fa-download"></i> ${t.btn_download || 'Download'}`;
        const btnAction = isInstalled ? `deleteTheme('${theme.id}')` : `installTheme('${theme.id}', '${theme.download_url}')`;

        const card = document.createElement('div');
        card.className = 'store-card theme-card';
        card.id = `theme-card-${theme.id}`;
        
        let previewStyle = '';
        if (theme.preview && (theme.preview.startsWith('http') || theme.preview.startsWith('data:'))) {
            previewStyle = `background-image: url('${theme.preview}');`;
        } else {
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
                <button class="${btnClass}" id="btn-theme-${theme.id}" onclick="${btnAction}">${btnText}</button>
            </div>
            <div class="mod-progress" id="prog-theme-${theme.id}"></div>
        `;
        container.appendChild(card);
    });
}

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

window.updateThemeProgress = function(id, percent, status) {
    const bar = document.getElementById(`prog-theme-${id}`);
    const btn = document.getElementById(`btn-theme-${id}`);
    if (bar) bar.style.width = `${percent}%`;

    if (status === 'downloading') btn.innerText = `${percent}%`;
    else if (status === 'extracting') btn.innerText = "Установка...";
    else if (status === 'done') {
        btn.className = 'btn-store uninstall';
        btn.innerHTML = 'Удалить';
        btn.disabled = false;
        btn.onclick = function() { deleteTheme(id); };
        if(bar) setTimeout(() => bar.style.width = '0%', 1000);
    } else if (status === 'error') {
        btn.innerText = "Ошибка";
        btn.disabled = false;
        if(bar) bar.style.background = 'var(--danger-color)';
    }
}