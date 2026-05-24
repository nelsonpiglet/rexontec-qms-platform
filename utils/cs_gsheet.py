"""
REXONTEC 力科 — 客訴與8D管理系統 Google Sheet 連線工具
試算表：客訴清單 / 8D記錄
"""
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# ── 使用與維修系統同一試算表（不同工作表）──────────
# 若需獨立試算表，請建立新的 Google Sheet 並更換此 ID
SPREADSHEET_ID = "1OksPtvaabwXIMdO8gPA7A6s6oHpLy_Liewcc_pyOmA8"
CS_SHEET_NAME  = "客訴清單"
D8_SHEET_NAME  = "8D記錄"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── 客訴欄位 ──────────────────────────────────────
CS_COLUMNS = [
    "編號", "客訴編號", "客戶名稱", "機型", "SN/Lot", "飛行時數",
    "客訴日期", "客訴類型", "客訴等級", "是否重大客訴",
    "客訴描述", "照片連結", "影片連結", "負責人",
    "流程狀態", "8D編號", "建立日期", "結案日期", "備註",
]

# ── 8D 欄位 ───────────────────────────────────────
D8_COLUMNS = [
    "編號", "8D編號", "客訴編號",
    "D1_團隊成員", "D2_問題描述", "D3_臨時對策",
    "D4_根因分析", "D5_永久改善", "D6_改善驗證",
    "D7_預防措施", "D8_結案表揚",
    "CAPA狀態", "驗證附件連結", "熱像圖連結", "測試資料連結",
    "建立日期", "結案日期", "負責人",
    # v2 擴充欄位（附後確保向下相容）
    "照片連結", "M/O編號", "批量", "出貨日期",
    "抱怨方式", "首發再發", "核准人", "審核人", "經辦人", "SOP參考",
]

CS_STATUS_LIST = [
    "客訴建立", "品保確認", "RD分析", "原因分析",
    "8D開立", "改善驗證", "客戶回覆", "結案", "已取消",
]

DONE_STATUS = {"結案", "已取消"}
OVERDUE_DAYS = {"客訴建立": 1, "品保確認": 3, "RD分析": 7,
                "原因分析": 14, "8D開立": 3, "改善驗證": 14,
                "客戶回覆": 7, "結案": 0}


@st.cache_resource(show_spinner="連線客訴系統 Google Sheet...")
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


def _get_or_create_sheet(sheet_name: str, columns: list):
    client = get_client()
    ss     = client.open_by_key(SPREADSHEET_ID)
    titles = [ws.title for ws in ss.worksheets()]
    if sheet_name in titles:
        ws = ss.worksheet(sheet_name)
    else:
        ws = ss.add_worksheet(title=sheet_name, rows=2000, cols=len(columns) + 2)
        ws.insert_row(columns, 1)
        get_client.clear()
    return ws


def get_cs_sheet():
    return _get_or_create_sheet(CS_SHEET_NAME, CS_COLUMNS)


def get_d8_sheet():
    return _get_or_create_sheet(D8_SHEET_NAME, D8_COLUMNS)


def ensure_headers(sheet, columns: list):
    first = sheet.row_values(1)
    if not first or first[0] != columns[0]:
        sheet.insert_row(columns, 1)
    elif len(first) < len(columns):
        for i in range(len(first), len(columns)):
            sheet.update_cell(1, i + 1, columns[i])


def _generate_id(sheet, prefix: str) -> str:
    total_rows = len(sheet.get_all_values())
    seq  = total_rows
    year = datetime.now().year
    return f"{prefix}-{year}-{str(seq).zfill(4)}"


def generate_cs_id(sheet) -> str:
    return _generate_id(sheet, "CS")


def generate_d8_id(sheet) -> str:
    return _generate_id(sheet, "8D")


# ── 客訴 CRUD ────────────────────────────────────

CS_COL = {col: i + 1 for i, col in enumerate(CS_COLUMNS)}
D8_COL = {col: i + 1 for i, col in enumerate(D8_COLUMNS)}


def _find_row(sheet, col_idx: int, target: str) -> int:
    vals = sheet.col_values(col_idx)
    for i, v in enumerate(vals):
        if v == target:
            return i + 1
    return -1


def append_complaint(data: dict) -> str:
    sheet  = get_cs_sheet()
    ensure_headers(sheet, CS_COLUMNS)
    cs_id   = generate_cs_id(sheet)
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    seq     = len(sheet.get_all_values())
    row = [
        seq, cs_id,
        data.get("customer", ""),
        data.get("model", ""),
        data.get("sn_lot", ""),
        data.get("flight_hours", ""),
        data.get("cs_date", ""),
        data.get("cs_type", ""),
        data.get("cs_level", ""),
        data.get("is_major", "否"),
        data.get("cs_desc", ""),
        data.get("photo_url", ""),
        data.get("video_url", ""),
        data.get("owner", ""),
        "客訴建立",
        "",       # 8D編號
        now_str,  # 建立日期
        "",       # 結案日期
        data.get("note", ""),
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    return cs_id


def load_all_complaints() -> pd.DataFrame:
    sheet   = get_cs_sheet()
    records = sheet.get_all_records()
    if records:
        return pd.DataFrame(records)
    return pd.DataFrame(columns=CS_COLUMNS)


def get_complaint_by_id(cs_id: str) -> dict:
    sheet   = get_cs_sheet()
    row_num = _find_row(sheet, CS_COL["客訴編號"], cs_id)
    if row_num == -1:
        return {}
    values = sheet.row_values(row_num)
    return {col: (values[i] if i < len(values) else "") for i, col in enumerate(CS_COLUMNS)}


def update_cs_status(cs_id: str, new_status: str, note: str = "") -> bool:
    sheet   = get_cs_sheet()
    row_num = _find_row(sheet, CS_COL["客訴編號"], cs_id)
    if row_num == -1:
        return False
    sheet.update_cell(row_num, CS_COL["流程狀態"], new_status)
    if new_status in DONE_STATUS:
        now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
        sheet.update_cell(row_num, CS_COL["結案日期"], now_str)
    if note:
        sheet.update_cell(row_num, CS_COL["備註"], note)
    return True


def link_8d_to_cs(cs_id: str, d8_id: str) -> bool:
    sheet   = get_cs_sheet()
    row_num = _find_row(sheet, CS_COL["客訴編號"], cs_id)
    if row_num == -1:
        return False
    sheet.update_cell(row_num, CS_COL["8D編號"], d8_id)
    return True


# ── 8D CRUD ──────────────────────────────────────

def append_8d(cs_id: str, data: dict) -> str:
    sheet   = get_d8_sheet()
    ensure_headers(sheet, D8_COLUMNS)
    d8_id   = generate_d8_id(sheet)
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    seq     = len(sheet.get_all_values())
    row = [
        seq, d8_id, cs_id,
        data.get("d1", ""), data.get("d2", ""), data.get("d3", ""),
        data.get("d4", ""), data.get("d5", ""), data.get("d6", ""),
        data.get("d7", ""), data.get("d8", ""),
        data.get("capa_status", "進行中"),
        data.get("attach_url", ""),
        data.get("thermal_url", ""),
        data.get("test_url", ""),
        now_str, "", data.get("owner", ""),
        # v2 擴充欄位
        data.get("photo_url", ""),
        data.get("mo_number", ""),
        data.get("batch", ""),
        data.get("ship_date", ""),
        data.get("complaint_method", ""),
        data.get("first_recur", ""),
        data.get("approver", ""),
        data.get("reviewer", ""),
        data.get("handler", ""),
        data.get("sop_ref", ""),
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    link_8d_to_cs(cs_id, d8_id)
    return d8_id


def load_all_8d() -> pd.DataFrame:
    sheet   = get_d8_sheet()
    records = sheet.get_all_records()
    if records:
        return pd.DataFrame(records)
    return pd.DataFrame(columns=D8_COLUMNS)


def get_8d_by_cs(cs_id: str) -> dict:
    sheet   = get_d8_sheet()
    row_num = _find_row(sheet, D8_COL["客訴編號"], cs_id)
    if row_num == -1:
        return {}
    values = sheet.row_values(row_num)
    return {col: (values[i] if i < len(values) else "") for i, col in enumerate(D8_COLUMNS)}


def get_8d_by_id(d8_id: str) -> dict:
    sheet   = get_d8_sheet()
    row_num = _find_row(sheet, D8_COL["8D編號"], d8_id)
    if row_num == -1:
        return {}
    values = sheet.row_values(row_num)
    return {col: (values[i] if i < len(values) else "") for i, col in enumerate(D8_COLUMNS)}


def update_8d(d8_id: str, data: dict) -> bool:
    sheet   = get_d8_sheet()
    row_num = _find_row(sheet, D8_COL["8D編號"], d8_id)
    if row_num == -1:
        return False
    field_map = [
        ("d1","D1_團隊成員"), ("d2","D2_問題描述"), ("d3","D3_臨時對策"),
        ("d4","D4_根因分析"), ("d5","D5_永久改善"), ("d6","D6_改善驗證"),
        ("d7","D7_預防措施"), ("d8","D8_結案表揚"),
        ("capa_status","CAPA狀態"), ("owner","負責人"),
        ("attach_url","驗證附件連結"), ("thermal_url","熱像圖連結"),
        ("test_url","測試資料連結"),
        # v2 欄位
        ("photo_url","照片連結"), ("mo_number","M/O編號"),
        ("batch","批量"), ("ship_date","出貨日期"),
        ("complaint_method","抱怨方式"), ("first_recur","首發再發"),
        ("approver","核准人"), ("reviewer","審核人"),
        ("handler","經辦人"), ("sop_ref","SOP參考"),
    ]
    for field, col_name in field_map:
        if field in data and col_name in D8_COL:
            sheet.update_cell(row_num, D8_COL[col_name], data[field])
    if data.get("capa_status") == "完成":
        sheet.update_cell(row_num, D8_COL["結案日期"],
                          datetime.now().strftime("%Y/%m/%d %H:%M"))
    return True
