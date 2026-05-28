"""
REXONTEC — 簽核人員 & 客戶名稱 動態資料庫
Google Sheets 工作表：users_signature

欄位：user_name | role_type | created_at

role_type 定義：
  inspector   → 檢驗員
  qa_manager  → 品保主管
  approver    → 核准人員
  customer    → 客戶名稱
"""
import time
from datetime import datetime

SHEET_NAME = "users_signature"
COLS       = ["user_name", "role_type", "created_at"]
_CACHE_TTL = 30.0          # 快取有效秒數

_cache_rows = None
_cache_ts   = 0.0


# ── 內部工具 ──────────────────────────────────────────
def _ws():
    from utils.gsheet import _open_sheet
    return _open_sheet(SHEET_NAME, COLS)


def _invalidate():
    global _cache_rows, _cache_ts
    _cache_rows = None
    _cache_ts   = 0.0


def _all_rows() -> list:
    """讀取全部列（含 30 s TTL 快取）。"""
    global _cache_rows, _cache_ts
    now = time.time()
    if _cache_rows is not None and (now - _cache_ts) < _CACHE_TTL:
        return _cache_rows
    try:
        _cache_rows = _ws().get_all_records()
        _cache_ts   = now
    except Exception:
        _cache_rows = []
    return _cache_rows


# ── 公開 API ──────────────────────────────────────────
def get_names(role: str) -> list:
    """取得指定 role 的去重名稱清單（依建立時間順序）。"""
    seen, result = set(), []
    for r in _all_rows():
        n = (r.get("user_name") or "").strip()
        if r.get("role_type") == role and n and n not in seen:
            seen.add(n)
            result.append(n)
    return result


def name_exists(name: str, role: str) -> bool:
    """檢查名稱是否已存在於指定 role。"""
    name = (name or "").strip()
    return any(
        r.get("user_name", "").strip() == name and r.get("role_type") == role
        for r in _all_rows()
    )


def add_name(name: str, role: str) -> bool:
    """
    新增名稱到 users_signature。
    重複或空白 → 回傳 False，成功新增 → 回傳 True。
    """
    name = (name or "").strip()
    if not name:
        return False
    if name_exists(name, role):
        return False
    try:
        _ws().append_row(
            [name, role, datetime.now().strftime("%Y/%m/%d %H:%M")],
            value_input_option="USER_ENTERED",
        )
        _invalidate()
        return True
    except Exception:
        return False


def seed_if_empty(role: str, names: list) -> None:
    """
    若 DB 內該 role 尚無資料，自動植入初始名單。
    過濾空字串與「其他」。
    """
    if get_names(role):
        return          # 已有資料，略過
    for n in names:
        n = (n or "").strip()
        if n and n != "其他":
            add_name(n, role)
