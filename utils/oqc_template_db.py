"""
REXONTEC OQC — 成檢表模板資料庫
儲存於 config/oqc_templates.json

Template 格式（與 inspection_data.py 的 sections 結構相容）：
{
  "MD1003RX": {
    "model": "MD1003RX",
    "created_at": "2026-05-27",
    "updated_at": "2026-05-27 10:00",
    "sections": [
      {
        "id": "A",
        "label": "包裝類 01",
        "subtitle": "",
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
import os
import json
from datetime import datetime

_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "config", "oqc_templates.json",
)


def load_templates() -> dict:
    """讀取所有模板，不存在或格式錯誤回傳空 dict。"""
    try:
        with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_templates(templates: dict) -> None:
    """儲存所有模板至 JSON 檔案。"""
    os.makedirs(os.path.dirname(_TEMPLATE_PATH), exist_ok=True)
    with open(_TEMPLATE_PATH, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


def list_models() -> list:
    """回傳所有已建立模板的機種名稱清單。"""
    return list(load_templates().keys())


def get_template(model: str) -> dict | None:
    """依機種取得完整模板，不存在回傳 None。"""
    return load_templates().get(model)


def get_sections(model: str) -> list:
    """依機種取得 sections 清單，不存在回傳空 list。"""
    tpl = load_templates().get(model)
    if tpl:
        return tpl.get("sections", [])
    return []


def upsert_template(model: str, sections: list, meta: dict = None) -> None:
    """新增或更新機種模板。meta 可帶 {'doc_no', 'rev', 'note', ...}。"""
    templates = load_templates()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    old = templates.get(model, {})
    templates[model] = {
        "model": model,
        "created_at": old.get("created_at", now[:10]),
        "updated_at": now,
        "sections": sections,
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
    """快速檢查指定機種是否有 OQC 模板。"""
    return model in load_templates()
