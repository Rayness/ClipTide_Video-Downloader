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
window.addLog = function(message) {
    const logContainer = document.getElementById("app-logs");
    if (!logContainer) return;

    const entry = document.createElement("div");
    entry.className = "log-entry";
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    entry.innerText = `[${timeStr}] ${message}`;
    logContainer.prepend(entry);
}

// --- Вспомогательные функции ---
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}