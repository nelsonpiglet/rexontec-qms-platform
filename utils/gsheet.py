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

SHEET_ESC        = "OQC_電調"
SHEET_MOTOR      = "OQC_馬達"
SHEET_IQC        = "IQC"
SHEET_IPQC       = "IPQC"
SHEET_SQM_DEFECT = "SQM_異常登錄"
SHEET_SQM_SCAR   = "SQM_SCAR"

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
    """
    取得工作表，若不存在自動建立並寫入標題。
    若已存在但欄數不足（因欄位定義增加），自動擴欄。
    """
    client = get_client()
    ss     = client.open_by_key(SPREADSHEET_ID)
    titles = [ws.title for ws in ss.worksheets()]
    need_cols = len(columns) + 2          # 保留 2 欄緩衝
    if sheet_name not in titles:
        ws = ss.add_worksheet(title=sheet_name, rows=2000, cols=need_cols)
        ws.insert_row(columns, 1)
        return ws
    ws = ss.worksheet(sheet_name)
    # 若現有欄數不足，自動擴展（不破壞既有資料）
    if ws.col_count < len(columns):
        ws.resize(cols=need_cols)
    return ws


def _ensure_headers(ws, columns: list):
    """確保工作表第一列為正確標題，欄數不足時先擴欄再補欄位名稱。
    使用完整欄位比對，任何欄位名稱不符時一次批次更新整列標題。
    """
    # 先確保欄數足夠，避免 exceeds grid limits 錯誤
    if ws.col_count < len(columns):
        ws.resize(cols=len(columns) + 2)
    first = ws.row_values(1)
    # 完整比對所有欄位名稱（非僅第一欄），確保欄位改版後正確更新
    if not first:
        ws.insert_row(columns, 1)
    elif list(first[:len(columns)]) != list(columns):
        # 一次批次更新整列標題，覆蓋舊名稱
        ws.update("A1", [columns])


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


COLS_IPQC = [
    "記錄編號",     # A
    "建立時間",     # B
    "機種ID",       # C
    "機種名稱",     # D
    "日期",         # E
    "製造編號",     # F
    "本批數量",     # G
    "檢查件數",     # H
    "不良件數",     # I
    "不良率",       # J
    "巡查員",       # K
    "巡檢類型",     # L  巡檢 / 首台FAI
    "總判定",       # M  OK / NG
    "NG工序數",     # N
    "CR_NG數",      # O
    "MA_NG數",      # P
    "MI_NG數",      # Q
    "NG_工序摘要",  # R
    "製造確認",     # S
    "品保確認",     # T
    "主管審核",     # U
    "明細JSON",     # V
]


def append_ipqc_record(header: dict, model: dict,
                       record_type: str, results: dict) -> str:
    """
    儲存一筆 IPQC 巡檢或首台FAI 記錄。

    header      : {model_id, model_name, date, mfg_no, batch_qty, inspect_qty,
                   defect_qty, defect_rate, inspector, mfg_sig, qc_sig, mgr_sig}
    model       : 完整 IPQC model dict（取站別 / 項目 / 等級）
    record_type : "patrol" | "fai"
    results     : patrol → {st_id: {"0": {am, pm, note, action}, ...}}
                  fai    → {st_id: {"0": {result, measure, note}, ...}}
    回傳: 記錄編號
    """
    ws = _open_sheet(SHEET_IPQC, COLS_IPQC)
    _ensure_headers(ws, COLS_IPQC)

    total   = len(ws.get_all_values())
    year    = datetime.now().year
    pfx     = "IPQC-P" if record_type == "patrol" else "IPQC-F"
    rec_id  = f"{pfx}-{year}-{str(total).zfill(4)}"
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")

    cr_ng = ma_ng = mi_ng = 0
    ng_stations: set = set()
    ng_summaries: list = []

    if record_type == "patrol":
        for station in model.get("patrol_stations", []):
            st_id   = station["id"]
            st_name = station["name"]
            st_ng   = []
            for i_idx, it in enumerate(station.get("items", [])):
                grade = it.get("grade", "MA")
                d     = results.get(st_id, {}).get(str(i_idx), {})
                if d.get("am") == "NG" or d.get("pm") == "NG":
                    if grade == "CR":   cr_ng += 1
                    elif grade == "MA": ma_ng += 1
                    else:               mi_ng += 1
                    ng_stations.add(st_id)
                    st_ng.append(f"[{grade}]{it['item'][:12]}")
            if st_ng:
                ng_summaries.append(f"{st_id}/{st_name}：{'；'.join(st_ng)}")
    else:  # fai
        for station in model.get("fai_stations", []):
            st_id   = station["id"]
            st_name = station["name"]
            st_ng   = []
            for i_idx, it in enumerate(station.get("items", [])):
                d = results.get(st_id, {}).get(str(i_idx), {})
                if d.get("result") == "×":
                    mi_ng += 1
                    ng_stations.add(st_id)
                    st_ng.append(it["item"][:12])
            if st_ng:
                ng_summaries.append(f"{st_id}/{st_name}：{'；'.join(st_ng)}")

    verdict    = "NG" if (cr_ng + ma_ng + mi_ng) > 0 else "OK"
    ng_summary = " | ".join(ng_summaries)

    row = [
        rec_id,  now_str,
        header.get("model_id",   ""),   header.get("model_name", ""),
        header.get("date",       ""),   header.get("mfg_no",     ""),
        header.get("batch_qty",  0),    header.get("inspect_qty", 0),
        header.get("defect_qty", 0),    header.get("defect_rate", ""),
        header.get("inspector",  ""),
        "巡檢" if record_type == "patrol" else "首台FAI",
        verdict, len(ng_stations), cr_ng, ma_ng, mi_ng,
        ng_summary,
        header.get("mfg_sig", ""), header.get("qc_sig", ""), header.get("mgr_sig", ""),
        json.dumps(results, ensure_ascii=False),
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return rec_id


def load_ipqc_records():
    """讀取所有 IPQC 記錄，回傳 DataFrame"""
    import pandas as pd
    try:
        ws      = _open_sheet(SHEET_IPQC, COLS_IPQC)
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=COLS_IPQC)
    except Exception:
        return pd.DataFrame(columns=COLS_IPQC)


# ═══════════════════════════════════════════════════════
# SQM 供應商品質管理 — 資料表欄位定義
# ═══════════════════════════════════════════════════════
COLS_SQM_DEFECT = [
    "記錄編號",            # A  系統自動產生
    "建立時間",            # B  系統自動產生
    # ── 基本資訊（比照 IQC問題點病歷 Excel）──
    "發生日期",            # C
    "來源",                # D  e.g. 進料退貨 / 產線無效工時
    "機種",                # E  e.g. GPS / PJ2+GPS
    "零件名稱",            # F
    "零件編號（單據號碼）",# G
    "廠商",                # H
    "不良數",              # I
    # ── PDCA 分析 ──────────────────────────
    "P問題點",             # J
    "原因分析",            # K
    "D改善對策",           # L
    "C效果確認",           # M
    "A標準化",             # N
    # ── 管理欄位 ────────────────────────────
    "責任歸屬",            # O
    "完成日期",            # P
    "負責人",              # Q
    "狀態",                # R  處理中 / 結案 / 再發
    "照片",                # S
    "廠商稽核",            # T
    # ── 系統連結 ────────────────────────────
    "SCAR編號",            # U
    "處理狀態",            # V  系統用：待處理/SCAR開立中/等待供應商回覆/已結案
]

COLS_SQM_SCAR = [
    "SCAR編號",       # A
    "建立時間",       # B
    "異常記錄編號",   # C
    "供應商",         # D
    "料號",           # E
    "品名",           # F
    "異常日期",       # G
    "異常類別",       # H
    "異常描述",       # I
    "異常數量",       # J
    "要求回覆期限",   # K
    "供應商回覆狀態", # L
    "供應商回覆日期", # M
    "供應商回覆內容", # N
    "臨時對策_D3",    # O
    "根本原因_D4D5",  # P
    "永久對策_D6",    # Q
    "CAPA驗證_D7",    # R
    "CAPA狀態",       # S
    "結案狀態",       # T
    "責任歸屬",       # U
    "建立人員",       # V
    "主管審核",       # W
    "備註",           # X
]


# ──────────────────────────────────────────────────────
# SQM 進料異常登錄
# ──────────────────────────────────────────────────────
def append_sqm_defect(data: dict) -> str:
    """
    新增一筆進料異常記錄至 SQM_異常登錄 工作表。
    data keys 比照 IQC問題點病歷 Excel 欄位：
      發生日期, 來源, 機種, 零件名稱, 零件編號（單據號碼）, 廠商, 不良數,
      P問題點, 原因分析, D改善對策, C效果確認, A標準化,
      責任歸屬, 完成日期, 負責人, 狀態, 照片, 廠商稽核
    回傳: 記錄編號
    """
    ws = _open_sheet(SHEET_SQM_DEFECT, COLS_SQM_DEFECT)
    _ensure_headers(ws, COLS_SQM_DEFECT)

    total   = len(ws.get_all_values())
    year    = datetime.now().year
    rec_id  = f"SQM-{year}-{str(total).zfill(4)}"
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")

    row = [
        rec_id,  now_str,
        str(data.get("發生日期",             "")),
        data.get("來源",                     ""),
        data.get("機種",                     ""),
        data.get("零件名稱",                 ""),
        data.get("零件編號（單據號碼）",     ""),
        data.get("廠商",                     ""),
        data.get("不良數",                   ""),
        data.get("P問題點",                  ""),
        data.get("原因分析",                 ""),
        data.get("D改善對策",                ""),
        data.get("C效果確認",                ""),
        data.get("A標準化",                  ""),
        data.get("責任歸屬",                 ""),
        data.get("完成日期",                 ""),
        data.get("負責人",                   ""),
        data.get("狀態",                     "處理中"),
        data.get("照片",                     ""),
        data.get("廠商稽核",                 ""),
        "",                                   # SCAR編號（待開立）
        data.get("處理狀態",                 "待處理"),
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return rec_id


def load_sqm_defects():
    """讀取所有進料異常記錄，回傳 DataFrame"""
    import pandas as pd
    try:
        ws      = _open_sheet(SHEET_SQM_DEFECT, COLS_SQM_DEFECT)
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=COLS_SQM_DEFECT)
    except Exception:
        return pd.DataFrame(columns=COLS_SQM_DEFECT)


def update_sqm_defect(rec_id: str, field: str, value: str):
    """更新 SQM_異常登錄 中某筆記錄的特定欄位"""
    import pandas as pd
    ws = _open_sheet(SHEET_SQM_DEFECT, COLS_SQM_DEFECT)
    records = ws.get_all_records()
    for i, rec in enumerate(records):
        if rec.get("記錄編號") == rec_id:
            row_idx = i + 2          # 1-based + header row
            col_idx = COLS_SQM_DEFECT.index(field) + 1
            ws.update_cell(row_idx, col_idx, str(value))
            return
    raise ValueError(f"記錄 {rec_id} 不存在")


# ──────────────────────────────────────────────────────
# SCAR 供應商異常單
# ──────────────────────────────────────────────────────
def append_scar(data: dict) -> str:
    """
    新增一筆 SCAR 記錄至 SQM_SCAR 工作表。
    data keys: 異常記錄編號, 供應商, 料號, 品名, 異常日期,
               異常類別, 異常描述, 異常數量, 要求回覆期限,
               責任歸屬, 建立人員, 備註
    回傳: SCAR編號
    """
    ws = _open_sheet(SHEET_SQM_SCAR, COLS_SQM_SCAR)
    _ensure_headers(ws, COLS_SQM_SCAR)

    total    = len(ws.get_all_values())
    year     = datetime.now().year
    scar_no  = f"SCAR-{year}-{str(total).zfill(4)}"
    now_str  = datetime.now().strftime("%Y/%m/%d %H:%M")

    row = [
        scar_no,  now_str,
        data.get("異常記錄編號", ""),
        data.get("供應商",       ""),
        data.get("料號",         ""),
        data.get("品名",         ""),
        str(data.get("異常日期", "")),
        data.get("異常類別",     ""),
        data.get("異常描述",     ""),
        data.get("異常數量",     0),
        str(data.get("要求回覆期限", "")),
        "待回覆",   # 供應商回覆狀態
        "",         # 供應商回覆日期
        "",         # 供應商回覆內容
        "",  "",  "",  "",   # D3~D7
        "未開始",   # CAPA狀態
        "Open",     # 結案狀態
        data.get("責任歸屬",  "供應商責任"),
        data.get("建立人員",  ""),
        "",         # 主管審核
        data.get("備註",      ""),
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return scar_no


def load_scars():
    """讀取所有 SCAR 記錄，回傳 DataFrame"""
    import pandas as pd
    try:
        ws      = _open_sheet(SHEET_SQM_SCAR, COLS_SQM_SCAR)
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=COLS_SQM_SCAR)
    except Exception:
        return pd.DataFrame(columns=COLS_SQM_SCAR)


def update_scar(scar_no: str, updates: dict):
    """
    更新 SCAR 記錄中的多個欄位。
    updates: {欄位名: 新值, ...}
    """
    ws = _open_sheet(SHEET_SQM_SCAR, COLS_SQM_SCAR)
    records = ws.get_all_records()
    row_idx = None
    for i, rec in enumerate(records):
        if rec.get("SCAR編號") == scar_no:
            row_idx = i + 2
            break
    if row_idx is None:
        raise ValueError(f"SCAR {scar_no} 不存在")
    for field, value in updates.items():
        if field in COLS_SQM_SCAR:
            col_idx = COLS_SQM_SCAR.index(field) + 1
            ws.update_cell(row_idx, col_idx, str(value))


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
