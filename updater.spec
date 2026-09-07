# -*- mode: python ; coding: utf-8 -*-
"""
Сборка апдейтера (onefile -> dist/update.exe).

Интерфейс апдейтера переведён на Qt вместе с основным приложением, поэтому
HTML-шаблон data/ui/updater.html больше не нужен, а из зависимостей уходят
pywebview и pythonnet. Апдейтеру достаточно QtCore/QtGui/QtWidgets, requests
и psutil — всё остальное вырезано, чтобы onefile не распухал.
"""

a = Analysis(
    ['update/update.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=['app.utils.paths', 'app.ui.qss', 'app.ui.tokens', 'app.ui.assets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', '_tkinter',
        'test', 'unittest', 'lib2to3', 'pydoc_data', 'idlelib',
        'pip', 'wheel',
        'webview', 'pywebview', 'clr', 'clr_loader', 'pythonnet', 'bottle',
        # Апдейтеру нужны только базовые виджеты
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQuick',
        'PySide6.QtQml', 'PySide6.QtMultimedia', 'PySide6.QtSql', 'PySide6.QtTest',
        'PySide6.QtDesigner', 'PySide6.QtCharts', 'PySide6.Qt3DCore',
        'PySide6.QtNetwork', 'PySide6.QtSvg', 'PySide6.QtOpenGL',
        'PySide6.QtPrintSupport', 'PySide6.QtPdf',
        # Тяжёлые зависимости основного приложения апдейтеру не нужны
        'PIL', 'yt_dlp', 'pypdfium2', 'pypdfium2_raw', 'ffmpeg',
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='update',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['Qt6*.dll', 'python3*.dll', 'pyside6*.dll', 'shiboken6*.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['data/ui/src/icon.ico'],
)
