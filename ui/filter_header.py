# ui/filter_header.py
# 项目阶段列表头：点击右侧漏斗图标弹出筛选菜单。
# 从 ui/app.py 抽离，职责单一、便于独立测试。

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath
from PySide6.QtWidgets import QHeaderView, QMenu

from config import COLORS, STAGE_ORDER


class FilterHeader(QHeaderView):
    """带筛选漏斗图标的水平表头。"""

    FILTER_COLUMN = 1  # 「项目阶段」所在列
    ICON_SIZE = 10

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.main_window = None  # 由外部注入 MainWindow 实例
        self.current_filter = "全部"
        self._hover_icon = False
        self.setSectionsClickable(True)
        self.setMouseTracking(True)

    # ---------- 几何计算 ----------
    def _section_rect(self, logical_index: int) -> QRect:
        pos = self.sectionViewportPosition(logical_index)
        return QRect(pos, 0, self.sectionSize(logical_index), self.height())

    def _icon_rect(self, section_rect: QRect) -> QRect:
        size = self.ICON_SIZE
        return QRect(
            section_rect.right() - size - 14,
            section_rect.center().y() - size // 2,
            size,
            size,
        )

    # ---------- 绘制漏斗图标 ----------
    def paintSection(self, painter, rect, logicalIndex):
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex != self.FILTER_COLUMN:
            return

        icon_rect = self._icon_rect(rect)
        active = self.current_filter != "全部"

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        color = QColor(COLORS["primary"]) if active else QColor(COLORS["gray"])
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)

        x, y, w, h = (
            icon_rect.x(),
            icon_rect.y(),
            icon_rect.width(),
            icon_rect.height(),
        )
        path = QPainterPath()
        path.moveTo(x, y)
        path.lineTo(x + w, y)
        path.lineTo(x + w * 0.62, y + h * 0.55)
        path.lineTo(x + w * 0.62, y + h)
        path.lineTo(x + w * 0.38, y + h * 0.8)
        path.lineTo(x + w * 0.38, y + h * 0.55)
        path.closeSubpath()
        painter.drawPath(path)

        if active:
            painter.setBrush(QColor(COLORS["primary"]))
            painter.drawEllipse(icon_rect.right() - 2, icon_rect.top() - 2, 6, 6)

        painter.restore()

    # ---------- 交互 ----------
    def mouseMoveEvent(self, event):
        idx = self.logicalIndexAt(event.pos())
        hovering = False
        if idx == self.FILTER_COLUMN:
            icon_rect = self._icon_rect(self._section_rect(idx))
            hovering = icon_rect.adjusted(-6, -6, 6, 6).contains(event.pos())
        if hovering != self._hover_icon:
            self._hover_icon = hovering
            self.setCursor(
                QCursor(Qt.PointingHandCursor) if hovering else QCursor(Qt.ArrowCursor)
            )
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        idx = self.logicalIndexAt(event.pos())
        if idx == self.FILTER_COLUMN:
            icon_rect = self._icon_rect(self._section_rect(idx))
            if icon_rect.adjusted(-6, -6, 6, 6).contains(event.pos()):
                self.show_filter_menu(event.globalPos())
                return
        super().mousePressEvent(event)

    def show_filter_menu(self, pos):
        menu = QMenu(self)
        for option in STAGE_ORDER:
            action = menu.addAction(option)
            action.setCheckable(True)
            action.setChecked(option == self.current_filter)
        chosen = menu.exec(pos)
        if chosen is not None:
            self.on_filter_selected(chosen.text())

    def on_filter_selected(self, filter_value: str) -> None:
        self.current_filter = filter_value
        if self.main_window is not None:
            self.main_window.apply_filter(filter_value)
        self.update()

    def reset_filter(self) -> None:
        self.current_filter = "全部"
        self.update()
