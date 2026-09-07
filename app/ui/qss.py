# Copyright (C) 2025 Rayness
# This program is free software under GPLv3. See LICENSE for details.

"""
QSS-шаблон интерфейса.

Один шаблон на всё приложение: цвета приходят из темы, геометрия — из
GEOMETRY в tokens.py. Подстановка идёт через string.Template с синтаксисом
${token}, потому что обычный str.format споткнулся бы о фигурные скобки QSS.

Чего в QSS нет и чем это заменено:
 * box-shadow — не поддерживается. Объём держим на границах и разнице
   фонов, как и было задумано в «строгой» редакции base.css.
 * transition — не поддерживается. Плавность там, где она нужна, делается
   через QPropertyAnimation в самих виджетах.
 * CSS-переменные — подставляются здесь, до отдачи в Qt.
"""

from __future__ import annotations

from string import Template


class _QssTemplate(Template):
    """Template, разрешающий дефис в именах токенов (--bg-color -> ${bg-color})."""
    idpattern = r"[a-zA-Z0-9_-]+"


STYLESHEET = _QssTemplate(r"""
/* ====================================================================
   БАЗА
   ==================================================================== */
* {
    font-family: ${font-family};
    font-size: ${font-size-md}px;
    outline: none;
}

QWidget {
    color: ${text-color};
    background: transparent;
}

#RootWindow {
    background: ${bg-color};
    border: ${border-width}px solid ${border-strong};
    border-radius: ${radius-lg}px;
}

QToolTip {
    background: ${card-bg};
    color: ${text-color};
    border: ${border-width}px solid ${border-strong};
    border-radius: ${radius-sm}px;
    padding: ${space-1}px ${space-2}px;
}

/* ====================================================================
   ЗАГОЛОВОК ОКНА
   ==================================================================== */
#TitleBar {
    background: ${titlebar-bg};
    border-top-left-radius: ${radius-lg}px;
    border-top-right-radius: ${radius-lg}px;
    border-bottom: ${border-width}px solid ${border-color};
}

#TitleBarText {
    color: ${titlebar-text};
    font-size: ${font-size-md}px;
    font-weight: 600;
    padding-left: ${space-2}px;
}

#TitleBarVersion {
    color: ${text-secondary};
    font-size: ${font-size-xs}px;
    padding-left: ${space-2}px;
}

QPushButton[winctl="true"] {
    background: transparent;
    border: none;
    border-radius: 0px;
    min-width: 44px;
    max-width: 44px;
    min-height: ${titlebar-height}px;
    max-height: ${titlebar-height}px;
    color: ${titlebar-text};
    font-size: 14px;
}
QPushButton[winctl="true"]:hover  { background: ${titlebar-btn-hover}; }
QPushButton[winctl="true"]:pressed{ background: ${input-bg}; }

QPushButton[winctl="close"]:hover   { background: ${danger-color}; color: #ffffff; }
QPushButton[winctl="close"]:pressed { background: ${danger-dark};  color: #ffffff; }

/* ====================================================================
   БОКОВАЯ НАВИГАЦИЯ
   ==================================================================== */
#Sidebar {
    background: ${dark-bg};
    border-right: ${border-width}px solid ${border-color};
}

QPushButton[nav="true"] {
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0px;
    color: ${text-secondary};
    text-align: left;
    padding: 0px ${space-4}px;
    min-height: 40px;
    font-size: ${font-size-md}px;
    font-weight: 500;
}
QPushButton[nav="true"]:hover {
    background: ${card-bg};
    color: ${text-color};
}
QPushButton[nav="true"]:checked {
    background: ${accent-dark-transparent};
    border-left: 2px solid ${accent-color};
    color: ${text-color};
    font-weight: 600;
}

#SidebarFooter {
    color: ${text-secondary};
    font-size: ${font-size-xs}px;
    padding: ${space-3}px ${space-4}px;
}

/* ====================================================================
   КОНТЕНТ И КАРТОЧКИ
   ==================================================================== */
#Content {
    background: ${bg-color};
}

QFrame[card="true"] {
    background: ${card-bg};
    border: ${border-width}px solid ${border-color};
    border-radius: ${radius-md}px;
}
QFrame[card="true"]:hover {
    border: ${border-width}px solid ${border-strong};
}

QLabel[heading="1"] {
    font-size: ${font-size-xl}px;
    font-weight: 600;
    color: ${text-color};
}
QLabel[heading="2"] {
    font-size: ${font-size-lg}px;
    font-weight: 600;
    color: ${text-color};
}
QLabel[muted="true"] {
    color: ${text-secondary};
    font-size: ${font-size-sm}px;
}
QLabel[mono="true"] {
    font-family: ${font-mono};
    font-size: ${font-size-sm}px;
    color: ${text-secondary};
}

QFrame[separator="true"] {
    background: ${border-color};
    max-height: 1px;
    min-height: 1px;
    border: none;
}

/* ====================================================================
   КНОПКИ
   ==================================================================== */
QPushButton {
    background: ${card-bg};
    color: ${text-color};
    border: ${border-width}px solid ${border-strong};
    border-radius: ${radius-sm}px;
    padding: 0px ${space-4}px;
    min-height: ${control-height}px;
    font-size: ${font-size-md}px;
    font-weight: 500;
}
QPushButton:hover   { background: ${input-bg}; border-color: ${accent-color}; }
QPushButton:pressed { background: ${dark-bg}; }
QPushButton:disabled{ color: ${text-secondary}; border-color: ${border-color}; background: ${card-bg}; }

QPushButton[variant="primary"] {
    background: ${accent-color};
    border: ${border-width}px solid ${accent-color};
    color: #ffffff;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover   { background: ${accent-dark}; border-color: ${accent-dark}; }
QPushButton[variant="primary"]:pressed { background: ${accent-dark}; }
QPushButton[variant="primary"]:disabled{
    background: ${accent-dark-transparent};
    border-color: transparent;
    color: ${text-secondary};
}

QPushButton[variant="danger"] {
    background: transparent;
    border: ${border-width}px solid ${danger-color};
    color: ${danger-color};
}
QPushButton[variant="danger"]:hover { background: ${danger-color}; color: #ffffff; }

QPushButton[variant="ghost"] {
    background: transparent;
    border: none;
    color: ${text-secondary};
    padding: 0px ${space-2}px;
}
QPushButton[variant="ghost"]:hover { color: ${text-color}; background: ${card-bg}; }

QPushButton[variant="icon"] {
    background: transparent;
    border: none;
    min-width: ${control-height-sm}px;
    max-width: ${control-height-sm}px;
    min-height: ${control-height-sm}px;
    max-height: ${control-height-sm}px;
    padding: 0px;
    color: ${text-secondary};
}
QPushButton[variant="icon"]:hover { background: ${input-bg}; color: ${text-color}; }

/* ====================================================================
   ПОЛЯ ВВОДА
   ==================================================================== */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background: ${input-bg};
    color: ${text-color};
    border: ${border-width}px solid ${border-color};
    border-radius: ${radius-sm}px;
    padding: 0px ${space-3}px;
    min-height: ${control-height}px;
    selection-background-color: ${accent-color};
    selection-color: #ffffff;
}
QPlainTextEdit, QTextEdit { padding: ${space-2}px ${space-3}px; }

QLineEdit:hover, QSpinBox:hover { border-color: ${border-strong}; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus {
    border-color: ${accent-color};
    background: ${input-bg};
}
QLineEdit:disabled { color: ${text-secondary}; }
QLineEdit[invalid="true"] { border-color: ${danger-color}; }

QComboBox {
    background: ${input-bg};
    color: ${text-color};
    border: ${border-width}px solid ${border-color};
    border-radius: ${radius-sm}px;
    padding: 0px ${space-3}px;
    min-height: ${control-height}px;
}
QComboBox:hover { border-color: ${border-strong}; }
QComboBox:focus { border-color: ${accent-color}; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow {
    /* Треугольник «прозрачными границами» в Qt не собирается — берём PNG,
       отрисованный под цвет темы в app/ui/assets.py */
    image: url(${asset-chevron-down});
    width: 10px;
    height: 10px;
    margin-right: ${space-2}px;
}
QComboBox QAbstractItemView {
    background: ${card-bg};
    color: ${text-color};
    border: ${border-width}px solid ${border-strong};
    border-radius: ${radius-sm}px;
    padding: ${space-1}px;
    selection-background-color: ${accent-color-transparent};
    selection-color: ${text-color};
    outline: none;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background: transparent;
    border: none;
    width: 16px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: url(${asset-chevron-down});
    width: 9px; height: 9px;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: url(${asset-chevron-down});
    width: 9px; height: 9px;
}

/* ====================================================================
   ЧЕКБОКСЫ И ПЕРЕКЛЮЧАТЕЛИ
   ==================================================================== */
QCheckBox, QRadioButton { spacing: ${space-2}px; color: ${text-color}; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
QCheckBox::indicator {
    border: ${border-width}px solid ${border-strong};
    border-radius: ${radius-sm}px;
    background: ${input-bg};
}
QCheckBox::indicator:hover { border-color: ${accent-color}; }
QCheckBox::indicator:checked {
    background: ${accent-color};
    border-color: ${accent-color};
    image: url(${asset-check});
}
QRadioButton::indicator { border: ${border-width}px solid ${border-strong}; border-radius: 8px; background: ${input-bg}; }
QRadioButton::indicator:checked { border: 5px solid ${accent-color}; background: ${input-bg}; }

/* ====================================================================
   СЛАЙДЕРЫ
   ==================================================================== */
QSlider::groove:horizontal {
    height: 4px;
    background: ${input-bg};
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: ${accent-color};
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: ${text-color};
    border: none;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::handle:horizontal:hover { background: ${accent-color}; }

/* ====================================================================
   ПРОГРЕСС
   ==================================================================== */
QProgressBar {
    background: ${input-bg};
    border: none;
    border-radius: 3px;
    /* height сам по себе Qt игнорирует — размер держим min/max */
    min-height: 6px;
    max-height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: ${progress-gradient};
    border-radius: 3px;
}
QProgressBar[state="error"]::chunk   { background: ${danger-color}; }
QProgressBar[state="done"]::chunk    { background: ${success-color}; }

/* ====================================================================
   СПИСКИ И ТАБЛИЦЫ
   ==================================================================== */
QListView, QTreeView, QTableView {
    background: transparent;
    border: none;
    outline: none;
    selection-background-color: transparent;
}
QListView::item, QTreeView::item {
    border-radius: ${radius-sm}px;
    padding: ${space-1}px;
}
QListView::item:hover  { background: ${card-bg}; }
QListView::item:selected{ background: ${accent-color-transparent}; }

QHeaderView::section {
    background: ${dark-bg};
    color: ${text-secondary};
    border: none;
    border-bottom: ${border-width}px solid ${border-color};
    padding: ${space-2}px ${space-3}px;
    font-size: ${font-size-sm}px;
    font-weight: 600;
}

/* ====================================================================
   ВКЛАДКИ
   ==================================================================== */
QTabWidget::pane { border: none; }
QTabBar::tab {
    background: transparent;
    color: ${text-secondary};
    border: none;
    border-bottom: 2px solid transparent;
    padding: ${space-2}px ${space-4}px;
    font-weight: 500;
}
QTabBar::tab:hover    { color: ${text-color}; }
QTabBar::tab:selected { color: ${text-color}; border-bottom: 2px solid ${accent-color}; font-weight: 600; }

/* ====================================================================
   ПОЛОСЫ ПРОКРУТКИ — тонкие, без стрелок
   ==================================================================== */
QScrollArea { background: transparent; border: none; }

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: ${border-strong};
    border-radius: 5px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: ${text-secondary}; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: ${border-strong};
    border-radius: 5px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover { background: ${text-secondary}; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ====================================================================
   МЕНЮ И ДИАЛОГИ
   ==================================================================== */
QMenu {
    background: ${card-bg};
    border: ${border-width}px solid ${border-strong};
    border-radius: ${radius-md}px;
    padding: ${space-1}px;
}
QMenu::item {
    padding: ${space-2}px ${space-4}px;
    border-radius: ${radius-sm}px;
    color: ${text-color};
}
QMenu::item:selected { background: ${accent-color-transparent}; }
QMenu::separator { height: 1px; background: ${border-color}; margin: ${space-1}px ${space-2}px; }

QDialog { background: ${bg-color}; }

/* ====================================================================
   СТАТУСНАЯ СТРОКА
   ==================================================================== */
#StatusBar {
    background: ${dark-bg};
    border-top: ${border-width}px solid ${border-color};
    color: ${text-secondary};
    min-height: 26px;
    max-height: 26px;
}
#StatusBar QLabel { color: ${text-secondary}; font-size: ${font-size-sm}px; }

/* ====================================================================
   БЕЙДЖИ СТАТУСА ЗАДАЧ
   ==================================================================== */
QLabel[badge="queued"] {
    background: ${input-bg}; color: ${text-secondary};
    border-radius: ${radius-sm}px; padding: 2px ${space-2}px; font-size: ${font-size-xs}px; font-weight: 600;
}
QLabel[badge="processing"] {
    background: ${accent-color-transparent}; color: ${accent-color};
    border-radius: ${radius-sm}px; padding: 2px ${space-2}px; font-size: ${font-size-xs}px; font-weight: 600;
}
QLabel[badge="done"] {
    background: rgba(34, 197, 94, 0.16); color: ${success-color};
    border-radius: ${radius-sm}px; padding: 2px ${space-2}px; font-size: ${font-size-xs}px; font-weight: 600;
}
QLabel[badge="error"] {
    background: rgba(239, 68, 68, 0.16); color: ${danger-color};
    border-radius: ${radius-sm}px; padding: 2px ${space-2}px; font-size: ${font-size-xs}px; font-weight: 600;
}

/* Зона перетаскивания файлов */
#DropZone {
    background: ${input-bg};
    border: 2px dashed ${border-strong};
    border-radius: ${radius-md}px;
    color: ${text-secondary};
}
#DropZone[hover="true"] {
    border-color: ${accent-color};
    background: ${accent-dark-transparent};
    color: ${text-color};
}
""")


def render(tokens: dict[str, str]) -> str:
    """
    Подставляет токены в шаблон.
    safe_substitute, а не substitute: незнакомый токен в пользовательской теме
    не должен ронять всё приложение — он просто останется в тексте и Qt его
    молча проигнорирует.
    """
    return STYLESHEET.safe_substitute(tokens)
