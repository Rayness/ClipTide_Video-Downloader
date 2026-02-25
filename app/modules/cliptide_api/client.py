# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
ClipTide API Client для синхронизации истории загрузок.

Поддерживает:
- Авторизацию (login/register)
- Синхронизацию истории загрузок (bulk/single)
- Получение даты последней синхронизации
"""

import requests
from datetime import datetime
from typing import Optional, List, Dict, Any


class ClipTideAuthError(Exception):
    """Ошибка авторизации"""
    pass


class ClipTideSyncError(Exception):
    """Ошибка синхронизации"""
    pass


class ClipTideAPIClient:
    """Клиент для работы с ClipTide API"""

    # Base URLs
    DEV_URL = "http://localhost:5002/api"
    PROD_URL = "https://api.cliptide.com/api"

    def __init__(self, use_production: bool = True):
        """
        Инициализация клиента.

        Args:
            use_production: True для production API, False для dev
        """
        self.base_url = self.PROD_URL if use_production else self.DEV_URL
        self.token: Optional[str] = None
        self.user_data: Optional[Dict[str, Any]] = None

        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })

    def _get_auth_headers(self) -> Dict[str, str]:
        """Получить заголовки для авторизованных запросов"""
        if not self.token:
            return {}
        return {'Authorization': f'Bearer {self.token}'}

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Вход в аккаунт ClipTide.

        Args:
            email: Email пользователя
            password: Пароль

        Returns:
            Данные пользователя включая токен

        Raises:
            ClipTideAuthError: При ошибке авторизации
        """
        try:
            response = self.session.post(
                f"{self.base_url}/users/login",
                json={'email': email, 'password': password},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                raise ClipTideAuthError(f"API error: {data}")

            user_data = data.get('data', {})
            self.token = user_data.get('token')
            self.user_data = user_data

            return user_data

        except requests.exceptions.RequestException as e:
            raise ClipTideAuthError(f"Network error: {str(e)}")
        except (KeyError, ValueError) as e:
            raise ClipTideAuthError(f"Invalid response: {str(e)}")

    def register(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """
        Регистрация нового пользователя.

        Args:
            username: Имя пользователя
            email: Email
            password: Пароль

        Returns:
            Данные пользователя
        """
        try:
            response = self.session.post(
                f"{self.base_url}/users/register",
                json={'username': username, 'email': email, 'password': password},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                raise ClipTideAuthError(f"API error: {data}")

            return data.get('data', {})

        except requests.exceptions.RequestException as e:
            raise ClipTideAuthError(f"Network error: {str(e)}")

    def logout(self):
        """Выйти из аккаунта"""
        self.token = None
        self.user_data = None

    def is_authenticated(self) -> bool:
        """Проверить, авторизован ли клиент"""
        return self.token is not None

    def get_last_sync(self) -> Optional[datetime]:
        """
        Получить дату последней синхронизации.

        Returns:
            datetime последней синхронизации или None
        """
        if not self.token:
            return None

        try:
            response = self.session.get(
                f"{self.base_url}/downloads/last-sync",
                headers=self._get_auth_headers(),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get('success'):
                sync_date = data.get('data', {}).get('lastSync')
                if sync_date:
                    return datetime.fromisoformat(sync_date.replace('Z', '+00:00'))

        except (requests.exceptions.RequestException, ValueError, KeyError):
            pass

        return None

    def sync_downloads(self, downloads: List[Dict[str, Any]]) -> int:
        """
        Синхронизировать загрузки с сервером.

        Args:
            downloads: Список загрузок для синхронизации
                Каждая загрузка должна содержать:
                - url: URL видео
                - title: Название
                - format: Формат (mp4, mp3, etc)
                - size: Размер в байтах (опционально)
                - source: Источник (по умолчанию 'cliptide')
                - createdAt: Дата загрузки в ISO формате

        Returns:
            Количество успешно синхронизированных загрузок

        Raises:
            ClipTideSyncError: При ошибке синхронизации
        """
        if not self.token:
            raise ClipTideSyncError("Требуется авторизация")

        if not downloads:
            return 0

        try:
            # Форматируем загрузки для API
            formatted_downloads = []
            for dl in downloads:
                formatted = {
                    'url': dl.get('url', ''),
                    'title': dl.get('title', ''),
                    'format': dl.get('format', 'mp4'),
                    'size': dl.get('size', 0),
                    'source': dl.get('source', 'cliptide'),
                    'createdAt': dl.get('createdAt', datetime.utcnow().isoformat() + 'Z')
                }
                formatted_downloads.append(formatted)

            response = self.session.post(
                f"{self.base_url}/downloads/bulk",
                headers=self._get_auth_headers(),
                json={'downloads': formatted_downloads},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            if data.get('success'):
                return data.get('count', len(formatted_downloads))
            else:
                raise ClipTideSyncError(f"API error: {data}")

        except requests.exceptions.RequestException as e:
            raise ClipTideSyncError(f"Network error: {str(e)}")
        except (KeyError, ValueError) as e:
            raise ClipTideSyncError(f"Invalid response: {str(e)}")

    def add_single_download(self, download_data: Dict[str, Any]) -> bool:
        """
        Добавить одну загрузку.

        Args:
            download_data: Данные загрузки

        Returns:
            True при успехе
        """
        if not self.token:
            return False

        try:
            formatted = {
                'url': download_data.get('url', ''),
                'title': download_data.get('title', ''),
                'format': download_data.get('format', 'mp4'),
                'size': download_data.get('size', 0),
                'source': download_data.get('source', 'cliptide')
            }

            response = self.session.post(
                f"{self.base_url}/downloads",
                headers=self._get_auth_headers(),
                json=formatted,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            return data.get('success', False)

        except requests.exceptions.RequestException:
            return False

    def get_downloads_stats(self) -> Optional[Dict[str, Any]]:
        """
        Получить статистику загрузок.

        Returns:
            Статистика или None при ошибке
        """
        if not self.token:
            return None

        try:
            response = self.session.get(
                f"{self.base_url}/downloads/stats",
                headers=self._get_auth_headers(),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get('success'):
                return data.get('data', {})

        except (requests.exceptions.RequestException, ValueError, KeyError):
            pass

        return None
