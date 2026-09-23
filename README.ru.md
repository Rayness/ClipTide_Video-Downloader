<div align="center">

# ClipTide

### Современный загрузчик медиа с красивым интерфейсом

[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-%234B8BBE?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Загрузки](https://img.shields.io/github/downloads/Rayness/YouTube-Downloader/total?style=for-the-badge&logo=github)](https://github.com/Rayness/YouTube-Downloader/releases)
[![Версия](https://img.shields.io/github/v/tag/Rayness/YouTube-Downloader?style=for-the-badge&logo=semver&label=версия)](https://github.com/Rayness/YouTube-Downloader/releases)
[![Лицензия](https://img.shields.io/badge/лицензия-GPLv3-blue.svg?style=for-the-badge&logo=gnu)](LICENSE)

<img src="https://github.com/user-attachments/assets/9b7b0afc-d138-4496-9e87-176246057eeb" width="650" style="border-radius: 20px">

**[Сайт](https://cliptide.ru)** • **[Скачать](https://github.com/Rayness/YouTube-Downloader/releases)** • **[Документация](#-быстрый-старт)** • **[Сообщить об ошибке](https://github.com/Rayness/YouTube-Downloader/issues)**

[English](README.md) • [Русский](README.ru.md)

</div>

---

## ✨ Возможности

<table>
<tr>
<td width="50%">

### 🎥 **Поддержка множества платформ**
Загрузка контента с YouTube, Twitch, Rutube, VKVideo и [1000+ сайтов](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

### 🎨 **Красивые темы**
5 потрясающих встроенных тем: ClipTide, DarkTide, Forest, Neon City и Sunset

### 🌍 **Мультиязычность**
Полная поддержка русского, английского, украинского, китайского, японского, немецкого, французского, итальянского и польского языков

</td>
<td width="50%">

### 🔄 **Конвертация форматов**
Встроенный конвертер на основе FFmpeg для бесшовного изменения форматов

### 📥 **Система очередей**
Добавляйте несколько загрузок и обрабатывайте их в фоновом режиме

### ⚙️ **Расширенные настройки**
Поддержка прокси, загрузка субтитров, выбор языка аудио и многое другое

</td>
</tr>
</table>

---

## 📸 Скриншоты

<div align="center">

### Современный интерфейс
<img src="https://github.com/user-attachments/assets/4bd9f3bb-25a7-467c-96f6-42ce111f8427" width="700">

*Элегантный и интуитивный интерфейс ClipTide*

</div>

---

## 🚀 Быстрый старт

### 📦 Установка

#### Вариант 1: Установщик (Рекомендуется)
1. Скачайте последний установщик со страницы [Releases](https://github.com/Rayness/YouTube-Downloader/releases)
2. Запустите `ClipTide-Setup.exe`
3. Следуйте инструкциям мастера установки
4. Запустите ClipTide из меню "Пуск"

#### Вариант 2: Портативная версия
1. Скачайте `ClipTide-Portable.zip` со страницы [Releases](https://github.com/Rayness/YouTube-Downloader/releases)
2. Распакуйте в любое удобное место
3. Запустите `ClipTide.exe`

### 🎯 Как использовать

1. **Вставьте URL** - Скопируйте и вставьте ссылку на видео из браузера
2. **Выберите формат** - Выберите желаемое качество и формат (по умолчанию: MP4 FullHD)
3. **Добавьте в очередь** - Нажмите кнопку "Добавить в очередь"
4. **Начните загрузку** - Нажмите "Начать загрузку" и дождитесь завершения
5. **Готово** - Папка с загруженными файлами откроется автоматически

> **💡 Совет:** Очередь загрузок сохраняется автоматически. Вы можете закрыть приложение в любое время и продолжить позже!

### 🔗 Из других программ

ClipTide принимает ссылки снаружи и сразу их качает — без кнопки «Начать загрузку»:

```powershell
ClipTide.exe --download "https://youtu.be/..." --format mp3 --quality 720 --minimized
ClipTide.exe --show
```

Если ClipTide уже запущен, второй запуск передаёт ему команду и закрывается. Программы
могут писать напрямую в канал `\\.\pipe\ClipTide.<имя пользователя>` — по строке JSON
на сообщение (`download`, `show`, `subscribe` для живого прогресса); формат описан в
`app/core/remote.py`. Так работает [Islet](https://github.com/Rayness/Islet): `ct <ссылка>`
в островке ставит видео на загрузку, а прогресс виден в его капсуле.

---

## 🛠️ Разработка

### Требования

- Python 3.12 или 3.13
- Git
- ОС Windows (для сборки исполняемых файлов)

### Локальная настройка

```bash
# Клонируйте репозиторий
git clone https://github.com/Rayness/YouTube-Downloader.git
cd YouTube-Downloader

# Установите зависимости
pip install -r requirements.txt

# Запустите приложение
python start.py
```

### Структура проекта

```
ClipTide/
├── app/                    # Основной код приложения
│   ├── core/              # Основная функциональность
│   ├── modules/           # Модули функций
│   │   ├── downloader/    # Модуль загрузки
│   │   ├── converter/     # Конвертер форматов
│   │   └── settings/      # Менеджер настроек
│   └── utils/             # Утилиты
├── data/                   # Данные приложения
│   ├── ui/                # Файлы интерфейса
│   │   ├── scripts/       # JavaScript модули
│   │   ├── styles/        # CSS стили
│   │   └── themes/        # Определения тем
│   └── localization/      # Файлы переводов
├── update/                # Автообновление
└── start.py               # Точка входа приложения
```

### Сборка из исходников

```bash
# Установите PyInstaller
pip install pyinstaller

# Соберите исполняемый файл
pyinstaller ClipTide.spec
pyinstaller updater.spec

# Результат будет в папке dist/
```

---

## 🎨 Кастомизация

### Темы

ClipTide поставляется с 5 красивыми темами:

- **ClipTide** - Стандартная светлая тема с морской тематикой
- **DarkTide** - Элегантная тёмная тема
- **Forest** - Зелёная палитра в природном стиле
- **Neon City** - Футуристическая киберпанк эстетика
- **Sunset** - Тёплые вечерние цвета

Создайте свою тему, добавив новую папку в `data/ui/themes/` с файлами `config.json` и `styles.css`.

### Языки

Чтобы добавить перевод:
1. Скопируйте файл `data/localization/en.json`
2. Переведите значения (ключи оставьте без изменений)
3. Сохраните как `data/localization/[код_языка].json`
4. Отправьте pull request!

---

## 🔧 Конфигурация

### Настройки загрузки
- **Папка сохранения** - Выберите, куда сохранять файлы
- **Качество** - Выберите от 144p до 8K
- **Формат** - MP4, WebM, MKV, MP3 и другие
- **Субтитры** - Автозагрузка, встраивание или отдельное сохранение

### Настройки сети
- **Поддержка прокси** - HTTP/HTTPS/SOCKS5
- **Тайм-аут соединения** - Настройте для медленных сетей
- **Параллельные загрузки** - Контроль одновременных загрузок

### Расширенные функции
- **Язык аудио** - Выбор предпочитаемой аудиодорожки
- **Языки субтитров** - Загрузка нескольких дорожек субтитров
- **Уведомления** - Системные уведомления о завершении
- **Автообновление** - Автоматическое обновление приложения

---

## 📚 Часто задаваемые вопросы

<details>
<summary><b>Почему загрузка медленная?</b></summary>
<br>
Скорость загрузки зависит от вашего интернет-соединения и сервера источника. Попробуйте включить прокси, если сайт ограничен в вашем регионе.
</details>

<details>
<summary><b>Могу ли я загрузить целые плейлисты?</b></summary>
<br>
Да! Просто вставьте URL плейлиста, и все видео будут автоматически добавлены в очередь.
</details>

<details>
<summary><b>Какие видеоформаты поддерживаются?</b></summary>
<br>
ClipTide поддерживает MP4, WebM, MKV, FLV, 3GP и многие другие. Для аудио: MP3, M4A, WAV, FLAC, OGG и другие.
</details>

<details>
<summary><b>Законно ли скачивать видео?</b></summary>
<br>
Загрузка видео для личного использования законна в большинстве стран. Всегда соблюдайте законы об авторском праве и условия использования платформ.
</details>

---

## 🗺️ Дорожная карта

- [x] Многоязычная поддержка
- [x] Автообновление
- [x] Система тем
- [x] Встроенный конвертер
- [ ] Миграция на Electron (в будущем)
- [ ] Мобильное приложение (в будущем)
- [ ] Расширение для браузера (запланировано)
- [ ] Облачная синхронизация (запланировано)

---

## 🤝 Участие в проекте

Мы приветствуем вклад в развитие! Вот как вы можете помочь:

1. 🐛 **Сообщайте об ошибках** - Откройте issue с подробностями
2. 💡 **Предлагайте функции** - Делитесь своими идеями
3. 🌍 **Переводите** - Добавьте поддержку новых языков
4. 🎨 **Создавайте темы** - Разрабатывайте новые цветовые схемы
5. 💻 **Отправляйте PR** - Исправляйте ошибки или добавляйте функции

### Правила разработки

- Следуйте стилю PEP 8 для Python
- Пишите понятные сообщения коммитов
- Тестируйте изменения перед отправкой
- Обновляйте документацию при необходимости

---

## 📄 Лицензия

Этот проект лицензирован под **GNU General Public License v3.0** - подробности в файле [LICENSE](LICENSE).

### Лицензии сторонних библиотек

ClipTide использует следующие библиотеки с открытым исходным кодом:

- **[pywebview](https://github.com/r0x0r/pywebview)** - Лицензия BSD 3-Clause
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Общественное достояние
- **[FFmpeg](https://ffmpeg.org)** - Лицензия LGPL/GPL

---

## 💖 Поддержка

Если вам нравится ClipTide, поддержите проект:

- ⭐ **Поставьте звезду репозиторию**
- 🐛 **Сообщайте об ошибках**
- 💡 **Предлагайте новые функции**
- 🌍 **Помогайте с переводами**
- ☕ **[Угостите меня кофе](https://boosty.to/rayness/donate)**

---

## 📞 Контакты

- **Сайт:** [cliptide.ru](https://cliptide.ru)
- **GitHub:** [@Rayness](https://github.com/Rayness)
- **Проблемы:** [Сообщить об ошибке](https://github.com/Rayness/YouTube-Downloader/issues)

---

<div align="center">

**Сделано с ❤️ [Rayness](https://github.com/Rayness)**

*Скачивайте интернет, по одному клипу за раз* 🌊

[![GitHub stars](https://img.shields.io/github/stars/Rayness/YouTube-Downloader?style=social)](https://github.com/Rayness/YouTube-Downloader/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Rayness/YouTube-Downloader?style=social)](https://github.com/Rayness/YouTube-Downloader/network/members)

</div>
