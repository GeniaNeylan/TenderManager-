# database.py
# 数据访问层：所有 SQLite 读写集中在此。
# 重构要点：
#   1. 默认设置 / 放弃原因映射改从 utils.constants 导入，消除与 dialogs 的重复定义；
#   2. 用 _connect() 上下文管理器统一 connect/commit/close，去掉每函数重复的样板；
#   3. 字段清单抽为模块级常量，update_project 不再硬编码 16 个字段名。

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence

from utils.constants import DB_PATH, DEFAULT_SETTINGS, DROP_REASON_MAP

# 项目主表中可被更新的业务字段（不含 id / created_at / updated_at）。
PROJECT_FIELDS = (
    "name", "region", "category", "agency", "publish_date", "signup_deadline",
    "bid_deadline", "shortlist_count", "url", "lifecycle", "progress", "result",
    "signup_status", "drop_reason_category", "drop_reason_detail", "note",
)


@contextmanager
def _connect(row_factory: bool = False) -> Iterator[sqlite3.Cursor]:
    """统一连接管理：自动提交并关闭，调用方无需关心资源释放。"""
    conn = sqlite3.connect(DB_PATH)
    try:
        if row_factory:
            conn.row_factory = sqlite3.Row
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


# ==================== 初始化数据库 ====================
def init_db() -> None:
    with _connect() as cur:
        # 1. 项目主表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tender_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                region TEXT,
                category TEXT,
                agency TEXT,
                publish_date TEXT,
                signup_deadline TEXT,
                bid_deadline TEXT,
                shortlist_count INTEGER DEFAULT 0,
                url TEXT,
                lifecycle TEXT DEFAULT '潜在机会',
                progress TEXT,
                result TEXT,
                signup_status TEXT DEFAULT '未报名',
                drop_reason_category TEXT,
                drop_reason_detail TEXT,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # 2. 设置表（下拉选项以 JSON 存储）
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )

        # 3. 首次建库写入默认设置
        cur.execute("SELECT COUNT(*) FROM settings")
        if cur.fetchone()[0] == 0:
            defaults = {
                "regions": DEFAULT_SETTINGS["regions"],
                "categories": DEFAULT_SETTINGS["categories"],
                "agencies": DEFAULT_SETTINGS["agencies"],
                "drop_reasons": DROP_REASON_MAP,
            }
            for key, val in defaults.items():
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    (key, json.dumps(val, ensure_ascii=False)),
                )

    print("✅ 数据库初始化完成！")


# ==================== 通用设置读写 ====================
def get_setting(key: str) -> Any:
    with _connect() as cur:
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
    return json.loads(row[0]) if row else None


def set_setting(key: str, value: Any) -> None:
    with _connect() as cur:
        cur.execute(
            "REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )


# ==================== 项目 CRUD ====================
def get_all_projects() -> list[dict]:
    with _connect(row_factory=True) as cur:
        cur.execute("SELECT * FROM tender_projects ORDER BY bid_deadline ASC")
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def add_project(data: Mapping[str, Any]) -> None:
    with _connect() as cur:
        cur.execute(
            """
            INSERT INTO tender_projects (
                name, region, category, agency, publish_date, signup_deadline,
                bid_deadline, shortlist_count, url, lifecycle, progress, result,
                signup_status, drop_reason_category, drop_reason_detail, note, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data.get("region"),
                data.get("category"),
                data.get("agency"),
                data.get("publish_date"),
                data.get("signup_deadline"),
                data.get("bid_deadline"),
                _as_int(data.get("shortlist_count")),
                data.get("url"),
                data.get("lifecycle", "潜在机会"),
                data.get("progress"),
                data.get("result"),
                data.get("signup_status", "未报名"),
                data.get("drop_reason_category"),
                data.get("drop_reason_detail"),
                data.get("note"),
                datetime.now().isoformat(),
            ),
        )


def update_project(project_id: int, data: Mapping[str, Any]) -> None:
    """按 PROJECT_FIELDS 全量更新；shortlist_count 强制为整数。"""
    values = [data.get(f) for f in PROJECT_FIELDS]
    values[PROJECT_FIELDS.index("shortlist_count")] = _as_int(
        data.get("shortlist_count")
    )
    with _connect() as cur:
        set_clause = ", ".join(f"{f} = ?" for f in PROJECT_FIELDS)
        cur.execute(
            f"UPDATE tender_projects SET {set_clause}, updated_at = ? WHERE id = ?",
            (*values, datetime.now().isoformat(), project_id),
        )


def delete_project(project_id: int) -> None:
    with _connect() as cur:
        cur.execute("DELETE FROM tender_projects WHERE id = ?", (project_id,))


def clear_all_projects() -> int:
    """清空项目主表全部记录（保留 settings 表），并重置自增主键。

    返回被删除的记录条数；用于「设置 → 一键清空数据」。
    """
    with _connect() as cur:
        cur.execute("SELECT COUNT(*) FROM tender_projects")
        n = cur.fetchone()[0]
        cur.execute("DELETE FROM tender_projects")
        # 重置自增计数（SQLite 的自增序列表），让下次新增 id 从 1 开始
        cur.execute(
            "DELETE FROM sqlite_sequence WHERE name = 'tender_projects'"
        )
    print(f"🗑 已清空 {n} 条项目数据")
    return n


def get_project_by_id(project_id: int) -> Optional[dict]:
    with _connect(row_factory=True) as cur:
        cur.execute("SELECT * FROM tender_projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
    return dict(row) if row else None


# ==================== 小工具 ====================
def _as_int(value: Any) -> int:
    """把任意值安全转为 int，失败返回 0（用于入围数等整型字段）。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# ==================== 仅用于测试（直接运行此文件时执行） ====================
if __name__ == "__main__":
    init_db()
    print("当前项目数：", len(get_all_projects()))
