# utils/date_utils.py
# 集中处理项目里分散在 app.py / calendar_widget.py / database.py 中的日期解析逻辑。
# 原代码中反复出现 `datetime.strptime(deadline_str.split()[0], "%Y-%m-%d")`，
# 既冗余又容易因格式不一致而抛异常，这里统一收敛为纯函数。

from __future__ import annotations

from datetime import date, datetime

from utils.constants import DATE_FORMAT, DATETIME_FORMAT

# 排序 / 比较时使用的「无穷大」占位（无法解析的日期排到最后）。
_SENTINEL = float("inf")


def parse_date(value: str | None) -> date | None:
    """将数据库里的日期字符串解析为 date 对象。

    兼容两种存储格式：
      - "2024-01-15"          （纯日期）
      - "2024-01-15 14:30"    （含时间，自动取空格前的日期部分）

    解析失败 / 空值返回 None，绝不向外抛异常。
    """
    if not value:
        return None
    raw = value.strip().split()[0]  # 去掉可能存在的 "HH:mm" 后缀
    for fmt in (DATE_FORMAT, DATETIME_FORMAT):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def days_until(value: str | None) -> int | None:
    """距离该日期还有多少天（负数表示已过期）。无法解析返回 None。"""
    d = parse_date(value)
    return (d - date.today()).days if d else None


def format_date(value: str | None) -> str:
    """统一输出 YYYY-MM-DD 字符串；空 / 异常返回空串。"""
    d = parse_date(value)
    return d.strftime(DATE_FORMAT) if d else ""


def sort_key(value: str | None) -> float:
    """用于按截止日排序的 key：可解析日期返回序数，否则排在末尾。"""
    d = parse_date(value)
    return d.toordinal() if d else _SENTINEL


def is_overdue(value: str | None) -> bool:
    """是否已过期。"""
    days = days_until(value)
    return days is not None and days < 0


def urgency_level(value: str | None) -> str:
    """根据剩余天数返回紧急程度标签，供 UI 着色使用：
    danger（已过期或 ≤3 天）/ warning（≤7 天）/ normal（其余）。"""
    days = days_until(value)
    if days is None:
        return "normal"
    if days < 0 or days <= 3:
        return "danger"
    if days <= 7:
        return "warning"
    return "normal"
