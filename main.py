# main.py
import sys
import os
import io


class _SafeStream(io.TextIOBase):
    """无控制台（--windowed）时 sys.stdout/stderr 为 None，print 会崩溃；
    这里用空操作流兜底，保证任何 print 都安全无副作用。"""

    def write(self, s):  # noqa: A003
        return 0

    def flush(self):
        return None


# 统一 stdout/stderr：
#   - 为 None（windowed）：替换为安全空流；
#   - 存在但编码为 GBK：重设为 UTF-8，避免打印 emoji/中文时崩溃。
for _name in ("stdout", "stderr"):
    _s = getattr(sys, _name, None)
    if _s is None:
        setattr(sys, _name, _SafeStream())
    else:
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QPalette, QIcon
from config import COLORS
from ui.styles import MODERN_QSS
from ui.app import MainWindow

# 👇 新增导入
from database import init_db

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 👇 关键修复：在启动 UI 之前，强制初始化数据库（建表）
    init_db()

    # 应用图标：源码运行取脚本目录；打包后优先取 exe 同目录，
    # 再回退到 _internal（PyInstaller onedir 的 --add-data 落点）。
    _base = os.path.dirname(sys.executable)
    _candidates = [
        os.path.join(_base, "app_icon.ico"),
        os.path.join(_base, "_internal", "app_icon.ico"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico"),
    ]
    _icon_path = next((p for p in _candidates if os.path.exists(p)), None)
    if _icon_path:
        app.setWindowIcon(QIcon(_icon_path))

    app.setStyle("Fusion")

    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["surface"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["surface_alt"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["bg"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["primary"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["text"]))
    palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
    app.setPalette(palette)

    app.setStyleSheet(MODERN_QSS)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
