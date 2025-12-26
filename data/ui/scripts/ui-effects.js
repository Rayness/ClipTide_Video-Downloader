// Copyright (C) 2025 Rayness
// This program is free software under GPLv3. See LICENSE for details.

document.addEventListener("DOMContentLoaded", () => {
    const elements = document.querySelectorAll(".fade-in");
    const buttons = document.querySelectorAll(".main__button");

    buttons.forEach(button => {
        button.addEventListener("mouseenter", () => {
            button.style.transform = "scale(1.1)";
        });

        button.addEventListener("mouseleave", () => {
            button.style.transform = "scale(1)";
        });

        button.addEventListener("mousedown", () => {
            button.style.transform = "scale(0.95)";
            button.style.boxShadow = "0px 0px 15px rgba(74, 86, 198, 0.5)";
        });

        button.addEventListener("mouseup", () => {
            button.style.transform = "scale(1.05)";
            setTimeout(() => {
                button.style.transform = "scale(1)";
                button.style.boxShadow = "none";
            }, 150);
        });
    });

    elements.forEach((el) => {
        el.style.opacity = 0;
        el.style.transform = "translateY(20px)";
        setTimeout(() => {
            el.style.transition = "opacity 0.3s ease-out, transform 0.3s ease-out";
            el.style.opacity = 1;
            el.style.transform = "translateY(0)";
        }, 100);
    });

    initCustomSelects();
});

function updateProgress(value) {
    const progressBar = document.getElementById("progress-fill");
    progressBar.style.transition = "width 0.5s ease-in-out";
    progressBar.style.width = value + "%";
}


const buttons = document.querySelectorAll('.tab-btn');

    buttons.forEach(btn => {
    btn.addEventListener('click', () => {
        buttons.forEach(b => b.classList.remove('active')); // убрать у всех
        btn.classList.add('active'); // добавить только этой
    });
});

// --- CUSTOM SELECT LOGIC ---

function initCustomSelects() {
    const selects = document.querySelectorAll('select.js-custom-select');
    
    selects.forEach(el => {
        // Если уже инициализирован - пропускаем (чтобы не дублировать при повторном вызове)
        if (el.parentNode.classList.contains('custom-select-wrapper')) return;

        // Прячем оригинал
        // Но не display:none, чтобы он оставался в потоке (иногда важно), а просто скрываем
        // В нашем случае лучше обернуть
        
        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select-wrapper custom-select';
        
        el.parentNode.insertBefore(wrapper, el);
        wrapper.appendChild(el);
        
        // Создаем "Голову"
        const trigger = document.createElement('div');
        trigger.className = 'custom-select-trigger';
        // Текст выбранного элемента
        const selectedOption = el.options[el.selectedIndex];
        trigger.textContent = selectedOption ? selectedOption.textContent : 'Select';
        
        // Создаем "Список"
        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'custom-options';
        
        // Наполняем опциями
        Array.from(el.options).forEach(option => {
            const optDiv = document.createElement('div');
            optDiv.className = 'custom-option';
            optDiv.textContent = option.textContent;
            optDiv.dataset.value = option.value;
            
            if (option.selected) optDiv.classList.add('selected');
            if (option.disabled) optDiv.classList.add('disabled');
            
            // Клик по опции
            optDiv.addEventListener('click', function(e) {
                if (option.disabled) return;
                
                // 1. Визуальное обновление
                trigger.textContent = this.textContent;
                wrapper.classList.remove('open');
                
                wrapper.querySelectorAll('.custom-option').forEach(o => o.classList.remove('selected'));
                this.classList.add('selected');
                
                // 2. Обновление оригинала
                el.value = this.dataset.value;
                
                // 3. Триггер события change (чтобы сработал скрипт логики)
                const event = new Event('change', { bubbles: true });
                el.dispatchEvent(event);
                // Также триггерим input на всякий случай
                el.dispatchEvent(new Event('input', { bubbles: true }));
            });
            
            optionsDiv.appendChild(optDiv);
        });
        
        wrapper.appendChild(trigger);
        wrapper.appendChild(optionsDiv);
        
        // Открытие/Закрытие
        trigger.addEventListener('click', function(e) {
            // Закрываем все другие
            document.querySelectorAll('.custom-select').forEach(s => {
                if (s !== wrapper) s.classList.remove('open');
            });
            wrapper.classList.toggle('open');
            e.stopPropagation();
        });
        
        // Слушаем изменения оригинала (если JS изменит value программно)
        el.addEventListener('change', function() {
            const newSelected = el.options[el.selectedIndex];
            trigger.textContent = newSelected.textContent;
            
            optionsDiv.querySelectorAll('.custom-option').forEach(o => {
                if (o.dataset.value === el.value) o.classList.add('selected');
                else o.classList.remove('selected');
            });
        });
    });
}

// Закрытие при клике вне
window.addEventListener('click', function(e) {
    if (!e.target.closest('.custom-select')) {
        document.querySelectorAll('.custom-select').forEach(s => s.classList.remove('open'));
    }
});

// Функция для обновления опций кастомного селекта, если оригинал изменился
function refreshCustomSelectOptions() {
    const selects = document.querySelectorAll('select.js-custom-select');
    selects.forEach(el => {
        const wrapper = el.closest('.custom-select-wrapper');
        if (!wrapper) return;
        
        const optionsDiv = wrapper.querySelector('.custom-options');
        optionsDiv.innerHTML = ''; // Чистим старые
        
        // Создаем заново
        Array.from(el.options).forEach(option => {
            const optDiv = document.createElement('div');
            optDiv.className = 'custom-option';
            optDiv.textContent = option.textContent;
            optDiv.dataset.value = option.value;
            
            if (option.selected) optDiv.classList.add('selected');
            if (option.disabled) optDiv.classList.add('disabled');
            
            optDiv.addEventListener('click', function(e) {
                // ... (копируем логику клика из initCustomSelects или выносим в отдельную функцию) ...
                if (option.disabled) return;
                wrapper.querySelector('.custom-select-trigger').textContent = this.textContent;
                wrapper.classList.remove('open');
                wrapper.querySelectorAll('.custom-option').forEach(o => o.classList.remove('selected'));
                this.classList.add('selected');
                el.value = this.dataset.value;
                el.dispatchEvent(new Event('change', { bubbles: true }));
            });
            optionsDiv.appendChild(optDiv);
        });
        
        // Обновляем заголовок
        const selectedOption = el.options[el.selectedIndex];
        if (selectedOption) {
            wrapper.querySelector('.custom-select-trigger').textContent = selectedOption.textContent;
        }
    });
}