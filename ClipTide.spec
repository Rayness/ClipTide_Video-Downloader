# -*- mode: python ; coding: utf-8 -*-
"""
Сборка ClipTide. Два режима, переключаются переменной окружения:

    CLIPTIDE_BUILD=onefile  (по умолчанию) -> dist/ClipTide.exe, один файл
    CLIPTIDE_BUILD=onedir                  -> dist/ClipTide/ с _internal/

Оба режима используют один и тот же Analysis, чтобы списки исключений и
вырезаемого не разъезжались. Цена onefile: загрузчик распаковывает всё
содержимое (вместе со 160 МБ ffmpeg) во временную папку при каждом запуске,
поэтому старт заметно медленнее, чем у onedir.

Что здесь решается помимо обычной сборки:

1. ДЕДУПЛИКАЦИЯ FFMPEG. Раньше папка ffmpeg отдавалась через `datas`. PyInstaller
   переклассифицирует найденные там .dll в бинарники и прогоняет по ним анализ
   зависимостей, поэтому av*.dll оказывались в сборке ДВАЖДЫ: внутри
   _internal/ffmpeg/.../bin/ и ещё раз в корне _internal/. Это ~150 МБ впустую.

2. FFPLAY. ffplay.exe (12.8 МБ) не вызывается нигде в коде — не кладём.

3. ОТСЕВ ЛИШНЕГО В QT. Хук PySide6 тянет всё подряд: программный OpenGL
   (20 МБ), переводы Qt на все языки мира (6.7 МБ), QtNetwork с собственной
   копией OpenSSL. Приложение — обычные виджеты, сеть на requests,
   иконки рисуются кодом. Список PRUNE_PATTERNS ниже вырезает это.

4. EXCLUDES. tkinter/tcl/tk (~9 МБ) тянулись транзитивно, хотя диалоги давно
   нативные. Отдельно исключены pywebview/pythonnet/bottle — интерфейс
   переехал на Qt и больше не зависит от Edge WebView2 Runtime.
"""

import fnmatch
import os
from pathlib import Path

PROJECT_DIR = Path(SPECPATH)

# Языки, которые поддерживает приложение: переводы Qt для остальных не нужны
APP_LANGUAGES = ('ru', 'en', 'uk', 'de', 'fr', 'it', 'pl', 'ja', 'zh')

# --------------------------------------------------------------------------
# FFmpeg: берём только то, что реально запускается, плюс их зависимости.
# --------------------------------------------------------------------------
FFMPEG_TOOLS = ('ffmpeg.exe', 'ffprobe.exe')      # ffplay.exe намеренно пропущен
FFMPEG_DEST = 'ffmpeg/bin'


def _find_ffmpeg_bin():
    """Папка с бинарями ffmpeg — поддерживаем плоскую и версионированную раскладку."""
    candidates = [PROJECT_DIR / 'ffmpeg' / 'bin']
    candidates += sorted((PROJECT_DIR / 'ffmpeg').glob('*/bin'))
    for candidate in candidates:
        if (candidate / 'ffmpeg.exe').is_file():
            return candidate
    return None


_ffmpeg_bin = _find_ffmpeg_bin()
if _ffmpeg_bin is None:
    raise SystemExit(
        'ffmpeg не найден. Ожидается ffmpeg/bin/ffmpeg.exe (или '
        'ffmpeg/<любая-папка>/bin/ffmpeg.exe) в корне проекта.'
    )

_ffmpeg_files = [p for p in _ffmpeg_bin.iterdir()
                 if p.name in FFMPEG_TOOLS or p.suffix.lower() == '.dll']
ffmpeg_binaries = [(str(p), FFMPEG_DEST) for p in _ffmpeg_files]
_ffmpeg_names = {p.name.lower() for p in _ffmpeg_files}

# --------------------------------------------------------------------------
# Что вырезать из собранного дерева (сопоставляется с путём назначения)
# --------------------------------------------------------------------------
PRUNE_PATTERNS = [
    # Программный OpenGL (Mesa llvmpipe). QtWidgets рисует растровым движком,
    # а не через OpenGL, поэтому 20 МБ фолбэка не нужны.
    'PySide6/opengl32sw.dll',
    'PySide6/Qt6Pdf*.dll',

    # Сеть у нас на requests; вместе с QtNetwork уходят tls-плагины и
    # вторая копия OpenSSL, которую Qt тащит для себя.
    'PySide6/Qt6Network.dll',
    'PySide6/QtNetwork.pyd',
    'PySide6/plugins/tls/*',
    'PySide6/plugins/networkinformation/*',
    'PySide6/lib*crypto*x64.dll',
    'PySide6/lib*ssl*x64.dll',

    # SVG больше не грузим — иконки рисуются кодом в app/ui/widgets/icons.py
    'PySide6/Qt6Svg.dll',
    'PySide6/plugins/iconengines/*',
    'PySide6/plugins/imageformats/qsvg.dll',

    # Экзотические форматы картинок: превью у нас JPEG/PNG/WEBP
    'PySide6/plugins/imageformats/qtiff.dll',
    'PySide6/plugins/imageformats/qtga.dll',
    'PySide6/plugins/imageformats/qicns.dll',
    'PySide6/plugins/imageformats/qwbmp.dll',
    'PySide6/plugins/imageformats/qpdf.dll',
]


def _prune(entries, label):
    """Убирает из TOC всё, что попало под PRUNE_PATTERNS или чужой перевод Qt."""
    kept, dropped = [], 0
    for entry in entries:
        dest = entry[0].replace('\\', '/')

        if any(fnmatch.fnmatch(dest, pattern) for pattern in PRUNE_PATTERNS):
            dropped += 1
            continue

        # Переводы Qt: qtbase_de.qm и т.п. Оставляем только наши языки.
        if dest.startswith('PySide6/translations/') and dest.endswith('.qm'):
            stem = Path(dest).stem                    # qtbase_de
            language = stem.split('_', 1)[1] if '_' in stem else ''
            if not any(language == code or language.startswith(code + '_')
                       for code in APP_LANGUAGES):
                dropped += 1
                continue

        kept.append(entry)

    if dropped:
        print(f'[spec] {label}: вырезано {dropped} лишних файлов Qt')
    return kept


a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=ffmpeg_binaries,
    datas=[
        ('data', 'data'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Диалоги нативные, Tk не нужен (~9 МБ вместе с tcl/tk data)
        'tkinter', '_tkinter', 'Tkinter',
        # Тестовые и служебные пакеты стандартной библиотеки
        'test', 'unittest', 'lib2to3', 'pydoc_data', 'idlelib',
        # Инструменты установки в рантайме не нужны
        'pip', 'wheel',
        # Модули Qt, которые приложение не использует
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQuick',
        'PySide6.QtQml', 'PySide6.Qt3DCore', 'PySide6.QtCharts',
        'PySide6.QtDataVisualization', 'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets', 'PySide6.QtBluetooth', 'PySide6.QtPositioning',
        'PySide6.QtSensors', 'PySide6.QtSerialPort', 'PySide6.QtDesigner',
        'PySide6.QtTest', 'PySide6.QtSql', 'PySide6.QtSvg', 'PySide6.QtSvgWidgets',
        'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets', 'PySide6.QtPrintSupport',
        'PySide6.QtNetwork', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
        # PyMuPDF заменён на pypdfium2 (37 МБ -> 4 МБ)
        'fitz', 'pymupdf',
        # Интерфейс переведён на Qt: pywebview, его бэкенд на .NET и
        # HTTP-сервер редактора больше не нужны
        'webview', 'pywebview', 'clr', 'clr_loader', 'pythonnet',
        'bottle', 'proxy_tools',
    ],
    noarchive=False,
    optimize=1,   # -O: выкидывает assert'ы. -OO (docstrings) не берём —
                  # часть библиотек читает __doc__ в рантайме.
)

# --------------------------------------------------------------------------
# Убираем дубликаты ffmpeg-DLL, которые анализ зависимостей положил в корень.
# --------------------------------------------------------------------------
_deduped, _dropped = [], 0
for entry in a.binaries:
    dest_dir, dest_name = os.path.split(entry[0])
    if dest_name.lower() in _ffmpeg_names and dest_dir.replace('\\', '/') != FFMPEG_DEST:
        _dropped += 1
        continue
    _deduped.append(entry)

if _dropped:
    print(f'[spec] ffmpeg: убрано {_dropped} дублирующихся бинарников из корня _internal')

a.binaries = _prune(_deduped, 'binaries')
a.datas = _prune(a.datas, 'datas')

pyz = PYZ(a.pure)

# UPX ломает подписанные системные библиотеки и Qt-плагины — не трогаем их.
# Крупные DLL ffmpeg тоже исключены: выигрыш небольшой, а сборка и распаковка
# ощутимо дольше.
UPX_EXCLUDE = [
    'vcruntime140.dll', 'msvcp140*.dll', 'ucrtbase.dll', 'python3*.dll',
    'Qt6*.dll', 'pyside6*.dll', 'shiboken6*.dll',
    'avcodec-*.dll', 'avformat-*.dll', 'avfilter-*.dll', 'avutil-*.dll',
    'avdevice-*.dll', 'swscale-*.dll', 'swresample-*.dll', 'postproc-*.dll',
    'ffmpeg.exe', 'ffprobe.exe', 'qjs.exe',
]

BUILD_MODE = os.environ.get('CLIPTIDE_BUILD', 'onefile').strip().lower()
if BUILD_MODE not in ('onefile', 'onedir'):
    raise SystemExit(
        f'CLIPTIDE_BUILD={BUILD_MODE!r}: ожидается "onefile" или "onedir".'
    )
print(f'[spec] режим сборки: {BUILD_MODE}')

_exe_common = dict(
    name='ClipTide',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['favicon.ico'],
)

if BUILD_MODE == 'onefile':
    # Всё внутрь exe: binaries и datas передаются прямо в EXE, COLLECT не нужен
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        exclude_binaries=False,
        upx_exclude=UPX_EXCLUDE,
        runtime_tmpdir=None,
        **_exe_common,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        upx_exclude=[],
        **_exe_common,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=UPX_EXCLUDE,
        name='ClipTide',
    )
