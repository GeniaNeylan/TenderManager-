# config.py
# 全局常量配置

PAGE_SIZE = 15  # 每页显示条数

# ==================== 颜色配置（统一主题令牌） ====================
# 修改这里即可整体调整主题配色，UI 各处不再写死颜色值
COLORS = {
    "primary":          "#d86a6a",
    "primary_hover":    "#c95a5a",
    "primary_pressed":  "#b84a4a",
    "primary_soft":     "#fbeceb",

    "bg":               "#f5f6f8",
    "surface":          "#ffffff",
    "surface_alt":      "#fafbfc",

    "text":             "#2c3e50",
    "text_secondary":   "#6a7a8a",
    "text_muted":       "#9a9da2",

    "border":           "#eef0f2",
    "border_strong":    "#e4e6ea",

    "success":          "#4caf7d",
    "success_soft":     "#e8f6ee",
    "warning":          "#e0a63e",
    "warning_soft":     "#fdf3e3",
    "danger":           "#e05c5c",
    "danger_soft":      "#fdeaea",
    "info":             "#6a8caf",
    "info_soft":        "#eaf1f7",

    "gray":             "#b0b4ba",
}

# 项目阶段 -> 徽章配色 (文字色, 背景色)
STAGE_COLORS = {
    "潜在机会": ("#6a8caf", "#eaf1f7"),
    "跟进中":   ("#d86a6a", "#fbeceb"),
    "已放弃":   ("#9a9da2", "#f0f1f3"),
    "已结束":   ("#4caf7d", "#e8f6ee"),
}

# 快捷筛选/统计卡片顺序（与 utils.constants.STAGE_ORDER 保持一致，单一来源）
from utils.constants import STAGE_ORDER  # noqa: E402  (置于文件末尾以复用常量层)

# 字体
FONT_FAMILY = "PingFang SC, Microsoft YaHei, -apple-system, sans-serif"
