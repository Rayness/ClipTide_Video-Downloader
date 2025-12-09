# app/utils/network.py

import requests

def check_proxy_connection(proxy_url):
    """
    Проверяет работоспособность прокси, пытаясь достучаться до Google.
    Возвращает (True, "OK") или (False, "Ошибка").
    """
    if not proxy_url:
        return False, "URL пуст"

    # Формируем словарь для requests
    # requests понимает формат scheme://user:pass@host:port
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    try:
        # Пытаемся получить доступ к Google с таймаутом 5 секунд
        response = requests.get("https://www.google.com", proxies=proxies, timeout=5)
        
        if response.status_code == 200:
            return True, f"OK ({response.elapsed.total_seconds():.2f}s)"
        else:
            return False, f"HTTP {response.status_code}"
            
    except requests.exceptions.ProxyError:
        return False, "Ошибка прокси (недоступен или неверные данные)"
    except requests.exceptions.ConnectTimeout:
        return False, "Таймаут соединения"
    except Exception as e:
        return False, str(e)