# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
Точка входа ClipTide.

В windowed-сборке нет ни консоли, ни stderr: любое исключение до создания
окна раньше превращалось в безымянный диалог PyInstaller. Поэтому падение
записывается в файл рядом с остальными логами и показывается пользователю
понятным сообщением.
"""

import sys
import traceback


def _report_crash(error: BaseException) -> None:
    text = "".join(traceback.format_exception(error))

    try:
        from app.utils.paths import LOGS_DIR
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        crash_file = LOGS_DIR / "crash.log"
        with open(crash_file, "a", encoding="utf-8") as handle:
            from datetime import datetime
            handle.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{text}")
        location = str(crash_file)
    except Exception:
        location = "не удалось записать лог"

    print(text)

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                f"ClipTide не смог запуститься.\n\n{error}\n\nПодробности: {location}",
                "ClipTide",
                0x10,   # MB_ICONERROR
            )
        except Exception:
            pass


def main() -> int:
    try:
        from app.ui.qt_app import main as run
        return run()
    except BaseException as error:      # noqa: BLE001 — верхний уровень
        _report_crash(error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
