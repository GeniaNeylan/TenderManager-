# ui/dialogs.py
# 设置 / 新增编辑 / 详情三类弹窗。
# 重构要点：
#   1. 放弃原因两级映射改为从 utils.constants 引入，消除与 database 的重复；
#   2. 下拉选项改用 LIFECYCLE_STAGES / PROGRESS_STAGES / SIGNUP_STATUSES 常量；
#   3. 日期控件 -> 字符串的重复逻辑收敛为 _qdatetime_to_str 辅助函数；
#   4. 日期编辑 / 日历弹窗样式统一移至 styles.DIALOG_QSS。

from __future__ import annotations

import re

from PySide6.QtCore import Qt, QDate, QDateTime, Signal
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDateTimeEdit, QDialog, QDialogButtonBox,
    QFormLayout, QFrame, QGroupBox, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

import database
from config import COLORS
from ui.styles import DIALOG_QSS
from utils.constants import (
    DROP_REASON_MAP, LIFECYCLE_STAGES, PROGRESS_STAGES, SIGNUP_STATUSES,
    DATE_FORMAT, DATETIME_FORMAT,
)

REQUIRED_MARK = f'<span style="color:{COLORS["danger"]}">&nbsp;*</span>'


def _style_ok_cancel(btn_box: QDialogButtonBox, ok_text="确定", cancel_text="取消") -> None:
    ok_btn = btn_box.button(QDialogButtonBox.Ok)
    if ok_btn:
        ok_btn.setText(ok_text)
        ok_btn.setProperty("primary", True)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.style().unpolish(ok_btn)
        ok_btn.style().polish(ok_btn)
    cancel_btn = btn_box.button(QDialogButtonBox.Cancel)
    if cancel_btn:
        cancel_btn.setText(cancel_text)
        cancel_btn.setCursor(Qt.PointingHandCursor)


def _split_list(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"[,，]", text) if x.strip()]


def _qdatetime_to_str(qdt: QDateTime) -> str:
    """QDateTimeEdit 取值 -> 存储字符串（整点日期省略时间部分）。"""
    if not qdt.isValid():
        return ""
    if qdt.time().hour() == 0 and qdt.time().minute() == 0:
        return qdt.toString(DATE_FORMAT)
    return qdt.toString(DATETIME_FORMAT)


# ======================= 设置弹窗 =======================
class SettingsDialog(QDialog):
    # 数据被清空后发出，供主窗口刷新表格与日历
    dataCleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 系统设置")
        self.resize(520, 460)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 28, 28, 28)

        title = QLabel("基础数据管理")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLORS['text']};")
        layout.addWidget(title)

        subtitle = QLabel("修改新增/编辑项目弹窗中的下拉选项，多个选项请用逗号分隔")
        subtitle.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        group = QGroupBox("下拉菜单选项管理")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(12)

        regions = database.get_setting("regions") or []
        categories = database.get_setting("categories") or []
        agencies = database.get_setting("agencies") or []

        self.region_edit = QLineEdit(", ".join(regions))
        form.addRow("区域列表:", self.region_edit)
        self.cat_edit = QLineEdit(", ".join(categories))
        form.addRow("项目类别:", self.cat_edit)
        self.agency_edit = QLineEdit(", ".join(agencies))
        form.addRow("常用代理:", self.agency_edit)

        layout.addWidget(group)

        # ===== 数据管理（危险操作） =====
        danger_group = QGroupBox("数据管理")
        danger_group.setStyleSheet(
            f"QGroupBox{{color:{COLORS['danger']};font-weight:600;}}")
        dv = QVBoxLayout(danger_group)
        dv.setSpacing(10)

        clear_hint = QLabel("清空后所有项目记录将被永久删除且不可恢复，请谨慎操作。")
        clear_hint.setStyleSheet(
            f"color:{COLORS['text_muted']};font-size:12px;")
        clear_hint.setWordWrap(True)
        dv.addWidget(clear_hint)

        self.btn_clear = QPushButton("🗑 一键清空所有数据")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet(
            f"QPushButton{{background:{COLORS['danger']};color:#fff;"
            f"border:none;border-radius:8px;padding:9px 16px;"
            f"font-size:13px;font-weight:600;}}"
            f"QPushButton:hover{{background:{COLORS['primary_pressed']};}}")
        self.btn_clear.clicked.connect(self._on_clear_data)
        dv.addWidget(self.btn_clear)

        layout.addWidget(danger_group)
        layout.addStretch()

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        _style_ok_cancel(btn_box, "保存", "取消")
        btn_box.accepted.connect(self.on_save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def on_save(self) -> None:
        regions = _split_list(self.region_edit.text())
        categories = _split_list(self.cat_edit.text())
        agencies = _split_list(self.agency_edit.text())

        if not regions or not categories:
            QMessageBox.warning(self, "提示", "区域列表和项目类别不能为空")
            return

        database.set_setting("regions", regions)
        database.set_setting("categories", categories)
        database.set_setting("agencies", agencies)
        QMessageBox.information(self, "已保存", "✅ 设置已保存，下次新增/编辑项目时生效")
        self.accept()

    def _on_clear_data(self) -> None:
        """一键清空：二次确认后删除全部项目数据，并通知主窗口刷新。"""
        ret = QMessageBox.warning(
            self, "确认清空数据",
            "此操作将<font color='#e05c5c'><b>永久删除全部项目记录</b></font>，"
            "且不可恢复！\n\n确定要清空所有数据吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        n = database.clear_all_projects()
        QMessageBox.information(self, "已清空", f"已清空 {n} 条项目数据。")
        self.dataCleared.emit()


# ======================= 新增/编辑项目弹窗 =======================
class AddProjectDialog(QDialog):
    def __init__(self, parent=None, project_data: dict | None = None):
        super().__init__(parent)
        self.is_edit = project_data is not None
        self.project_id = project_data.get("id") if project_data else None
        self.setWindowTitle("✏️ 编辑项目" if self.is_edit else "➕ 新增项目")
        self.resize(760, 700)
        self.setModal(True)
        self.setStyleSheet(DIALOG_QSS)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(28, 28, 28, 28)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        scroll_layout.setSpacing(14)

        scroll_layout.addWidget(self._build_basic_group(project_data))
        scroll_layout.addWidget(self._build_time_group(project_data))
        scroll_layout.addWidget(self._build_status_group(project_data))
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        _style_ok_cancel(btn_box, "保存" if self.is_edit else "确认新增", "取消")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

        # 信号连接
        self.lifecycle_combo.currentTextChanged.connect(self.on_lifecycle_changed)
        self.drop_category_combo.currentTextChanged.connect(self.update_detail_combo)

        if project_data and project_data.get("lifecycle") == "已放弃":
            self._restore_drop_reasons(project_data)

    # ---------- 分组构建 ----------
    def _build_basic_group(self, project_data: dict | None) -> QGroupBox:
        group = QGroupBox("📌 基本信息")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入项目全称")
        if project_data:
            self.name_edit.setText(project_data.get("name") or "")
        form.addRow(QLabel("项目名称" + REQUIRED_MARK + ":"), self.name_edit)

        regions = database.get_setting("regions") or ["其他"]
        self.region_combo = QComboBox()
        self.region_combo.addItems([""] + regions)
        if project_data:
            self.region_combo.setCurrentText(project_data.get("region") or "")
        form.addRow("区域:", self.region_combo)

        categories = database.get_setting("categories") or ["其他"]
        self.category_combo = QComboBox()
        self.category_combo.addItems(categories)
        if project_data:
            self.category_combo.setCurrentText(project_data.get("category") or "")
        form.addRow("项目类别:", self.category_combo)

        agencies = database.get_setting("agencies") or []
        self.agency_edit = QComboBox()
        self.agency_edit.setEditable(True)
        self.agency_edit.addItems([""] + agencies)
        if project_data:
            self.agency_edit.setCurrentText(project_data.get("agency") or "")
        self.agency_edit.lineEdit().setPlaceholderText("如：浙江省成套招标代理有限公司")
        form.addRow("招标代理:", self.agency_edit)
        return group

    def _build_time_group(self, project_data: dict | None) -> QGroupBox:
        group = QGroupBox("⏰ 时间节点")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.publish_date_edit = QDateEdit()
        self.publish_date_edit.setCalendarPopup(True)
        self.publish_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.publish_date_edit.setSpecialValueText("未设置")
        self.publish_date_edit.setMinimumWidth(180)
        if project_data and project_data.get("publish_date"):
            d = QDate.fromString(project_data["publish_date"], "yyyy-MM-dd")
            if d.isValid():
                self.publish_date_edit.setDate(d)
        form.addRow("发布时间:", self.publish_date_edit)

        self.signup_deadline_edit = QDateTimeEdit()
        self.signup_deadline_edit.setCalendarPopup(True)
        self.signup_deadline_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.signup_deadline_edit.setSpecialValueText("未设置")
        self.signup_deadline_edit.setDateTime(QDateTime.currentDateTime())
        self.signup_deadline_edit.setMinimumWidth(180)
        self._apply_datetime(self.signup_deadline_edit, project_data, "signup_deadline")
        form.addRow("报名截止日:", self.signup_deadline_edit)

        self.bid_deadline_edit = QDateTimeEdit()
        self.bid_deadline_edit.setCalendarPopup(True)
        self.bid_deadline_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.bid_deadline_edit.setDateTime(QDateTime.currentDateTime())
        self.bid_deadline_edit.setMinimumWidth(180)
        self._apply_datetime(self.bid_deadline_edit, project_data, "bid_deadline")
        form.addRow(QLabel("投标截止日" + REQUIRED_MARK + ":"), self.bid_deadline_edit)

        self.shortlist_edit = QLineEdit()
        self.shortlist_edit.setPlaceholderText("0")
        if project_data and project_data.get("shortlist_count"):
            self.shortlist_edit.setText(str(project_data.get("shortlist_count", 0)))
        form.addRow("入围数:", self.shortlist_edit)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://...")
        if project_data:
            self.url_edit.setText(project_data.get("url") or "")
        form.addRow("公告网址:", self.url_edit)
        return group

    def _build_status_group(self, project_data: dict | None) -> QGroupBox:
        group = QGroupBox("📋 状态与进度")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.lifecycle_combo = QComboBox()
        self.lifecycle_combo.addItems(LIFECYCLE_STAGES)
        if project_data:
            self.lifecycle_combo.setCurrentText(project_data.get("lifecycle") or "潜在机会")
        form.addRow("项目阶段:", self.lifecycle_combo)

        self.progress_combo = QComboBox()
        self.progress_combo.addItems(PROGRESS_STAGES)
        if project_data:
            self.progress_combo.setCurrentText(project_data.get("progress") or "未开始")
        form.addRow("执行进度:", self.progress_combo)

        self.signup_combo = QComboBox()
        self.signup_combo.addItems(SIGNUP_STATUSES)
        if project_data:
            self.signup_combo.setCurrentText(project_data.get("signup_status") or "未报名")
        form.addRow("报名状态:", self.signup_combo)

        self.drop_category_combo = QComboBox()
        self.drop_category_combo.addItems(list(DROP_REASON_MAP.keys()))
        self.drop_category_combo.setVisible(False)
        form.addRow("放弃原因(一级):", self.drop_category_combo)

        self.drop_detail_combo = QComboBox()
        self.drop_detail_combo.addItems(["请先选择一级分类"])
        self.drop_detail_combo.setVisible(False)
        form.addRow("放弃原因(二级):", self.drop_detail_combo)

        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("输入备注信息...")
        self.note_edit.setMaximumHeight(70)
        if project_data:
            self.note_edit.setText(project_data.get("note") or "")
        form.addRow("备注:", self.note_edit)
        return group

    # ---------- 辅助 ----------
    @staticmethod
    def _apply_datetime(edit: QDateTimeEdit, project_data: dict | None, key: str) -> None:
        if not project_data or not project_data.get(key):
            return
        dt_str = project_data[key]
        fmt = "yyyy-MM-dd HH:mm" if " " in dt_str else "yyyy-MM-dd"
        dt = QDateTime.fromString(dt_str, fmt)
        if dt.isValid():
            edit.setDateTime(dt)

    def _restore_drop_reasons(self, project_data: dict) -> None:
        self.drop_category_combo.setVisible(True)
        self.drop_detail_combo.setVisible(True)
        cat = project_data.get("drop_reason_category")
        detail = project_data.get("drop_reason_detail")
        if cat:
            idx = self.drop_category_combo.findText(cat)
            if idx >= 0:
                self.drop_category_combo.setCurrentIndex(idx)
        self.update_detail_combo()
        if detail:
            idx = self.drop_detail_combo.findText(detail)
            if idx >= 0:
                self.drop_detail_combo.setCurrentIndex(idx)

    # ---------- 交互 ----------
    def on_lifecycle_changed(self, text: str) -> None:
        is_dropped = (text == "已放弃")
        self.drop_category_combo.setVisible(is_dropped)
        self.drop_detail_combo.setVisible(is_dropped)
        if not is_dropped:
            self.drop_category_combo.setCurrentIndex(0)
            self.drop_detail_combo.clear()
            self.drop_detail_combo.addItems(["请先选择一级分类"])

    def update_detail_combo(self) -> None:
        category = self.drop_category_combo.currentText()
        self.drop_detail_combo.clear()
        self.drop_detail_combo.addItems(DROP_REASON_MAP.get(category, ["请先选择一级分类"]))

    def accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写项目名称")
            return
        if self.lifecycle_combo.currentText() == "已放弃":
            if not self.drop_category_combo.currentText() or not self.drop_detail_combo.currentText():
                QMessageBox.warning(self, "提示", "请完整选择放弃原因（一级和二级）")
                return
        super().accept()

    def get_data(self) -> dict:
        lifecycle = self.lifecycle_combo.currentText()
        is_dropped = lifecycle == "已放弃"
        return {
            "name": self.name_edit.text().strip(),
            "region": self.region_combo.currentText() or "",
            "category": self.category_combo.currentText() or "",
            "agency": self.agency_edit.currentText().strip(),
            "publish_date": self.publish_date_edit.date().toString(DATE_FORMAT)
            if self.publish_date_edit.date().isValid() else "",
            "signup_deadline": _qdatetime_to_str(self.signup_deadline_edit.dateTime()),
            "bid_deadline": _qdatetime_to_str(self.bid_deadline_edit.dateTime()),
            "shortlist_count": int(self.shortlist_edit.text()) if self.shortlist_edit.text().isdigit() else 0,
            "url": self.url_edit.text().strip(),
            "lifecycle": lifecycle,
            "progress": self.progress_combo.currentText(),
            "signup_status": self.signup_combo.currentText(),
            "note": self.note_edit.toPlainText().strip(),
            "result": "",
            "drop_reason_category": self.drop_category_combo.currentText() if is_dropped else "",
            "drop_reason_detail": self.drop_detail_combo.currentText() if is_dropped else "",
        }


# ======================= 项目详情弹窗 =======================
class ProjectDetailDialog(QDialog):
    def __init__(self, project_data: dict, parent=None):
        super().__init__(parent)
        self.project_data = project_data
        self.parent_window = parent
        self.setWindowTitle(f"📄 {project_data.get('name', '项目详情')}")
        self.resize(600, 520)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(project_data.get("name", "项目详情"))
        header.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {COLORS['text']};")
        header.setWordWrap(True)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        form_layout = QFormLayout(content)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(10)

        fields = [
            ("区域", "region"), ("项目类别", "category"),
            ("招标代理", "agency"), ("发布时间", "publish_date"),
            ("报名截止日", "signup_deadline"), ("投标截止日", "bid_deadline"),
            ("入围数", "shortlist_count"), ("公告网址", "url"),
            ("项目阶段", "lifecycle"), ("进度", "progress"),
            ("报名状态", "signup_status"), ("备注", "note"),
        ]
        for label, key in fields:
            value = project_data.get(key, "") or "-"
            if key == "url" and value != "-":
                lbl = QLabel(f'<a href="{value}" style="color:{COLORS["primary"]};">{value}</a>')
                lbl.setOpenExternalLinks(True)
                lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
            else:
                lbl = QLabel(str(value))
                lbl.setWordWrap(True)
                lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form_layout.addRow(label + ":", lbl)

        if project_data.get("drop_reason_category"):
            form_layout.addRow("放弃原因（一级）:", QLabel(project_data.get("drop_reason_category")))
        if project_data.get("drop_reason_detail"):
            form_layout.addRow("放弃原因（二级）:", QLabel(project_data.get("drop_reason_detail")))

        scroll.setWidget(content)
        layout.addWidget(scroll)

        btn_box = QDialogButtonBox()
        btn_edit = QPushButton("✏️ 编辑")
        btn_edit.setProperty("primary", True)
        btn_edit.setCursor(Qt.PointingHandCursor)
        btn_edit.clicked.connect(self.on_edit)
        btn_box.addButton(btn_edit, QDialogButtonBox.ActionRole)

        btn_delete = QPushButton("🗑 删除")
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_delete.setStyleSheet(f"color: {COLORS['danger']};")
        btn_delete.clicked.connect(self.on_delete)
        btn_box.addButton(btn_delete, QDialogButtonBox.ActionRole)

        btn_close = QPushButton("关闭")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        btn_box.addButton(btn_close, QDialogButtonBox.RejectRole)
        layout.addWidget(btn_box)

    def on_edit(self) -> None:
        dialog = AddProjectDialog(self, self.project_data)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            if not new_data["name"] or not new_data["bid_deadline"]:
                QMessageBox.warning(self, "提示", "项目名称和投标截止日为必填项")
                return
            try:
                database.update_project(self.project_data["id"], new_data)
                QMessageBox.information(self, "成功", "项目已更新")
                self.accept()
                if self.parent_window:
                    self.parent_window.load_data()
            except Exception as e:  # noqa: BLE001
                QMessageBox.critical(self, "错误", f"更新失败：{str(e)}")

    def on_delete(self) -> None:
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除项目「{self.project_data.get('name')}」吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            database.delete_project(self.project_data["id"])
            QMessageBox.information(self, "已删除", "项目已成功删除")
            self.accept()
            if self.parent_window:
                self.parent_window.load_data()
