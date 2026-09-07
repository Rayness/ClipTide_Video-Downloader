# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""Экран настроек."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..i18n import t
from ..widgets import icons

LANGUAGES = [
    ("Русский", "ru"), ("English", "en"), ("Українська", "uk"), ("Deutsch", "de"),
    ("Français", "fr"), ("Italiano", "it"), ("Polski", "pl"), ("日本語", "ja"),
    ("中文", "cn"),
]

SUBTITLE_LANGS = [
    ("Все доступные", "all"), ("Русские", "ru"), ("Английские", "en"),
    ("Украинские", "uk"), ("Немецкие", "de"), ("Французские", "fr"),
]

AUDIO_LANGS = [
    ("Оригинальная дорожка", "none"), ("Все дорожки", "all_tracks"),
    ("Русская", "ru"), ("Английская", "en"), ("Украинская", "uk"),
]

EDITOR_PRESETS = [
    ("Очень быстро", "ultrafast"), ("Быстро", "fast"),
    ("Сбалансированно", "medium"), ("Качественно", "slow"),
]

EDITOR_FORMATS = [("MP4", "mp4"), ("MKV", "mkv")]

UPDATE_CHANNELS = [("Стабильный", "stable"), ("Тестовый (dev)", "dev")]


def _section(title: str) -> QLabel:
    label = QLabel(title)
    label.setProperty("heading", "2")
    return label


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("muted", "true")
    return label


def _left(widget: QWidget) -> QHBoxLayout:
    """Кладёт виджет влево, не давая ему растянуться на всю ширину вкладки."""
    row = QHBoxLayout()
    row.addWidget(widget)
    row.addStretch(1)
    return row


def _separator() -> QFrame:
    line = QFrame()
    line.setProperty("separator", "true")
    return line


def _scrollable(inner: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    area.setWidget(inner)
    return area


class SettingsPage(QWidget):
    def __init__(self, settings, channel, theme_manager, version: str,
                 on_theme_applied=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = settings
        self.ctx = settings.ctx
        self.channel = channel
        self.themes = theme_manager
        self.version = version
        self._on_theme_applied = on_theme_applied
        self._loading = True

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(14)

        title = QLabel(t("sections.setting", "Настройки"))
        title.setProperty("heading", "1")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(_scrollable(self._build_general_tab()), "Общие")
        self.tabs.addTab(_scrollable(self._build_appearance_tab()), "Внешний вид")
        self.tabs.addTab(_scrollable(self._build_download_tab()), "Загрузка")
        self.tabs.addTab(_scrollable(self._build_editor_tab()), "Редактор")
        self.tabs.addTab(_scrollable(self._build_network_tab()), "Сеть и обновления")
        root.addWidget(self.tabs, 1)

        self._connect_channel()
        self._loading = False

    # ==================================================================
    # Общие
    # ==================================================================
    def _build_general_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 16, 12, 16)
        layout.setSpacing(12)

        layout.addWidget(_section("Язык интерфейса"))
        self.cmb_language = QComboBox()
        for label, code in LANGUAGES:
            self.cmb_language.addItem(label, code)
        self._select(self.cmb_language, self.ctx.language)
        self.cmb_language.currentIndexChanged.connect(self._on_language)
        self.cmb_language.setFixedWidth(280)
        layout.addLayout(_left(self.cmb_language))

        self.lbl_language_hint = _caption("")
        self.lbl_language_hint.setVisible(False)
        self.lbl_language_hint.setWordWrap(True)
        layout.addWidget(self.lbl_language_hint)

        layout.addWidget(_separator())
        layout.addWidget(_section("Папки"))

        self.lbl_download_dir = _caption("")
        layout.addWidget(self.lbl_download_dir)
        self.btn_download_dir = QPushButton("  Папка загрузок")
        self.btn_download_dir.clicked.connect(self.settings.choose_folder)
        layout.addLayout(_left(self.btn_download_dir))

        self.lbl_converter_dir = _caption("")
        layout.addWidget(self.lbl_converter_dir)
        self.btn_converter_dir = QPushButton("  Папка конвертации")
        self.btn_converter_dir.clicked.connect(self.settings.choose_converter_folder)
        layout.addLayout(_left(self.btn_converter_dir))

        layout.addWidget(_separator())
        layout.addWidget(_section("Открывать папку по завершении"))

        self.chk_open_dl = self._checkbox("после загрузки", "Folders", "dl")
        self.chk_open_cv = self._checkbox("после конвертации", "Folders", "cv")
        self.chk_open_ed = self._checkbox("после обрезки", "Folders", "editor")
        for widget in (self.chk_open_dl, self.chk_open_cv, self.chk_open_ed):
            layout.addWidget(widget)

        layout.addWidget(_separator())
        layout.addWidget(_section("Уведомления"))
        self.chk_notify_dl = self._checkbox("о завершении загрузок", "Notifications", "downloads")
        self.chk_notify_cv = self._checkbox("о завершении конвертации", "Notifications", "conversion")
        layout.addWidget(self.chk_notify_dl)
        layout.addWidget(self.chk_notify_cv)

        layout.addStretch(1)
        self._refresh_folder_labels()
        return page

    # ==================================================================
    # Внешний вид
    # ==================================================================
    def _build_appearance_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 16, 12, 16)
        layout.setSpacing(12)

        layout.addWidget(_section("Тема"))
        self.cmb_theme = QComboBox()
        self._fill_themes()
        self.cmb_theme.currentIndexChanged.connect(self._on_theme)
        layout.addWidget(self.cmb_theme)

        layout.addWidget(_caption("Вариант темы"))
        self.cmb_style = QComboBox()
        self.cmb_style.currentIndexChanged.connect(self._on_style)
        layout.addWidget(self.cmb_style)
        self._fill_styles()

        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_import_theme = QPushButton("  Установить из ZIP")
        self.btn_import_theme.clicked.connect(self.settings.import_theme_from_zip)
        row.addWidget(self.btn_import_theme)

        self.btn_delete_theme = QPushButton("Удалить тему")
        self.btn_delete_theme.setProperty("variant", "danger")
        self.btn_delete_theme.clicked.connect(self._on_delete_theme)
        row.addWidget(self.btn_delete_theme)
        row.addStretch(1)
        layout.addLayout(row)

        self.lbl_theme_info = _caption("")
        self.lbl_theme_info.setWordWrap(True)
        layout.addWidget(self.lbl_theme_info)

        layout.addWidget(_separator())
        layout.addWidget(_section("О программе"))
        about = _caption(
            f"ClipTide {self.version}\n"
            "Свободное ПО по лицензии GPLv3.\n"
            "Темы читаются из папки themes в данных приложения."
        )
        about.setWordWrap(True)
        layout.addWidget(about)

        layout.addStretch(1)
        self._refresh_theme_info()
        return page

    # ==================================================================
    # Загрузка
    # ==================================================================
    def _build_download_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 16, 12, 16)
        layout.setSpacing(12)

        layout.addWidget(_section("Субтитры"))
        self.chk_subs = self._checkbox("Скачивать субтитры", "Subtitles", "enabled")
        self.chk_subs.stateChanged.connect(self._sync_subtitle_controls)
        layout.addWidget(self.chk_subs)

        self.chk_subs_auto = self._checkbox("Включая автоматические", "Subtitles", "auto")
        layout.addWidget(self.chk_subs_auto)

        self.chk_subs_embed = self._checkbox("Встраивать в видеофайл", "Subtitles", "embed")
        layout.addWidget(self.chk_subs_embed)

        layout.addWidget(_caption("Языки субтитров"))
        self.cmb_subs_lang = QComboBox()
        for label, code in SUBTITLE_LANGS:
            self.cmb_subs_lang.addItem(label, code)
        self._select(self.cmb_subs_lang,
                     self.ctx.config.get("Subtitles", "langs", fallback="all"))
        self.cmb_subs_lang.currentIndexChanged.connect(
            lambda: self.settings.switch_subs_setting("langs", self.cmb_subs_lang.currentData())
        )
        layout.addWidget(self.cmb_subs_lang)

        layout.addWidget(_separator())
        layout.addWidget(_section("Аудиодорожки"))
        self.cmb_audio = QComboBox()
        for label, code in AUDIO_LANGS:
            self.cmb_audio.addItem(label, code)
        self._select(self.cmb_audio, self.ctx.config.get("Audio", "lang", fallback="none"))
        self.cmb_audio.currentIndexChanged.connect(
            lambda: self.settings.switch_audio_setting("lang", self.cmb_audio.currentData())
        )
        layout.addWidget(self.cmb_audio)
        layout.addWidget(_caption(
            "«Все дорожки» принудительно сохраняет результат в MKV: "
            "MP4 плохо склеивает несколько звуковых дорожек."
        ))

        layout.addStretch(1)
        self._sync_subtitle_controls()
        return page

    # ==================================================================
    # Редактор
    # ==================================================================
    def _build_editor_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 16, 12, 16)
        layout.setSpacing(12)

        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(10)

        grid.addWidget(_caption("Пресет кодирования"), 0, 0)
        self.cmb_preset = QComboBox()
        for label, value in EDITOR_PRESETS:
            self.cmb_preset.addItem(label, value)
        self._select(self.cmb_preset, self.ctx.config.get("Editor", "preset", fallback="fast"))
        self.cmb_preset.currentIndexChanged.connect(
            lambda: self.settings.switch_editor_setting("preset", self.cmb_preset.currentData())
        )
        grid.addWidget(self.cmb_preset, 0, 1)

        grid.addWidget(_caption("Контейнер"), 1, 0)
        self.cmb_editor_format = QComboBox()
        for label, value in EDITOR_FORMATS:
            self.cmb_editor_format.addItem(label, value)
        self._select(self.cmb_editor_format,
                     self.ctx.config.get("Editor", "format", fallback="mp4"))
        self.cmb_editor_format.currentIndexChanged.connect(
            lambda: self.settings.switch_editor_setting(
                "format", self.cmb_editor_format.currentData())
        )
        grid.addWidget(self.cmb_editor_format, 1, 1)
        layout.addLayout(grid)

        row = QHBoxLayout()
        row.addWidget(_caption("Качество (CRF)"))
        row.addStretch(1)
        self.lbl_crf = QLabel(self.ctx.config.get("Editor", "crf", fallback="18"))
        row.addWidget(self.lbl_crf)
        layout.addLayout(row)

        self.sld_crf = QSlider(Qt.Horizontal)
        self.sld_crf.setRange(14, 32)
        self.sld_crf.setValue(int(self.ctx.config.get("Editor", "crf", fallback="18")))
        self.sld_crf.valueChanged.connect(self._on_crf)
        layout.addWidget(self.sld_crf)
        layout.addWidget(_caption("Меньше значение — выше качество и больше размер файла."))

        layout.addStretch(1)
        return page

    # ==================================================================
    # Сеть и обновления
    # ==================================================================
    def _build_network_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 16, 12, 16)
        layout.setSpacing(12)

        layout.addWidget(_section("Прокси"))
        self.chk_proxy = QCheckBox("Использовать прокси")
        self.chk_proxy.setChecked(str(self.ctx.proxy_enabled) == "True")
        self.chk_proxy.stateChanged.connect(self._on_proxy_toggle)
        layout.addWidget(self.chk_proxy)

        self.txt_proxy = QLineEdit(self.ctx.proxy_url)
        self.txt_proxy.setPlaceholderText("http://user:pass@host:port")
        self.txt_proxy.editingFinished.connect(
            lambda: self.settings.switch_proxy_url(self.txt_proxy.text().strip())
        )
        layout.addWidget(self.txt_proxy)

        row = QHBoxLayout()
        self.btn_test_proxy = QPushButton("Проверить соединение")
        self.btn_test_proxy.clicked.connect(
            lambda: self.settings.test_user_proxy(self.txt_proxy.text().strip())
        )
        row.addWidget(self.btn_test_proxy)
        self.lbl_proxy_status = _caption("")
        row.addWidget(self.lbl_proxy_status)
        row.addStretch(1)
        layout.addLayout(row)

        layout.addWidget(_separator())
        layout.addWidget(_section("Обновления"))

        layout.addWidget(_caption("Канал обновлений"))
        self.cmb_channel = QComboBox()
        for label, value in UPDATE_CHANNELS:
            self.cmb_channel.addItem(label, value)
        self._select(self.cmb_channel,
                     self.ctx.config.get("Updates", "channel", fallback="stable"))
        self.cmb_channel.currentIndexChanged.connect(
            lambda: self.settings.switch_update_channel(self.cmb_channel.currentData())
        )
        layout.addWidget(self.cmb_channel)

        row2 = QHBoxLayout()
        self.btn_check_update = QPushButton("Проверить обновления")
        self.btn_check_update.clicked.connect(self._on_check_update)
        row2.addWidget(self.btn_check_update)

        self.btn_install_update = QPushButton("Установить")
        self.btn_install_update.setProperty("variant", "primary")
        self.btn_install_update.setEnabled(False)
        self.btn_install_update.clicked.connect(self.settings.launch_update)
        row2.addWidget(self.btn_install_update)
        row2.addStretch(1)
        layout.addLayout(row2)

        self.lbl_update_status = _caption(f"Текущая версия: {self.version}")
        self.lbl_update_status.setWordWrap(True)
        layout.addWidget(self.lbl_update_status)

        layout.addStretch(1)
        self._sync_proxy_controls()
        return page

    # ==================================================================
    # Вспомогательное
    # ==================================================================
    @staticmethod
    def _select(combo: QComboBox, value) -> None:
        index = combo.findData(str(value))
        if index >= 0:
            combo.setCurrentIndex(index)

    def _checkbox(self, text: str, section: str, key: str) -> QCheckBox:
        box = QCheckBox(text)
        box.setChecked(self.ctx.config.get(section, key, fallback="False") == "True")
        box.stateChanged.connect(
            lambda state, s=section, k=key: self._save_flag(s, k, state)
        )
        return box

    def _save_flag(self, section: str, key: str, state) -> None:
        if self._loading:
            return
        value = "True" if Qt.CheckState(state) == Qt.Checked else "False"
        self.ctx.update_config_value(section, key, value)

    def _refresh_folder_labels(self) -> None:
        metrics = self.lbl_download_dir.fontMetrics()
        width = 520
        self.lbl_download_dir.setText(
            metrics.elidedText(str(self.ctx.download_folder), Qt.ElideMiddle, width)
        )
        self.lbl_download_dir.setToolTip(str(self.ctx.download_folder))
        self.lbl_converter_dir.setText(
            metrics.elidedText(str(self.ctx.converter_folder), Qt.ElideMiddle, width)
        )
        self.lbl_converter_dir.setToolTip(str(self.ctx.converter_folder))

    # ------------------------------------------------------------------
    def _fill_themes(self) -> None:
        self.cmb_theme.blockSignals(True)
        self.cmb_theme.clear()
        for theme in self.themes.as_ui_list():
            suffix = "" if theme["builtin"] else "  ·  установлена"
            self.cmb_theme.addItem(f"{theme['name']}{suffix}", theme["id"])
        self._select(self.cmb_theme, self.ctx.theme)
        self.cmb_theme.blockSignals(False)

    def _fill_styles(self) -> None:
        self.cmb_style.blockSignals(True)
        self.cmb_style.clear()
        theme = self.themes.themes.get(self.cmb_theme.currentData())
        styles = list(theme.styles) if theme and theme.styles else ["default"]
        if "default" not in styles:
            styles.insert(0, "default")
        for style in styles:
            self.cmb_style.addItem(
                {"default": "Основной", "light": "Светлый"}.get(style, style.title()),
                style,
            )
        self._select(self.cmb_style, self.ctx.style)
        self.cmb_style.blockSignals(False)

    def _refresh_theme_info(self) -> None:
        theme = self.themes.themes.get(self.cmb_theme.currentData())
        if theme is None:
            self.lbl_theme_info.setText("")
            return
        parts = [f"Автор: {theme.author or 'не указан'}"]
        if theme.version:
            parts.append(f"версия {theme.version}")
        parts.append("встроенная" if theme.builtin else "установленная")
        self.lbl_theme_info.setText("  ·  ".join(parts))
        self.btn_delete_theme.setEnabled(not theme.builtin)

    def _apply_theme(self) -> None:
        theme_id = self.cmb_theme.currentData()
        style = self.cmb_style.currentData() or "default"
        self.themes.apply(theme_id, style)
        if self._on_theme_applied:
            self._on_theme_applied(self.themes.palette_for(theme_id, style))

    # ------------------------------------------------------------------
    # Обработчики
    # ------------------------------------------------------------------
    def _on_language(self) -> None:
        if self._loading:
            return
        self.settings.switch_language(self.cmb_language.currentData())
        # Подписи виджетов собираются один раз при старте, поэтому смена
        # языка применяется к уже построенному интерфейсу только после
        # перезапуска. Говорим об этом прямо, а не молча.
        self.lbl_language_hint.setText(
            t("settings.restart_required",
              "Язык интерфейса сменится после перезапуска приложения")
        )
        self.lbl_language_hint.setVisible(True)

    def _on_theme(self) -> None:
        if self._loading:
            return
        self.settings.switch_theme(self.cmb_theme.currentData())
        self._fill_styles()
        self._refresh_theme_info()
        self._apply_theme()

    def _on_style(self) -> None:
        if self._loading:
            return
        self.settings.switch_style(self.cmb_style.currentData())
        self._apply_theme()

    def _on_delete_theme(self) -> None:
        theme_id = self.cmb_theme.currentData()
        if self.settings.delete_theme(theme_id):
            self.themes.reload()
            self._fill_themes()
            self._fill_styles()
            self._apply_theme()

    def _on_crf(self, value: int) -> None:
        self.lbl_crf.setText(str(value))
        if not self._loading:
            self.settings.switch_editor_setting("crf", str(value))

    def _on_proxy_toggle(self, state) -> None:
        enabled = "True" if Qt.CheckState(state) == Qt.Checked else "False"
        if not self._loading:
            self.settings.switch_proxy(enabled)
        self._sync_proxy_controls()

    def _sync_proxy_controls(self) -> None:
        enabled = self.chk_proxy.isChecked()
        self.txt_proxy.setEnabled(enabled)
        self.btn_test_proxy.setEnabled(enabled)

    def _sync_subtitle_controls(self) -> None:
        enabled = self.chk_subs.isChecked()
        for widget in (self.chk_subs_auto, self.chk_subs_embed, self.cmb_subs_lang):
            widget.setEnabled(enabled)

    def _on_check_update(self) -> None:
        self.lbl_update_status.setText("Проверяю...")
        self.btn_check_update.setEnabled(False)
        self.settings.check_update_for_channel(self.cmb_channel.currentData())

    # ------------------------------------------------------------------
    # События канала
    # ------------------------------------------------------------------
    def _connect_channel(self) -> None:
        signals = self.channel.signals
        signals.download_folder_changed.connect(lambda _p: self._refresh_folder_labels())
        signals.converter_folder_changed.connect(lambda _p: self._refresh_folder_labels())
        signals.proxy_check_result.connect(self.on_proxy_result)
        signals.update_check_result.connect(self.on_update_result)
        signals.themes_reloaded.connect(self.on_themes_reloaded)

    def on_proxy_result(self, state: str, message: str) -> None:
        prefix = {"loading": "…", "success": "✓", "error": "✕"}.get(state, "")
        self.lbl_proxy_status.setText(f"{prefix} {message}")

    def on_update_result(self, result: dict) -> None:
        self.btn_check_update.setEnabled(True)
        if result.get("error"):
            self.lbl_update_status.setText(f"Ошибка: {result.get('message', '')}")
            return
        if result.get("has_update"):
            self.lbl_update_status.setText(
                f"Доступна версия {result.get('latest_version')} "
                f"(установлена {result.get('current_version')})\n"
                f"{result.get('description', '')}"
            )
            self.btn_install_update.setEnabled(True)
        else:
            self.lbl_update_status.setText(
                f"Установлена последняя версия ({result.get('current_version')})"
            )
            self.btn_install_update.setEnabled(False)

    def on_themes_reloaded(self, _themes: list) -> None:
        self.themes.reload()
        self._fill_themes()
        self._fill_styles()
        self._refresh_theme_info()

    # ------------------------------------------------------------------
    def apply_palette(self, palette: dict[str, str]) -> None:
        text = palette.get("text-color", "#e6e8ec")
        self.btn_download_dir.setIcon(icons.icon("folder", text, 15))
        self.btn_converter_dir.setIcon(icons.icon("folder", text, 15))
        self.btn_import_theme.setIcon(icons.icon("plus", text, 15))
