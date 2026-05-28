"""
REXONTEC OQC — 馬達 Motor per-model 檢驗模板資料庫
資料永久儲存於 Google Sheets「Config」工作表（key = "motor_templates"）。

Template 格式（與 inspection_data.py 的 sections 結構相容）：
{
  "某型號馬達": {
    "model": "某型號馬達",
    "created_at": "2026-05-28",
    "updated_at": "2026-05-28 10:00",
    "sections": [
      {
        "id": "A",
        "label": "外觀尺寸類",
        "subtitle": "卡尺 / 目視",
        "items": [
          {
            "id": "A1", "no": "1.0", "name": "...", "spec": "...",
            "grade": "MA", "type": "pf", "tool": "目視"
          },
          ...
        ]
      }
    ]
  }
}
"""
import streamlit as st
from datetime import datetime

_GSHEET_KEY = "motor_templates"


# ── 帶快取的讀取（30 秒 TTL）──────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _mtr_cached_load() -> dict:
    """從 Google Sheets Config 讀取 Motor 模板（最多快取 30 秒）。"""
    try:
        from utils.gsheet import get_config_json
        result = get_config_json(_GSHEET_KEY)
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


# ── 公開 API ────────────────────────────────────────────────────
def load_templates() -> dict:
    """讀取所有模板，連線失敗回傳空 dict。"""
    return _mtr_cached_load()


def save_templates(templates: dict) -> None:
    """儲存所有模板至 Google Sheets Config，並立即清除快取。"""
    from utils.gsheet import set_config_json
    set_config_json(_GSHEET_KEY, templates)
    _mtr_cached_load.clear()


def list_models() -> list:
    """回傳所有已建立模板的機種名稱清單。"""
    return list(load_templates().keys())


def get_template(model: str) -> dict | None:
    """依機種取得完整模板，不存在回傳 None。"""
    return load_templates().get(model)


def get_sections(model: str) -> list:
    """依機種取得 sections 清單，不存在回傳空 list。"""
    tpl = load_templates().get(model)
    return tpl.get("sections", []) if tpl else []


def upsert_template(model: str, sections: list, meta: dict = None) -> None:
    """新增或更新機種模板。meta 可帶 {'note', ...}。"""
    templates = load_templates()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    old = templates.get(model, {})
    templates[model] = {
        "model":      model,
        "created_at": old.get("created_at", now[:10]),
        "updated_at": now,
        "sections":   sections,
        **(meta or {}),
    }
    save_templates(templates)


def delete_template(model: str) -> bool:
    """刪除機種模板，成功回傳 True，找不到回傳 False。"""
    templates = load_templates()
    if model in templates:
        del templates[model]
        save_templates(templates)
        return True
    return False


def has_template(model: str) -> bool:
    """快速檢查指定機種是否有 Motor 模板。"""
    return model in load_templates()
