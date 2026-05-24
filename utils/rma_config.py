"""
REXONTEC 力科 — 維修保養系統本地設定管理
讀寫 rma_config.json，供 Email 通知等模組使用
"""
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "rma_config.json")

DEFAULT_CFG = {
    "email": {
        "smtp_server":     "smtp.gmail.com",
        "smtp_port":       587,
        "sender_email":    "",
        "sender_password": "",
        "sales_email":     "",
        "cc_email":        "",
    }
}


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = {**DEFAULT_CFG, **data}
        merged["email"] = {**DEFAULT_CFG["email"], **data.get("email", {})}
        return merged
    except Exception:
        return {k: v.copy() if isinstance(v, dict) else v
                for k, v in DEFAULT_CFG.items()}


def save_config(cfg: dict) -> bool:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[RMA Config] 儲存失敗：{e}")
        return False


def get_email_cfg() -> dict | None:
    cfg = load_config()
    email = cfg.get("email", {})
    if email.get("sender_email") and email.get("sender_password") and email.get("sales_email"):
        return email
    return None
