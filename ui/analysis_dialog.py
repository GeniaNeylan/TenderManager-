# ui/analysis_dialog.py
# 投标分析中心：左侧投标漏斗（4 层转化）+ 右侧放弃原因饼图 + 导出报表。
# 饼图使用 QPainter 自绘，零额外依赖，支持点击扇形联动 / 查看项目清单。

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QApplication, QDialog, QHeaderView, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from config import COLORS
from utils.constants import DROP_REASON_MAP
from ui.toast import show_toast

FONT = "Microsoft YaHei"

# 漏斗四层配色
FUNNEL_COLORS = ["#5B8FF9", "#5AD8A6", "#F6BD16", "#E8684A"]

# 饼图调色板（前 7 个原因 + “其他”）
PIE_COLORS = [
    "#5B8FF9", "#5AD8A6", "#F6BD16", "#E8684A",
    "#6DC8EC", "#9270CA", "#FF9D4D", "#269A99",
    "#FF99C3", "#D3D3D3",
]

# 三大一级放弃原因配色（图例）
CAT_COLORS = {
    "客观资质不符": "#5B8FF9",
    "主观战略放弃": "#F6BD16",
    "执行卡顿": "#E8684A",
}


# ==================== 业务判定 ====================
def _is_actual_bid(row: dict) -> bool:
    """判定项目是否进入「实际投标」环节。"""
    if (row.get("signup_status") or "") == "已报名":
        return True
    return (row.get("progress") or "") in ("已投标", "已中标", "未中标")


def _funnel_subset(rows: list[dict], level: int) -> list[dict]:
    """返回某个漏斗层级对应的项目集合。"""
    if level == 0:  # 总公告
        return rows
    if level == 1:  # 资质符合（潜在机会）
        return [r for r in rows if (r.get("lifecycle") or "") == "潜在机会"]
    if level == 2:  # 实际投标
        return [r for r in rows if _is_actual_bid(r)]
    return [r for r in rows if (r.get("result") or "") == "已中标"]  # 已中标


# ==================== 漏斗单行 ====================
class FunnelRow(QWidget):
    clicked = Signal(int)

    def __init__(self, level: int, color: str, name: str, number: int, rate_text: str):
        super().__init__()
        self.level = level
        self.setObjectName("funnelRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        layout.addWidget(dot)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text']};")
        info.addWidget(name_lbl)
        if rate_text:
            rate_lbl = QLabel(rate_text)
            rate_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']};")
            info.addWidget(rate_lbl)
        layout.addLayout(info)

        layout.addStretch()
        num_lbl = QLabel(str(number))
        num_lbl.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {color};")
        layout.addWidget(num_lbl)

        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.setStyleSheet(
                f"QWidget#funnelRow {{ background: {COLORS['primary_soft']}; border-radius: 10px; }}"
            )
        else:
            self.setStyleSheet(
                f"QWidget#funnelRow {{ background: transparent; border-radius: 10px; }}"
                f"QWidget#funnelRow:hover {{ background: {COLORS['surface_alt']}; }}"
            )

    def mouseReleaseEvent(self, event) -> None:
        self.clicked.emit(self.level)
        super().mouseReleaseEvent(event)


# ==================== 自绘饼图 ====================
class PieChartWidget(QWidget):
    segmentClicked = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.segments: list[tuple[str, int, str]] = []  # (label, value, color)
        self._hit: list[tuple[float, float, int]] = []
        self.setMinimumSize(240, 240)

    def set_data(self, segments: list[tuple[str, int, str]]) -> None:
        self.segments = segments
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        if not self.segments:
            painter.setPen(QColor(COLORS["text_muted"]))
            painter.setFont(QFont(FONT, 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无放弃数据")
            return

        total = sum(v for _, v, _ in self.segments)
        if total <= 0:
            painter.setPen(QColor(COLORS["text_muted"]))
            painter.setFont(QFont(FONT, 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无放弃数据")
            return

        margin = 12
        side = min(w, h) - 2 * margin
        cx, cy = w // 2, h // 2
        r = side / 2
        angle = -90.0
        self._hit = []
        for i, (label, value, color) in enumerate(self.segments):
            if value <= 0:
                continue
            sweep = value / total * 360.0
            painter.setBrush(QColor(color))
            painter.setPen(Qt.NoPen)
            painter.drawPie(
                int(cx - r), int(cy - r), int(2 * r), int(2 * r),
                int(angle * 16), int(sweep * 16),
            )
            self._hit.append((angle, angle + sweep, i))
            mid = math.radians(angle + sweep / 2)
            lx = cx + 0.60 * r * math.cos(mid)
            ly = cy + 0.60 * r * math.sin(mid)
            pct = value / total * 100
            if pct >= 4:
                painter.setPen(Qt.white)
                painter.setFont(QFont(FONT, 9, QFont.Bold))
                painter.drawText(QRectF(lx - 22, ly - 10, 44, 20), Qt.AlignCenter, f"{pct:.0f}%")
            angle += sweep

    def mousePressEvent(self, event) -> None:
        if not self.segments or not self._hit:
            return
        w, h = self.width(), self.height()
        margin = 12
        side = min(w, h) - 2 * margin
        cx, cy = w // 2, h // 2
        r = side / 2
        dx = event.position().x() - cx
        dy = event.position().y() - cy
        if math.hypot(dx, dy) > r:
            return  # 圆外点击
        ang = math.degrees(math.atan2(dy, dx))
        for start, end, idx in self._hit:
            a = ang
            while a < start:
                a += 360
            while a >= start + 360:
                a -= 360
            if start <= a < end:
                self.segmentClicked.emit(idx)
                return


# ==================== 项目清单弹窗 ====================
class ProjectListDialog(QDialog):
    def __init__(self, title: str, projects: list[dict], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(f"📋 {title}")
        self.resize(580, 460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        tip = QLabel(f"共 {len(projects)} 个项目")
        tip.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(tip)

        table = QTableWidget(len(projects), 3)
        table.setHorizontalHeaderLabels(["项目名称", "阶段", "放弃原因"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in (1, 2):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        for i, p in enumerate(projects):
            name = p.get("name") or "-"
            stage = p.get("lifecycle") or "-"
            reason = (p.get("drop_reason_detail") or p.get("drop_reason_category") or "-")
            table.setItem(i, 0, QTableWidgetItem(name))
            table.setItem(i, 1, QTableWidgetItem(stage))
            table.setItem(i, 2, QTableWidgetItem(reason))
        layout.addWidget(table)

        btn = QPushButton("关闭")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignRight)


# ==================== 主对话框 ====================
class AnalysisDialog(QDialog):
    def __init__(self, rows: list[dict], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.rows = rows
        self.funnel = self._build_funnel(rows)
        self.selected_level = 0
        self.current_segments: list[tuple[str, int, list[dict]]] = []

        self.setWindowTitle("📊 投标分析中心")
        self.resize(940, 580)
        self.setModal(True)

        self.setup_ui()
        self._update_pie(0)

    # ---------- 统计计算 ----------
    def _build_funnel(self, rows: list[dict]) -> list[tuple[str, int, Optional[int]]]:
        total = len(rows)
        qualified = sum(1 for r in rows if (r.get("lifecycle") or "") == "潜在机会")
        bid = sum(1 for r in rows if _is_actual_bid(r))
        won = sum(1 for r in rows if (r.get("result") or "") == "已中标")
        return [
            ("总公告", total, None),
            ("资质符合", qualified, total),
            ("实际投标", bid, qualified),
            ("已中标", won, bid),
        ]

    def _dist_for_subset(self, subset: list[dict]) -> list[tuple[str, int, list[dict]]]:
        """统计子集内「已放弃」项目的放弃原因分布（detail 优先，否则 category）。"""
        dropped = [r for r in subset if (r.get("lifecycle") or "") == "已放弃"]
        buckets: dict[str, list[dict]] = {}
        for r in dropped:
            detail = (r.get("drop_reason_detail") or "").strip()
            cat = (r.get("drop_reason_category") or "").strip()
            key = detail if detail else (cat if cat else "未填写原因")
            buckets.setdefault(key, []).append(r)

        items = sorted(buckets.items(), key=lambda kv: len(kv[1]), reverse=True)
        segments: list[tuple[str, int, list[dict]]] = []
        if len(items) > 7:
            top = items[:7]
            rest_projects: list[dict] = []
            for _, ps in items[7:]:
                rest_projects.extend(ps)
            for label, ps in top:
                segments.append((label, len(ps), ps))
            segments.append(("其他", len(rest_projects), rest_projects))
        else:
            for label, ps in items:
                segments.append((label, len(ps), ps))
        return segments

    def _cat_counts(self, subset: list[dict]) -> dict[str, int]:
        dropped = [r for r in subset if (r.get("lifecycle") or "") == "已放弃"]
        counts = {cat: 0 for cat in DROP_REASON_MAP.keys()}
        for r in dropped:
            cat = (r.get("drop_reason_category") or "").strip()
            if cat in counts:
                counts[cat] += 1
        return counts

    # ---------- UI 构建 ----------
    def setup_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(14)

        header = QLabel("📊 投标分析中心")
        header.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLORS['text']};")
        main.addWidget(header)

        split = QHBoxLayout()
        split.setSpacing(18)
        split.addLayout(self._build_funnel_panel(), stretch=5)
        split.addLayout(self._build_pie_panel(), stretch=6)
        main.addLayout(split)

        bottom = QHBoxLayout()
        latest = max((r.get("updated_at") or "") for r in self.rows) if self.rows else ""
        if not latest:
            latest = datetime.now().strftime("%Y-%m-%d %H:%M")
        lbl_total = QLabel(f"项目总数：{len(self.rows)}")
        lbl_total.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 500;")
        lbl_update = QLabel(f"数据更新：{latest}")
        lbl_update.setStyleSheet(f"color: {COLORS['gray']};")
        bottom.addWidget(lbl_total)
        bottom.addStretch()
        bottom.addWidget(lbl_update)
        main.addLayout(bottom)

    def _build_funnel_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(6)

        title = QLabel("🔁 投标漏斗")
        title.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {COLORS['text']};")
        layout.addWidget(title)

        self.funnel_rows: list[FunnelRow] = []
        for i, (name, number, base) in enumerate(self.funnel):
            if base:
                rate = f"转化率 {number / base * 100:.1f}%"
            elif base is None:
                rate = ""
            else:
                rate = "转化率 0.0%"
            row = FunnelRow(i, FUNNEL_COLORS[i], name, number, rate)
            row.clicked.connect(self._on_funnel_clicked)
            self.funnel_rows.append(row)
            layout.addWidget(row)
            if i < len(self.funnel) - 1:
                arrow = QLabel("▼")
                arrow.setAlignment(Qt.AlignCenter)
                arrow.setStyleSheet(f"color: {COLORS['gray']}; font-size: 12px;")
                layout.addWidget(arrow)
        self.funnel_rows[0].set_selected(True)

        layout.addStretch()
        export_btn = QPushButton("📋 导出报表")
        export_btn.setProperty("primary", True)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_report)
        layout.addWidget(export_btn, alignment=Qt.AlignLeft)
        return layout

    def _build_pie_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        title = QLabel("📉 放弃原因分布")
        title.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {COLORS['text']};")
        layout.addWidget(title)

        self.legend_layout = QHBoxLayout()
        self.legend_layout.setSpacing(14)
        layout.addLayout(self.legend_layout)

        self.pie = PieChartWidget()
        self.pie.segmentClicked.connect(self._on_segment_clicked)
        layout.addWidget(self.pie, alignment=Qt.AlignCenter)

        hint = QLabel("💡 点击扇形查看该原因对应的项目清单")
        hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        return layout

    # ---------- 交互 ----------
    def _on_funnel_clicked(self, level: int) -> None:
        if level == self.selected_level:
            return
        self.funnel_rows[self.selected_level].set_selected(False)
        self.selected_level = level
        self.funnel_rows[level].set_selected(True)
        self._update_pie(level)

    def _update_pie(self, level: int) -> None:
        subset = _funnel_subset(self.rows, level)
        segments = self._dist_for_subset(subset)
        self.current_segments = segments
        pie_data = [
            (label, count, PIE_COLORS[i % len(PIE_COLORS)])
            for i, (label, count, _projects) in enumerate(segments)
        ]
        self.pie.set_data(pie_data)
        self._update_legend(subset)

    def _update_legend(self, subset: list[dict]) -> None:
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        counts = self._cat_counts(subset)
        for cat in DROP_REASON_MAP.keys():
            color = CAT_COLORS.get(cat, "#999999")
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color};")
            h.addWidget(dot)
            h.addWidget(QLabel(f"{cat}：{counts.get(cat, 0)}"))
            self.legend_layout.addWidget(w)

    def _on_segment_clicked(self, idx: int) -> None:
        if 0 <= idx < len(self.current_segments):
            label, _count, projects = self.current_segments[idx]
            if projects:
                ProjectListDialog(label, projects, self).exec()

    # ---------- 导出报表 ----------
    def _export_report(self) -> None:
        lines = [
            "=" * 50,
            "📊 投标分析报告",
            "=" * 50,
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "🔁 投标漏斗",
        ]
        for name, number, base in self.funnel:
            if base is None:
                lines.append(f"{name}：{number}")
            else:
                pct = (number / base * 100) if base else 0.0
                suffix = "（潜在机会）" if name == "资质符合" else ""
                lines.append(f"{name}{suffix}：{number}（{pct:.1f}%）")

        lines += ["", "📉 放弃原因分布"]
        segments = self._dist_for_subset(self.rows)
        total_dropped = sum(c for _, c, _ in segments)
        if total_dropped == 0:
            lines.append("（暂无放弃项目）")
        else:
            for label, count, _ in segments:
                pct = count / total_dropped * 100
                lines.append(f"{label}：{count} 个（{pct:.1f}%）")
        lines.append("=" * 50)

        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        show_toast(self, "📋 报表已复制到剪贴板", kind="success")
