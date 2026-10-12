# ui/app.py
# 主窗口：负责 UI 编排与状态管理，具体的 Excel / 数据包 / 自动扫描
# 等逻辑已下沉到 utils 下对应模块，保持本文件聚焦于「界面与交互」。

from __future__ import annotations

import math
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QPushButton, QStackedWidget,
    QTabWidget, QToolButton, QVBoxLayout, QWidget, QButtonGroup,
    QAbstractItemView, QLineEdit, QMainWindow,
    QTableWidget, QTableWidgetItem,
)

import database
import utils.auto_scan as auto_scan
import utils.date_utils as date_utils
import utils.excel_io as excel_io
import utils.data_pack as data_pack
from config import PAGE_SIZE, COLORS, STAGE_COLORS, STAGE_ORDER
from ui.dialogs import AddProjectDialog, ProjectDetailDialog, SettingsDialog
from ui.filter_header import FilterHeader
from ui.toast import show_toast
from ui.calendar_widget import CalendarWidget


# ==================== 自定义表头（带筛选按钮） ====================
# 注：FilterHeader 已抽离至 ui/filter_header.py，这里仅保留别名以便阅读。


# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📋 招标台账管理系统")
        self.resize(1320, 840)

        self.all_data: list[dict] = []
        self.filtered_data: list[dict] = []
        self.current_filter = "全部"
        self.search_text = ""
        self.current_page = 1

        self.setup_ui()
        self.load_data()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # ===== Ribbon（功能分区） =====
        self.ribbon = QTabWidget()
        self.ribbon.setFixedHeight(130)

        self.ribbon.addTab(self._build_ribbon_tab("开始", [
            ("➕", "新增", self.on_add),
            ("📅", "日历", self.toggle_calendar_view),
            ("📂", "导入", self.on_import),
            ("💾", "导出", self.on_export),
            ("🔄", "刷新", self.on_refresh),
            ("📊", "导出Excel", self.export_to_excel),
            ("📥", "导入Excel", self.import_from_excel),
        ]), "开始")

        self.ribbon.addTab(self._build_ribbon_tab("分析中心", [
            ("📊", "投标分析", self.on_analysis),
            ("📝", "周报", self.on_weekly_report),
        ]), "分析中心")

        btn_settings = QPushButton("⚙️ 设置")
        btn_settings.setObjectName("settingsBtn")
        btn_settings.setCursor(Qt.PointingHandCursor)
        btn_settings.clicked.connect(self.on_settings)
        self.ribbon.setCornerWidget(btn_settings, Qt.TopRightCorner)

        main_layout.addWidget(self.ribbon)

        # ===== 堆叠页面（台账列表 / 日历） =====
        self.stacked = QStackedWidget()
        main_layout.addWidget(self.stacked)

        self.stacked.addWidget(self._build_list_page())
        self.calendar_widget = CalendarWidget()
        self.stacked.addWidget(self.calendar_widget)

        # ===== 状态栏 =====
        status_bar = self.statusBar()
        status_bar.setStyleSheet("QStatusBar { background: transparent; border: none; }")
        self.lbl_total = QLabel("共 0 个项目")
        self.lbl_total.setStyleSheet(
            f"font-weight: 500; color: {COLORS['text_muted']}; padding: 4px 0;"
        )
        status_bar.addWidget(self.lbl_total)
        self.lbl_update = QLabel("最后更新：-")
        self.lbl_update.setStyleSheet(f"color: {COLORS['gray']};")
        status_bar.addPermanentWidget(self.lbl_update)

    def _build_ribbon_tab(self, _title: str, buttons: list[tuple[str, str, callable]]) -> QWidget:
        """根据 (emoji, 文案, 回调) 列表构建一个 Ribbon 页。"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(6)
        for emoji, text, slot in buttons:
            layout.addWidget(self._create_ribbon_btn(emoji, text, slot))
        layout.addStretch()
        return tab

    def _build_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._build_filter_bar())

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["项目名称", "项目阶段", "关键截止日", "进度", "备注", "入围数"]
        )
        self.filter_header = FilterHeader(self.table)
        self.table.setHorizontalHeader(self.filter_header)
        self.filter_header.main_window = self

        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(60)
        # 项目名称：Stretch 自适应，占满剩余空间
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        # 项目阶段：固定 120px（容纳 6 个中文字符 + 漏斗图标）
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 120)
        # 关键截止日：按内容自适应
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        # 进度：按内容自适应
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        # 备注：按内容自适应
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        # 入围数：按内容自适应
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        # 总列宽超过窗口时出现横向滚动条
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setCursor(Qt.PointingHandCursor)
        self.table.cellClicked.connect(self.on_row_clicked)
        layout.addWidget(self.table)

        layout.addWidget(self._build_paging())
        return page

    def _build_filter_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.stage_buttons: dict[str, QPushButton] = {}
        self.filter_btn_group = QButtonGroup(self)
        self.filter_btn_group.setExclusive(True)

        for stage in STAGE_ORDER:
            btn = QPushButton(stage)
            btn.setProperty("filterButton", True)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked, s=stage: self.apply_filter(s))
            self.filter_btn_group.addButton(btn)
            layout.addWidget(btn)
            self.stage_buttons[stage] = btn
        self.stage_buttons["全部"].setChecked(True)

        layout.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setProperty("search", True)
        self.search_edit.setPlaceholderText("🔍 搜索项目名称")
        self.search_edit.setFixedWidth(220)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_edit)
        return bar

    def _build_paging(self) -> QWidget:
        paging = QWidget()
        layout = QHBoxLayout(paging)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.addStretch()

        self.btn_prev = QPushButton("◀ 上一页")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(self.prev_page)
        layout.addWidget(self.btn_prev)

        self.lbl_page = QLabel("1 / 1")
        self.lbl_page.setStyleSheet(
            f"font-weight: 500; color: {COLORS['text_muted']}; padding: 0 16px; min-width: 60px;"
        )
        self.lbl_page.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_page)

        self.btn_next = QPushButton("下一页 ▶")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self.next_page)
        layout.addWidget(self.btn_next)
        layout.addStretch()
        return paging

    def _create_ribbon_btn(self, emoji: str, text: str, callback) -> QToolButton:
        btn = QToolButton()
        btn.setText(f"{emoji}\n{text}")
        btn.setFont(QFont("PingFang SC", 9))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(72, 72)
        btn.clicked.connect(callback)
        return btn

    def toggle_calendar_view(self) -> None:
        self.stacked.setCurrentIndex(0 if self.stacked.currentIndex() == 1 else 1)
        if self.stacked.currentIndex() == 1:
            self.calendar_widget.set_project_data(self.all_data)

    # ------------------------------------------------------------------
    # 数据加载
    # ------------------------------------------------------------------
    def load_data(self) -> None:
        auto_scan.run_auto_scan()  # 启动前自动扫描过期项目
        raw_data = database.get_all_projects()
        self.all_data = []
        latest_update = ""

        for row in raw_data:
            lifecycle = row.get("lifecycle") or ""
            # 关键截止日：潜在机会看报名截止，跟进中看投标截止
            if lifecycle == "潜在机会":
                deadline = row.get("signup_deadline") or "-"
            elif lifecycle == "跟进中":
                deadline = row.get("bid_deadline") or "-"
            else:
                deadline = "-"
            progress = (row.get("progress") or "-") if lifecycle == "跟进中" else "-"

            up_time = row.get("updated_at") or ""
            if up_time and up_time > latest_update:
                latest_update = up_time

            self.all_data.append({
                "name": row.get("name") or "",
                "lifecycle": lifecycle,
                "deadline": deadline,
                "progress": progress,
                "note": row.get("note") or "",
                "url": row.get("url") or "",
                "shortlist_count": row.get("shortlist_count") or 0,
                "raw": row,
            })

        self.all_data.sort(key=lambda item: date_utils.sort_key(item["deadline"]))

        self.update_stage_counts()
        self.apply_filter(self.current_filter)

        if not latest_update:
            latest_update = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.lbl_update.setText(f"最后更新：{latest_update}")
        self.calendar_widget.set_project_data(self.all_data)

    def update_stage_counts(self) -> None:
        counts = {"全部": len(self.all_data)}
        for stage in STAGE_ORDER[1:]:
            counts[stage] = sum(1 for item in self.all_data if item.get("lifecycle") == stage)
        for stage, btn in self.stage_buttons.items():
            btn.setText(f"{stage} · {counts.get(stage, 0)}")

    # ------------------------------------------------------------------
    # 筛选
    # ------------------------------------------------------------------
    def apply_filter(self, filter_value: str) -> None:
        self.current_filter = filter_value
        self.filter_header.current_filter = filter_value
        self.filter_header.update()
        if filter_value in self.stage_buttons:
            self.stage_buttons[filter_value].setChecked(True)

        data = self.all_data
        if filter_value != "全部":
            data = [item for item in data if item.get("lifecycle") == filter_value]
        if self.search_text:
            kw = self.search_text.lower()
            data = [item for item in data if kw in item.get("name", "").lower()]
        self.filtered_data = data

        self.current_page = 1
        self.update_table()
        self.lbl_total.setText(f"共 {len(self.filtered_data)} 个项目")

    def on_search_changed(self, text: str) -> None:
        self.search_text = text.strip()
        self.apply_filter(self.current_filter)

    # ------------------------------------------------------------------
    # 表格渲染
    # ------------------------------------------------------------------
    def _make_stage_badge(self, stage: str) -> QWidget:
        text_color, bg_color = STAGE_COLORS.get(
            stage, (COLORS["text_secondary"], COLORS["surface_alt"])
        )
        label = QLabel(stage or "-")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                background-color: {bg_color};
                border-radius: 11px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 500;
            }}
        """)
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch()
        lay.addWidget(label)
        lay.addStretch()
        return container

    def _deadline_color(self, deadline_str: str) -> tuple[str, bool]:
        """返回 (颜色, 是否加粗)。基于剩余天数着色。"""
        level = date_utils.urgency_level(deadline_str)
        if level == "danger":
            return COLORS["danger"], True
        if level == "warning":
            return COLORS["warning"], False
        return COLORS["text"], False

    def update_table(self) -> None:
        total = len(self.filtered_data)
        pages = max(1, math.ceil(total / PAGE_SIZE))
        self.current_page = max(1, min(self.current_page, pages))

        self.lbl_page.setText(f"{self.current_page} / {pages}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < pages)

        start = (self.current_page - 1) * PAGE_SIZE
        page_data = self.filtered_data[start:start + PAGE_SIZE]

        if not page_data:
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, 6)
            if self.current_filter != "全部" or self.search_text:
                msg = "🔍 没有符合当前筛选 / 搜索条件的项目"
            else:
                msg = "📭 暂无项目，点击「➕ 新增」开始记录第一条台账"
            empty_item = QTableWidgetItem(msg)
            empty_item.setTextAlignment(Qt.AlignCenter)
            empty_item.setForeground(QColor(COLORS["text_muted"]))
            self.table.setItem(0, 0, empty_item)
            return
        self.table.clearSpans()

        self.table.setRowCount(len(page_data))
        for i, item in enumerate(page_data):
            self.table.setCellWidget(i, 0, self._build_name_cell(item))
            self.table.setCellWidget(i, 1, self._make_stage_badge(item["lifecycle"]))

            deadline_item = QTableWidgetItem(item["deadline"])
            deadline_item.setTextAlignment(Qt.AlignCenter)
            color, is_bold = self._deadline_color(item["deadline"])
            deadline_item.setForeground(QColor(color))
            if is_bold:
                f = deadline_item.font()
                f.setBold(True)
                deadline_item.setFont(f)
            self.table.setItem(i, 2, deadline_item)

            prog = QTableWidgetItem(item["progress"])
            prog.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, prog)

            note = item["note"]
            display_note = note if len(note) <= 12 else note[:12] + "..."
            note_item = QTableWidgetItem(display_note)
            if note:
                note_item.setToolTip(note)
            self.table.setItem(i, 4, note_item)

            shortlist = item.get("shortlist_count", 0)
            shortlist_item = QTableWidgetItem(
                str(shortlist) if shortlist and shortlist > 0 else "-"
            )
            shortlist_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 5, shortlist_item)

    def _build_name_cell(self, item: dict) -> QWidget:
        """项目名称单元格：名称 + 可选的外链图标。"""
        name = item["name"]
        url = item.get("url", "")
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: 500;")
        layout.addWidget(name_label)

        if url and url.strip():
            link_label = QLabel(f'<a href="{url}" style="text-decoration:none;">🔗</a>')
            link_label.setOpenExternalLinks(True)
            link_label.setToolTip("点击打开公告网址")
            layout.addWidget(link_label)
        layout.addStretch()
        return container

    def prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.update_table()

    def next_page(self) -> None:
        pages = max(1, math.ceil(len(self.filtered_data) / PAGE_SIZE))
        if self.current_page < pages:
            self.current_page += 1
            self.update_table()

    # ------------------------------------------------------------------
    # 导入 / 导出（委托给 utils 模块）
    # ------------------------------------------------------------------
    def export_to_excel(self) -> None:
        excel_io.export_projects_to_excel(self.filtered_data, self)

    def import_from_excel(self) -> None:
        excel_io.import_projects_from_excel(self, self.load_data)

    def on_export(self) -> None:
        data_pack.export_data_pack(self, len(self.all_data))

    def on_import(self) -> None:
        data_pack.import_data_pack(self, self.load_data)

    # ------------------------------------------------------------------
    # 其它槽函数
    # ------------------------------------------------------------------
    def on_add(self) -> None:
        dialog = AddProjectDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if not _validate_required(self, data):
                return
            database.add_project(data)
            self.load_data()
            show_toast(self, f"项目「{data['name']}」已添加", kind="success")

    def on_refresh(self) -> None:
        self.load_data()
        show_toast(self, "数据已刷新", kind="info")

    def on_weekly_report(self) -> None:
        from ui.weekly_report_dialog import WeeklyReportDialog
        rows = [item["raw"] for item in self.all_data]
        WeeklyReportDialog(rows, parent=self).exec()

    def on_analysis(self) -> None:
        from ui.analysis_dialog import AnalysisDialog
        rows = [item["raw"] for item in self.all_data]
        AnalysisDialog(rows, parent=self).exec()

    def on_settings(self) -> None:
        dlg = SettingsDialog(self)
        dlg.dataCleared.connect(self.load_data)
        dlg.exec()

    def on_row_clicked(self, row: int, _col: int) -> None:
        idx = (self.current_page - 1) * PAGE_SIZE + row
        if idx < len(self.filtered_data):
            dialog = ProjectDetailDialog(self.filtered_data[idx]["raw"], self)
            dialog.exec()
            self.load_data()


def _validate_required(parent: QWidget, data: dict) -> bool:
    """校验新增/编辑必填项（名称 + 投标截止日）。"""
    from PySide6.QtWidgets import QMessageBox

    if not data["name"] or not data["bid_deadline"]:
        QMessageBox.warning(parent, "提示", "项目名称和投标截止日为必填项")
        return False
    return True
