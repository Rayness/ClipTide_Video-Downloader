# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Сетевой слой приложения.

Все HTTP-запросы идут через один общий Session: TCP/TLS-соединения
переиспользуются, а не устанавливаются заново на каждый вызов (проверка
обновлений, каталог модулей, каталог тем, загрузка тем — раньше это были
четыре независимых requests.get с полным TLS-хендшейком каждый).
"""

from __future__ import annotations

import threading

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session: requests.Session | None = None
_session_lock = threading.Lock()

# Лёгкая точка для проверки связи: отдаёт 204 и пустое тело вместо
# ~50 КБ главной страницы Google, которые качались на каждый тест прокси.
CONNECTIVITY_URL = "https://www.gstatic.com/generate_204"


def get_session() -> requests.Session:
    """Общий Session с пулом соединений и ретраями на сетевые сбои."""
    global _session
    if _session is not None:
        return _session
    with _session_lock:
        if _session is None:
            session = requests.Session()
            retry = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(("GET", "HEAD")),
            )
            adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            _session = session
    return _session


def check_proxy_connection(proxy_url):
    """
    Проверяет работоспособность прокси.
    Возвращает (True, "OK (0.42s)") или (False, "причина").
    """
    if not proxy_url:
        return False, "URL пуст"

    proxies = {"http": proxy_url, "https": proxy_url}

    try:
        # Отдельный Session: прокси не должен осесть в общем пуле соединений.
        with requests.Session() as probe:
            response = probe.get(CONNECTIVITY_URL, proxies=proxies, timeout=5)

        if response.status_code in (200, 204):
            return True, f"OK ({response.elapsed.total_seconds():.2f}s)"
        return False, f"HTTP {response.status_code}"

    except requests.exceptions.ProxyError:
        return False, "Ошибка прокси (недоступен или неверные данные)"
    except requests.exceptions.ConnectTimeout:
        return False, "Таймаут соединения"
    except Exception as e:
        return False, str(e)
