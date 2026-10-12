# utils/excel_io.py
# Excel 导入 / 导出逻辑，从 ui/app.py 抽离。
# 导出：把内存中的项目列表写为 .xlsx；
# 导入：读取 .xlsx，按列名模糊匹配字段，去重后写入数据库。

from __future__ import annotations

from datetime import datetime
from typing import Callable, Sequence

from PySide6.QtWidgets import QFileDialog, QMessageBox

import database

# 导出列顺序：(中文表头, 取数 key)
EXPORT_COLUMNS = [
    ("项目名称", "name"),
    ("区域", "region"),
    ("项目类别", "category"),
    ("招标代理", "agency"),
    ("发布时间", "publish_date"),
    ("报名截止日", "signup_deadline"),
    ("投标截止日", "bid_deadline"),
    ("入围数", "shortlist_count"),
    ("项目阶段", "lifecycle"),
    ("进度", "progress"),
    ("报名状态", "signup_status"),
    ("放弃原因(一级)", "drop_reason_category"),
    ("放弃原因(二级)", "drop_reason_detail"),
    ("备注", "note"),
    ("公告链接", "url"),
]

# 列名模糊匹配规则：(命中关键词, 目标字段)；按顺序优先匹配。
COLUMN_ALIASES = [
    (("项目名称", "名称", "name"), "name"),
    (("区域", "地区", "region"), "region"),
    (("类别", "category"), "category"),
    (("代理", "agency"), "agency"),
    (("发布时间", "publish"), "publish_date"),
    (("报名截止", "signup"), "signup_deadline"),
    (("投标截止", "bid"), "bid_deadline"),
    (("入围", "shortlist"), "shortlist_count"),
    (("阶段", "lifecycle"), "lifecycle"),
    (("进度", "progress"), "progress"),
    (("报名状态", "signup_status"), "signup_status"),
    (("备注", "note"), "note"),
    (("链接", "url"), "url"),
]


def export_projects_to_excel(projects: Sequence[dict], parent=None) -> None:
    """将项目列表导出为 Excel。projects 为展示层 dict，含 'raw' 原始记录。"""
    try:
        import pandas as pd
    except ImportError:
        QMessageBox.critical(
            parent, "缺少依赖", "请先安装 pandas 和 openpyxl：pip install pandas openpyxl"
        )
        return

    if not projects:
        QMessageBox.warning(parent, "提示", "当前没有数据可导出")
        return

    try:
        rows = []
        for item in projects:
            raw = item.get("raw", {})
            rows.append({header: raw.get(key, "") for header, key in EXPORT_COLUMNS})
        df = pd.DataFrame(rows)
        filename = f"台账_导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False, engine="openpyxl")
        QMessageBox.information(parent, "导出成功", f"✅ 已导出到：\n{filename}")
    except Exception as e:  # noqa: BLE001 - 向用户暴露原始错误
        QMessageBox.critical(parent, "导出失败", str(e))


def _map_columns(columns) -> dict:
    """把 Excel 列名映射到数据库字段。返回 {excel列名: db字段}。"""
    mapping = {}
    for col in columns:
        col_lower = str(col).strip().lower()
        for keywords, field in COLUMN_ALIASES:
            if any(k in col_lower for k in keywords):
                mapping[col] = field
                break
    return mapping


def import_projects_from_excel(parent=None, reload_callback: Callable[[], None] | None = None) -> None:
    """从 Excel 导入项目，按名称去重。导入完成后调用 reload_callback 刷新界面。"""
    file_path, _ = QFileDialog.getOpenFileName(
        parent, "选择 Excel 文件", "", "Excel Files (*.xlsx *.xls)"
    )
    if not file_path:
        return

    try:
        import pandas as pd
    except ImportError:
        QMessageBox.critical(
            parent, "缺少依赖", "请先安装 pandas 和 openpyxl：pip install pandas openpyxl"
        )
        return

    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        if df.empty:
            QMessageBox.warning(parent, "提示", "Excel 文件为空")
            return

        col_mapping = _map_columns(df.columns)
        if "name" not in col_mapping.values():
            QMessageBox.warning(parent, "提示", "Excel 中缺少【项目名称】列，无法导入")
            return

        existing_names = {p["name"] for p in database.get_all_projects()}
        imported_count = skipped_count = 0

        for _, row in df.iterrows():
            data = _blank_record()
            for excel_col, db_field in col_mapping.items():
                val = row.get(excel_col)
                if pd.notna(val):
                    data[db_field] = (
                        int(val) if db_field == "shortlist_count" else str(val).strip()
                    )

            if not data["name"] or data["name"] in existing_names:
                skipped_count += 1
                continue

            database.add_project(data)
            existing_names.add(data["name"])
            imported_count += 1

        if reload_callback:
            reload_callback()
        QMessageBox.information(
            parent,
            "导入完成",
            f"✅ 成功导入 {imported_count} 个项目\n"
            f"⏭️ 跳过 {skipped_count} 个（空名称或已存在）",
        )
    except Exception as e:  # noqa: BLE001
        QMessageBox.critical(parent, "导入失败", f"错误信息：{str(e)}")


def _blank_record() -> dict:
    return {
        "name": "", "region": "", "category": "", "agency": "",
        "publish_date": "", "signup_deadline": "", "bid_deadline": "",
        "shortlist_count": 0, "url": "", "lifecycle": "潜在机会",
        "progress": "未开始", "signup_status": "未报名", "note": "",
        "result": "", "drop_reason_category": "", "drop_reason_detail": "",
    }
