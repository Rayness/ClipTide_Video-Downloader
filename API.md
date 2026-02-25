# ClipTide API Documentation

Полная документация по API для синхронизации с приложением ClipTide.

## 📡 Base URL

```
Development: http://localhost:5000/api
Production: https://api.cliptide.com/api
```

## 🔐 Авторизация

Все защищённые endpoints требуют JWT токен в заголовке:

```
Authorization: Bearer <your-jwt-token>
```

## 📚 Endpoints

### Аутентификация

#### POST /users/login
Вход в аккаунт

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "_id": "user_id",
    "username": "username",
    "email": "user@example.com",
    "role": "user",
    "token": "jwt_token_here"
  }
}
```

#### POST /users/register
Регистрация нового пользователя

**Request:**
```json
{
  "username": "username",
  "email": "user@example.com",
  "password": "password123"
}
```

---

### История загрузок

#### GET /downloads
Получить историю загрузок пользователя

**Query Parameters:**
- `page` (number): Номер страницы (default: 1)
- `limit` (number): Количество записей (default: 50, max: 100)
- `source` (string): Фильтр по источнику (cliptide, cliptide-lite, web-tool)
- `format` (string): Фильтр по формату (mp4, mp3, avi, etc)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "_id": "download_id",
      "url": "https://youtube.com/watch?v=xxx",
      "title": "Video Title",
      "format": "mp4",
      "size": 12345678,
      "source": "cliptide",
      "status": "completed",
      "createdAt": "2024-01-01T12:00:00.000Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 100,
    "totalPages": 2
  }
}
```

#### POST /downloads
Добавить одну загрузку

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=xxx",
  "title": "Video Title",
  "format": "mp4",
  "size": 12345678,
  "source": "cliptide"
}
```

#### POST /downloads/bulk
Пакетное добавление загрузок (для синхронизации)

**Request:**
```json
{
  "downloads": [
    {
      "url": "https://youtube.com/watch?v=xxx",
      "title": "Video 1",
      "format": "mp4",
      "size": 12345678,
      "source": "cliptide",
      "createdAt": "2024-01-01T12:00:00.000Z"
    },
    {
      "url": "https://youtube.com/watch?v=yyy",
      "title": "Video 2",
      "format": "mp3",
      "size": 8765432,
      "source": "cliptide",
      "createdAt": "2024-01-02T12:00:00.000Z"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": [...],
  "count": 2
}
```

#### GET /downloads/stats
Получить статистику загрузок

**Response:**
```json
{
  "success": true,
  "data": {
    "total": 100,
    "totalSize": 1234567890,
    "bySource": {
      "cliptide": 80,
      "cliptide-lite": 20
    },
    "byFormat": {
      "mp4": 60,
      "mp3": 40
    }
  }
}
```

#### GET /downloads/last-sync
Получить дату последней синхронизации

**Response:**
```json
{
  "success": true,
  "data": {
    "lastSync": "2024-01-15T10:30:00.000Z"
  }
}
```

#### DELETE /downloads/:id
Удалить загрузку

---

### Посты

#### GET /posts/:userId
Получить посты пользователя (публичный доступ)

**Query Parameters:**
- `page` (number): Номер страницы
- `limit` (number): Количество постов

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "_id": "post_id",
      "content": "Текст поста",
      "user": {
        "username": "username",
        "avatar": "avatar_url"
      },
      "likes": ["user_id_1", "user_id_2"],
      "createdAt": "2024-01-01T12:00:00.000Z"
    }
  ]
}
```

#### POST /posts
Создать пост (требуется авторизация)

**Request:**
```json
{
  "content": "Текст поста (макс. 5000 символов)"
}
```

#### DELETE /posts/:id
Удалить пост (только автор)

#### POST /posts/:id/like
Лайкнуть пост

---

### Профиль пользователя

#### PUT /users/profile
Обновить профиль (требуется авторизация)

**Request:**
```json
{
  "username": "new_username",
  "email": "new@email.com",
  "avatar": "base64_encoded_image",
  "bio": "О себе (макс. 500 символов)"
}
```

#### GET /users/:userId
Получить публичный профиль пользователя

---

## 💻 Пример клиента для ClipTide (Node.js)

```javascript
const axios = require('axios');

class ClipTideClient {
  constructor(apiUrl = 'http://localhost:5000/api') {
    this.apiUrl = apiUrl;
    this.token = null;
    this.client = axios.create({
      baseURL: this.apiUrl,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Авторизация
  async login(email, password) {
    const response = await this.client.post('/users/login', {
      email,
      password
    });
    
    if (response.data.success) {
      this.token = response.data.data.token;
      this.client.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
    }
    
    return response.data;
  }

  // Синхронизация истории загрузок
  async syncDownloads(downloads) {
    if (!this.token) {
      throw new Error('Требуется авторизация');
    }

    const response = await this.client.post('/downloads/bulk', {
      downloads: downloads.map(d => ({
        url: d.url,
        title: d.title,
        format: d.format || 'mp4',
        size: d.size || 0,
        source: d.source || 'cliptide',
        createdAt: d.date || new Date().toISOString()
      }))
    });

    return response.data;
  }

  // Добавить одну загрузку
  async addDownload(downloadData) {
    if (!this.token) {
      throw new Error('Требуется авторизация');
    }

    const response = await this.client.post('/downloads', downloadData);
    return response.data;
  }

  // Получить историю загрузок
  async getDownloads(page = 1, limit = 50, filters = {}) {
    if (!this.token) {
      throw new Error('Требуется авторизация');
    }

    const params = new URLSearchParams({ page, limit });
    if (filters.source) params.append('source', filters.source);
    if (filters.format) params.append('format', filters.format);

    const response = await this.client.get(`/downloads?${params}`);
    return response.data;
  }

  // Выйти
  logout() {
    this.token = null;
    delete this.client.defaults.headers.common['Authorization'];
  }
}

// Пример использования
async function main() {
  const client = new ClipTideClient();

  // Вход
  await client.login('user@example.com', 'password123');

  // Синхронизация истории
  const downloads = [
    {
      url: 'https://youtube.com/watch?v=xxx',
      title: 'Video 1',
      format: 'mp4',
      size: 12345678,
      date: '2024-01-01T12:00:00.000Z'
    },
    {
      url: 'https://youtube.com/watch?v=yyy',
      title: 'Video 2',
      format: 'mp3',
      size: 8765432,
      date: '2024-01-02T12:00:00.000Z'
    }
  ];

  const result = await client.syncDownloads(downloads);
  console.log(`Синхронизировано ${result.count} загрузок`);

  // Получить историю
  const history = await client.getDownloads(1, 50, { source: 'cliptide' });
  console.log(`Всего загрузок: ${history.pagination.total}`);
}

main().catch(console.error);
```

## 📝 Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успех |
| 201 | Создано |
| 400 | Ошибка валидации |
| 401 | Неавторизован |
| 403 | Доступ запрещён |
| 404 | Не найдено |
| 500 | Ошибка сервера |

## 🔄 Синхронизация

Рекомендуемый алгоритм синхронизации для ClipTide:

1. При запуске приложения проверить наличие токена
2. Если токена нет — предложить пользователю войти
3. Получить дату последней синхронизации (`GET /downloads/last-sync`)
4. Найти все загрузки новее этой даты
5. Отправить пакетом (`POST /downloads/bulk`)
6. Сохранить дату успешной синхронизации

## 🔒 Безопасность

- Все запросы к API должны идти по HTTPS в production
- Токен хранить в защищённом хранилище
- Не логировать чувствительные данные
- Использовать rate limiting для защиты от перебора
