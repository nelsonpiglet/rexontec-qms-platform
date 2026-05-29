"""
REXONTEC 力科 — 維修技術檢測項目設定管理
自定義的額外檢測項目儲存於 Google Sheets Config（key = "rma_detection_custom"）。

資料格式（各 Step 的自定義 checkbox 項目清單）：
{
  "S1": [{"id": "漆面刮傷", "label": "漆面刮傷"}, ...],
  "S2": [],
  "S3": [],
  "S4": [],
  "S5": []
}
"""
import streamlit as st

_GSHEET_KEY = "rma_detection_custom"

# 標準 Steps 定義（id, 中文名稱，emoji），供 UI 使用
STANDARD_STEPS = [
    {"id": "S1", "name": "外觀檢測",    "icon": "🔬"},
    {"id": "S2", "name": "手感測試",    "icon": "🤚"},
    {"id": "S3", "name": "電氣測試",    "icon": "⚡"},
    {"id": "S4", "name": "通電測試",    "icon": "🔌"},
    {"id": "S5", "name": "拆解分析",    "icon": "🔩"},
]

# 各 Step 的標準項目（顯示在 UI 的固定欄位，供設定頁顯示用）
STANDARD_ITEMS = {
    "S1": ["外殼撞傷", "軸心歪斜", "沙土侵入", "螺絲裂痕", "正常"],
    "S2": ["異音", "卡頓", "軸承鬆動", "正常"],
    "S3": ["AB阻值（Ω）", "BC阻值（Ω）", "CA阻值（Ω）", "線圈異常（自動判定）"],
    "S4": ["高震動", "高溫", "無法啟動", "正常"],
    "S5": ["線圈燒毀", "磁鐵脫落", "生鏽", "正常"],
}


@st.cache_data(ttl=30, show_spinner=False)
def _cached_load() -> dict:
    """從 Google Sheets Config 讀取自定義檢測項目（30 秒快取）。"""
    try:
        from utils.gsheet import get_config_json
        result = get_config_json(_GSHEET_KEY)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    return {s["id"]: [] for s in STANDARD_STEPS}


def load_custom() -> dict:
    """回傳 {step_id: [{"id":..., "label":...}, ...]}。"""
    base = {s["id"]: [] for s in STANDARD_STEPS}
    loaded = _cached_load()
    base.update(loaded)
    return base


def save_custom(data: dict) -> None:
    """儲存自定義項目並清除快取。"""
    from utils.gsheet import set_config_json
    set_config_json(_GSHEET_KEY, data)
    _cached_load.clear()


def get_step_custom_items(step_id: str) -> list:
    """取得某 Step 的自定義項目清單。"""
    return load_custom().get(step_id, [])


def add_custom_item(step_id: str, item_id: str, label: str) -> bool:
    """新增自定義項目。id 重複時回傳 False。"""
    data = load_custom()
    items = data.get(step_id, [])
    if any(x["id"] == item_id for x in items):
        return False
    items.append({"id": item_id, "label": label})
    data[step_id] = items
    save_custom(data)
    return True


def remove_custom_item(step_id: str, item_id: str) -> bool:
    """刪除自定義項目。找不到回傳 False。"""
    data = load_custom()
    items = data.get(step_id, [])
    new_items = [x for x in items if x["id"] != item_id]
    if len(new_items) == len(items):
        return False
    data[step_id] = new_items
    save_custom(data)
    return True
