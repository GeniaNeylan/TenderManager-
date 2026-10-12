# ui/weekly_report_dialog.py
# 周报生成器：按自然周（周一~周日）汇总台账，生成纯文本周报。
# 七个章节可独立勾选（默认全选），包含自定义备注输入，支持复制 / 导出 .txt。

from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QPlainTextEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from config import COLORS
from ui.toast import show_toast
from utils.constants import DROP_REASON_MAP, LIFECYCLE_STAGES
from utils.date_utils import parse_date

# 七个章节：(key, 显示名)
SECTIONS = [
    ("overview", "本周概览"),
    ("funnel", "投标漏斗"),
    ("drop", "放弃原因"),
    ("inprogress", "进行中项目清单"),
    ("nextweek", "下周截止提醒"),
    ("distribution", "区域/类别分布"),
    ("remarks", "自定义备注"),
]


# ==================== 业务辅助 ====================
def _parse_datetime(value: str | None) -> datetime | None:
    """解析 created_at / updated_at 等时间戳（含秒）；失败返回 None。"""
    if not value:
        return None
    v = value.strip().replace("T", " ").split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def _effective_deadline(row: dict) -> str:
    """按生命周期取有效截止日：潜在机会看报名截止，跟进中看投标截止。"""
    lc = (row.get("lifecycle") or "")
    if lc == "潜在机会":
        return row.get("signup_deadline") or ""
    if lc == "跟进中":
        return row.get("bid_deadline") or ""
    return ""


def _is_actual_bid(row: dict) -> bool:
    if (row.get("signup_status") or "") == "已报名":
        return True
    return (row.get("progress") or "") in ("已投标", "已中标", "未中标")


def _funnel_counts(rows: list[dict]) -> tuple[int, int, int, int]:
    total = len(rows)
    qualified = sum(1 for r in rows if (r.get("lifecycle") or "") == "潜在机会")
    bid = sum(1 for r in rows if _is_actual_bid(r))
    won = sum(1 for r in rows if (r.get("result") or "") == "已中标")
    return total, qualified, bid, won


def _drop_distribution(rows: list[dict]) -> list[tuple[str, int]]:
    """已放弃项目的放弃原因分布（detail 优先，否则 category），Top7 + 其他。"""
    buckets: dict[str, int] = {}
    for r in rows:
        if (r.get("lifecycle") or "") != "已放弃":
            continue
        detail = (r.get("drop_reason_detail") or "").strip()
        cat = (r.get("drop_reason_category") or "").strip()
        key = detail if detail else (cat if cat else "未填写原因")
        buckets[key] = buckets.get(key, 0) + 1
    items = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
    if len(items) > 7:
        top = items[:7]
        rest = sum(c for _, c in items[7:])
        return top + [("其他", rest)]
    return items


# ==================== 周报对话框 ====================
class WeeklyReportDialog(QDialog):
    def __init__(self, rows: list[dict], parent: QWidget | None = None):
        super().__init__(parent)
        self.rows = rows
        self.setWindowTitle("📝 周报生成器")
        self.resize(940, 640)
        self.setModal(True)

        # 自然周范围
        today = date.today()
        self.monday = today - timedelta(days=today.weekday())
        self.sunday = self.monday + timedelta(days=6)
        self.next_monday = self.monday + timedelta(days=7)
        self.next_sunday = self.next_monday + timedelta(days=6)

        self._checkboxes: dict[str, QCheckBox] = {}
        self._build_ui()
        self._refresh()

    # ---------- UI 构建 ----------
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        # ===== 左侧：选项 + 备注 =====
        left = QVBoxLayout()
        left.setSpacing(10)

        title = QLabel("📝 周报生成器")
        title.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {COLORS['text']};")
        left.addWidget(title)

        week_lbl = QLabel(
            f"统计周期：本周（{self.monday} ~ {self.sunday}）"
        )
        week_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        left.addWidget(week_lbl)

        sel_row = QHBoxLayout()
        sel_all = QPushButton("全选")
        sel_all.setCursor(Qt.PointingHandCursor)
        sel_all.clicked.connect(lambda: self._toggle_all(True))
        clear_all = QPushButton("全不选")
        clear_all.setCursor(Qt.PointingHandCursor)
        clear_all.clicked.connect(lambda: self._toggle_all(False))
        sel_row.addWidget(sel_all)
        sel_row.addWidget(clear_all)
        sel_row.addStretch()
        left.addLayout(sel_row)

        group = QGroupBox("报告章节（默认全选，可取消勾选）")
        group.setStyleSheet(f"QGroupBox {{ color: {COLORS['text_secondary']}; }}")
        g_layout = QVBoxLayout(group)
        g_layout.setSpacing(6)
        for key, name in SECTIONS:
            cb = QCheckBox(name)
            cb.setChecked(True)
            cb.stateChanged.connect(self._refresh)
            self._checkboxes[key] = cb
            g_layout.addWidget(cb)
        left.addWidget(group)

        remarks_box = QGroupBox("自定义备注")
        remarks_box.setStyleSheet(f"QGroupBox {{ color: {COLORS['text_secondary']}; }}")
        r_layout = QVBoxLayout(remarks_box)
        self.remarks_edit = QTextEdit()
        self.remarks_edit.setPlaceholderText("可在此补充本周总结、待办或说明，将出现在报告末尾…")
        self.remarks_edit.setMaximumHeight(120)
        self.remarks_edit.textChanged.connect(self._refresh)
        r_layout.addWidget(self.remarks_edit)
        left.addWidget(remarks_box)

        left.addStretch()
        root.addLayout(left, stretch=4)

        # ===== 右侧：预览 + 操作 =====
        right = QVBoxLayout()
        right.setSpacing(10)

        preview_title = QLabel("📄 报告预览（纯文本）")
        preview_title.setStyleSheet(f"font-weight: 600; color: {COLORS['text']};")
        right.addWidget(preview_title)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Microsoft YaHei", 12))
        self.preview.setStyleSheet(
            f"background: {COLORS['surface_alt']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 10px; color: {COLORS['text']};"
        )
        right.addWidget(self.preview, stretch=1)

        actions = QHBoxLayout()
        actions.addStretch()
        copy_btn = QPushButton("📋 复制文本")
        copy_btn.setProperty("primary", True)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(self._copy)
        export_btn = QPushButton("💾 导出 .txt")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export)
        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        actions.addWidget(copy_btn)
        actions.addWidget(export_btn)
        actions.addWidget(close_btn)
        right.addLayout(actions)

        root.addLayout(right, stretch=6)

    # ---------- 交互 ----------
    def _toggle_all(self, state: bool) -> None:
        for cb in self._checkboxes.values():
            cb.setChecked(state)

    def _enabled(self, key: str) -> bool:
        return self._checkboxes[key].isChecked()

    def _refresh(self) -> None:
        self.preview.setPlainText(self.build_report())

    # ---------- 报告生成 ----------
    def build_report(self) -> str:
        lines: list[str] = []
        now = datetime.now()

        def hr() -> None:
            lines.append("=" * 50)

        hr()
        lines.append("📝 招标周报")
        lines.append(f"统计周期：{self.monday} ~ {self.sunday}（本周）")
        lines.append(f"生成时间：{now.strftime('%Y-%m-%d %H:%M')}")
        hr()
        lines.append("")

        if self._enabled("overview"):
            self._section_overview(lines)
        if self._enabled("funnel"):
            self._section_funnel(lines)
        if self._enabled("drop"):
            self._section_drop(lines)
        if self._enabled("inprogress"):
            self._section_inprogress(lines)
        if self._enabled("nextweek"):
            self._section_nextweek(lines)
        if self._enabled("distribution"):
            self._section_distribution(lines)
        if self._enabled("remarks"):
            self._section_remarks(lines)

        hr()
        return "\n".join(lines)

    # ===== 各章节 =====
    def _section_overview(self, lines: list[str]) -> None:
        rows = self.rows
        new_cnt = sum(
            1 for r in rows
            if _parse_datetime(r.get("created_at")) and self.monday <= _parse_datetime(r["created_at"]).date() <= self.sunday
        )
        upd_cnt = sum(
            1 for r in rows
            if _parse_datetime(r.get("updated_at")) and self.monday <= _parse_datetime(r["updated_at"]).date() <= self.sunday
        )
        counts = {s: sum(1 for r in rows if (r.get("lifecycle") or "") == s) for s in LIFECYCLE_STAGES}
        lines.append("【本周概览】")
        lines.append(f"• 本周新增项目：{new_cnt} 个")
        lines.append(f"• 本周更新项目：{upd_cnt} 个")
        lines.append(
            f"• 当前台账：共 {len(rows)} 个"
            f"（潜在机会 {counts['潜在机会']} / 跟进中 {counts['跟进中']} / "
            f"已放弃 {counts['已放弃']} / 已结束 {counts['已结束']}）"
        )
        lines.append("")

    def _section_funnel(self, lines: list[str]) -> None:
        total, qualified, bid, won = _funnel_counts(self.rows)
        lines.append("【投标漏斗】")
        lines.append(f"• 总公告：{total}")
        pct = (qualified / total * 100) if total else 0.0
        lines.append(f"• 资质符合（潜在机会）：{qualified}（{pct:.1f}%）")
        pct = (bid / qualified * 100) if qualified else 0.0
        lines.append(f"• 实际投标：{bid}（{pct:.1f}%）")
        pct = (won / bid * 100) if bid else 0.0
        lines.append(f"• 已中标：{won}（{pct:.1f}%）")
        lines.append("")

    def _section_drop(self, lines: list[str]) -> None:
        dist = _drop_distribution(self.rows)
        total_dropped = sum(c for _, c in dist)
        lines.append("【放弃原因分布】")
        if not total_dropped:
            lines.append("（暂无放弃项目）")
        else:
            for label, count in dist:
                pct = count / total_dropped * 100
                lines.append(f"• {label}：{count} 个（{pct:.1f}%）")
        lines.append("")

    def _section_inprogress(self, lines: list[str]) -> None:
        items = [
            r for r in self.rows
            if (r.get("lifecycle") or "") in ("潜在机会", "跟进中")
        ]
        items.sort(key=lambda r: parse_date(_effective_deadline(r)) or date.max)
        lines.append(f"【进行中项目清单】（共 {len(items)} 个）")
        if not items:
            lines.append("（无）")
        else:
            for i, r in enumerate(items, 1):
                name = r.get("name") or "-"
                lc = r.get("lifecycle") or "-"
                dl = parse_date(_effective_deadline(r))
                dl_str = dl.strftime("%Y-%m-%d") if dl else "未设置"
                lines.append(f"{i}. {name} ｜ {lc} ｜ 截止 {dl_str}")
        lines.append("")

    def _section_nextweek(self, lines: list[str]) -> None:
        items = []
        for r in self.rows:
            lc = (r.get("lifecycle") or "")
            if lc not in ("潜在机会", "跟进中"):
                continue
            d = parse_date(_effective_deadline(r))
            if d and self.next_monday <= d <= self.next_sunday:
                days_left = (d - date.today()).days
                items.append((d, r.get("name") or "-", days_left))
        items.sort(key=lambda x: x[0])
        lines.append(f"【下周截止提醒】（{self.next_monday} ~ {self.next_sunday}）")
        if not items:
            lines.append("（下周无即将截止的项目）")
        else:
            for d, name, days_left in items:
                lines.append(f"⚠ {name} ｜ 截止 {d.strftime('%Y-%m-%d')} ｜ 剩 {days_left} 天")
        lines.append("")

    def _section_distribution(self, lines: list[str]) -> None:
        rows = self.rows
        region_cnt: dict[str, int] = {}
        category_cnt: dict[str, int] = {}
        for r in rows:
            region = (r.get("region") or "").strip()
            if region:
                region_cnt[region] = region_cnt.get(region, 0) + 1
            category = (r.get("category") or "").strip()
            if category:
                category_cnt[category] = category_cnt.get(category, 0) + 1

        lines.append("【区域分布】")
        if not region_cnt:
            lines.append("（暂无数据）")
        else:
            for region, cnt in sorted(region_cnt.items(), key=lambda kv: kv[1], reverse=True):
                lines.append(f"• {region}：{cnt}")
        lines.append("")
        lines.append("【类别分布】")
        if not category_cnt:
            lines.append("（暂无数据）")
        else:
            for category, cnt in sorted(category_cnt.items(), key=lambda kv: kv[1], reverse=True):
                lines.append(f"• {category}：{cnt}")
        lines.append("")

    def _section_remarks(self, lines: list[str]) -> None:
        text = self.remarks_edit.toPlainText().strip()
        lines.append("【自定义备注】")
        lines.append(text if text else "（无）")
        lines.append("")

    # ---------- 输出 ----------
    def _copy(self) -> None:
        text = self.build_report()
        QApplication.clipboard().setText(text)
        show_toast(self, "📋 周报已复制到剪贴板", kind="success")

    def _export(self) -> None:
        text = self.build_report()
        path, _ = QFileDialog.getSaveFileName(
            self, "导出周报", f"招标周报_{self.monday}.txt", "文本文件 (*.txt)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            show_toast(self, f"💾 已导出：{path}", kind="success")
        except OSError as e:
            show_toast(self, f"导出失败：{e}", kind="danger")
