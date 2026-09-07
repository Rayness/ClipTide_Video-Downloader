# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Асинхронная загрузка превью по URL.

Обложки роликов приходят ссылками на i.ytimg.com. Тянуть их в главном
потоке нельзя — интерфейс замирал бы на каждую карточку, поэтому загрузка
идёт в пуле потоков, а готовый QPixmap возвращается сигналом.

Загруженное кэшируется в памяти по URL: в очереди часто оказываются ролики
одного канала с одинаковыми обложками, да и пересоздание карточек при
перерисовке не должно дёргать сеть заново.
"""

from __future__ import annotations

import base64
import threading

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap

_cache: dict[str, bytes] = {}
_cache_lock = threading.Lock()

#: Ограничение кэша, чтобы длинная очередь не съедала память
MAX_CACHED = 200


class _LoaderSignals(QObject):
    finished = Signal(str, bytes)   # url, сырые байты изображения


class _LoaderTask(QRunnable):
    def __init__(self, url: str, signals: _LoaderSignals, proxies: dict | None):
        super().__init__()
        self.url = url
        self.signals = signals
        self.proxies = proxies

    def run(self) -> None:
        from app.utils.network import get_session

        try:
            response = get_session().get(self.url, timeout=15, proxies=self.proxies)
            data = response.content if response.status_code == 200 else b""
        except Exception:
            data = b""

        if data:
            with _cache_lock:
                if len(_cache) >= MAX_CACHED:
                    _cache.pop(next(iter(_cache)))
                _cache[self.url] = data

        self.signals.finished.emit(self.url, data)


class ThumbnailLoader(QObject):
    """Один загрузчик на приложение; виджеты подписываются на `loaded`."""

    loaded = Signal(str, QPixmap)   # url, картинка

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(4)
        self._pending: set[str] = set()
        self._signals = _LoaderSignals()
        self._signals.finished.connect(self._on_finished)
        self._proxies: dict | None = None

    def set_proxy(self, url: str | None) -> None:
        self._proxies = {"http": url, "https": url} if url else None

    def request(self, url: str) -> QPixmap | None:
        """
        Возвращает картинку сразу, если она в кэше.
        Иначе ставит загрузку в очередь и позже испускает `loaded`.
        """
        if not url:
            return None

        with _cache_lock:
            cached = _cache.get(url)
        if cached is not None:
            return _pixmap_from_bytes(cached)

        if url not in self._pending:
            self._pending.add(url)
            self._pool.start(_LoaderTask(url, self._signals, self._proxies))
        return None

    def _on_finished(self, url: str, data: bytes) -> None:
        self._pending.discard(url)
        if not data:
            return
        pixmap = _pixmap_from_bytes(data)
        if pixmap is not None:
            self.loaded.emit(url, pixmap)


def _pixmap_from_bytes(data: bytes) -> QPixmap | None:
    pixmap = QPixmap()
    return pixmap if pixmap.loadFromData(data) else None


def pixmap_from_data_uri(data_uri: str | None) -> QPixmap | None:
    """data:image/jpeg;base64,... -> QPixmap."""
    if not data_uri or "," not in data_uri:
        return None
    try:
        raw = base64.b64decode(data_uri.split(",", 1)[1])
    except (ValueError, TypeError):
        return None
    return _pixmap_from_bytes(raw)


def fit(pixmap: QPixmap | None, size, background: str = "#0e1014") -> QPixmap:
    """Вписывает картинку в рамку заданного размера, сохраняя пропорции."""
    canvas = QPixmap(size)
    canvas.fill(QColor(background))
    if pixmap is None or pixmap.isNull():
        return canvas

    scaled = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    painter = QPainter(canvas)
    painter.drawPixmap(
        (size.width() - scaled.width()) // 2,
        (size.height() - scaled.height()) // 2,
        scaled,
    )
    painter.end()
    return canvas
