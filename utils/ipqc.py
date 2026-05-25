"""
REXONTEC — IPQC 巡檢設定管理工具
"""
import os
import json
import copy

IPQC_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'ipqc_config.json')


def load_config() -> dict:
    try:
        with open(IPQC_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"models": []}
    except Exception:
        return {"models": []}


def save_config(cfg: dict):
    os.makedirs(os.path.dirname(IPQC_PATH), exist_ok=True)
    with open(IPQC_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_models() -> list:
    return load_config().get("models", [])


def get_model(model_id: str) -> dict | None:
    for m in get_models():
        if m["id"] == model_id:
            return m
    return None


def add_model(model: dict):
    cfg = load_config()
    cfg["models"].append(model)
    save_config(cfg)


def delete_model(model_id: str):
    cfg = load_config()
    cfg["models"] = [m for m in cfg["models"] if m["id"] != model_id]
    save_config(cfg)


def update_model_meta(model_id: str, updates: dict):
    cfg = load_config()
    for m in cfg["models"]:
        if m["id"] == model_id:
            for k, v in updates.items():
                if k not in ("patrol_stations", "fai_stations"):
                    m[k] = v
    save_config(cfg)


def add_station(model_id: str, station_type: str, station: dict):
    """station_type: 'patrol_stations' or 'fai_stations'"""
    cfg = load_config()
    for m in cfg["models"]:
        if m["id"] == model_id:
            m.setdefault(station_type, []).append(station)
    save_config(cfg)


def delete_station(model_id: str, station_type: str, station_idx: int):
    cfg = load_config()
    for m in cfg["models"]:
        if m["id"] == model_id:
            lst = m.get(station_type, [])
            if 0 <= station_idx < len(lst):
                lst.pop(station_idx)
    save_config(cfg)


def add_item(model_id: str, station_type: str, station_idx: int, item: dict):
    cfg = load_config()
    for m in cfg["models"]:
        if m["id"] == model_id:
            m.get(station_type, [])[station_idx]["items"].append(item)
    save_config(cfg)


def delete_item(model_id: str, station_type: str, station_idx: int, item_idx: int):
    cfg = load_config()
    for m in cfg["models"]:
        if m["id"] == model_id:
            items = m.get(station_type, [])[station_idx]["items"]
            if 0 <= item_idx < len(items):
                items.pop(item_idx)
    save_config(cfg)


def update_item(model_id: str, station_type: str, station_idx: int, item_idx: int, updates: dict):
    cfg = load_config()
    for m in cfg["models"]:
        if m["id"] == model_id:
            item = m.get(station_type, [])[station_idx]["items"][item_idx]
            item.update(updates)
    save_config(cfg)
