// Copyright (C) 2025 Rayness
// This program is free software under GPLv3. See LICENSE for details.

/**
 * ClipTide API Integration
 * Обработка авторизации и синхронизации с ClipTide
 */

(function() {
    'use strict';

    // Элементы UI
    const elements = {
        // Auth block
        authBlock: document.getElementById('cliptide-auth-block'),
        profileBlock: document.getElementById('cliptide-profile-block'),
        emailInput: document.getElementById('cliptide-email'),
        passwordInput: document.getElementById('cliptide-password'),
        authStatus: document.getElementById('cliptide-auth-status'),

        // Profile block
        userEmail: document.getElementById('cliptide-user-email'),
        avatarInitial: document.getElementById('cliptide-avatar-initial'),
        syncToggle: document.getElementById('cliptide-sync-toggle'),
        syncStatus: document.getElementById('cliptide-sync-status'),
        lastSyncLabel: document.getElementById('cliptide-last-sync-label'),

        // Buttons
        loginBtn: document.getElementById('btn-cliptide-login'),
        registerBtn: document.getElementById('btn-cliptide-register'),
        logoutBtn: document.getElementById('btn-cliptide-logout'),
        syncNowBtn: document.getElementById('btn-cliptide-sync-now')
    };

    // Состояние
    let isAuthenticated = false;
    let currentEmail = '';

    /**
     * Показать сообщение о статусе
     */
    function showStatus(element, message, isError = false) {
        element.textContent = message;
        element.style.color = isError ? 'var(--danger-color)' : 'var(--success-color)';
    }

    /**
     * Обновить метку последней синхронизации
     */
    function updateLastSyncLabel(lastSync) {
        if (!elements.lastSyncLabel) return;
        if (lastSync) {
            const date = new Date(lastSync);
            const formatted = date.toLocaleString();
            elements.lastSyncLabel.textContent = 'Последняя синхронизация: ' + formatted;
            elements.lastSyncLabel.style.display = 'block';
        } else {
            elements.lastSyncLabel.style.display = 'none';
        }
    }

    /**
     * Обновить отображение UI в зависимости от статуса авторизации
     */
    function updateUI() {
        if (isAuthenticated) {
            elements.authBlock.style.display = 'none';
            elements.profileBlock.style.display = 'block';
            elements.userEmail.textContent = currentEmail;

            // Первая буква email как аватар
            const firstChar = currentEmail.charAt(0).toUpperCase();
            elements.avatarInitial.textContent = firstChar;
        } else {
            elements.authBlock.style.display = 'block';
            elements.profileBlock.style.display = 'none';
        }
    }

    /**
     * Обработчик кнопки входа
     */
    function handleLogin() {
        const email = elements.emailInput.value.trim();
        const password = elements.passwordInput.value;

        if (!email || !password) {
            showStatus(elements.authStatus, 'Введите email и пароль', true);
            return;
        }

        showStatus(elements.authStatus, 'Выполняется вход...');
        elements.loginBtn.disabled = true;

        try {
            window.pywebview.api.cliptide_login(email, password);
        } catch (e) {
            showStatus(elements.authStatus, 'Ошибка: ' + e.message, true);
            elements.loginBtn.disabled = false;
        }
    }

    /**
     * Обработчик кнопки регистрации
     */
    function handleRegister() {
        const email = elements.emailInput.value.trim();
        const password = elements.passwordInput.value;

        if (!email || !password) {
            showStatus(elements.authStatus, 'Введите email и пароль', true);
            return;
        }

        if (password.length < 6) {
            showStatus(elements.authStatus, 'Пароль должен быть не менее 6 символов', true);
            return;
        }

        // Используем первую часть email как username
        const username = email.split('@')[0];

        showStatus(elements.authStatus, 'Выполняется регистрация...');
        elements.registerBtn.disabled = true;

        try {
            window.pywebview.api.cliptide_register(username, email, password);
        } catch (e) {
            showStatus(elements.authStatus, 'Ошибка: ' + e.message, true);
            elements.registerBtn.disabled = false;
        }
    }

    /**
     * Обработчик кнопки выхода
     */
    function handleLogout() {
        if (confirm('Вы уверены, что хотите выйти из аккаунта ClipTide?')) {
            try {
                window.pywebview.api.cliptide_logout();
            } catch (e) {
                console.error('Logout error:', e);
            }
        }
    }

    /**
     * Обработчик переключателя синхронизации
     */
    function handleSyncToggle() {
        const enabled = elements.syncToggle.checked;

        try {
            window.pywebview.api.cliptide_set_sync_enabled(enabled);
            showStatus(elements.syncStatus, enabled ? 'Синхронизация включена' : 'Синхронизация выключена');
        } catch (e) {
            console.error('Sync toggle error:', e);
            elements.syncToggle.checked = !enabled;
        }
    }

    /**
     * Обработчик кнопки синхронизации
     */
    function handleSyncNow() {
        showStatus(elements.syncStatus, 'Начинается синхронизация...');
        elements.syncNowBtn.disabled = true;

        try {
            window.pywebview.api.cliptide_sync_now();
        } catch (e) {
            showStatus(elements.syncStatus, 'Ошибка: ' + e.message, true);
            elements.syncNowBtn.disabled = false;
        }
    }

    // === Callback функции из Python ===

    /**
     * Успешная авторизация
     */
    window.onClipTideAuthSuccess = function(userData) {
        console.log('ClipTide auth success:', userData);
        isAuthenticated = true;
        currentEmail = userData.email || userData.data?.email || elements.emailInput.value;

        showStatus(elements.authStatus, 'Вход выполнен успешно!');
        updateUI();

        elements.loginBtn.disabled = false;
        elements.registerBtn.disabled = false;

        // Запросить актуальный статус
        setTimeout(() => {
            window.pywebview.api.cliptide_get_status();
        }, 500);
    };

    /**
     * Ошибка авторизации
     */
    window.onClipTideAuthError = function(errorMessage) {
        console.error('ClipTide auth error:', errorMessage);
        showStatus(elements.authStatus, errorMessage, true);
        elements.loginBtn.disabled = false;
        elements.registerBtn.disabled = false;
    };

    /**
     * Выход из аккаунта
     */
    window.onClipTideLogout = function() {
        console.log('ClipTide logout');
        isAuthenticated = false;
        currentEmail = '';
        elements.emailInput.value = '';
        elements.passwordInput.value = '';
        showStatus(elements.authStatus, '');
        updateUI();
    };

    /**
     * Получение статуса авторизации
     */
    window.onClipTideStatus = function(status) {
        console.log('ClipTide status:', status);
        isAuthenticated = status.authenticated;
        currentEmail = status.email || '';

        if (elements.syncToggle) {
            elements.syncToggle.checked = status.sync_enabled;
        }

        updateLastSyncLabel(status.last_sync || null);
        updateUI();
    };

    /**
     * Начало синхронизации
     */
    window.onClipTideSyncStart = function() {
        console.log('ClipTide sync started');
        showStatus(elements.syncStatus, 'Синхронизация...');
    };

    /**
     * Завершение синхронизации
     */
    window.onClipTideSyncComplete = function(result) {
        console.log('ClipTide sync complete:', result);
        showStatus(elements.syncStatus, `Синхронизировано загрузок: ${result.count}`);
        elements.syncNowBtn.disabled = false;
        updateLastSyncLabel(result.last_sync || null);
    };

    // === Инициализация ===

    function init() {
        // Навешиваем обработчики
        if (elements.loginBtn) {
            elements.loginBtn.addEventListener('click', handleLogin);
        }

        if (elements.registerBtn) {
            elements.registerBtn.addEventListener('click', handleRegister);
        }

        if (elements.logoutBtn) {
            elements.logoutBtn.addEventListener('click', handleLogout);
        }

        if (elements.syncToggle) {
            elements.syncToggle.addEventListener('change', handleSyncToggle);
        }

        if (elements.syncNowBtn) {
            elements.syncNowBtn.addEventListener('click', handleSyncNow);
        }

        // Запрашиваем статус при загрузке
        setTimeout(() => {
            if (window.pywebview?.api?.cliptide_get_status) {
                window.pywebview.api.cliptide_get_status();
            }
        }, 1000);

        console.log('ClipTide integration initialized');
    }

    // Запуск после загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
