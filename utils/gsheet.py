"""
REXONTEC OQC — Google Sheet 連線與讀寫
試算表需含兩個工作表：OQC_電調 / OQC_馬達
"""

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# ── 請填入你的 Google Sheet ID ──────────────────────
SPREADSHEET_ID = "1JU9nhimkhEMYeu1hzQGutpg1EmnmRMbzTxCevjMxYwU"
# ────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_ESC   = "OQC_電調"
SHEET_MOTOR = "OQC_馬達"
SHEET_IQC   = "IQC"

# ─────────────────────────────────────────────────────
# 各表的欄位定義
# ─────────────────────────────────────────────────────
COLS_COMMON = [
    "記錄編號",       # A
    "建立時間",       # B
    "產品類型",       # C
    "機種",           # D
    "料號",           # E
    "客戶名稱",       # F
    "批號",           # G
    "序號範圍",       # H
    "本批數量",       # I
    "抽驗數量",       # J
    "檢驗日期",       # K
    "檢驗員",         # L
    "主管(品保)",     # M
    "總判定",         # N  PASS / FAIL / 待審
    "CR_不良數",      # O
    "MA_不良數",      # P
    "MI_不良數",      # Q
    "NG_項目摘要",    # R
    "備註",           # S
    "照片連結",       # T
    "明細JSON",       # U  per-unit results
]

COLS_ESC = COLS_COMMON + [
    "製造組別",       # V
    "製造編號",       # W
]

COLS_MOTOR = COLS_COMMON  # same


# ─────────────────────────────────────────────────────
# 連線（快取）
# ─────────────────────────────────────────────────────
@st.cache_resource(show_spinner="連線 Google Sheet 中…")
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


def _open_sheet(sheet_name: str, columns: list):
    """取得工作表，若不存在自動建立並寫入標題"""
    client = get_client()
    ss     = client.open_by_key(SPREADSHEET_ID)
    titles = [ws.title for ws in ss.worksheets()]
    if sheet_name not in titles:
        ws = ss.add_worksheet(title=sheet_name, rows=2000, cols=len(columns) + 2)
        ws.insert_row(columns, 1)
        return ws
    return ss.worksheet(sheet_name)


def _ensure_headers(ws, columns: list):
    first = ws.row_values(1)
    if not first or first[0] != columns[0]:
        ws.insert_row(columns, 1)
    elif len(first) < len(columns):
        for i in range(len(first), len(columns)):
            ws.update_cell(1, i + 1, columns[i])


def _gen_id(ws, prefix: str) -> str:
    total = len(ws.get_all_values())  # 含標題
    year  = datetime.now().year
    return f"OQC-{prefix}-{year}-{str(total).zfill(4)}"


# ─────────────────────────────────────────────────────
# 公開 API
# ─────────────────────────────────────────────────────
def append_oqc_record(product_type: str, header: dict,
                      results: dict, ng_summary: str,
                      photo_urls: list[str], note: str) -> str:
    """
    將一筆 OQC 記錄寫入對應的 Google Sheet 工作表。

    product_type : "esc" | "motor"
    header       : 表頭欄位 dict
    results      : {item_id: {unit_sn: {"result":"PASS"|"FAIL"|"─", "value": float|None}}}
    ng_summary   : NG 項目文字摘要
    photo_urls   : Google Drive 照片 URL 列表
    note         : 備註
    回傳: 記錄編號 (str)
    """
    is_esc = (product_type == "esc")
    sheet_name = SHEET_ESC if is_esc else SHEET_MOTOR
    columns    = COLS_ESC  if is_esc else COLS_MOTOR

    ws = _open_sheet(sheet_name, columns)
    _ensure_headers(ws, columns)

    rec_id  = _gen_id(ws, "ESC" if is_esc else "MD")
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")

    # 統計不良
    from utils.inspection_data import get_sections
    sections = get_sections(product_type)
    cr_ng, ma_ng, mi_ng = 0, 0, 0
    for sec in sections:
        for item in sec["items"]:
            unit_res = results.get(item["id"], {})
            if any(v.get("result") == "FAIL" for v in unit_res.values()):
                g = item["grade"]
                if g == "CR": cr_ng += 1
                elif g == "MA": ma_ng += 1
                else: mi_ng += 1

    if cr_ng > 0 or ma_ng > 0:
        verdict = "FAIL"
    elif mi_ng > 0:
        verdict = "FAIL(MI)"
    elif _all_judged(results, sections):
        verdict = "PASS"
    else:
        verdict = "待審"

    detail_json = json.dumps(results, ensure_ascii=False)

    row_common = [
        rec_id,                         # 記錄編號
        now_str,                        # 建立時間
        "電調" if is_esc else "馬達",   # 產品類型
        header.get("model", ""),        # 機種
        header.get("part_no", ""),      # 料號
        header.get("customer", ""),     # 客戶名稱
        header.get("batch_no", ""),     # 批號
        header.get("serial_range", ""), # 序號範圍
        header.get("qty", ""),          # 本批數量
        header.get("sample_qty", ""),   # 抽驗數量
        header.get("date", ""),         # 檢驗日期
        header.get("inspector", ""),    # 檢驗員
        header.get("supervisor", ""),   # 主管
        verdict,                        # 總判定
        cr_ng, ma_ng, mi_ng,            # CR/MA/MI 不良數
        ng_summary,                     # NG 項目摘要
        note,                           # 備註
        ", ".join(photo_urls),          # 照片連結
        detail_json,                    # 明細JSON
    ]

    if is_esc:
        row_common += [
            header.get("mfg_group", ""),
            header.get("mfg_order_no", ""),
        ]

    ws.append_row(row_common, value_input_option="USER_ENTERED")
    return rec_id


COLS_IQC = [
    "記錄編號",       # A
    "建立時間",       # B
    "零件ID",         # C
    "零件名稱",       # D
    "料號",           # E
    "供應商",         # F
    "批號",           # G
    "採購單號",       # H
    "進料數量",       # I
    "抽樣數量",       # J
    "檢驗日期",       # K
    "IQC檢驗員",      # L
    "總判定",         # M
    "CR_不良數",      # N
    "MA_不良數",      # O
    "MI_不良數",      # P
    "NG_項目摘要",    # Q
    "備註",           # R
    "明細JSON",       # S
]


def append_iqc_record(part: dict, header: dict, results: dict) -> str:
    """
    將一筆 IQC 進料檢驗記錄寫入 Google Sheet「IQC」工作表。

    part    : iqc_data 零件字典
    header  : {part, vendor, lot, po, qty, sample, date, inspector, ...}
    results : {item_id: {"result": "pass"|"fail"|None, "inputs": {...}, "remark": ""}}
    回傳: 記錄編號 (str)
    """
    ws = _open_sheet(SHEET_IQC, COLS_IQC)
    _ensure_headers(ws, COLS_IQC)

    # 產生 IQC 專用編號
    total  = len(ws.get_all_values())
    year   = datetime.now().year
    rec_id = f"IQC-{part.get('id','PART')}-{year}-{str(total).zfill(4)}"
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")

    # 展開所有項目
    all_items = [
        item
        for sec in part.get("sections", [])
        for item in sec.get("items", [])
    ]

    cr_ng = sum(1 for it in all_items
                if it["grade"] == "CR"
                and results.get(it["id"], {}).get("result") == "fail")
    ma_ng = sum(1 for it in all_items
                if it["grade"] == "MA"
                and results.get(it["id"], {}).get("result") == "fail")
    mi_ng = sum(1 for it in all_items
                if it["grade"] == "MI"
                and results.get(it["id"], {}).get("result") == "fail")

    if cr_ng > 0 or ma_ng > 0:
        verdict = "FAIL"
    elif mi_ng > 0:
        verdict = "FAIL(MI)"
    else:
        # 確認所有項目都判定了才算 PASS
        judged = all(
            results.get(it["id"], {}).get("result") in ("pass", "fail")
            for it in all_items
        )
        verdict = "PASS" if judged else "待審"

    ng_names = [
        it["name"] for it in all_items
        if results.get(it["id"], {}).get("result") == "fail"
    ]
    ng_summary = "；".join(ng_names)

    row = [
        rec_id,
        now_str,
        part.get("id", ""),
        header.get("part") or part.get("name", ""),
        part.get("pn", ""),
        header.get("vendor") or part.get("vendor", ""),
        header.get("lot", ""),
        header.get("po", ""),
        header.get("qty", 0),
        header.get("sample", 0),
        header.get("date", ""),
        header.get("inspector", ""),
        verdict,
        cr_ng, ma_ng, mi_ng,
        ng_summary,
        "",                                          # 備註（後續可擴充）
        json.dumps(results, ensure_ascii=False),
    ]

    ws.append_row(row, value_input_option="USER_ENTERED")
    return rec_id


def load_oqc_records(product_type: str):
    """讀取所有 OQC 記錄，回傳 DataFrame"""
    import pandas as pd
    is_esc = (product_type == "esc")
    sheet_name = SHEET_ESC if is_esc else SHEET_MOTOR
    columns    = COLS_ESC  if is_esc else COLS_MOTOR
    try:
        ws = _open_sheet(sheet_name, columns)
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=columns)
    except Exception:
        return pd.DataFrame(columns=columns)


def load_iqc_records():
    """讀取所有 IQC 記錄，回傳 DataFrame"""
    import pandas as pd
    try:
        ws = _open_sheet(SHEET_IQC, COLS_IQC)
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=COLS_IQC)
    except Exception:
        return pd.DataFrame(columns=COLS_IQC)


# ─────────────────────────────────────────────────────
# 輔助
# ─────────────────────────────────────────────────────
def _all_judged(results: dict, sections: list) -> bool:
    for sec in sections:
        for item in sec["items"]:
            unit_res = results.get(item["id"], {})
            if not unit_res:
                return False
            if any(v.get("result") == "─" for v in unit_res.values()):
                return False
    return True
