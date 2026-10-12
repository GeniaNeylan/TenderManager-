# utils/data_pack.py
# 数据包（ZIP）导入 / 导出，从 ui/app.py 抽离。
# 导出：把 tender.db + metadata.json 打包；
# 导入：先备份当前数据，再覆盖，并提供回调刷新界面。

from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Callable

from PySide6.QtWidgets import QFileDialog, QMessageBox

from utils.constants import DB_PATH


def export_data_pack(parent=None, project_count: int = 0) -> None:
    """导出当前数据为 ZIP 数据包。"""
    default_name = f"台账数据包_{datetime.now().strftime('%Y%m%d')}.zip"
    file_path, _ = QFileDialog.getSaveFileName(
        parent, "导出数据包", default_name, "ZIP 文件 (*.zip)"
    )
    if not file_path:
        return

    if not os.path.exists(DB_PATH):
        QMessageBox.warning(parent, "提示", "数据库文件不存在，无法导出")
        return

    try:
        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(DB_PATH, os.path.basename(DB_PATH))
            metadata = {
                "export_time": datetime.now().isoformat(),
                "db_size": os.path.getsize(DB_PATH),
                "project_count": project_count,
            }
            zipf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        QMessageBox.information(parent, "导出成功", f"✅ 数据包已导出到：\n{file_path}")
    except Exception as e:  # noqa: BLE001
        QMessageBox.critical(parent, "导出失败", f"错误信息：{str(e)}")


def import_data_pack(
    parent=None,
    reload_callback: Callable[[], None] | None = None,
) -> None:
    """导入 ZIP 数据包，导入前自动备份当前数据。"""
    file_path, _ = QFileDialog.getOpenFileName(
        parent, "导入数据包", "", "ZIP 文件 (*.zip)"
    )
    if not file_path:
        return

    try:
        with zipfile.ZipFile(file_path, "r") as zipf:
            file_list = zipf.namelist()
            if DB_PATH not in file_list:
                QMessageBox.warning(parent, "提示", "所选数据包不包含 tender.db，无法导入")
                return

            reply = QMessageBox.question(
                parent,
                "确认导入",
                "导入将覆盖当前所有项目记录，是否继续？\n"
                "当前数据将自动备份。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_backup = f"tender_backup_{backup_time}.db"

            if os.path.exists(DB_PATH):
                shutil.copy2(DB_PATH, db_backup)

            with tempfile.TemporaryDirectory() as tmpdir:
                zipf.extractall(tmpdir)
                shutil.copy2(os.path.join(tmpdir, DB_PATH), DB_PATH)

        if reload_callback:
            reload_callback()

        QMessageBox.information(
            parent,
            "导入成功",
            "✅ 数据包导入完成！\n"
            f"📁 当前数据已备份为：\n{db_backup}",
        )
    except Exception as e:  # noqa: BLE001
        QMessageBox.critical(parent, "导入失败", f"错误信息：{str(e)}")
