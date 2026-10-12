# ui/toast.py
# 轻量级 Toast 提示：用于刷新成功、导入完成等非阻断反馈，
# 替代部分阻塞式 QMessageBox，提升交互流畅度。
# 每个父窗口仅保留一个 Toast 实例，连续触发会平滑替换。

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect, QWidget

_KIND_STYLES = {
    "success": ("#4caf7d", "#e8f6ee"),
    "info": ("#6a8caf", "#eaf1f7"),
    "warning": ("#e0a63e", "#fdf3e3"),
    "danger": ("#e05c5c", "#fdeaea"),
}

_ICONS = {"success": "✅", "info": "ℹ️", "warning": "⚠️", "danger": "⛔"}


class _Toast(QLabel):
    def __init__(self, parent: QWidget, text: str, kind: str):
        super().__init__(parent)
        fg, bg = _KIND_STYLES.get(kind, _KIND_STYLES["info"])
        self.setMinimumWidth(220)
        self.setMaximumWidth(420)
        self.setWordWrap(True)
        self.setText(f"{_ICONS.get(kind, 'ℹ️')}  {text}")
        self.setAlignment(Qt.AlignCenter)
        self.setObjectName("toast")
        self.setStyleSheet(
            f"""
            QLabel#toast {{
                background: {bg};
                color: {fg};
                border: 1px solid {fg};
                border-radius: 10px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 500;
            }}
            """
        )
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.adjustSize()

        # 透明渐变
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0)
        self.setGraphicsEffect(self._effect)

        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(260)

    def fade_in(self):
        self._anim.stop()
        self._anim.setStartValue(0)
        self._anim.setEndValue(1)
        self._anim.start()

    def fade_out(self):
        self._anim.stop()
        self._anim.setStartValue(1)
        self._anim.setEndValue(0)
        self._anim.start()
        self._anim.finished.connect(self.hide)


def show_toast(parent: QWidget, text: str, kind: str = "success", timeout: int = 2200) -> None:
    """在 parent 顶部居中显示一条 Toast，timeout 毫秒后自动消失。"""
    existing = getattr(parent, "_toast", None)
    if isinstance(existing, _Toast):
        existing.deleteLater()

    toast = _Toast(parent, text, kind)
    toast.show()

    # 定位到父窗口顶部居中
    pw = parent.width()
    x = max(12, (pw - toast.width()) // 2)
    toast.move(x, 18)
    parent._toast = toast

    toast.fade_in()

    def _hide():
        toast.fade_out()

    from PySide6.QtCore import QTimer

    QTimer.singleShot(timeout, _hide)
