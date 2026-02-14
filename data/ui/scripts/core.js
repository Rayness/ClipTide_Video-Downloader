 /* Copyright (C) 2025 Rayness */
 /* This program is free software under GPLv3. See LICENSE for details. */

// --- Инициализация и Вкладки ---
document.addEventListener('DOMContentLoaded', function() {
    window.isDomReady = true;
    
    // Инициализация табов основного меню
    const buttons = document.querySelectorAll('.tab-btn');
    const name = document.getElementById('name');
    
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            // Убираем актив у всех
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.content').forEach(block => block.classList.remove('active'));
            
            // Активируем текущий
            this.classList.add('active');
            
            const tabId = this.getAttribute('data-tab');
            const block = document.getElementById(tabId);
            if(block) {
                block.classList.add('active');
                if(name) name.textContent = block.getAttribute('data-status');
            }
        });
    });
    
    // Активируем первую вкладку
    if(buttons.length > 0) buttons[0].click();

    // Блокируем кнопку стоп конвертера при старте
    const stopBtnConv = document.getElementById("stopBtn_conv");
    if(stopBtnConv) stopBtnConv.disabled = true;
});

// --- Логирование ---
window.addLog = function(message, level = 'info', code = null) {
    const logContainer = document.getElementById("app-logs");
    if (!logContainer) return;

    // 1. Проверяем, прижат ли скролл к низу (с допуском 50px)
    // Если разница между полной высотой и текущей прокруткой меньше высоты окна + 50px
    const isAtBottom = (logContainer.scrollHeight - logContainer.scrollTop) <= (logContainer.clientHeight + 50);

    const entry = document.createElement("div");
    entry.className = `log-entry ${level}`;
    
    if (code) {
        entry.setAttribute('data-code', code);
        entry.title = `Код: ${code}`;
    }
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    entry.innerHTML = `<span class="log-time">${timeStr}</span><span class="log-msg">${message}</span>`;
    
    // 2. Вставляем элемент
    logContainer.appendChild(entry);
    
    // 3. Если пользователь был внизу (следил за логом) - скроллим к новому элементу
    if (isAtBottom) {
        // setTimeout дает браузеру время отрисовать высоту элемента
        setTimeout(() => {
            entry.scrollIntoView({ behavior: "smooth", block: "end" });
            // Или жесткий вариант, если smooth глючит:
            // logContainer.scrollTop = logContainer.scrollHeight;
        }, 10);
    }
}

// --- Вспомогательные функции ---
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Обработка кнопки уведомлений в шапке
const notifiBtn = document.getElementById('notifications-btn');
if (notifiBtn) {
    notifiBtn.addEventListener('click', () => {
        // Эмулируем клик по скрытому табу или просто показываем секцию
        // У нас есть секция id="12" для уведомлений
        
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.content').forEach(block => block.classList.remove('active'));
        
        const block = document.getElementById('12');
        if (block) {
            block.classList.add('active');
            const title = window.i18n?.sections?.notifications || "Notifications";
            document.getElementById('name').textContent = title;
        }
        
        // Визуально подсвечиваем кнопку (опционально)
        notifiBtn.classList.add('active');
    });
}