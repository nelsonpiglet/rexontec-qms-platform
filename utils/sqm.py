"""
REXONTEC — SQM 供應商品質管理 常數與工具
Supplier Quality Management — constants, helpers, color maps
"""

# ═══════════════════════════════════════════════════════
# 分類常數
# ═══════════════════════════════════════════════════════
DEFECT_CATEGORIES = [
    "外觀不良", "尺寸超差", "功能失效", "電性不良",
    "材料不符", "包裝不良", "文件缺失", "其他",
]

JUDGMENT_OPTIONS = [
    "拒收退貨", "讓步接收", "全檢後接收", "報廢處理", "退廠加工",
]

RESP_UNITS = [
    "供應商責任", "來料檢驗疏失", "設計變更未通知", "雙方共同責任",
]

DEFECT_STATUS = [
    "待處理", "SCAR開立中", "等待供應商回覆", "已結案",
]

SCAR_REPLY_STATUS = [
    "待回覆", "已回覆", "逾期未回覆",
]

CAPA_STATUS = [
    "未開始", "進行中", "驗證中", "完成",
]

CLOSE_STATUS = ["Open", "Closed"]

# ═══════════════════════════════════════════════════════
# 顏色映射
# ═══════════════════════════════════════════════════════
STATUS_COLOR: dict[str, str] = {
    "待處理":         "#e74c3c",
    "SCAR開立中":     "#e67e22",
    "等待供應商回覆": "#f39c12",
    "已結案":         "#27ae60",
    "Open":           "#e67e22",
    "Closed":         "#27ae60",
    "完成":           "#27ae60",
    "進行中":         "#3498db",
    "驗證中":         "#9b59b6",
    "未開始":         "#95a5a6",
    "已回覆":         "#27ae60",
    "待回覆":         "#e74c3c",
    "逾期未回覆":     "#c0392b",
}

JUDGMENT_COLOR: dict[str, str] = {
    "拒收退貨":  "#e74c3c",
    "報廢處理":  "#c0392b",
    "讓步接收":  "#f39c12",
    "全檢後接收": "#e67e22",
    "退廠加工":  "#9b59b6",
}

CATEGORY_COLOR: dict[str, str] = {
    "外觀不良": "#3498db",
    "尺寸超差": "#e67e22",
    "功能失效": "#e74c3c",
    "電性不良": "#9b59b6",
    "材料不符": "#c0392b",
    "包裝不良": "#1abc9c",
    "文件缺失": "#95a5a6",
    "其他":     "#7f8c8d",
}


# ═══════════════════════════════════════════════════════
# HTML 工具
# ═══════════════════════════════════════════════════════
def status_chip(text: str, color_map: dict | None = None) -> str:
    """回傳 HTML 狀態標籤（帶顏色背景）"""
    cmap  = color_map or STATUS_COLOR
    color = cmap.get(str(text), "#95a5a6")
    return (
        f'<span style="background:{color}22;color:{color};padding:2px 10px;'
        f'border-radius:99px;font-size:11px;font-weight:700;'
        f'border:1px solid {color}66">{text}</span>'
    )


def verdict_chip(text: str) -> str:
    """回傳判定標籤"""
    return status_chip(text, JUDGMENT_COLOR)
