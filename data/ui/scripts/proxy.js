// Copyright (C) 2025 Rayness

// Переключатель вкл/выкл
document.getElementById('switch_proxy').addEventListener('change', function () {
    const checkbox = document.getElementById('switch_proxy');
    const input = document.getElementById('input_proxy');
    const btnCheck = document.getElementById('proxy_check');
    const btnApply = document.getElementById('proxy_apply');

    if (checkbox.checked) {
        window.pywebview.api.switch_proxy("True");
        input.disabled = false;
        btnCheck.disabled = false;
        btnApply.disabled = false;
    } else {
        input.disabled = true;
        btnCheck.disabled = true;
        btnApply.disabled = true;
        window.pywebview.api.switch_proxy("False");
        
        // Сбрасываем статус
        setProxyCheckStatus("none", "");
    }
});

// Кнопка Сохранить
document.getElementById('proxy_apply').addEventListener('click', function () {
    const input = document.getElementById('input_proxy').value;
    window.pywebview.api.switch_proxy_url(input);
    // Можно добавить визуал, что сохранено
    const btn = document.getElementById('proxy_apply');
    const originalIcon = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i>';
    setTimeout(() => btn.innerHTML = originalIcon, 1000);
});

// Кнопка Проверить
document.getElementById('proxy_check').addEventListener('click', function () {
    const input = document.getElementById('input_proxy').value;
    if (!input) return;
    
    window.pywebview.api.test_proxy(input);
});

// Функция вызывается из Python для отображения результата
window.setProxyCheckStatus = function(status, message) {
    const statusText = document.getElementById('proxy-status-text');
    const btnCheck = document.getElementById('proxy_check');
    
    if (status === "loading") {
        statusText.style.color = "#aaa";
        statusText.innerText = message;
        btnCheck.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        btnCheck.disabled = true;
    } 
    else if (status === "success") {
        statusText.style.color = "var(--green)"; // или #4caf50
        statusText.innerText = message;
        btnCheck.innerHTML = '<i class="fa-solid fa-bolt"></i>';
        btnCheck.disabled = false;
    } 
    else if (status === "error") {
        statusText.style.color = "var(--danger-color)";
        statusText.innerText = message;
        btnCheck.innerHTML = '<i class="fa-solid fa-bolt"></i>';
        btnCheck.disabled = false;
    }
    else {
        statusText.innerText = "";
        btnCheck.innerHTML = '<i class="fa-solid fa-bolt"></i>';
    }
}

// Загрузка настроек при старте
function loadproxy(proxy, proxy_enabled) {
    const input = document.getElementById('input_proxy');
    const checkbox = document.getElementById('switch_proxy');
    const btnCheck = document.getElementById('proxy_check');
    const btnApply = document.getElementById('proxy_apply');

    input.value = proxy;

    if (proxy_enabled == "True") {
        input.disabled = false;
        checkbox.checked = true;
        btnCheck.disabled = false;
        btnApply.disabled = false;
    } else {
        input.disabled = true;
        checkbox.checked = false;
        btnCheck.disabled = true;
        btnApply.disabled = true;
    }
}

document.getElementById('help-proxy').addEventListener('click', () => {
    if(typeof openInfoModal === 'function') openInfoModal('proxy');
});