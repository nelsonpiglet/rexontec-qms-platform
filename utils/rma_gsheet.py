"""
REXONTEC 力科 — 維修保養系統 Google Sheet 連線工具
試算表：返廠清單
"""
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime

SPREADSHEET_ID = "1OksPtvaabwXIMdO8gPA7A6s6oHpLy_Liewcc_pyOmA8"
SHEET_NAME     = "返廠清單"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLUMNS = [
    "編號", "馬達序號", "產品型號", "故障類別",
    "是否曾撞擊/墜機", "飛行總時數(估計)", "故障詳細描述",
    "內部-技術檢測", "內部-保固判定", "RMA編號", "收件日期",
    "客戶公司", "聯絡人", "聯絡電話", "客戶Email",
    "馬達數量", "維修類型", "維修狀態", "優先等級", "備註",
    "故障照片連結",
    # ─── 技術檢測欄位 ────────────────────────────────
    "S1-外殼撞傷", "S1-軸心歪斜", "S1-沙土侵入", "S1-螺絲裂痕", "S1-正常",
    "S2-異音", "S2-卡頓", "S2-軸承鬆動", "S2-正常",
    "S3-AB阻值", "S3-BC阻值", "S3-CA阻值", "S3-線圈異常",
    "S4-高震動", "S4-高溫", "S4-無法啟動", "S4-正常",
    "S5-線圈燒毀", "S5-磁鐵脫落", "S5-生鏽", "S5-正常",
    "最終判定", "保固判定", "維修方式", "是否報廢", "五步檢測時間",
    # ─── 分離技術判定欄位 ─────────────────────────
    "技術判定", "是否可維修", "維修成本評估",
]

@st.cache_resource(show_spinner="連線維修系統 Google Sheet 中...")
def get_client():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES
        )
    except (KeyError, FileNotFoundError):
        creds = Credentials.from_service_account_file(
            "service_account.json", scopes=SCOPES
        )
    return gspread.authorize(creds)


def get_sheet():
    client    = get_client()
    ss        = client.open_by_key(SPREADSHEET_ID)
    titles    = [ws.title for ws in ss.worksheets()]
    need_cols = len(COLUMNS) + 5          # 多 5 欄緩衝，未來擴欄不用改
    if SHEET_NAME in titles:
        ws = ss.worksheet(SHEET_NAME)
        # 若現有欄數不足（舊表），自動擴欄
        if ws.col_count < len(COLUMNS):
            ws.resize(cols=need_cols)
        return ws
    ws = ss.add_worksheet(title=SHEET_NAME, rows=2000, cols=need_cols)
    ws.insert_row(COLUMNS, 1)
    get_client.clear()
    return ws


def ensure_headers(sheet):
    # 先確保欄數足夠，避免 exceeds grid limits
    if sheet.col_count < len(COLUMNS):
        sheet.resize(cols=len(COLUMNS) + 5)
    first = sheet.row_values(1)
    if not first or first[0] != "編號":
        sheet.insert_row(COLUMNS, 1)
    elif len(first) < len(COLUMNS):
        # 一次批次更新整列標題，比 update_cell 逐欄快很多
        sheet.update("A1", [COLUMNS])


def generate_rma_id(sheet) -> str:
    total_rows = len(sheet.get_all_values())
    seq  = total_rows
    year = datetime.now().year
    return f"RMA-{year}-{str(seq).zfill(4)}"


COL_INDEX  = {col: i + 1 for i, col in enumerate(COLUMNS)}
STATUS_COL = COL_INDEX["維修狀態"]
NOTE_COL   = COL_INDEX["備註"]
TECH_COL   = COL_INDEX["內部-技術檢測"]
RMA_COL    = COL_INDEX["RMA編號"]
PHOTO_COL  = COL_INDEX["故障照片連結"]


def find_row_by_rma(sheet, rma_id: str) -> int:
    col_vals = sheet.col_values(RMA_COL)
    for i, val in enumerate(col_vals):
        if val == rma_id:
            return i + 1
    return -1


def append_case(data: dict) -> str:
    sheet  = get_sheet()
    ensure_headers(sheet)
    rma_id  = generate_rma_id(sheet)
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    seq     = len(sheet.get_all_values())
    row = [
        seq, data["motor_sn"], data["model"], data["fault_type"],
        data["crash"], data["flight_hours"], data["fault_desc"],
        "", "", rma_id, now_str,
        data["company"], data["contact"], data["phone"], data["email"],
        data["qty"], data["repair_type"], "待收件", data["priority"], data["note"],
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    return rma_id


def append_batch_cases(shared: dict, motors: list) -> list:
    sheet   = get_sheet()
    ensure_headers(sheet)
    rma_ids = []
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    for motor in motors:
        rma_id = generate_rma_id(sheet)
        seq    = len(sheet.get_all_values())
        row = [
            seq, motor.get("motor_sn", ""),
            motor.get("model", shared.get("model", "")),
            motor.get("fault_type", shared.get("fault_type", "")),
            shared.get("crash", "否"), shared.get("flight_hours", 0),
            shared.get("fault_desc", ""), "", "", rma_id, now_str,
            shared.get("company", ""), shared.get("contact", ""),
            shared.get("phone", ""), shared.get("email", ""),
            1, shared.get("repair_type", ""), "待收件",
            shared.get("priority", "P3"), shared.get("note", ""),
        ]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        rma_ids.append(rma_id)
    return rma_ids


def load_all_cases():
    import pandas as pd
    sheet   = get_sheet()
    records = sheet.get_all_records()
    if records:
        return pd.DataFrame(records)
    return pd.DataFrame(columns=COLUMNS)


def update_status(rma_id: str, new_status: str, tech_note: str = "", tech_judgment: str = "") -> bool:
    sheet   = get_sheet()
    row_num = find_row_by_rma(sheet, rma_id)
    if row_num == -1:
        return False
    sheet.update_cell(row_num, STATUS_COL, new_status)
    if tech_note:
        sheet.update_cell(row_num, TECH_COL, tech_note)
    if tech_judgment:
        headers = sheet.row_values(1)
        col_map = {h.strip(): i + 1 for i, h in enumerate(headers) if h.strip()}
        if "技術判定" in col_map:
            sheet.update_cell(row_num, col_map["技術判定"], tech_judgment)
    return True


def update_photos(rma_id: str, photo_urls: list) -> bool:
    sheet   = get_sheet()
    row_num = find_row_by_rma(sheet, rma_id)
    if row_num == -1:
        return False
    sheet.update_cell(row_num, PHOTO_COL, ", ".join(photo_urls))
    return True


def get_photos(rma_id: str) -> list:
    sheet   = get_sheet()
    row_num = find_row_by_rma(sheet, rma_id)
    if row_num == -1:
        return []
    val = sheet.cell(row_num, PHOTO_COL).value or ""
    return [u.strip() for u in val.split(",") if u.strip()]


def delete_case(rma_id: str, hard: bool = False) -> bool:
    sheet   = get_sheet()
    row_num = find_row_by_rma(sheet, rma_id)
    if row_num == -1:
        return False
    if hard:
        sheet.delete_rows(row_num)
    else:
        sheet.update_cell(row_num, STATUS_COL, "已取消")
    return True


def update_detection(rma_id: str, data: dict) -> bool:
    """技術檢測結果批次寫入（支援自定義項目動態新增欄位）"""
    import gspread.utils as gu
    sheet = get_sheet()
    ensure_headers(sheet)
    row_num = find_row_by_rma(sheet, rma_id)
    if row_num == -1:
        return False
    headers = sheet.row_values(1)
    col_map = {h.strip(): i + 1 for i, h in enumerate(headers) if h.strip()}

    # ── 自動新增缺少的欄位（自定義項目第一次寫入時）──────────
    missing = [k for k in data if k not in col_map]
    if missing:
        new_col_count = len(headers) + len(missing) + 5
        if sheet.col_count < new_col_count:
            sheet.resize(cols=new_col_count)
        next_col = len([h for h in headers if h.strip()]) + 1
        for col_name in missing:
            # 找到第一個空白欄填入
            while next_col <= len(headers) and headers[next_col - 1].strip():
                next_col += 1
            headers_padded = headers + [""] * max(0, next_col - len(headers))
            if next_col > len(headers_padded):
                headers_padded.extend([""] * (next_col - len(headers_padded)))
            headers_padded[next_col - 1] = col_name
            col_map[col_name] = next_col
            next_col += 1
            headers = headers_padded
        sheet.update("A1", [headers])

    updates = [
        {"range": gu.rowcol_to_a1(row_num, col_map[col]), "values": [[str(val)]]}
        for col, val in data.items()
        if col in col_map
    ]
    if updates:
        sheet.batch_update(updates, value_input_option="USER_ENTERED")
    return True


def get_case_by_rma(rma_id: str) -> dict:
    sheet   = get_sheet()
    row_num = find_row_by_rma(sheet, rma_id)
    if row_num == -1:
        return {}
    values = sheet.row_values(row_num)
    return {col: (values[i] if i < len(values) else "") for i, col in enumerate(COLUMNS)}
