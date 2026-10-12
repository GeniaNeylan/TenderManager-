# ui/styles.py
# 注：这里的颜色值与 config.COLORS 保持一致，如需整体换色，两处需同步修改。

MODERN_QSS = """
/* ========== 基础背景 ========== */
QWidget, QFrame, QScrollArea, QMainWindow, QDialog {
    background-color: #f5f6f8;
    color: #2c3e50;
    font-family: "PingFang SC", "Microsoft YaHei", -apple-system, sans-serif;
    font-size: 13px;
    font-weight: 400;
}

/* ========== 顶部 Ribbon / 标签栏 ========== */
QTabWidget::pane {
    border: 1px solid #eef0f2;
    background: #ffffff;
    border-radius: 14px;
    margin: 0;
}

QTabBar::tab {
    background: transparent;
    padding: 10px 26px;
    margin-right: 2px;
    color: #9a9da2;
    font-size: 14px;
    font-weight: 400;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
}

QTabBar::tab:selected {
    color: #2c3e50;
    background: transparent;
    border-bottom: 2px solid #d86a6a;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    color: #2c3e50;
    background: #f7f8fa;
}

QToolButton {
    border: none;
    border-radius: 10px;
    padding: 4px 10px;
    background: transparent;
    color: #555;
    font-size: 12px;
    font-weight: 400;
}
QToolButton:hover {
    background: #f0f1f3;
    color: #2c3e50;
}
QToolButton:pressed {
    background: #e4e6ea;
}

#settingsBtn {
    border: none;
    border-radius: 20px;
    padding: 6px 18px;
    background: #f0f1f3;
    color: #555;
    font-weight: 500;
    font-size: 12px;
}
#settingsBtn:hover {
    background: #e4e6ea;
    color: #2c3e50;
}

/* ========== 表格 ========== */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #eef0f2;
    border-radius: 14px;
    outline: none;
    gridline-color: transparent;
    selection-background-color: #fbeceb;
    selection-color: #2c3e50;
    padding: 0;
}

QTableWidget::item {
    padding: 12px 16px;
    border: none;
    border-bottom: 1px solid #f2f3f5;
}

QTableWidget::item:selected {
    background-color: #fbeceb;
    color: #2c3e50;
}

QTableWidget::item:hover {
    background-color: #fafbfc;
}

QHeaderView::section {
    background-color: #fafbfc;
    color: #9a9da2;
    padding: 12px 16px;
    border: none;
    border-bottom: 1px solid #eeeff1;
    font-weight: 500;
    font-size: 12px;
    letter-spacing: 0.3px;
}

QLabel[linkLabel="true"] {
    color: #6a7a8a;
    text-decoration: none;
    font-weight: 400;
    background: #f0f2f5;
    padding: 2px 10px;
    border-radius: 30px;
    font-size: 11px;
}
QLabel[linkLabel="true"]:hover {
    background: #e4e8ef;
    color: #2c3e50;
}

/* ========== 按钮 ========== */
QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 6px 16px;
    color: #555;
    font-weight: 400;
}
QPushButton:hover {
    background-color: #f0f1f3;
    color: #2c3e50;
}
QPushButton:pressed {
    background-color: #e4e6ea;
}
QPushButton:disabled {
    color: #c0c4cc;
    background: transparent;
}

QPushButton[primary="true"] {
    background-color: #d86a6a;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 500;
    padding: 8px 20px;
}
QPushButton[primary="true"]:hover {
    background-color: #c95a5a;
}
QPushButton[primary="true"]:pressed {
    background-color: #b84a4a;
}

/* ========== 输入框 ========== */
QLineEdit, QTextEdit, QComboBox, QDateEdit, QDateTimeEdit {
    background-color: #fafbfc;
    border: 1px solid #e4e6ea;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 20px;
    color: #2c3e50;
    selection-background-color: #d86a6a;
    selection-color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus {
    border-color: #d86a6a;
    background: #ffffff;
}
QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QDateTimeEdit:hover {
    border-color: #d0d3d8;
}
QComboBox::drop-down {
    border: none;
    width: 26px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #b0b4ba;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #eef0f2;
    border-radius: 8px;
    selection-background-color: #fbeceb;
    selection-color: #2c3e50;
    padding: 4px;
    outline: none;
}

/* ========== 搜索框 ========== */
QLineEdit[search="true"] {
    background-color: #fafbfc;
    border: 1px solid #e4e6ea;
    border-radius: 18px;
    padding: 7px 16px;
}
QLineEdit[search="true"]:focus {
    border-color: #d86a6a;
    background: #ffffff;
}

/* ========== 弹窗 ========== */
QDialog {
    background-color: #ffffff;
}
QGroupBox {
    border: none;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 600;
    color: #2c3e50;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 0px;
    padding: 0 8px 6px 0;
    color: #6a7a8a;
    font-size: 13px;
}

/* ========== 状态栏 ========== */
QStatusBar {
    background-color: transparent;
    color: #9a9da2;
    border: none;
    padding: 6px 4px;
    font-size: 12px;
}
QStatusBar QLabel {
    color: #9a9da2;
    padding: 4px 0;
}

/* ========== 日历 ========== */
QCalendarWidget {
    background: #ffffff;
    border: 1px solid #eef0f2;
    border-radius: 14px;
}
QCalendarWidget QWidget {
    background: #ffffff;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background: #ffffff;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    padding: 6px;
}
QCalendarWidget QToolButton {
    color: #2c3e50;
    font-weight: 500;
    font-size: 13px;
    border-radius: 8px;
    padding: 4px 10px;
}
QCalendarWidget QToolButton:hover {
    background: #f0f1f3;
}
QCalendarWidget QHeaderView::section {
    background: transparent;
    color: #9a9da2;
    padding: 8px;
    border: none;
    font-weight: 500;
}
QCalendarWidget QTableView {
    border: none;
    selection-background-color: transparent;
}
QCalendarWidget QTableView::item {
    padding: 6px;
    border: none;
    border-radius: 16px;
}
QCalendarWidget QTableView::item:selected {
    background-color: #d86a6a;
    color: white;
}
QCalendarWidget QTableView::item:hover {
    background-color: #f0f1f3;
}

/* ========== 列表 ========== */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #eef0f2;
    border-radius: 14px;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    padding: 9px 12px;
    border: none;
    border-radius: 8px;
    color: #2c3e50;
    margin: 1px 0;
}
QListWidget::item:hover {
    background: #f5f6f8;
}
QListWidget::item:selected {
    background: #fbeceb;
    color: #2c3e50;
}

/* ========== 筛选 / 统计 芯片按钮 ========== */
QPushButton[filterButton="true"] {
    border: 1px solid #e4e6ea;
    border-radius: 18px;
    padding: 7px 18px;
    background: #ffffff;
    color: #6a7a8a;
    font-weight: 500;
    font-size: 12px;
}
QPushButton[filterButton="true"]:checked {
    background-color: #d86a6a;
    color: white;
    border-color: #d86a6a;
}
QPushButton[filterButton="true"]:hover:!checked {
    background-color: #fbeceb;
    border-color: #f0d3d3;
    color: #d86a6a;
}
QPushButton[filterButton="true"]:pressed {
    background-color: #c95a5a;
    color: white;
}

/* ========== 菜单（表头筛选下拉等） ========== */
QMenu {
    background-color: #ffffff;
    border: 1px solid #eef0f2;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    padding: 7px 20px 7px 14px;
    border-radius: 6px;
    color: #2c3e50;
}
QMenu::item:selected {
    background-color: #fbeceb;
    color: #d86a6a;
}
QMenu::separator {
    height: 1px;
    background: #eef0f2;
    margin: 4px 6px;
}

/* ========== 滚动条 ========== */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #dfe2e6;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #c7cbd1;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #dfe2e6;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #c7cbd1;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ========== Tooltip ========== */
QToolTip {
    background-color: #2c3e50;
    color: #ffffff;
    border: none;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}

/* ========== 弹窗内日期控件 / 日历弹层（供 AddProjectDialog 使用） ========== */
QDateTimeEdit {
    min-width: 180px;
}
QDateTimeEdit::drop-down {
    width: 30px;
}
QCalendarWidget {
    min-width: 480px;
    max-width: 480px;
    font-size: 11px;
}
QCalendarWidget QHeaderView::section {
    min-width: 50px;
    width: 50px;
    max-width: 50px;
    font-size: 10px;
}
QCalendarWidget QTableView {
    min-width: 460px;
}
"""

# 弹窗专属样式：保证日期控件下拉弹出的日历宽度合适。
# 与 MODERN_QSS 中的日历规则保持一致，供 ui/dialogs.py 在弹窗上单独应用。
DIALOG_QSS = """
QDateTimeEdit {
    min-width: 180px;
}
QDateTimeEdit::drop-down {
    width: 30px;
}
QCalendarWidget {
    min-width: 480px;
    max-width: 480px;
    font-size: 11px;
}
QCalendarWidget QHeaderView::section {
    min-width: 50px;
    width: 50px;
    max-width: 50px;
    font-size: 10px;
}
QCalendarWidget QTableView {
    min-width: 460px;
}
"""
