# utils/auto_scan.py
# 启动时的「状态自动扫描器」：对过期未响应的项目自动置为「已放弃」。
# 从 ui/app.py 抽离，作为纯数据逻辑，与 UI 解耦。

from __future__ import annotations

import database
from utils.constants import AUTO_DROP_BID, AUTO_DROP_SIGNUP
from utils.date_utils import is_overdue, parse_date


def run_auto_scan(verbose: bool = True) -> int:
    """扫描全部项目，把过期未报名 / 未投标的跟进类项目自动标记为「已放弃」。

    返回被更新的项目数量。verbose=True 时打印日志。
    """
    projects = database.get_all_projects()
    updated = 0

    for p in projects:
        # 潜在机会：报名截止已过且仍未报名 → 自动放弃
        if p["lifecycle"] == "潜在机会" and p["signup_status"] == "未报名":
            if _expired(p.get("signup_deadline")):
                p["lifecycle"] = "已放弃"
                p["drop_reason_category"], p["drop_reason_detail"] = AUTO_DROP_SIGNUP
                database.update_project(p["id"], p)
                updated += 1
                if verbose:
                    print(f"🔄 自动放弃：{p['name']} (报名过期)")

        # 跟进中：投标截止已过且未投标 → 自动放弃
        elif p["lifecycle"] == "跟进中" and p.get("progress") != "已投标":
            if _expired(p.get("bid_deadline")):
                p["lifecycle"] = "已放弃"
                p["drop_reason_category"], p["drop_reason_detail"] = AUTO_DROP_BID
                database.update_project(p["id"], p)
                updated += 1
                if verbose:
                    print(f"🔄 自动放弃：{p['name']} (投标过期)")

    if verbose:
        if updated:
            print("✅ 状态扫描完成，已自动更新项目状态。")
        else:
            print("✅ 状态扫描完成，无项目需要自动更新。")
    return updated


def _expired(deadline: str | None) -> bool:
    """仅当存在合法日期且已过期时返回 True（格式异常视为不过期，避免误判）。"""
    d = parse_date(deadline)
    return d is not None and is_overdue(deadline)
