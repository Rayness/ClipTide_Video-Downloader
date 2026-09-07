# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Самообновление приложения.

Начиная с 2.0 ClipTide — один exe, и обновление сводится к замене одного
файла. Отдельный update.exe для этого не нужен: Windows не даёт перезаписать
запущенный исполняемый файл, но **переименовать** его разрешает. На этом и
построена замена:

    ClipTide.exe -> ClipTide.exe.old      (работающий процесс не мешает)
    новый файл   -> ClipTide.exe
    перезапуск, а .old удаляется при следующем старте

Если что-то сорвётся между двумя шагами, старый файл возвращается на место,
поэтому пользователь не остаётся без программы.

Версии до 2.0 обновиться так не могут: там onedir-раскладка, где рядом с exe
лежит папка _internal с сотнями занятых файлов. Им остаётся прежний путь —
скачать сборку с GitHub вручную; интерфейс это и предлагает, когда
самообновление недоступно.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

from app.core.ui_channel import UIChannel
from app.utils.network import get_session
from app.utils.paths import APP_DIR, IS_ONEFILE, USER_DATA_DIR

#: Имя исполняемого файла внутри архива релиза
APP_EXECUTABLE = "ClipTide.exe"

#: Куда складываем скачанное, прежде чем менять файл на месте
DOWNLOAD_DIR = USER_DATA_DIR / "updates"

#: Минимальный размер вменяемой сборки. Защита от того, что сервер отдал
#: страницу с ошибкой вместо файла, а мы этим затёрли рабочий exe.
MIN_EXE_SIZE = 5 * 1024 * 1024

_HEADERS = {"User-Agent": "ClipTide-App"}


def self_update_supported() -> bool:
    """Самообновление есть только в onefile-сборке (см. модуль docstring)."""
    return IS_ONEFILE


def current_executable() -> Path:
    return Path(sys.executable).resolve()


def download_url_for(entry: dict) -> str:
    """
    Адрес, откуда берём новую сборку.

    Манифест исторически указывает на zip (его же читает старый апдейтер
    версий 1.7.x), поэтому поле url остаётся основным. Если в записи есть
    exe — берём его: качать голый файл дешевле, чем архив с ним внутри.
    """
    entry = entry or {}
    return str(entry.get("exe") or entry.get("url") or "")


def looks_like_executable(path: Path) -> bool:
    """Грубая проверка, что скачали PE-файл, а не HTML с ошибкой."""
    try:
        if path.stat().st_size < MIN_EXE_SIZE:
            return False
        with open(path, "rb") as handle:
            return handle.read(2) == b"MZ"
    except OSError:
        return False


def download_to(url: str, dest: Path, progress=None) -> Path:
    """Качает url в dest, дёргая progress(percent) по мере поступления."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    response = get_session().get(url, headers=_HEADERS, stream=True, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"сервер ответил {response.status_code}")

    total = int(response.headers.get("content-length", 0))
    received = 0
    last_percent = -1

    with open(dest, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue
            handle.write(chunk)
            received += len(chunk)
            if total > 0 and progress is not None:
                percent = int(received / total * 100)
                if percent != last_percent:
                    last_percent = percent
                    progress(percent)

    return dest


def extract_app_exe(archive: Path, into: Path) -> Path:
    """Достаёт ClipTide.exe из zip релиза."""
    into.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive) as zf:
        names = [n for n in zf.namelist()
                 if Path(n).name.lower() == APP_EXECUTABLE.lower()]
        if not names:
            raise RuntimeError(f"в архиве нет {APP_EXECUTABLE}")

        target = into / APP_EXECUTABLE
        with zf.open(names[0]) as source, open(target, "wb") as handle:
            shutil.copyfileobj(source, handle)

    return target


def swap_executable(new_exe: Path, target: Path) -> Path:
    """
    Ставит new_exe на место target, отодвигая текущий файл в .old.

    Возвращает путь к отодвинутому файлу. При неудаче возвращает старый файл
    на место и поднимает исключение — программа остаётся работоспособной.
    """
    backup = target.parent / (target.name + ".old")

    if backup.exists():
        try:
            backup.unlink()
        except OSError:
            # Занят прошлым процессом — уступим ему уникальное имя
            backup = target.parent / (target.name + ".old.1")
            if backup.exists():
                backup.unlink()

    target.rename(backup)                 # запущенный exe переименовать можно
    try:
        shutil.move(str(new_exe), str(target))
    except Exception:
        backup.rename(target)             # откат: возвращаем рабочую версию
        raise

    return backup


class SelfUpdater:
    """Скачивает новую сборку и подменяет исполняемый файл."""

    def __init__(self, context):
        self.ctx = context
        self._busy = False

    @property
    def ui(self) -> UIChannel:
        return getattr(self.ctx, "ui", None) or UIChannel()

    # ------------------------------------------------------------------
    def start(self, entry: dict) -> None:
        """Запускает обновление в фоне. Повторные вызовы игнорируются."""
        if self._busy:
            return
        self._busy = True
        threading.Thread(target=self._run, args=(entry or {},), daemon=True).start()

    def _emit(self, state: str, percent: int = 0, detail: str = "") -> None:
        """
        Сообщает интерфейсу состояние; готовых фраз отсюда не уходит.

        Текст собирает страница настроек — иначе строки пришлось бы переводить
        в слое логики, который про язык интерфейса ничего не знает. В detail
        едет уточнение: для ready — номер версии, для error — причина.
        """
        self.ui.self_update_progress(state, percent, detail)

    def _run(self, entry: dict) -> None:
        try:
            self._apply(entry)
        except Exception as e:                    # noqa: BLE001 — верхний уровень
            self._emit("error", 0, str(e))
            self.ui.log(f"Самообновление не удалось: {e}", "error")
        finally:
            self._busy = False

    def _apply(self, entry: dict) -> None:
        if not self_update_supported():
            raise RuntimeError(
                "самообновление доступно только в сборке одним файлом"
            )

        url = download_url_for(entry)
        if not url:
            raise RuntimeError("в манифесте нет адреса загрузки")

        target = current_executable()
        if target.parent != APP_DIR:
            # Подстраховка: меняем только тот файл, из которого запущены
            raise RuntimeError("не удалось определить путь к программе")

        if DOWNLOAD_DIR.exists():
            shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        self._emit("downloading", 0)
        downloaded = download_to(
            url,
            DOWNLOAD_DIR / Path(url).name.split("?")[0],
            progress=lambda p: self._emit("downloading", p),
        )

        self._emit("installing", 100)

        if zipfile.is_zipfile(downloaded):
            new_exe = extract_app_exe(downloaded, DOWNLOAD_DIR / "unpacked")
        else:
            new_exe = downloaded

        if not looks_like_executable(new_exe):
            raise RuntimeError("скачанный файл не похож на программу")

        swap_executable(new_exe, target)
        shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)

        self._emit("ready", 100, str(entry.get("version", "")))

    # ------------------------------------------------------------------
    def restart(self) -> None:
        """Запускает обновлённый exe. Закрытие текущего окна — на стороне UI."""
        target = current_executable()
        try:
            subprocess.Popen([str(target)], cwd=str(target.parent),
                             close_fds=True)
        except Exception as e:                    # noqa: BLE001
            self.ui.log(f"Не удалось перезапустить программу: {e}", "error")
            raise


def cleanup_backup() -> int:
    """
    Удаляет отодвинутый прошлый exe. Вызывается при старте: пока программа
    работала из старого файла, удалить его было нельзя.
    """
    if not IS_ONEFILE:
        return 0

    freed = 0
    for name in (APP_EXECUTABLE + ".old", APP_EXECUTABLE + ".old.1"):
        leftover = APP_DIR / name
        if not leftover.is_file():
            continue
        try:
            size = leftover.stat().st_size
            leftover.unlink()
            freed += size
        except OSError:
            continue                              # ещё занят — уберём позже
    return freed

