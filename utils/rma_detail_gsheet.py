"""
REXONTEC 力科 — 維修保養系統 Google Sheet 連線工具
試算表：返廠子件 (RMA Detail)  子件編號格式：RMA-B2026-001-01
"""
from datetime import datetime
import streamlit as st

SPREADSHEET_ID     = "1OksPtvaabwXIMdO8gPA7A6s6oHpLy_Liewcc_pyOmA8"
DETAIL_SHEET_NAME  = "返廠子件"

DETAIL_COLUMNS = [
    "子件編號", "主單編號",
    "馬達序號", "產品型號", "故障類別",
    "是否曾撞擊/墜機", "飛行總時數(估計)", "故障詳細描述",
    "故障照片連結", "維修狀態", "維修類型", "備註", "內部-技術檢測",
    # ─── 技術檢測欄位 ─────────────────────────────────────
    "S1-外殼撞傷", "S1-軸心歪斜", "S1-沙土侵入", "S1-螺絲裂痕", "S1-正常",
    "S2-異音", "S2-卡頓", "S2-軸承鬆動", "S2-正常",
    "S3-AB阻值", "S3-BC阻值", "S3-CA阻值", "S3-線圈異常",
    "S4-高震動", "S4-高溫", "S4-無法啟動", "S4-正常",
    "S5-線圈燒毀", "S5-磁鐵脫落", "S5-生鏽", "S5-正常",
    "最終判定", "保固判定", "維修方式", "是否報廢", "五步檢測時間",
    # ─── 技術判定欄位 ──────────────────────────────────────
    "技術判定", "是否可維修", "維修成本評估",
]

DETAIL_COL = {col: i + 1 for i, col in enumerate(DETAIL_COLUMNS)}


def _client():
    from utils.rma_gsheet import get_client
    return get_client()


def get_detail_sheet():
    ss     = _client().open_by_key(SPREADSHEET_ID)
    titles = [ws.title for ws in ss.worksheets()]
    need   = len(DETAIL_COLUMNS) + 5
    if DETAIL_SHEET_NAME in titles:
        ws = ss.worksheet(DETAIL_SHEET_NAME)
        if ws.col_count < len(DETAIL_COLUMNS):
            ws.resize(cols=need)
        return ws
    ws = ss.add_worksheet(title=DETAIL_SHEET_NAME, rows=5000, cols=need)
    ws.insert_row(DETAIL_COLUMNS, 1)
    return ws


def ensure_detail_headers(sheet):
    if sheet.col_count < len(DETAIL_COLUMNS):
        sheet.resize(cols=len(DETAIL_COLUMNS) + 5)
    first = sheet.row_values(1)
    if not first or first[0] != "子件編號":
        sheet.insert_row(DETAIL_COLUMNS, 1)
    elif len(first) < len(DETAIL_COLUMNS):
        sheet.update("A1", [DETAIL_COLUMNS])


def _find_row(sheet, detail_id: str) -> int:
    col_vals = sheet.col_values(DETAIL_COL["子件編號"])
    for i, val in enumerate(col_vals):
        if val == detail_id:
            return i + 1
    return -1


def _gen_detail_id(master_id: str, seq: int) -> str:
    return f"{master_id}-{str(seq).zfill(2)}"


# ── CRUD ─────────────────────────────────────────────────────────────────────

def append_detail(master_id: str, seq: int, data: dict) -> str:
    """建立單筆子件，回傳 detail_id。"""
    sheet     = get_detail_sheet()
    ensure_detail_headers(sheet)
    detail_id = _gen_detail_id(master_id, seq)
    row = [
        detail_id, master_id,
        data.get("motor_sn",    ""),
        data.get("model",       ""),
        data.get("fault_type",  ""),
        data.get("crash",       "否"),
        data.get("flight_hours", 0),
        data.get("fault_desc",  ""),
        "",           # 故障照片連結
        "待收件",     # 維修狀態
        data.get("repair_type", ""),
        data.get("note",        ""),
        "",           # 內部-技術檢測
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    return detail_id


def append_batch_details(master_id: str, shared: dict, motors: list) -> list:
    """批次建立子件，回傳 [detail_id, ...]。"""
    sheet      = get_detail_sheet()
    ensure_detail_headers(sheet)
    detail_ids = []
    for seq, motor in enumerate(motors, start=1):
        detail_id = _gen_detail_id(master_id, seq)
        row = [
            detail_id, master_id,
            motor.get("motor_sn",  ""),
            motor.get("model",     shared.get("model",  "")),
            motor.get("fault_type",shared.get("fault_type","")),
            shared.get("crash",    "否"),
            shared.get("flight_hours", 0),
            shared.get("fault_desc",""),
            "",
            "待收件",
            shared.get("repair_type",""),
            shared.get("note",      ""),
            "",
        ]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        detail_ids.append(detail_id)
    return detail_ids


def load_all_details():
    import pandas as pd
    records = get_detail_sheet().get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(columns=DETAIL_COLUMNS)


def load_details_by_master(master_id: str):
    import pandas as pd
    df = load_all_details()
    if df.empty or "主單編號" not in df.columns:
        return pd.DataFrame(columns=DETAIL_COLUMNS)
    return df[df["主單編號"] == master_id].reset_index(drop=True)


def get_detail_by_id(detail_id: str) -> dict:
    sheet   = get_detail_sheet()
    row_num = _find_row(sheet, detail_id)
    if row_num == -1:
        return {}
    values = sheet.row_values(row_num)
    return {col: (values[i] if i < len(values) else "") for i, col in enumerate(DETAIL_COLUMNS)}


def update_detail_status(detail_id: str, new_status: str,
                         tech_note: str = "", tech_judgment: str = "") -> bool:
    import gspread.utils as gu
    sheet   = get_detail_sheet()
    row_num = _find_row(sheet, detail_id)
    if row_num == -1:
        return False
    updates = [{"range": gu.rowcol_to_a1(row_num, DETAIL_COL["維修狀態"]),
                "values": [[new_status]]}]
    if tech_note:
        updates.append({"range": gu.rowcol_to_a1(row_num, DETAIL_COL["內部-技術檢測"]),
                        "values": [[tech_note]]})
    if tech_judgment:
        updates.append({"range": gu.rowcol_to_a1(row_num, DETAIL_COL["技術判定"]),
                        "values": [[tech_judgment]]})
    sheet.batch_update(updates, value_input_option="USER_ENTERED")
    return True


def update_detail_detection(detail_id: str, data: dict) -> bool:
    """技術檢測結果批次寫入（支援自定義項目動態新增欄位）。"""
    import gspread.utils as gu
    sheet = get_detail_sheet()
    ensure_detail_headers(sheet)
    row_num = _find_row(sheet, detail_id)
    if row_num == -1:
        return False

    headers = sheet.row_values(1)
    col_map = {h.strip(): i + 1 for i, h in enumerate(headers) if h.strip()}

    # 自動新增缺少的自定義欄位
    missing = [k for k in data if k not in col_map]
    if missing:
        new_cnt = len(headers) + len(missing) + 5
        if sheet.col_count < new_cnt:
            sheet.resize(cols=new_cnt)
        next_col = len([h for h in headers if h.strip()]) + 1
        for col_name in missing:
            while next_col <= len(headers) and headers[next_col - 1].strip():
                next_col += 1
            padded = headers + [""] * max(0, next_col - len(headers))
            if next_col > len(padded):
                padded.extend([""] * (next_col - len(padded)))
            padded[next_col - 1] = col_name
            col_map[col_name]    = next_col
            next_col += 1
            headers = padded
        sheet.update("A1", [headers])

    updates = [
        {"range": gu.rowcol_to_a1(row_num, col_map[col]), "values": [[str(val)]]}
        for col, val in data.items()
        if col in col_map
    ]
    if updates:
        sheet.batch_update(updates, value_input_option="USER_ENTERED")
    return True


def update_detail_photos(detail_id: str, photo_urls: list) -> bool:
    sheet   = get_detail_sheet()
    row_num = _find_row(sheet, detail_id)
    if row_num == -1:
        return False
    sheet.update_cell(row_num, DETAIL_COL["故障照片連結"], ", ".join(photo_urls))
    return True


def get_detail_photos(detail_id: str) -> list:
    sheet   = get_detail_sheet()
    row_num = _find_row(sheet, detail_id)
    if row_num == -1:
        return []
    val = sheet.cell(row_num, DETAIL_COL["故障照片連結"]).value or ""
    return [u.strip() for u in val.split(",") if u.strip()]


def delete_detail(detail_id: str, hard: bool = False) -> bool:
    sheet   = get_detail_sheet()
    row_num = _find_row(sheet, detail_id)
    if row_num == -1:
        return False
    if hard:
        sheet.delete_rows(row_num)
    else:
        sheet.update_cell(row_num, DETAIL_COL["維修狀態"], "已取消")
    return True


def batch_update_details(detail_ids: list, data: dict) -> int:
    """
    批次更新多筆子件的相同欄位。
    只做 2 次讀取（標題列 + ID 欄）+ 1 次批次寫入。
    回傳實際更新筆數。
    """
    import gspread.utils as gu
    sheet   = get_detail_sheet()
    headers = sheet.row_values(1)
    col_map = {h.strip(): i + 1 for i, h in enumerate(headers) if h.strip()}

    # 讀取全部 ID 欄，建立 id→row_num 字典
    id_col_vals = sheet.col_values(DETAIL_COL["子件編號"])
    id_set      = set(detail_ids)
    row_map     = {val: i + 1 for i, val in enumerate(id_col_vals) if val in id_set}

    all_updates = []
    for did in detail_ids:
        row_num = row_map.get(did)
        if row_num is None:
            continue
        for col, val in data.items():
            if col in col_map:
                all_updates.append({
                    "range":  gu.rowcol_to_a1(row_num, col_map[col]),
                    "values": [[str(val)]],
                })

    if all_updates:
        sheet.batch_update(all_updates, value_input_option="USER_ENTERED")
    return len(row_map)
