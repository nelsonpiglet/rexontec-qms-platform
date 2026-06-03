"""
REXONTEC 力科 — 維修保養系統 Google Sheet 連線工具
試算表：返廠主單 (RMA Master)  主單編號格式：RMA-B2026-001
"""
from datetime import datetime

SPREADSHEET_ID    = "1OksPtvaabwXIMdO8gPA7A6s6oHpLy_Liewcc_pyOmA8"
MASTER_SHEET_NAME = "返廠主單"

MASTER_COLUMNS = [
    "主單編號",
    "客戶公司", "聯絡人", "聯絡電話", "客戶Email",
    "收件日期",
    "退修數量",
    "整體狀態",
    "優先等級",
    "維修類型",
    "故障詳細描述",
    "備註",
    "建立時間",
]

MASTER_COL = {col: i + 1 for i, col in enumerate(MASTER_COLUMNS)}

MASTER_DONE_STATUS = {"已完成", "已出廠", "已取消"}

STATUS_PRIORITY = {
    "待收件": 0, "已收件": 1, "初診中": 2, "待檢測": 3,
    "待零件": 4, "維修中": 5, "待QC": 6,
    "已完成": 7, "已出廠": 8, "已取消": -1,
}


def _client(fresh: bool = False):
    from utils.rma_gsheet import get_client
    if fresh:
        get_client.clear()
    return get_client()


def _open_master_sheet_once():
    ss     = _client().open_by_key(SPREADSHEET_ID)
    titles = [ws.title for ws in ss.worksheets()]
    need   = len(MASTER_COLUMNS) + 5
    if MASTER_SHEET_NAME in titles:
        ws = ss.worksheet(MASTER_SHEET_NAME)
        if ws.col_count < len(MASTER_COLUMNS):
            ws.resize(cols=need)
        return ws
    ws = ss.add_worksheet(title=MASTER_SHEET_NAME, rows=2000, cols=need)
    ws.insert_row(MASTER_COLUMNS, 1)
    return ws


def get_master_sheet():
    """取得 master worksheet；失敗時自動清除連線快取並重試最多 2 次。"""
    import time
    last_err = None
    for attempt in range(3):
        try:
            return _open_master_sheet_once()
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 ** attempt)
                _client(fresh=True)
    raise last_err


def ensure_master_headers(sheet):
    if sheet.col_count < len(MASTER_COLUMNS):
        sheet.resize(cols=len(MASTER_COLUMNS) + 5)
    first = sheet.row_values(1)
    if not first or first[0] != "主單編號":
        sheet.insert_row(MASTER_COLUMNS, 1)
    elif len(first) < len(MASTER_COLUMNS):
        sheet.update("A1", [MASTER_COLUMNS])


def _find_row(sheet, master_id: str) -> int:
    col_vals = sheet.col_values(MASTER_COL["主單編號"])
    for i, val in enumerate(col_vals):
        if val == master_id:
            return i + 1
    return -1


def _gen_id(sheet) -> str:
    existing = [v for v in sheet.col_values(MASTER_COL["主單編號"])[1:] if v]
    seq  = len(existing) + 1
    year = datetime.now().year
    return f"RMA-B{year}-{str(seq).zfill(3)}"


# ── CRUD ─────────────────────────────────────────────────────────────────────

def append_master(data: dict) -> str:
    """建立主單，回傳 master_id。"""
    sheet = get_master_sheet()
    ensure_master_headers(sheet)
    mid = _gen_id(sheet)
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    row = [
        mid,
        data.get("company",      ""),
        data.get("contact",      ""),
        data.get("phone",        ""),
        data.get("email",        ""),
        now,
        data.get("qty",          1),
        "待收件",
        data.get("priority",     "P3"),
        data.get("repair_type",  ""),
        data.get("fault_desc",   ""),
        data.get("note",         ""),
        now,
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    return mid


def load_all_masters():
    import pandas as pd
    records = get_master_sheet().get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(columns=MASTER_COLUMNS)


def get_master_by_id(master_id: str) -> dict:
    sheet   = get_master_sheet()
    row_num = _find_row(sheet, master_id)
    if row_num == -1:
        return {}
    values = sheet.row_values(row_num)
    return {col: (values[i] if i < len(values) else "") for i, col in enumerate(MASTER_COLUMNS)}


def update_master_status(master_id: str, new_status: str) -> bool:
    sheet   = get_master_sheet()
    row_num = _find_row(sheet, master_id)
    if row_num == -1:
        return False
    sheet.update_cell(row_num, MASTER_COL["整體狀態"], new_status)
    return True


def sync_master_status(master_id: str, details_df) -> str:
    """
    依子件狀態計算主單整體狀態並寫回 Google Sheet。
    details_df：該主單的所有子件 DataFrame。
    """
    if details_df is None or details_df.empty:
        return "待收件"
    statuses = details_df["維修狀態"].tolist()
    if all(s == "已取消" for s in statuses):
        new = "已取消"
    elif all(s in MASTER_DONE_STATUS for s in statuses):
        new = "已出廠" if all(s == "已出廠" for s in statuses) else "已完成"
    else:
        active = [s for s in statuses if s not in MASTER_DONE_STATUS]
        new = min(active, key=lambda s: STATUS_PRIORITY.get(s, 0)) if active else "維修中"
    update_master_status(master_id, new)
    return new
