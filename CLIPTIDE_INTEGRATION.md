# ClipTide API Integration - Руководство для фронтенда

## Обзор

В приложение добавлена интеграция с ClipTide API для:
- Авторизации пользователей (login/register)
- Синхронизации истории загрузок
- Управления профилем

## Структура проекта

```
app/
├── modules/
│   └── cliptide_api/          # Модуль ClipTide API
│       ├── __init__.py
│       └── client.py          # Клиент API
├── core/
│   ├── context.py             # AppContext с методами ClipTide
│   └── core.py                # WebViewApi с JS методами
└── main.py                    # Инициализация при старте

data/ui/
├── index.html                 # Вкладка настроек ClipTide
└── scripts/
    └── cliptide.js            # Обработчики UI
```

## JavaScript API методы

Все методы доступны через `pywebview` и вызываются через `window.pywebview.api`

### Авторизация

#### Вход в аккаунт
```javascript
window.pywebview.api.cliptide_login(email, password)
```

#### Регистрация
```javascript
window.pywebview.api.cliptide_register(username, email, password)
```

#### Выход
```javascript
window.pywebview.api.cliptide_logout()
```

#### Получить статус авторизации
```javascript
window.pywebview.api.cliptide_get_status()
```

### Синхронизация

#### Включить/выключить синхронизацию
```javascript
window.pywebview.api.cliptide_set_sync_enabled(enabled: boolean)
```

#### Принудительная синхронизация
```javascript
window.pywebview.api.cliptide_sync_now()
```

## Callback функции (Python → JS)

Эти функции должны быть определены в вашем JavaScript коде для получения ответов от Python:

### onClipTideAuthSuccess(userData)
Вызывается при успешной авторизации.

```javascript
function onClipTideAuthSuccess(userData) {
    // userData: { _id, username, email, role, token }
    console.log('Auth success:', userData);
    // Обновить UI, сохранить состояние
}
```

### onClipTideAuthError(errorMessage)
Вызывается при ошибке авторизации.

```javascript
function onClipTideAuthError(errorMessage) {
    console.error('Auth error:', errorMessage);
    // Показать ошибку пользователю
}
```

### onClipTideLogout()
Вызывается после выхода из аккаунта.

```javascript
function onClipTideLogout() {
    console.log('Logged out');
    // Очистить UI, удалить токен
}
```

### onClipTideStatus(status)
Вызывается при получении статуса авторизации.

```javascript
function onClipTideStatus(status) {
    // status: { authenticated: boolean, email: string, sync_enabled: boolean }
    console.log('ClipTide status:', status);
    // Обновить UI согласно статусу
}
```

### onClipTideSyncStart()
Вызывается при начале синхронизации.

```javascript
function onClipTideSyncStart() {
    console.log('Sync started...');
    // Показать индикатор загрузки
}
```

### onClipTideSyncComplete(result)
Вызывается после завершения синхронизации.

```javascript
function onClipTideSyncComplete(result) {
    // result: { count: number } - количество синхронизированных загрузок
    console.log('Sync complete:', result.count);
    // Скрыть индикатор, показать результат
}
```

## Пример использования в UI

### Форма входа
```html
<form id="loginForm">
    <input type="email" id="email" placeholder="Email" required>
    <input type="password" id="password" placeholder="Password" required>
    <button type="submit">Войти</button>
</form>

<script>
document.getElementById('loginForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    window.pywebview.api.cliptide_login(email, password);
});
</script>
```

### Отображение статуса
```javascript
// При загрузке приложения
window.pywebview.api.cliptide_get_status();

// Обработка статуса
function onClipTideStatus(status) {
    if (status.authenticated) {
        document.getElementById('userEmail').textContent = status.email;
        document.getElementById('syncToggle').checked = status.sync_enabled;
        showLoggedInView();
    } else {
        showLoggedOutView();
    }
}
```

### Переключатель синхронизации
```javascript
document.getElementById('syncToggle').addEventListener('change', (e) => {
    const enabled = e.target.checked;
    window.pywebview.api.cliptide_set_sync_enabled(enabled);
});
```

### Кнопка синхронизации
```html
<button onclick="window.pywebview.api.cliptide_sync_now()">
    Синхронизировать сейчас
</button>
```

## Хранение данных

Данные авторизации хранятся в конфигурационном файле приложения:

```ini
[ClipTide]
sync_enabled = False
api_url = production
auth_token = <jwt_token>
user_email = user@example.com
last_sync = 2024-01-15T10:30:00.000Z
```

## Автоматическая синхронизация

После каждой успешной загрузки видео приложение автоматически отправляет данные в ClipTide API, если:
1. Пользователь авторизован
2. Синхронизация включена в настройках

## Ошибки

Все ошибки авторизации и синхронизации логируются в консоль приложения и могут быть отображены пользователю через callback `onClipTideAuthError`.
