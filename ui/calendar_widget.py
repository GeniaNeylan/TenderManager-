# ui/calendar_widget.py
# 投标日历（Outlook 风：左右两栏共用同一张白底大卡片 + 中间竖线分隔）。
#
# 按设计规格实现：
#   整体大卡片：左右两栏共用同一白底（surface），视觉融为一体；
#       内部 padding 一致：上下 40px、左右 30px；
#       中间竖线分隔，上下各留白 40px（由卡片 padding 保证，不顶边）。
#   左栏（宽度自适应，可切月/周视图）：◀ 今天 ▶ 导航 + 月/周切换；
#       星期栏周末红字；日期格悬停背景、今日红色实心圆圈、选中浅红背景；
#       标记点四态：蓝=报名 / 红=投标 / 绿=发布 / 橙=报名+投标同日。
#   右栏（自适应吸收剩余宽度）：当日项目清单。卡片含左侧彩条（蓝/红/绿）、
#       项目名称、阶段徽章、截止时间、进度、区域；悬停右移+背景变化；
#       点击弹 ProjectDetailDialog；空状态显示 📭。
#
# 数据来源：主窗口传入的 all_data，每个 item 含 raw（原始行，
# 带 publish_date / signup_deadline / bid_deadline / region 等）。

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate, QSize, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFrame, QSizePolicy,
    QDialog, QStackedWidget,
)

from utils import date_utils
from utils.constants import CALENDAR_COLORS
from config import COLORS, STAGE_COLORS
from ui.dialogs import ProjectDetailDialog

_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
_KIND_COLOR = {
    "signup": CALENDAR_COLORS["signup"],   # 报名截止 · 蓝
    "bid": CALENDAR_COLORS["bid"],         # 投标截止 · 红
    "publish": CALENDAR_COLORS["publish"], # 发布时间 · 绿
}
_KIND_LABEL = {
    "signup": "报名截止",
    "bid": "投标截止",
    "publish": "发布时间",
}
_ACTIVE_STAGES = ("潜在机会", "跟进中")


class DayCell(QWidget):
    """单个日期格：自绘背景、数字、标记点；支持悬停与选中。"""

    clicked = Signal(QDate)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.qdate = QDate()
        self.in_month = True
        self.is_weekend = False
        self.is_today = False
        self.is_selected = False
        self.events: list[dict] = []
        self._hover = False
        self.setMinimumSize(44, 50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_data(self, qdate: QDate, in_month: bool, is_weekend: bool,
                 is_today: bool, is_selected: bool, events: list[dict]) -> None:
        self.qdate = qdate
        self.in_month = in_month
        self.is_weekend = is_weekend
        self.is_today = is_today
        self.is_selected = is_selected
        self.events = events or []
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        rect = self.rect()

        # 背景优先级：选中浅红 > 悬停 > 白
        if self.is_selected:
            bg = QColor(CALENDAR_COLORS["selected_bg"])
        elif self._hover:
            bg = QColor(CALENDAR_COLORS["hover_bg"])
        else:
            bg = QColor("#FFFFFF")
        painter.fillRect(rect, bg)

        # 边框
        painter.setPen(QPen(QColor(CALENDAR_COLORS["cell_border"]), 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        # 统计当天涉及的事件类型（报名 / 投标 / 发布）
        kinds = set()
        for ev in self.events:
            if ev["kind"] in ("signup", "bid", "publish"):
                kinds.add(ev["kind"])
        # 同日双截止（报名+投标）用橙色单点；其余按类型各画一色点
        if kinds == {"signup", "bid"}:
            marks = [CALENDAR_COLORS["mark_orange"]]
        else:
            order = [("signup", CALENDAR_COLORS["signup"]),
                     ("bid", CALENDAR_COLORS["bid"]),
                     ("publish", CALENDAR_COLORS["publish"])]
            marks = [c for k, c in order if k in kinds]

        day = self.qdate.day()

        if self.is_today:
            # 今日：红色实心圆圈 + 白字居中
            r = min(w, h) * 0.34
            cx, cy = w / 2, h * 0.40
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(CALENDAR_COLORS["today_circle"])))
            painter.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
            painter.drawText(int(cx - r), int(cy - r), int(2 * r), int(2 * r),
                             Qt.AlignCenter, str(day))
        else:
            if not self.in_month:
                fg = QColor(COLORS["gray"])
            else:
                fg = QColor(COLORS["text"])
            painter.setPen(fg)
            painter.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
            painter.drawText(8, 6, w - 16, 22, Qt.AlignLeft | Qt.AlignTop, str(day))

        # 标记点（底部居中的一簇色点）
        if marks:
            dot = 8
            gap = 4
            total = len(marks) * dot + (len(marks) - 1) * gap
            x = (w - total) / 2
            y = h - 14
            painter.setPen(Qt.NoPen)
            for color in marks:
                painter.setBrush(QBrush(QColor(color)))
                painter.drawEllipse(int(x), int(y), dot, dot)
                x += dot + gap

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.clicked.emit(self.qdate)


class CalendarWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.all_data: list[dict] = []
        self.date_events: dict[date, list[dict]] = {}
        self.current_date = QDate.currentDate()   # 视图锚点
        self.selected_date = QDate.currentDate()  # 当前选中日
        self.view_mode = "month"                  # 视图模式：month / week
        self._build_ui()
        self._render()

    # ---------------- UI 构建 ----------------
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ===== 共用白底大卡片（左右两栏融为一体，宽度自适应）=====
        cal_card = QFrame()
        cal_card.setObjectName("calCard")
        cal_card.setStyleSheet(
            f"QFrame#calCard{{background:{COLORS['surface']};"
            f"border:1px solid {COLORS['border']};border-radius:16px;}}")
        card_layout = QHBoxLayout(cal_card)
        # 内部 padding 一致：上下 40px，左右 30px
        card_layout.setContentsMargins(30, 40, 30, 40)
        # 列间留白，分隔线两侧有呼吸感（精致）
        card_layout.setSpacing(24)

        # ----- 左栏（宽度自适应，月/周视图切换）：导航 + 月/周切换 -----
        left = QWidget()
        left.setMinimumWidth(380)   # 窄屏下限，避免日期格挤成一团
        left.setMaximumWidth(780)   # 宽屏上限，避免日期格过大
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        # 月份导航：◀ 今天 ▶
        nav = QHBoxLayout()
        nav.setSpacing(8)
        btn_style = "QPushButton{font-size:13px;font-weight:600;}"
        self.btn_prev = QPushButton("◀")
        self.btn_today = QPushButton("今天")
        self.btn_next = QPushButton("▶")
        for b, fn in ((self.btn_prev, lambda: self._nav(-1)),
                      (self.btn_next, lambda: self._nav(1)),
                      (self.btn_today, self._go_today)):
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(32)
            b.setStyleSheet(btn_style)
            b.clicked.connect(fn)
        self.btn_prev.setFixedWidth(40)
        self.btn_next.setFixedWidth(40)
        self.btn_today.setFixedWidth(72)   # 加宽，避免「今天」二字被裁切
        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet(
            f"font-weight:700;color:{COLORS['text']};font-size:15px;")
        nav.addWidget(self.btn_prev)
        nav.addStretch(1)
        nav.addWidget(self.lbl_title)
        nav.addStretch(1)
        nav.addWidget(self.btn_today)
        nav.addWidget(self.btn_next)
        left_layout.addLayout(nav)

        # 月/周视图切换（独立一行，左对齐的分段控件）
        seg_w = QWidget()
        seg = QHBoxLayout(seg_w)
        seg.setContentsMargins(0, 0, 0, 0)
        seg.setSpacing(0)
        self.btn_month = QPushButton("月")
        self.btn_week = QPushButton("周")
        for b, fn in ((self.btn_month, lambda: self._set_mode("month")),
                      (self.btn_week, lambda: self._set_mode("week"))):
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(40, 28)
            b.clicked.connect(fn)
            seg.addWidget(b)
        self.btn_month.setChecked(True)
        seg_style = (
            "QPushButton{background:" + COLORS["surface"] +
            ";border:1px solid " + COLORS["border"] +
            ";padding:4px 0;color:" + COLORS["text_secondary"] +
            ";font-size:12px;font-weight:600;}"
            "QPushButton:first{border-top-left-radius:8px;"
            "border-bottom-left-radius:8px;}"
            "QPushButton:last{border-top-right-radius:8px;"
            "border-bottom-right-radius:8px;}"
            "QPushButton:checked{background:" + CALENDAR_COLORS["signup"] +
            ";border-color:" + CALENDAR_COLORS["signup"] + ";color:#FFFFFF;}"
        )
        self.btn_month.setStyleSheet(seg_style)
        self.btn_week.setStyleSheet(seg_style)
        left_layout.addWidget(seg_w)

        # 星期栏（周末红字）
        wd_row = QHBoxLayout()
        wd_row.setSpacing(2)
        for i, wd in enumerate(_WEEKDAYS):
            is_weekend = i >= 5
            color = CALENDAR_COLORS["weekend_header"] if is_weekend else COLORS["text_secondary"]
            lbl = QLabel(wd, alignment=Qt.AlignCenter)
            lbl.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;padding:4px 0;")
            wd_row.addWidget(lbl)
        left_layout.addLayout(wd_row)

        # 月 / 周视图堆叠（共用星期栏）
        self.stacked = QStackedWidget()

        # —— 月视图页（7 列 × 6 行）——
        self.month_page = QWidget()
        month_layout = QVBoxLayout(self.month_page)
        month_layout.setContentsMargins(0, 0, 0, 0)
        month_layout.setSpacing(0)
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)
        self.month_cells: list[DayCell] = []
        for i in range(42):
            cell = DayCell()
            cell.clicked.connect(self._on_cell_clicked)
            r, c = divmod(i, 7)
            grid.addWidget(cell, r, c)
            grid.setRowStretch(r, 1)
            self.month_cells.append(cell)
        month_layout.addLayout(grid, 1)
        self.stacked.addWidget(self.month_page)

        # —— 周视图页（单行 7 格）——
        self.week_page = QWidget()
        week_layout = QVBoxLayout(self.week_page)
        week_layout.setContentsMargins(0, 0, 0, 0)
        week_layout.setSpacing(0)
        week_grid = QGridLayout()
        week_grid.setSpacing(8)
        week_grid.setContentsMargins(0, 0, 0, 0)
        self.week_cells: list[DayCell] = []
        for c in range(7):
            cell = DayCell()
            cell.clicked.connect(self._on_cell_clicked)
            week_grid.addWidget(cell, 0, c)
            week_grid.setColumnStretch(c, 1)
            self.week_cells.append(cell)
        week_layout.addLayout(week_grid, 1)
        self.stacked.addWidget(self.week_page)

        left_layout.addWidget(self.stacked, 1)

        card_layout.addWidget(left, 1)  # 与右栏 1:1 共享可用宽度

        # ----- 竖线分隔（上下留白由卡片 40px padding 保证，不顶边）-----
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background:{COLORS['border']};border:none;")
        card_layout.addWidget(divider)

        # ----- 右栏（自适应吸收剩余宽度）：当日项目清单 -----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        self.lbl_detail = QLabel("📌 当日项目")
        self.lbl_detail.setStyleSheet(
            f"font-weight:700;color:{COLORS['text']};font-size:15px;")
        right_layout.addWidget(self.lbl_detail)

        self.detail_list = QListWidget()
        self.detail_list.setSpacing(10)
        self.detail_list.setStyleSheet("QListWidget{border:none;background:transparent;}")
        right_layout.addWidget(self.detail_list, 1)

        card_layout.addWidget(right, 1)  # 自适应吸收剩余宽度

        root.addWidget(cal_card, 1)  # 宽度自适应：卡片撑满可用宽度

    # ---------------- 数据注入 ----------------
    def set_project_data(self, data: list[dict]) -> None:
        self.all_data = data
        self.date_events = {}
        for item in data:
            raw = item.get("raw") or {}
            name = item.get("name") or ""
            lifecycle = item.get("lifecycle") or ""
            progress = item.get("progress") or "-"
            region = raw.get("region") or ""
            for kind, field in (("signup", "signup_deadline"),
                                ("bid", "bid_deadline"),
                                ("publish", "publish_date")):
                val = raw.get(field)
                d = date_utils.parse_date(val)
                if d is None:
                    continue
                self.date_events.setdefault(d, []).append({
                    "name": name,
                    "lifecycle": lifecycle,
                    "kind": kind,
                    "time_str": (val or "").strip(),
                    "progress": progress,
                    "region": region,
                    "raw": dict(raw),
                })
        self._render()

    # ---------------- 渲染 ----------------
    def _render(self) -> None:
        if self.view_mode == "month":
            self.stacked.setCurrentWidget(self.month_page)
            self._render_month()
        else:
            self.stacked.setCurrentWidget(self.week_page)
            self._render_week()
        self._update_detail(self.selected_date)

    def _render_month(self) -> None:
        y, m = self.current_date.year(), self.current_date.month()
        first = QDate(y, m, 1)
        offset = first.dayOfWeek() - 1  # 周一为首列
        start = first.addDays(-offset)
        self.lbl_title.setText(f"{y}年{m:02d}月")
        for i in range(42):
            qd = start.addDays(i)
            in_month = (qd.year() == y and qd.month() == m)
            is_weekend = qd.dayOfWeek() in (6, 7)
            is_today = (qd == QDate.currentDate())
            is_sel = (qd == self.selected_date)
            key = date(qd.year(), qd.month(), qd.day())
            evs = self.date_events.get(key, [])
            self.month_cells[i].set_data(qd, in_month, is_weekend, is_today, is_sel, evs)

    def _render_week(self) -> None:
        anchor = self.current_date
        monday = anchor.addDays(-(anchor.dayOfWeek() - 1))  # 本周一
        end = monday.addDays(6)
        if monday.month() == end.month():
            self.lbl_title.setText(
                f"{monday.year()}年{monday.month():02d}月 {monday.day()}–{end.day()}日")
        else:
            self.lbl_title.setText(
                f"{monday.toString('M.d')} – {end.toString('M.d')}")
        for i in range(7):
            qd = monday.addDays(i)
            in_month = (qd.month() == anchor.month())
            is_weekend = qd.dayOfWeek() in (6, 7)
            is_today = (qd == QDate.currentDate())
            is_sel = (qd == self.selected_date)
            key = date(qd.year(), qd.month(), qd.day())
            evs = self.date_events.get(key, [])
            self.week_cells[i].set_data(qd, in_month, is_weekend, is_today, is_sel, evs)

    # ---------------- 交互 ----------------
    def _set_mode(self, mode: str) -> None:
        if mode == self.view_mode:
            return
        self.view_mode = mode
        self.btn_month.setChecked(mode == "month")
        self.btn_week.setChecked(mode == "week")
        self._render()

    def _nav(self, delta: int) -> None:
        if self.view_mode == "month":
            self.current_date = self.current_date.addMonths(delta)
        else:
            self.current_date = self.current_date.addDays(7 * delta)
        self._render()

    def _go_today(self) -> None:
        self.current_date = QDate.currentDate()
        self.selected_date = QDate.currentDate()
        self._render()

    def _on_cell_clicked(self, qdate: QDate) -> None:
        self.selected_date = qdate
        # 月视图下点击非当月日期时跳转到对应月份
        if self.view_mode == "month" and (
                qdate.year() != self.current_date.year()
                or qdate.month() != self.current_date.month()):
            self.current_date = qdate
        self._render()

    # ---------------- 当日详情 ----------------
    def _update_detail(self, qdate: QDate) -> None:
        d = date(qdate.year(), qdate.month(), qdate.day())
        evs = self.date_events.get(d, [])
        wd = _WEEKDAYS[qdate.dayOfWeek() - 1]
        self.lbl_detail.setText(
            f"📌 {qdate.toString('yyyy-MM-dd')} {wd}（{len(evs)} 个项目）")
        self.detail_list.clear()

        if not evs:
            item = QListWidgetItem()
            empty = QWidget()
            ev = QVBoxLayout(empty)
            ev.setContentsMargins(0, 40, 0, 40)
            ev.setAlignment(Qt.AlignCenter)
            icon = QLabel("📭")
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet("font-size:46px;")
            txt = QLabel("当天暂无项目")
            txt.setAlignment(Qt.AlignCenter)
            txt.setStyleSheet(f"color:{COLORS['text_muted']};font-size:14px;")
            ev.addWidget(icon)
            ev.addWidget(txt)
            item.setSizeHint(QSize(self.detail_list.viewport().width(), 220))
            self.detail_list.addItem(item)
            self.detail_list.setItemWidget(item, empty)
            return

        for ev in evs:
            item = QListWidgetItem()
            widget = self._make_detail_item(ev)
            self.detail_list.addItem(item)
            self.detail_list.setItemWidget(item, widget)
        # 先把卡片宽度锁到列表实际宽度（视口，已排除滚动条），
        # 让名称/区域按真实列宽换行后再测量行高，避免文字被纵向裁切。
        self._relayout_detail()

    def _relayout_detail(self) -> None:
        """按列表视口实际宽度重算每个卡片行高（支持名称/区域换行）。"""
        if not self.detail_list:
            return
        lw = self.detail_list.viewport().width()
        for i in range(self.detail_list.count()):
            item = self.detail_list.item(i)
            widget = self.detail_list.itemWidget(item)
            if widget is None:
                continue
            widget.setFixedWidth(lw)
            item.setSizeHint(QSize(lw, widget.sizeHint().height()))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout_detail()

    def _make_detail_item(self, ev: dict) -> QFrame:
        kind = ev["kind"]
        bar_color = _KIND_COLOR.get(kind, COLORS["gray"])

        card = QFrame()
        card.setObjectName("projCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(
            "QFrame#projCard{"
            "background:" + COLORS["surface"] + ";"
            "border:1px solid " + COLORS["border"] + ";"
            "border-radius:12px;padding:12px 14px;}"
            "QFrame#projCard:hover{"
            "background:" + CALENDAR_COLORS["hover_bg"] + ";"
            "border-color:" + CALENDAR_COLORS["selected_bg"] + ";"
            "padding-left:20px;}"
        )
        card.mousePressEvent = lambda _e, raw=ev.get("raw"): self._open_detail(raw)

        h = QHBoxLayout(card)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)

        # 左侧彩条（蓝=报名 / 红=投标）
        bar = QFrame()
        bar.setFixedWidth(5)
        bar.setStyleSheet(f"background:{bar_color};border-radius:3px;")
        h.addWidget(bar)

        # 内容
        c = QWidget()
        v = QVBoxLayout(c)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        # 行1：名称 + 阶段徽章
        r1 = QHBoxLayout()
        name = QLabel(ev["name"])
        name.setWordWrap(True)
        name.setStyleSheet(f"font-weight:600;color:{COLORS['text']};font-size:14px;")
        fg, bg = STAGE_COLORS.get(ev["lifecycle"], (COLORS["text"], "#f0f1f3"))
        badge = QLabel(ev["lifecycle"])
        badge.setStyleSheet(
            f"color:{fg};background:{bg};border-radius:6px;padding:2px 8px;font-size:11px;")
        r1.addWidget(name, 1)
        r1.addWidget(badge)
        v.addLayout(r1)

        # 行2：类型 + 截止时间
        r2 = QHBoxLayout()
        info = QLabel(f"{_KIND_LABEL.get(kind, kind)}：{ev['time_str'] or '-'}")
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{COLORS['text_secondary']};font-size:12px;")
        r2.addWidget(info, 1)
        v.addLayout(r2)

        # 行3：进度 + 区域
        extra = []
        if kind == "bid" and ev["lifecycle"] == "跟进中" \
                and ev.get("progress") and ev["progress"] != "-":
            extra.append(f"进度：{ev['progress']}")
        if ev.get("region"):
            extra.append(f"区域：{ev['region']}")
        if extra:
            r3 = QHBoxLayout()
            ex = QLabel("　·　".join(extra))
            ex.setWordWrap(True)
            ex.setStyleSheet(f"color:{COLORS['text_muted']};font-size:12px;")
            r3.addWidget(ex, 1)
            v.addLayout(r3)

        h.addWidget(c, 1)
        return card

    def _open_detail(self, raw: dict | None) -> None:
        if not raw:
            return
        dlg = ProjectDetailDialog(raw, self.window())
        if dlg.exec() == QDialog.Accepted:
            # 数据被编辑/删除，刷新主窗口与日历
            win = self.window()
            if hasattr(win, "load_data"):
                win.load_data()
            else:
                self._render()
