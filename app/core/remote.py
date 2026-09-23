# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Связь ClipTide с другими программами: команды внутрь, состояние загрузок наружу.

Канал — именованный пайп \\\\.\\pipe\\ClipTide.<пользователь>, одна строка JSON
на сообщение:

    {"type": "download", "url": "https://…", "format": "mp4", "quality": "1080"}
    {"type": "show"}
    {"type": "subscribe"}

После "subscribe" соединение остаётся открытым, и ClipTide сам пишет в него
состояние загрузок — при каждом изменении, не чаще трёх раз в секунду:

    {"type": "state", "analyzing": 1, "queued": 0,
     "downloads": [{"id": "…", "title": "…", "thumbnail": "https://…",
                    "percent": 42.0, "detail": "2.1 МБ/с", "eta": "1м 3с"}]}
    {"type": "error", "url": "…", "title": "…", "message": "…"}
                        — ссылка из канала не разобралась или не скачалась
    {"type": "ping"}                                  — раз в полминуты, если тихо

Так ссылку в загрузку отправляет Islet (островок на рабочем столе) и
показывает прогресс у себя в капсуле. Тот же канал делает ClipTide
единственным экземпляром: второй запуск передаёт команду первому и выходит.

    ClipTide.exe --download <ссылка> [--format mp3] [--quality 720] [--minimized]
    ClipTide.exe --show

Где лежит exe, другие программы узнают из launch.json в папке данных:
его переписывает каждый запуск.

QtNetwork (QLocalServer) из сборки вырезан ради размера, поэтому пайп — на
WinAPI через ctypes. ClipTide запускается с правами администратора, а
программы, которые к нему обращаются, — обычно без: канал создаётся с
явным дескриптором (владелец — сам пользователь, метка целостности Medium),
иначе процессу без прав в него не написать.
"""

from __future__ import annotations

import ctypes
import json
import os
import re
import sys
import threading
import time
import uuid
from ctypes import wintypes

from app.utils.paths import APP_DIR, IS_FROZEN, USER_DATA_DIR

PIPE_NAME = f"ClipTide.{os.environ.get('USERNAME') or 'user'}"
PIPE_PATH = rf"\\.\pipe\{PIPE_NAME}"
LAUNCH_FILE = USER_DATA_DIR / "launch.json"
PROTOCOL_VERSION = 1

#: Ключ перезапуска: новый процесс не должен отдавать команду старому,
#: который вот-вот закроется.
RESTART_FLAG = "--restarted"

#: id разбора, пришедшего через канал: его ошибку отправляем подписчикам
REMOTE_PREFIX = "r-"

VIDEO_FORMATS = ("mp4", "mkv", "webm")
AUDIO_FORMATS = ("mp3", "m4a", "opus", "flac")
QUALITIES = ("2160", "1440", "1080", "720", "480", "360", "240")

MAX_MESSAGE = 64 * 1024
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
PUSH_INTERVAL_SEC = 0.3
PING_INTERVAL_SEC = 30.0


# ----------------------------------------------------------------------
# Команды
# ----------------------------------------------------------------------
class Request:
    """Что просили в командной строке: сообщение для канала и как показать окно."""

    def __init__(self, message: dict, minimized: bool = False):
        self.message = message
        self.minimized = minimized


def parse_args(argv: list[str]) -> Request | None:
    """Ключи командной строки → сообщение канала. None — обычный запуск."""
    args = [a for a in argv if a != RESTART_FLAG]
    if not args:
        return None

    def value(flag: str) -> str | None:
        if flag in args:
            i = args.index(flag)
            if i + 1 < len(args):
                return args[i + 1]
        return None

    minimized = "--minimized" in args
    url = value("--download")
    # «Открыть с помощью» и ярлыки отдают ссылку без ключа
    if url is None:
        url = next((a for a in args if a.lower().startswith(("http://", "https://"))), None)
    if url:
        message = {"type": "download", "url": url}
        if fmt := value("--format"):
            message["format"] = fmt
        if quality := value("--quality"):
            message["quality"] = quality
        return Request(message, minimized)
    if "--show" in args:
        return Request({"type": "show"})
    return None


def download_args(message: dict) -> tuple[str, str, str] | None:
    """Проверенные (ссылка, формат, качество) из команды download."""
    url = str(message.get("url") or "").strip()
    if not url.lower().startswith(("http://", "https://")) or len(url) > 4096:
        return None
    fmt = str(message.get("format") or "mp4").lower()
    if fmt not in VIDEO_FORMATS + AUDIO_FORMATS:
        fmt = "mp4"
    quality = str(message.get("quality") or "1080").lower().removesuffix("p")
    quality = {"4k": "2160", "2k": "1440"}.get(quality, quality)
    if quality not in QUALITIES:
        quality = "1080"
    return url, fmt, quality


def new_remote_id() -> str:
    return f"{REMOTE_PREFIX}{uuid.uuid4()}"


def is_restart(argv: list[str]) -> bool:
    return RESTART_FLAG in argv


def write_launch_info(version: str) -> None:
    """Как запустить этот ClipTide и где его канал — для Islet и скриптов."""
    command = [sys.executable] if IS_FROZEN else [sys.executable, str(APP_DIR / "start.py")]
    data = {
        "protocol": PROTOCOL_VERSION,
        "pipe": PIPE_NAME,
        "pid": os.getpid(),
        "version": version,
        "command": command,
    }
    temp = LAUNCH_FILE.with_suffix(".tmp")
    try:
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, LAUNCH_FILE)
    except OSError as e:
        print(f"[WARN] launch.json не записан: {e}")


# ----------------------------------------------------------------------
# WinAPI
# ----------------------------------------------------------------------
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

PIPE_ACCESS_DUPLEX = 0x00000003
FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
PIPE_TYPE_BYTE = 0x0
PIPE_WAIT = 0x0
PIPE_REJECT_REMOTE_CLIENTS = 0x8
PIPE_UNLIMITED_INSTANCES = 255
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
ERROR_BROKEN_PIPE = 109
ERROR_MORE_DATA = 234
ERROR_PIPE_BUSY = 231
ERROR_PIPE_CONNECTED = 535
TOKEN_QUERY = 0x0008
TOKEN_USER_CLASS = 1
SDDL_REVISION_1 = 1


class _SecurityAttributes(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]


_kernel32.CreateNamedPipeW.restype = wintypes.HANDLE
_kernel32.CreateNamedPipeW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(_SecurityAttributes),
]
_kernel32.ConnectNamedPipe.restype = wintypes.BOOL
_kernel32.ConnectNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
_kernel32.ReadFile.restype = wintypes.BOOL
_kernel32.ReadFile.argtypes = [
    wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
]
_kernel32.WriteFile.restype = wintypes.BOOL
_kernel32.WriteFile.argtypes = [
    wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
]
_kernel32.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.WaitNamedPipeW.restype = wintypes.BOOL
_kernel32.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
_kernel32.GetCurrentProcess.restype = wintypes.HANDLE
_kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
_advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
_advapi32.GetTokenInformation.argtypes = [
    wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
]
_advapi32.ConvertSidToStringSidW.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.LPWSTR)]
_advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID), ctypes.POINTER(wintypes.ULONG),
]


def _user_sid() -> str | None:
    """SID текущего пользователя строкой — одинаковый с правами админа и без."""
    token = wintypes.HANDLE()
    if not _advapi32.OpenProcessToken(_kernel32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token)):
        return None
    try:
        size = wintypes.DWORD()
        _advapi32.GetTokenInformation(token, TOKEN_USER_CLASS, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not _advapi32.GetTokenInformation(token, TOKEN_USER_CLASS, buffer, size, ctypes.byref(size)):
            return None
        # TOKEN_USER начинается с указателя на SID
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        text = wintypes.LPWSTR()
        if not _advapi32.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            return None
        try:
            return text.value
        finally:
            _kernel32.LocalFree(ctypes.cast(text, wintypes.HLOCAL))
    finally:
        _kernel32.CloseHandle(token)


def _security_attributes() -> _SecurityAttributes | None:
    """
    Доступ только своему пользователю и системе, метка целостности Medium.

    Без этого у канала процесса с правами администратора владелец —
    группа «Администраторы», а метка — High: обычный процесс того же
    пользователя в такой канал не пишет, а .NET-клиент с CurrentUserOnly
    отказывается подключаться, потому что владелец не он.
    """
    sid = _user_sid()
    if not sid:
        return None
    sddl = f"O:{sid}D:P(A;;GA;;;{sid})(A;;GA;;;SY)S:(ML;;NW;;;ME)"
    descriptor = wintypes.LPVOID()
    if not _advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, SDDL_REVISION_1, ctypes.byref(descriptor), None):
        return None
    # Дескриптор живёт до конца процесса — канал пересоздаётся на каждое подключение
    return _SecurityAttributes(ctypes.sizeof(_SecurityAttributes), descriptor, False)


def send(message: dict, timeout_ms: int = 1500) -> bool:
    """Отдать команду запущенному ClipTide. False — его нет."""
    data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    deadline = time.monotonic() + timeout_ms / 1000
    while True:
        try:
            with open(PIPE_PATH, "wb", buffering=0) as pipe:
                pipe.write(data)
            return True
        except FileNotFoundError:
            return False
        except OSError as e:
            if getattr(e, "winerror", None) == ERROR_PIPE_BUSY and time.monotonic() < deadline:
                _kernel32.WaitNamedPipeW(PIPE_PATH, 200)
                continue
            return False


# ----------------------------------------------------------------------
# Сервер канала
# ----------------------------------------------------------------------
class _Subscriber:
    def __init__(self):
        self.cond = threading.Condition()
        self.events: list[str] = []
        self.dirty = True


class PipeServer:
    """
    Принимает подключения в фоне. Каждое — в своём потоке: команды читаются
    до конца соединения, а после "subscribe" поток только пишет состояние.
    Читать и писать один синхронный хэндл из разных потоков нельзя — Windows
    выстраивает такие вызовы в очередь, и запись ждала бы чтения.
    """

    def __init__(self, on_command):
        self._on_command = on_command
        self._subscribers: list[_Subscriber] = []
        self._lock = threading.Lock()
        self._state = json.dumps({"type": "state", "analyzing": 0, "queued": 0, "downloads": []})
        self._stopped = False
        self._security = _security_attributes()

    def start(self) -> None:
        threading.Thread(target=self._serve, name="cliptide-pipe", daemon=True).start()

    def stop(self) -> None:
        self._stopped = True
        with self._lock:
            subscribers = list(self._subscribers)
        for sub in subscribers:
            with sub.cond:
                sub.cond.notify()

    # --- наружу ---------------------------------------------------------
    def publish(self, state: dict) -> None:
        """Новое состояние загрузок. Подписчики получат последнее, промежуточные схлопнутся."""
        self._state = json.dumps({"type": "state", **state}, ensure_ascii=False)
        self._notify(lambda sub: setattr(sub, "dirty", True))

    def event(self, message: dict) -> None:
        """Разовое событие: не схлопывается, доходит до каждого подписчика."""
        line = json.dumps(message, ensure_ascii=False)
        self._notify(lambda sub: sub.events.append(line))

    def _notify(self, change) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for sub in subscribers:
            with sub.cond:
                change(sub)
                sub.cond.notify()

    # --- приём подключений ---------------------------------------------
    def _create(self, first: bool):
        flags = PIPE_ACCESS_DUPLEX | (FILE_FLAG_FIRST_PIPE_INSTANCE if first else 0)
        security = ctypes.byref(self._security) if self._security else None
        handle = _kernel32.CreateNamedPipeW(
            PIPE_PATH, flags, PIPE_TYPE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
            PIPE_UNLIMITED_INSTANCES, MAX_MESSAGE, MAX_MESSAGE, 0, security)
        return None if handle in (None, INVALID_HANDLE_VALUE) else handle

    def _serve(self) -> None:
        # Первый экземпляр канала: при перезапуске старый процесс может ещё
        # держать его несколько секунд
        handle = None
        for _ in range(20):
            handle = self._create(first=True)
            if handle is not None or self._stopped:
                break
            time.sleep(0.5)
        if handle is None:
            print("[WARN] Канал ClipTide занят — команды извне работать не будут")
            return

        while not self._stopped:
            connected = _kernel32.ConnectNamedPipe(handle, None) \
                or ctypes.get_last_error() == ERROR_PIPE_CONNECTED
            if connected:
                threading.Thread(target=self._client, args=(handle,), daemon=True).start()
            else:
                _kernel32.CloseHandle(handle)
            # Следующий экземпляр — сразу, чтобы клиент не застал канал без слушателя
            handle = None
            while handle is None and not self._stopped:
                handle = self._create(first=False)
                if handle is None:
                    time.sleep(1)

    def _client(self, handle) -> None:
        buffer = b""
        try:
            while not self._stopped:
                chunk = self._read(handle)
                if chunk is None:
                    break
                buffer += chunk
                if len(buffer) > MAX_MESSAGE:
                    return
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if self._dispatch(line, handle):
                        return
            if buffer.strip():
                self._dispatch(buffer, handle)
        except Exception as e:                    # noqa: BLE001 — поток канала не должен падать
            print(f"[WARN] Канал ClipTide: {e}")
        finally:
            _kernel32.DisconnectNamedPipe(handle)
            _kernel32.CloseHandle(handle)

    def _dispatch(self, line: bytes, handle) -> bool:
        """True — соединение перешло в подписку и уже закрыто."""
        try:
            message = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        if not isinstance(message, dict):
            return False
        if message.get("type") == "subscribe":
            self._subscribe(handle)
            return True
        self._on_command(message)
        return False

    def _subscribe(self, handle) -> None:
        sub = _Subscriber()
        with self._lock:
            self._subscribers.append(sub)
        try:
            while not self._stopped:
                with sub.cond:
                    sub.cond.wait_for(lambda: sub.events or sub.dirty or self._stopped,
                                      timeout=PING_INTERVAL_SEC)
                    lines, sub.events = sub.events, []
                    if sub.dirty:
                        lines.append(self._state)
                        sub.dirty = False
                if self._stopped:
                    break
                # Тишина полминуты — пинг: так узнаём, что подписчик ушёл
                if not self._write(handle, lines or ['{"type":"ping"}']):
                    break
                time.sleep(PUSH_INTERVAL_SEC)
        finally:
            with self._lock:
                self._subscribers.remove(sub)

    @staticmethod
    def _read(handle) -> bytes | None:
        buffer = ctypes.create_string_buffer(4096)
        read = wintypes.DWORD()
        ok = _kernel32.ReadFile(handle, buffer, len(buffer), ctypes.byref(read), None)
        if not ok and ctypes.get_last_error() != ERROR_MORE_DATA:
            return None
        return buffer.raw[:read.value]

    @staticmethod
    def _write(handle, lines: list[str]) -> bool:
        data = ("\n".join(lines) + "\n").encode("utf-8")
        view = memoryview(data)
        while view:
            written = wintypes.DWORD()
            if not _kernel32.WriteFile(handle, bytes(view), len(view), ctypes.byref(written), None):
                return False
            view = view[written.value:]
        return True


# ----------------------------------------------------------------------
# Состояние загрузок для подписчиков
# ----------------------------------------------------------------------
class DownloadState:
    """
    Следит за загрузчиком через сигналы интерфейса (главный поток) и
    отдаёт подписчикам сводку: что разбирается, что качается, сколько ждёт.
    """

    def __init__(self, server: PipeServer, queue_getter):
        self._server = server
        self._queue = queue_getter
        self._analyzing: dict[str, str] = {}
        self._active: dict[str, dict] = {}
        #: задачи, пришедшие через канал: об их ошибках сообщаем подписчикам
        self._remote: set[str] = set()
        self._last_error = ""

    def log(self, message: str, level: str, code: str, source: str) -> None:
        # Причину ошибки загрузчик пишет только в журнал — берём оттуда
        if level == "error" and source == "downloader":
            self._last_error = message

    def analysis_started(self, temp_id: str, url: str) -> None:
        self._analyzing[temp_id] = url
        self._publish()

    def analysis_failed(self, temp_id: str, url: str, message: str) -> None:
        if temp_id.startswith(REMOTE_PREFIX):
            self._error(url, "", message)

    def placeholder_removed(self, temp_id: str) -> None:
        if self._analyzing.pop(temp_id, None) is not None:
            self._publish()

    def item_added(self, item: dict) -> None:
        temp_id = item.get("temp_id") or ""
        self._analyzing.pop(temp_id, None)
        if temp_id.startswith(REMOTE_PREFIX):
            self._remote.add(item["id"])
        self._publish()

    def item_removed(self, task_id: str) -> None:
        self._active.pop(task_id, None)
        self._remote.discard(task_id)
        self._publish()

    def progress(self, task_id: str, percent: float, detail: str, eta: str) -> None:
        # Название и превью — из самой очереди: задачи, сохранённые с прошлого
        # запуска, через item_added не проходили
        task = next((v for v in list(self._queue() or []) if v.get("id") == task_id), None) or {}
        status = task.get("status")
        if status == "downloading":
            self._active[task_id] = {
                "id": task_id,
                "title": task.get("title", ""),
                "thumbnail": task.get("thumbnail", ""),
                "percent": round(float(percent), 1),
                "detail": detail,
                "eta": eta,
            }
        else:
            self._active.pop(task_id, None)
            if status == "error" and task_id in self._remote:
                self._error(task.get("url", ""), task.get("title", ""), self._last_error)
        self._publish()

    def finished(self) -> None:
        self._active.clear()
        self._publish()

    def _error(self, url: str, title: str, message: str) -> None:
        # yt-dlp красит «ERROR:» ANSI-кодами, если у процесса есть консоль
        text = _ANSI.sub("", message).replace("ERROR:", "").strip()
        # Загрузчик пишет в журнал «Ошибка [название]: причина» — название
        # подписчик получает отдельно
        if title and f"[{title}]:" in text:
            text = text.split(f"[{title}]:", 1)[1].strip()
        self._server.event({"type": "error", "url": url, "title": title, "message": text[:500]})

    def _publish(self) -> None:
        queued = sum(1 for v in list(self._queue() or []) if v.get("status") == "queued")
        self._server.publish({
            "analyzing": len(self._analyzing),
            "queued": queued,
            "downloads": list(self._active.values()),
        })
