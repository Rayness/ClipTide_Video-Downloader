 /* Copyright (C) 2025 Rayness */
 /* This program is free software under GPLv3. See LICENSE for details. */

let cachedNotifications = [];

function loadNotifications(data) {
    const container = document.getElementById("notification-container");
    if (!container) return; // Защита
    container.innerHTML = "";
    
    // Обновляем кэш
    cachedNotifications = Array.isArray(data) ? data : [];
    console.log("Notifications loaded:", cachedNotifications.length);

    const sortedData = [...cachedNotifications].reverse();
    const tHistory = window.i18n?.history || {};

    if (sortedData.length === 0) {
        container.innerHTML = `<div style="text-align:center; color:#777; margin-top:2rem;">${tHistory.empty || 'History is empty'}</div>`;
        return;
    }

    sortedData.forEach(n => {
        const block = document.createElement("div");
        block.className = "block fade-in";
        block.id = "notif-" + n.id;
        
        // Определяем иконку
        let icon = '<i class="fa-solid fa-info-circle"></i>';
        if (n.source == "downloader") icon = '<i class="fa-solid fa-download"></i>';
        if (n.source == "converter") icon = '<i class="fa-solid fa-rotate"></i>';

        // Прозрачность для прочитанных
        if (n.read === "True") {
            block.style.opacity = "0.7";
        }

        block.innerHTML = `
            <div class="icon">${icon}</div>
            <div class="body">
                <h4>${n.title}</h4>
                <p>${n.message}</p>
                <div class="datetime">
                    <p>${n.timestamp}</p>
                </div>
            </div>
            <div class="remove">
                <button class="delete-notif-btn" title="${tHistory.delete_title || 'Delete'}">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;

        // ОБРАБОТЧИК КЛИКА ПО КАРТОЧКЕ
        block.addEventListener("click", () => {
            console.log("Card clicked, ID:", n.id);
            openHistoryModal(n.id);
        });

        // ОБРАБОТЧИК КЛИКА ПО УДАЛЕНИЮ
        const delBtn = block.querySelector(".delete-notif-btn");
        delBtn.addEventListener("click", (e) => {
            e.stopPropagation(); // Чтобы не открывалась модалка
            deleteNotification(n.id);
        });

        container.appendChild(block);
    });
}

window.deleteNotification = function(id) {
    // Удаляем визуально сразу
    const item = document.getElementById(`notif-${id}`);
    if (item) item.remove();
    
    // Обновляем кэш
    cachedNotifications = cachedNotifications.filter(n => n.id != id);
    
    // Шлем в Python
    window.pywebview.api.delete_notification(id);
}

function openHistoryModal(id) {
    console.log("Opening modal for ID:", id);
    
    // Ищем уведомление в кэше. Сравниваем как строки на всякий случай.
    const notif = cachedNotifications.find(n => String(n.id) === String(id));
    
    if (!notif) {
        console.error("Notification not found in cache!");
        return;
    }

    const modal = document.getElementById("modal-history");
    if (!modal) {
        console.error("Modal element #modal-history not found in DOM!");
        return;
    }

    // Помечаем прочитанным
    if (notif.read !== "True") {
        window.pywebview.api.mark_notification_as_read(id);
        const el = document.getElementById(`notif-${id}`);
        if(el) el.style.opacity = "0.7";
        notif.read = "True";
    }

    try {
        // Заполняем данными
        const payload = (notif && typeof notif.payload === "object" && notif.payload) ? notif.payload : {};
        const tHistory = window.i18n?.history || {};
        
        document.getElementById("hist-title").innerText = notif.title || "";
        document.getElementById("hist-date").innerText = notif.timestamp || "";
        
        const img = document.getElementById("hist-img");
        // Проверка, есть ли картинка, иначе дефолт
        img.src = payload.thumbnail ? payload.thumbnail : "src/default_thumbnail.png";
        
        // Формат
        let fmtInfo = tHistory.info_missing || "No details";
        if (typeof payload.format === "string" && payload.format.length > 0) {
            fmtInfo = payload.format.toUpperCase();
            if (payload.resolution) fmtInfo += ` / ${payload.resolution}p`;
        }
        document.getElementById("hist-fmt").innerText = fmtInfo;

        // Ссылка
        const linkEl = document.getElementById("hist-link");
        if (payload.url) {
            linkEl.href = payload.url;
            linkEl.innerText = payload.url;
            linkEl.style.display = "block";
        } else {
            linkEl.style.display = "none";
        }

        // Кнопка ре-скачивания
        const btnRedownload = document.getElementById("btn-redownload");
        if (payload.url) {
            btnRedownload.style.display = "flex";
            btnRedownload.onclick = function() {
                modal.classList.remove("show");
                
                // Переход на вкладку 1 (Загрузчик)
                const tab = document.querySelector('[data-tab="1"]');
                if(tab) tab.click();

                // Создаем заглушку и отправляем запрос
                const tempId = Date.now().toString();
                if (typeof window.createLoadingItem === 'function') window.createLoadingItem(tempId);

                window.pywebview.api.addVideoToQueue(
                    payload.url, 
                    payload.format || 'mp4', 
                    payload.resolution || '1080', 
                    tempId
                );
            };
        } else {
            btnRedownload.style.display = "none";
        }

        // Кнопка открытия папки
        const btnFolder = document.getElementById("btn-hist-folder");
        if (payload.folder) {
            btnFolder.style.display = "flex";
            btnFolder.onclick = function() {
                // Вызываем Python метод
                window.pywebview.api.open_path(payload.folder);
            };
        } else {
            btnFolder.style.display = "none";
        }


        // Кнопка удаления
        const btnDel = document.getElementById("btn-hist-delete");
        btnDel.onclick = function() {
            deleteNotification(id);
            modal.classList.remove("show");
        };
    } catch (err) {
        console.error("Failed to render history modal:", err);
    }

    // Показываем окно
    modal.classList.add("show");
}

// Закрытие модалки
const closeBtn = document.getElementById("close-history");
if(closeBtn) {
    closeBtn.addEventListener("click", () => {
        document.getElementById("modal-history").classList.remove("show");
    });
}

// Закрытие по клику на фон
const modalHist = document.getElementById("modal-history");
if(modalHist) {
    modalHist.addEventListener("click", (e) => {
        if (e.target === modalHist) {
            modalHist.classList.remove("show");
        }
    });
}

// ... Оставь код переключателей settings (load_settingsNotificatios и event listeners) ...
function load_settingsNotificatios(down, conv) {
    const swD = document.getElementById('switch_notifiDownload');
    const swC = document.getElementById('switch_notifiConvertion');
    if(swD) swD.checked = (down === "True");
    if(swC) swC.checked = (conv === "True");
}

const swD = document.getElementById('switch_notifiDownload');
if(swD) swD.addEventListener('change', (e) => {
    window.pywebview.api.switch_notifi("downloads", e.target.checked ? "True" : "False");
});

const swC = document.getElementById('switch_notifiConvertion');
if(swC) swC.addEventListener('change', (e) => {
    window.pywebview.api.switch_notifi("conversion", e.target.checked ? "True" : "False");
});