# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Проверка наличия WebView2 Runtime (необходим pywebview на Windows)
и его автоматическая установка, если компонент отсутствует или был удалён.

Порядок:
 1. Если рядом с exe лежит папка WebView2 (Fixed Version Runtime) —
    используем её, система вообще не трогается.
 2. Если рантайм установлен в системе (Evergreen) — ничего не делаем.
 3. Иначе предлагаем пользователю установить: скачиваем официальный
    бутстраппер Microsoft (~2 МБ) и запускаем тихую установку.
 4. Если не получилось — открываем страницу загрузки Microsoft.
"""

import os
import sys
import subprocess
import tempfile

# Официальный Evergreen Bootstrapper от Microsoft
BOOTSTRAPPER_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
DOWNLOAD_PAGE = "https://developer.microsoft.com/microsoft-edge/webview2/"

# {F3017226-...} — GUID клиента WebView2 Runtime в реестре EdgeUpdate
_WEBVIEW2_CLIENT_KEY = r"\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def _get_fixed_runtime_dir():
    """Возвращает путь к Fixed Version Runtime рядом с exe, если он там есть."""
    from app.utils.paths import FIXED_WEBVIEW2_DIR
    exe = FIXED_WEBVIEW2_DIR / "msedgewebview2.exe"
    if exe.exists():
        return str(FIXED_WEBVIEW2_DIR)
    return None


def is_webview2_installed() -> bool:
    """Проверяет наличие Evergreen WebView2 Runtime через реестр."""
    if sys.platform != "win32":
        return True
    import winreg

    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node" + _WEBVIEW2_CLIENT_KEY),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE" + _WEBVIEW2_CLIENT_KEY),
        (winreg.HKEY_CURRENT_USER, r"Software" + _WEBVIEW2_CLIENT_KEY),
    ]
    for root, subkey in keys:
        try:
            with winreg.OpenKey(root, subkey) as key:
                version, _ = winreg.QueryValueEx(key, "pv")
                if version and version != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False


def _message_box(text: str, title: str, flags: int) -> int:
    import ctypes
    return ctypes.windll.user32.MessageBoxW(None, text, title, flags)


def _install_runtime() -> bool:
    """Скачивает бутстраппер и запускает тихую установку. Возвращает True при успехе."""
    import requests

    installer_path = os.path.join(tempfile.gettempdir(), "MicrosoftEdgeWebView2Setup.exe")
    try:
        response = requests.get(BOOTSTRAPPER_URL, timeout=60)
        response.raise_for_status()
        with open(installer_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        print(f"[WebView2] Не удалось скачать установщик: {e}")
        return False

    try:
        # Без прав администратора бутстраппер выполнит установку per-user
        result = subprocess.run(
            [installer_path, "/silent", "/install"],
            timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print(f"[WebView2] Установщик завершился с кодом {result.returncode}")
    except Exception as e:
        print(f"[WebView2] Ошибка установки: {e}")
        return False
    finally:
        try:
            os.remove(installer_path)
        except OSError:
            pass

    return is_webview2_installed()


def ensure_webview2(app_name: str = "ClipTide") -> bool:
    """
    Гарантирует доступность WebView2 перед запуском окна.
    Возвращает False, если рантайма нет и установить его не удалось —
    в этом случае запускать webview нельзя.
    """
    if sys.platform != "win32":
        return True

    # 1. Fixed Version Runtime рядом с программой (полная независимость от системы)
    fixed_dir = _get_fixed_runtime_dir()
    if fixed_dir:
        os.environ["WEBVIEW2_BROWSER_EXECUTABLE_FOLDER"] = fixed_dir
        print(f"[WebView2] Используется локальный рантайм: {fixed_dir}")
        return True

    # 2. Системный Evergreen Runtime
    if is_webview2_installed():
        return True

    # 3. Рантайма нет — предлагаем установить
    import ctypes
    MB_YESNO = 0x04
    MB_ICONWARNING = 0x30
    MB_ICONERROR = 0x10
    MB_OK = 0x00
    IDYES = 6

    answer = _message_box(
        f"Для работы {app_name} требуется компонент Microsoft Edge WebView2, "
        "но он не найден в системе.\n\n"
        "Установить его сейчас автоматически? (потребуется интернет)\n\n"
        f"{app_name} requires the Microsoft Edge WebView2 runtime, "
        "but it was not found. Install it now?",
        f"{app_name} — WebView2",
        MB_YESNO | MB_ICONWARNING,
    )

    if answer == IDYES and _install_runtime():
        return True

    _message_box(
        "Компонент WebView2 не был установлен. Сейчас откроется страница загрузки — "
        "установите WebView2 Runtime и запустите программу снова.\n\n"
        "WebView2 was not installed. The download page will open — "
        "install the runtime and start the app again.",
        f"{app_name} — WebView2",
        MB_OK | MB_ICONERROR,
    )
    import webbrowser
    webbrowser.open(DOWNLOAD_PAGE)
    return False
