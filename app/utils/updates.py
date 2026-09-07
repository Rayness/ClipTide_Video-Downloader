# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Проверка обновлений.

Приложение обновления НЕ скачивает и не устанавливает — только сообщает, что
вышла новая версия, и открывает страницу релизов на GitHub.

Почему так. Раньше установкой занимался отдельный update.exe: в onedir-сборке
заменить файлы на ходу нельзя, сотни файлов в _internal заняты работающим
процессом. После перехода на onefile обновление свелось бы к замене одного
файла, и второй исполняемый файл перестал себя окупать — 38 МБ ради второй
копии Qt. Заодно он был сломан: раскладывал рядом с собой update.exe.new в
расчёте, что приложение подменит файл при следующем запуске, но такого кода
в приложении не было никогда.

Источник правды один — манифест updates.json. Прежде версия сверялась в двух
местах по-разному: на старте с тегом релиза из GitHub API, в настройках — с
манифестом. Теги пишутся как "v2.0.0", а версия в манифесте идёт без
префикса, поэтому сравнение на старте срабатывало всегда и приложение
сообщало об обновлении на ровном месте. Здесь префикс срезается у обеих
сторон, так что "v2.0.0" и "2.0.0" — одна версия.
"""

from __future__ import annotations

from app.utils.const import GITHUB_REPO, MANIFEST_URL, VERSION_FILE
from app.utils.network import get_session

#: Куда отправляем пользователя за новой версией, если манифест не сказал иного
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

_HEADERS = {"User-Agent": "ClipTide-App", "Accept": "application/json"}


def normalize(version) -> str:
    """Приводит номер версии к виду без ведущей «v»."""
    text = str(version or "").strip()
    return text[1:] if text[:1] in ("v", "V") else text


def _parts(version) -> tuple:
    """
    Числовая часть версии для сравнения: "1.7.3f" -> (1, 7, 3).

    Номера здесь исторически разношёрстные — "1.7.3f", "1.7.1-build_1.0", —
    поэтому от каждого куска между точками берём ведущие цифры, а хвост
    игнорируем. Если цифр нет вовсе, вернётся пустой кортеж, и вызывающий
    код откатится на сравнение строк.
    """
    numbers = []
    for chunk in normalize(version).split("."):
        digits = ""
        for char in chunk:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            break
        numbers.append(int(digits))
    return tuple(numbers)


def is_newer(remote, local) -> bool:
    """
    True, если remote старше local.

    Раньше сравнивали просто на неравенство, и сборка свежее манифеста
    считалась устаревшей: пользователю предлагали «обновиться» на версию
    ниже той, что у него стоит.

    При равных числах решает строка целиком: буквенный хвост в этом проекте
    означает выпуск-заплатку, то есть "1.7.3f" новее, чем "1.7.3".
    """
    remote_parts, local_parts = _parts(remote), _parts(local)
    if remote_parts and local_parts and remote_parts != local_parts:
        return remote_parts > local_parts
    return normalize(remote) > normalize(local)


def local_version() -> str:
    """Версия текущей сборки из data/version.txt."""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as handle:
            return handle.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def release_page_url(entry: dict | None = None) -> str:
    """Страница загрузки: из манифеста, иначе последний релиз на GitHub."""
    page = (entry or {}).get("page")
    return str(page) if page else RELEASES_URL


def check(channel: str = "stable") -> dict:
    """
    Сверяет локальную версию с манифестом.

    Возвращает словарь для интерфейса. Ключ error говорит, что сверить не
    удалось; has_update — что версии разошлись.
    """
    current = local_version()

    try:
        response = get_session().get(MANIFEST_URL, headers=_HEADERS, timeout=10)
    except Exception as e:                        # noqa: BLE001 — сеть
        return {"error": True, "message": str(e), "current_version": current}

    if response.status_code != 200:
        return {
            "error": True,
            "message": f"HTTP {response.status_code}",
            "current_version": current,
        }

    try:
        data = response.json()
    except ValueError as e:
        return {"error": True, "message": f"Разбор манифеста: {e}",
                "current_version": current}

    if channel not in data:
        return {"error": True, "message": "Канал не найден",
                "current_version": current}

    entry = data[channel] or {}
    latest = entry.get("version", "0.0.0")

    return {
        "error": False,
        "has_update": is_newer(latest, current),
        "latest_version": latest,
        "current_version": current,
        "description": entry.get("description", ""),
        "page_url": release_page_url(entry),
        "channel": channel,
        # Запись целиком — из неё самообновление берёт адрес сборки
        "entry": dict(entry),
    }
