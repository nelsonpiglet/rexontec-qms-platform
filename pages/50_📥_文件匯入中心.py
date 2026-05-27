"""
REXONTEC — 文件自動匯入中心
Document Auto-Import Center
Phase 1: Excel → SQM IQC 異常登錄（批次建案）
"""
import io
from datetime import datetime

import pandas as pd
import streamlit as st

from utils.auth  import require_login, user_info_bar
from utils.sqm   import SOURCE_OPTIONS, IQC_STATUS_OPTIONS, RESP_OPTIONS, DEFECT_CATEGORY_OPTIONS
from utils.style import QMS_CSS, page_header, topbar

# ── 頁面設定 ──────────────────────────────────────────
st.set_page_config(
    page_title="文件匯入中心 | REXONTEC QMS",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()
user_info_bar()

# ── 導覽列 ────────────────────────────────────────────
n1, n2, n3, n4, n5, n6, n7, n8 = st.columns([1, 1, 1, 1, 1, 1, 1, 2])
with n1:
    if st.button("🏠 指揮平台",   use_container_width=True): st.switch_page("app.py")
with n2:
    if st.button("🔬 IQC 進料",   use_container_width=True): st.switch_page("pages/06_IQC進料檢驗.py")
with n3:
    if st.button("🏭 SQM 異常",   use_container_width=True): st.switch_page("pages/40_🏭_SQM異常登錄.py")
with n4:
    if st.button("📝 SCAR 管理",  use_container_width=True): st.switch_page("pages/41_📝_SCAR管理.py")
with n5:
    if st.button("📊 SQM 儀表板", use_container_width=True): st.switch_page("pages/42_📊_SQM儀表板.py")
with n6:
    if st.button("📥 文件匯入", use_container_width=True, type="primary"):
        st.switch_page("pages/50_📥_文件匯入中心.py")
with n7:
    if st.button("⚙️ 系統設定",   use_container_width=True): st.switch_page("pages/03_系統設定.py")

st.markdown(page_header(
    "文件自動匯入中心",
    "Excel / PDF / OCR 批次建案 — 欄位智能對應 · 資料驗證 · 一鍵匯入",
    "IMPORT",
), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# QMS 目標欄位定義（完全比照 IQC問題點病歷 Excel 格式）
# ═══════════════════════════════════════════════════
QMS_FIELDS: dict[str, dict] = {
    "發生日期":             {"required": True,  "type": "date", "hint": "問題發生日期"},
    "來源":                 {"required": False, "type": "str",  "hint": f"e.g. {'、'.join(SOURCE_OPTIONS[:3])}"},
    "機種":                 {"required": False, "type": "str",  "hint": "e.g. GPS / PJ2+GPS"},
    "零件名稱":             {"required": False, "type": "str",  "hint": "零件/材料名稱"},
    "零件編號（單據號碼）": {"required": True,  "type": "str",  "hint": "料號 / 批號"},
    "廠商":                 {"required": True,  "type": "str",  "hint": "供應商名稱"},
    "不良數":               {"required": True,  "type": "num",  "hint": "不良品數量（整數）"},
    "P問題點":              {"required": True,  "type": "str",  "hint": "具體不良現象描述"},
    "原因分析":             {"required": False, "type": "str",  "hint": "根本原因分析"},
    "D改善對策":            {"required": False, "type": "str",  "hint": "矯正/改善措施"},
    "C效果確認":            {"required": False, "type": "str",  "hint": "改善效果確認/驗證"},
    "A標準化":              {"required": False, "type": "str",  "hint": "標準化措施/文件更新"},
    "責任歸屬":             {"required": False, "type": "str",  "hint": f"e.g. {'、'.join(RESP_OPTIONS[:2])}"},
    "完成日期":             {"required": False, "type": "date", "hint": "預計/實際完成日期"},
    "負責人":               {"required": False, "type": "str",  "hint": "負責處理人員"},
    "狀態":                 {"required": False, "type": "str",  "hint": f"限定值：{'、'.join(IQC_STATUS_OPTIONS)}",
                             "options": IQC_STATUS_OPTIONS},
    "照片":                 {"required": False, "type": "str",  "hint": "Google Drive 照片連結"},
    "廠商稽核":             {"required": False, "type": "str",  "hint": "廠商稽核紀錄"},
    "異常類別":             {"required": False, "type": "str",  "hint": f"限定值：{'、'.join(DEFECT_CATEGORY_OPTIONS)}",
                             "options": DEFECT_CATEGORY_OPTIONS},
}

# 欄位關鍵字對應（規則式智能辨識）
# 中文關鍵字用 substring，英文用完全相符，避免 Unnamed 誤配
_FIELD_KEYWORDS: dict[str, list[str]] = {
    "發生日期":             ["日期", "發生日期", "入料日期", "發生"],
    "來源":                 ["來源", "入料來源", "source"],
    "機種":                 ["機種", "機型", "型號", "model"],
    "零件名稱":             ["零件名稱", "品名", "零件名", "品項", "物料名稱"],
    "零件編號（單據號碼）": ["零件編號", "料號", "零件號", "品號", "單據號碼", "partno", "part_no"],
    "廠商":                 ["廠商", "供應商", "vendor", "supplier"],
    "不良數":               ["不良數", "異常數量", "不良數量", "不良品數", "ng_qty", "defect_qty"],
    "P問題點":              ["p問題點", "問題點", "異常描述", "問題描述", "異常說明"],
    "原因分析":             ["原因分析", "根本原因", "原因"],
    "D改善對策":            ["d改善對策", "改善對策", "對策", "改善措施"],
    "C效果確認":            ["c效果確認", "效果確認", "確認"],
    "A標準化":              ["a標準化", "標準化"],
    "責任歸屬":             ["責任歸屬", "責任單位", "責任"],
    "完成日期":             ["完成日期", "結案日期", "due_date"],
    "負責人":               ["負責人", "建立人員", "檢驗員", "inspector", "creator"],
    "狀態":                 ["狀態", "結果"],
    "照片":                 ["照片", "photo", "image"],
    "廠商稽核":             ["廠商稽核", "稽核", "audit"],
    "異常類別":             ["異常類別", "不良類別", "缺陷類別", "defect_type", "defect_category"],
}

REQUIRED_FIELDS = [f for f, v in QMS_FIELDS.items() if v["required"]]
OPTIONAL_FIELDS = [f for f, v in QMS_FIELDS.items() if not v["required"]]


# ═══════════════════════════════════════════════════
# 工具函式
# ═══════════════════════════════════════════════════
def _norm(s: str) -> str:
    """標準化欄位名稱：去除空格/底線/括號/標點，轉小寫"""
    import re
    return re.sub(r"[^\w一-鿿]", "", str(s).lower()).replace("_", "")


def _auto_match(excel_cols: list[str]) -> dict[str, str]:
    """
    規則式欄位自動對應，回傳 {QMS欄位 → Excel欄位}。
    安全比對：純中文關鍵字用 substring；英文關鍵字須完全相符，
    避免 'name' 誤配 'Unnamed: 1' 之類問題。
    """
    import re
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for qms_field, keywords in _FIELD_KEYWORDS.items():
        for col in excel_cols:
            if col in used:
                continue
            col_norm = _norm(col)
            for kw in keywords:
                kw_norm = _norm(kw)
                # 中文關鍵字：substring 即可（中文無「詞語」邊界問題）
                is_cjk_kw = bool(re.search(r"[一-鿿]", kw))
                matched = (
                    kw_norm in col_norm         # CJK: substring
                    if is_cjk_kw
                    else col_norm == kw_norm    # 英文: 完全相符
                )
                if matched:
                    mapping[qms_field] = col
                    used.add(col)
                    break
            if qms_field in mapping:
                break
    return mapping


def _coerce_date(val: str) -> str:
    """嘗試標準化日期為 YYYY/MM/DD"""
    if not val or str(val).strip() == "":
        return ""
    try:
        return pd.to_datetime(str(val)).strftime("%Y/%m/%d")
    except Exception:
        return str(val).strip()


def _coerce_num(val: str) -> str:
    """嘗試轉為整數字串"""
    if not val or str(val).strip() == "":
        return ""
    try:
        return str(int(float(str(val).replace(",", ""))))
    except Exception:
        return str(val).strip()


def _detect_header_row(df_peek: pd.DataFrame) -> int:
    """
    自動偵測標題列位置（回傳 1-indexed 列號）。
    策略：找「非空且不含時間戳」的儲存格最多的那列，最可能是欄位標題列。
    通常：大標題合併列只有1格有值，欄位標題列有很多格有值。
    """
    import re
    ts_pat = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}")
    best_row, best_score = 0, -1
    for i, row in df_peek.iterrows():
        vals = [str(v).strip() for v in row if str(v).strip() and str(v).strip() != "nan"]
        # 分數 = 非空且不像時間戳的格子數
        score = sum(1 for v in vals if not ts_pat.search(v))
        if score > best_score:
            best_score = score
            best_row = int(i)
    return best_row + 1  # 轉為 1-indexed


def _validate_df(df_mapped: pd.DataFrame) -> pd.DataFrame:
    """
    驗證對應後資料。回傳含 _errors 欄的 DataFrame；
    空字串 = 無錯誤，可匯入。
    """
    errs = []
    for _, row in df_mapped.iterrows():
        row_errs: list[str] = []
        for field, info in QMS_FIELDS.items():
            if field not in df_mapped.columns:
                if info["required"]:
                    row_errs.append(f"[{field}]欄位未對應")
                continue
            val = str(row.get(field, "")).strip()
            if not val:
                if info["required"]:
                    row_errs.append(f"[{field}]不可為空")
                continue
            if info["type"] == "date":
                try:
                    pd.to_datetime(val)
                except Exception:
                    row_errs.append(f"[{field}]日期格式錯誤:{val}")
            elif info["type"] == "num":
                try:
                    float(val.replace(",", ""))
                except Exception:
                    row_errs.append(f"[{field}]應為數字:{val}")
            elif info["type"] == "option":
                if val not in info["options"]:
                    row_errs.append(f"[{field}]值不符:{val}")
        errs.append("；".join(row_errs))
    df_out = df_mapped.copy()
    df_out["_errors"] = errs
    return df_out


@st.cache_data(show_spinner=False)
def _build_template() -> bytes:
    """產生匯入範例 Excel 模板（比照 IQC問題點病歷格式）"""
    sample = {
        "發生日期":             ["2026/03/17", "2026/04/24", "2026/04/28"],
        "來源":                 ["產線無效工時", "進料退貨", "進料退貨"],
        "機種":                 ["GPS", "PJ2+GPS", "PJ2+GPS"],
        "零件名稱":             ["上蓋", "鋁本體", "視窗"],
        "零件編號（單據號碼）": ["10J43ANU", "1311-000-00046", "1332-002-00201"],
        "廠商":                 ["志泰", "遠通", "香港泓發"],
        "不良數":               [1, 12, 4],
        "P問題點":              [
            "按鍵毛邊",
            "1.電池卡扣有毛邊 2.旋鈕孔有毛邊 3.抽驗200PCS/12個不良",
            "1.PC透明保護膜刮傷 2.抽驗30PCS/4個不良",
        ],
        "原因分析":             ["毛邊未修剪", "毛邊未整修", "保護膜刮傷"],
        "D改善對策":            ["退貨重工修剪", "退貨重工", "更換保護膜"],
        "C效果確認":            ["IQC確認", "", ""],
        "A標準化":              ["列入廠商自主查表", "", ""],
        "責任歸屬":             ["供應商責任", "供應商責任", "供應商責任"],
        "完成日期":             ["2026/03/12", "", ""],
        "負責人":               ["白大中", "白大中", "白大中"],
        "狀態":                 ["結案", "再發", "再發"],
        "照片":                 ["", "", ""],
        "廠商稽核":             ["", "", ""],
    }
    buf = io.BytesIO()
    pd.DataFrame(sample).to_excel(buf, index=False)
    return buf.getvalue()


# ═══════════════════════════════════════════════════
# 主畫面 Tabs
# ═══════════════════════════════════════════════════
tab_excel, tab_oqc, tab_pdf, tab_ocr, tab_email = st.tabs([
    "📊 Excel 匯入 IQC 異常",
    "🔧 OQC 成檢表匯入",
    "📄 PDF 匯入 SCAR（預留）",
    "🖼️ 圖片 OCR 辨識（預留）",
    "📧 Email 自動建案（預留）",
])

# ═══════════════════════════════════════════════════
# Tab 2：OQC 成檢表 Excel 匯入（PoC — MD1003RX）
# ═══════════════════════════════════════════════════
with tab_oqc:
    st.markdown("""
    <div style="display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap;align-items:center">
      <div style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:8px;
                  padding:7px 14px;font-size:12px;font-weight:700;color:#2e7d32">
        ① 上傳成檢表 Excel</div>
      <div style="color:#ccc;font-size:18px">›</div>
      <div style="background:#e3f2fd;border:1px solid #90caf9;border-radius:8px;
                  padding:7px 14px;font-size:12px;font-weight:700;color:#1565c0">
        ② 解析預覽</div>
      <div style="color:#ccc;font-size:18px">›</div>
      <div style="background:#fff3e0;border:1px solid #ffcc80;border-radius:8px;
                  padding:7px 14px;font-size:12px;font-weight:700;color:#e65100">
        ③ 確認機種</div>
      <div style="color:#ccc;font-size:18px">›</div>
      <div style="background:#f3e5f5;border:1px solid #ce93d8;border-radius:8px;
                  padding:7px 14px;font-size:12px;font-weight:700;color:#6a1b9a">
        ④ 儲存為模板</div>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        "💡 上傳 MD1003RX 格式成檢表 Excel，系統自動識別檢驗區段與項目，"
        "轉換為 OQC 模板供「出廠檢驗輸入」頁面使用。"
        "  PoC 版本：目前支援 **MD1003RX 馬達成檢表** 格式。"
    )

    oqc_file = st.file_uploader(
        "拖曳或點擊上傳成檢表 Excel（.xlsx）",
        type=["xlsx"],
        key="oqc_excel_upload",
        label_visibility="collapsed",
    )

    if not oqc_file:
        st.markdown("""
        <div style="background:#fafbfc;border:2px dashed #ddd;border-radius:10px;
                    padding:36px;text-align:center;color:#bbb;margin-top:10px">
          <div style="font-size:36px;margin-bottom:8px">📋</div>
          <div style="font-size:13px;font-weight:600;color:#aaa">尚未上傳成檢表 Excel</div>
          <div style="font-size:11px;margin-top:6px">請上傳力山公司成品檢驗表格式的 Excel 檔案</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── ② 解析 Excel ─────────────────────────────
        try:
            from utils.oqc_excel_parser import parse_oqc_excel, extract_header_meta
            from utils.oqc_template_db  import upsert_template, list_models

            oqc_bytes   = oqc_file.read()
            sections    = parse_oqc_excel(oqc_bytes)
            header_meta = extract_header_meta(oqc_bytes)
            parse_ok    = True
        except Exception as _pe:
            st.error(f"❌ 解析失敗：{_pe}")
            parse_ok = False

        if parse_ok:
            if not sections:
                st.warning("⚠️ 未偵測到任何檢驗區段，請確認 Excel 格式正確。")
            else:
                total_items = sum(len(s["items"]) for s in sections)
                st.success(
                    f"✅ 解析成功：**{len(sections)}** 個區段｜"
                    f"**{total_items}** 個檢驗項目"
                )

                # ── 預覽解析結果 ─────────────────────────
                st.markdown(
                    '<div style="font-size:13px;font-weight:700;color:var(--navy);'
                    'border-left:4px solid #1565c0;padding-left:10px;margin:10px 0 8px">'
                    '② 解析結果預覽</div>',
                    unsafe_allow_html=True,
                )

                for sec in sections:
                    grade_counts = {}
                    type_counts  = {}
                    for it in sec["items"]:
                        grade_counts[it["grade"]] = grade_counts.get(it["grade"], 0) + 1
                        type_counts [it["type"]]  = type_counts .get(it["type"],  0) + 1

                    badge_html = "".join(
                        f'<span style="background:{"#c0392b" if g=="CR" else "#d68910" if g=="MA" else "#1e8449"};'
                        f'color:#fff;padding:1px 8px;border-radius:4px;font-size:10px;'
                        f'font-weight:800;margin-left:4px">{g}×{n}</span>'
                        for g, n in sorted(grade_counts.items())
                    )
                    type_html = "".join(
                        f'<span style="background:#e3f2fd;color:#1565c0;padding:1px 8px;'
                        f'border-radius:4px;font-size:10px;font-weight:700;margin-left:4px">'
                        f'{"PASS/FAIL" if t=="pf" else "數值量測"}×{n}</span>'
                        for t, n in sorted(type_counts.items())
                    )

                    with st.expander(
                        f"  **{sec['id']}｜{sec['label']}**  ·  {len(sec['items'])} 項",
                        expanded=True,
                    ):
                        st.markdown(
                            f'<div style="margin-bottom:8px">{badge_html}{type_html}</div>',
                            unsafe_allow_html=True,
                        )
                        import pandas as _pd
                        rows = []
                        for it in sec["items"]:
                            extra = ""
                            if it["type"] == "num":
                                u = it.get("unit", "")
                                mn = it.get("min")
                                mx = it.get("max")
                                if mn is not None and mx is not None:
                                    extra = f"{mn}～{mx} {u}"
                                elif mn is not None:
                                    extra = f"≧{mn} {u}"
                                elif mx is not None:
                                    extra = f"≦{mx} {u}"
                                else:
                                    extra = u
                            rows.append({
                                "ID": it["id"],
                                "No.": it["no"],
                                "等級": it["grade"],
                                "類型": "PASS/FAIL" if it["type"] == "pf" else "數值量測",
                                "檢驗項目": it["name"][:40],
                                "規格": it["spec"][:25],
                                "範圍/單位": extra,
                                "工具": it.get("tool", ""),
                            })
                        st.dataframe(
                            _pd.DataFrame(rows),
                            use_container_width=True,
                            height=min(300, 35 * len(rows) + 40),
                            hide_index=True,
                        )

                st.divider()

                # ── ③ 確認機種 ────────────────────────────
                st.markdown(
                    '<div style="font-size:13px;font-weight:700;color:var(--navy);'
                    'border-left:4px solid #e65100;padding-left:10px;margin:0 0 8px">'
                    '③ 確認機種名稱</div>',
                    unsafe_allow_html=True,
                )

                # 已有模板的機種清單（用於提示）
                existing_models = list_models()
                auto_model = header_meta.get("model", "") or "MD1003RX"

                oc1, oc2 = st.columns([2, 3])
                with oc1:
                    model_input = st.text_input(
                        "機種名稱（作為模板識別碼）",
                        value=auto_model,
                        placeholder="例：MD1003RX",
                        key="oqc_model_input",
                    )
                with oc2:
                    if existing_models:
                        st.markdown(
                            f'<div style="padding-top:28px;font-size:11.5px;color:var(--muted)">'
                            f'📋 已有模板：{"、".join(existing_models)}</div>',
                            unsafe_allow_html=True,
                        )
                    if model_input in existing_models:
                        st.warning(
                            f"⚠️ 機種「{model_input}」已有模板，儲存後將**覆蓋**舊模板。"
                        )

                doc_no  = st.text_input("文件編號（選填）", key="oqc_doc_no", placeholder="例：QC-MD1003-001")
                rev_no  = st.text_input("版次（選填）", key="oqc_rev_no", placeholder="例：V1.0")
                oqc_note = st.text_area("備註（選填）", key="oqc_note_input", height=60)

                st.divider()

                # ── ④ 儲存為模板 ─────────────────────────
                st.markdown(
                    '<div style="font-size:13px;font-weight:700;color:var(--navy);'
                    'border-left:4px solid #6a1b9a;padding-left:10px;margin:0 0 8px">'
                    '④ 儲存為 OQC 模板</div>',
                    unsafe_allow_html=True,
                )

                confirm_oqc = st.checkbox(
                    f"✅ 確認將 **{total_items}** 個檢驗項目儲存為「{model_input or '（請填機種名稱）'}」的 OQC 模板",
                    key="oqc_confirm_save",
                )

                if st.button(
                    "💾 儲存 OQC 模板",
                    type="primary",
                    use_container_width=True,
                    disabled=(not confirm_oqc or not (model_input or "").strip()),
                ):
                    try:
                        upsert_template(
                            model    = model_input.strip(),
                            sections = sections,
                            meta     = {
                                "doc_no": doc_no.strip(),
                                "rev":    rev_no.strip(),
                                "note":   oqc_note.strip(),
                                "source_file": oqc_file.name,
                            },
                        )
                        st.success(
                            f"🎉 OQC 模板「**{model_input}**」儲存成功！\n\n"
                            f"共 {len(sections)} 個區段、{total_items} 個檢驗項目。\n\n"
                            "前往「出廠檢驗輸入」→ 選擇馬達 Motor → 選取此機種，即可使用動態模板。"
                        )
                        oc_nav1, oc_nav2 = st.columns(2)
                        with oc_nav1:
                            if st.button("🔬 前往出廠檢驗", use_container_width=True, key="oqc_goto_insp"):
                                st.switch_page("pages/01_出廠檢驗輸入.py")
                        with oc_nav2:
                            if st.button("⚙️ 前往系統設定查看模板", use_container_width=True, key="oqc_goto_set"):
                                st.switch_page("pages/03_系統設定.py")
                    except Exception as _se:
                        st.error(f"❌ 儲存失敗：{_se}")


# ─── 預留功能佔位 ─────────────────────────────────
_placeholder = (
    '<div style="background:#fafbfc;border:2px dashed #ddd;border-radius:12px;'
    'padding:60px 20px;text-align:center;margin:20px 0">'
    '<div style="font-size:44px;margin-bottom:14px">{icon}</div>'
    '<div style="font-size:16px;font-weight:700;color:#999;margin-bottom:8px">{title}</div>'
    '<div style="font-size:12px;color:#bbb;line-height:1.8">{desc}</div>'
    '<div style="margin-top:18px;display:inline-block;background:#f0f0f0;'
    'border:1px solid #ddd;border-radius:20px;padding:4px 18px;'
    'font-size:11px;font-weight:700;letter-spacing:1px;color:#aaa">'
    '🔒 第二階段開發中</div></div>'
)

with tab_pdf:
    st.markdown(_placeholder.format(
        icon="📄", title="PDF 匯入 SCAR",
        desc="上傳供應商 SCAR 回覆 PDF，自動解析內容並建立 SCAR 記錄<br>"
             "支援表單型 / 圖掃型 PDF · 多頁批次上傳",
    ), unsafe_allow_html=True)

with tab_ocr:
    st.markdown(_placeholder.format(
        icon="🖼️", title="圖片 OCR 異常辨識",
        desc="上傳檢驗照片，AI 自動辨識異常類型並生成異常描述<br>"
             "支援 PNG / JPG / TIFF · 多圖批次上傳",
    ), unsafe_allow_html=True)

with tab_email:
    st.markdown(_placeholder.format(
        icon="📧", title="Email 自動建案",
        desc="連接供應商回覆信箱，自動解析 CAPA 內容並更新 SCAR<br>"
             "支援 Gmail / Outlook 整合 · 定時輪詢",
    ), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# Tab 1：Excel 匯入 IQC 異常
# ═══════════════════════════════════════════════════
with tab_excel:

    # ── 流程步驟指示列 ──────────────────────────────
    st.markdown("""
    <div style="display:flex;gap:6px;margin-bottom:20px;flex-wrap:wrap;align-items:center">
      <div style="background:#e3f2fd;border:1px solid #90caf9;border-radius:8px;
                  padding:7px 14px;font-size:12px;font-weight:700;color:#1565c0">
        ① 上傳 Excel</div>
      <div style="color:#ccc;font-size:18px">›</div>
      <div style="background:#f3e5f5;border:1px solid #ce93d8;border-radius:8px;
                  padding:7px 14px;font-size:12px;font-weight:700;color:#6a1b9a">
        ② 欄位對應</div>
      <div style="color:#ccc;font-size:18px">›</div>
      <div style="background:#fff3e0;border:1px solid #ffcc80;border-radius:8px;
                  padding:7px 14px;font-size:12px;font-weight:700;color:#e65100">
        ③ 資料驗證</div>
      <div style="color:#ccc;font-size:18px">›</div>
      <div style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:8px;
                  padding:7px 14px;font-size:12px;font-weight:700;color:#2e7d32">
        ④ 確認匯入</div>
    </div>
    """, unsafe_allow_html=True)

    # ────────────────────────────────────────────────
    # ① 上傳 Excel
    # ────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid #1565c0;padding-left:10px;margin:0 0 10px">'
        '① 上傳 Excel 檔案</div>',
        unsafe_allow_html=True,
    )

    dl_col, hint_col = st.columns([1, 3])
    with dl_col:
        st.download_button(
            "⬇️ 下載匯入範例模板",
            data=_build_template(),
            file_name="IQC異常匯入模板.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with hint_col:
        st.info(
            "💡 建議使用範例模板，系統可自動辨識欄位。"
            "非標準格式也支援手動欄位對應。每次最多可匯入 **5,000 筆**。"
        )

    uploaded = st.file_uploader(
        "拖曳或點擊上傳 Excel（.xlsx / .xls）",
        type=["xlsx", "xls"],
        help="Excel 第一列須為欄位標題列",
        label_visibility="collapsed",
    )

    if not uploaded:
        st.markdown("""
        <div style="background:#fafbfc;border:2px dashed #ddd;border-radius:10px;
                    padding:36px;text-align:center;color:#bbb;margin-top:10px">
          <div style="font-size:36px;margin-bottom:8px">📂</div>
          <div style="font-size:13px;font-weight:600;color:#aaa">尚未上傳 Excel 檔案</div>
          <div style="font-size:11px;margin-top:6px">請先下載範例模板，填寫後上傳</div>
        </div>
        """, unsafe_allow_html=True)

    else:
        # ── 讀取 Excel ───────────────────────────────
        try:
            xls = pd.ExcelFile(uploaded)
            sheet_names = xls.sheet_names
        except Exception as e:
            st.error(f"❌ 無法開啟 Excel 檔案：{e}")
            xls = None

        if xls is not None:
            selected_sheet = sheet_names[0]
            if len(sheet_names) > 1:
                selected_sheet = st.selectbox(
                    "📋 選擇要匯入的工作表",
                    sheet_names,
                    help="此 Excel 包含多個工作表",
                )

            # ── 先不帶 header 讀取，讓使用者確認標題列位置 ──
            try:
                df_peek = (
                    pd.read_excel(
                        xls, sheet_name=selected_sheet,
                        header=None, dtype=str, nrows=8,
                    ).fillna("")
                )
                peek_ok = True
            except Exception as e:
                st.error(f"❌ 讀取工作表失敗：{e}")
                peek_ok = False

            if peek_ok:
                # 顯示原始前8列（不含自動 header），協助確認標題列
                with st.expander("🔍 原始資料前8列預覽（用於確認標題列位置）", expanded=True):
                    st.dataframe(
                        df_peek.rename(columns=lambda c: f"第 {c+1} 欄"),
                        use_container_width=True,
                    )

                # 自動偵測標題列
                auto_hdr = _detect_header_row(df_peek)

                hdr_col, info_col = st.columns([1, 3])
                with hdr_col:
                    header_row = st.number_input(
                        "📌 欄位標題在第幾列？",
                        min_value=1, max_value=8,
                        value=auto_hdr,   # 自動偵測結果
                        step=1,
                        help="系統已自動偵測，若結果不對可手動調整",
                        key="header_row_sel",
                    )
                with info_col:
                    if auto_hdr == 1:
                        st.success(
                            f"✅ 自動偵測：第 **{auto_hdr}** 列為欄位標題列（直接開頭）"
                        )
                    else:
                        st.warning(
                            f"⚠️ 自動偵測：第 **{auto_hdr}** 列才是欄位標題列\n\n"
                            f"（前 {auto_hdr-1} 列為大標題/合併列，已自動跳過）\n\n"
                            "如果結果不對，請手動調整左方數字。"
                        )

                # ── 用正確的 header 重新讀取 ──────────────────
                try:
                    df_raw = (
                        pd.read_excel(
                            xls, sheet_name=selected_sheet,
                            header=int(header_row) - 1, dtype=str,
                        ).fillna("")
                    )
                    # 清理欄位名稱：去括號、多餘空格、換行
                    import re as _re
                    df_raw.columns = [
                        _re.sub(r"\s+", " ", str(c)).strip()
                        for c in df_raw.columns
                    ]
                    # 去除 Unnamed 欄（合併儲存格殘留的空欄）
                    df_raw = df_raw.loc[
                        :, ~df_raw.columns.str.startswith("Unnamed:")
                    ]
                    # 去除全空列
                    df_raw = df_raw[
                        ~df_raw.apply(lambda r: r.str.strip().eq("").all(), axis=1)
                    ].reset_index(drop=True)
                    read_ok = True
                except Exception as e:
                    st.error(f"❌ 讀取工作表失敗：{e}")
                    read_ok = False

                if read_ok:
                    if df_raw.empty:
                        st.warning("⚠️ 工作表無資料，請確認 Excel 格式與標題列設定。")
                    else:
                        st.success(
                            f"✅ 成功讀取 **{selected_sheet}**｜"
                            f"**{len(df_raw)}** 筆資料｜"
                            f"欄位：{' · '.join(df_raw.columns.tolist())}"
                        )
                    st.divider()

                    # ────────────────────────────────
                    # ② 欄位對應
                    # ────────────────────────────────
                    st.markdown(
                        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
                        'border-left:4px solid #6a1b9a;padding-left:10px;margin:0 0 8px">'
                        '② 欄位對應設定</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        "系統已依欄位名稱自動辨識對應，請確認或手動調整。"
                        "選「（略過）」表示不匯入此欄位。"
                    )

                    auto_map = _auto_match(list(df_raw.columns))
                    excel_options = ["（略過）"] + list(df_raw.columns)
                    mapping: dict[str, str] = {}

                    col_req, col_opt = st.columns(2)

                    with col_req:
                        st.markdown(
                            '<div style="font-size:11px;font-weight:700;color:#c62828;'
                            'letter-spacing:.5px;margin-bottom:8px">⭐ 必填欄位</div>',
                            unsafe_allow_html=True,
                        )
                        for field in REQUIRED_FIELDS:
                            default = auto_map.get(field, "（略過）")
                            idx = excel_options.index(default) if default in excel_options else 0
                            sel = st.selectbox(
                                f"**{field}**",
                                excel_options,
                                index=idx,
                                key=f"map_{field}",
                                help=QMS_FIELDS[field]["hint"],
                            )
                            if sel != "（略過）":
                                mapping[field] = sel

                    with col_opt:
                        st.markdown(
                            '<div style="font-size:11px;font-weight:700;color:#37474f;'
                            'letter-spacing:.5px;margin-bottom:8px">📝 選填欄位</div>',
                            unsafe_allow_html=True,
                        )
                        for field in OPTIONAL_FIELDS:
                            default = auto_map.get(field, "（略過）")
                            idx = excel_options.index(default) if default in excel_options else 0
                            sel = st.selectbox(
                                field,
                                excel_options,
                                index=idx,
                                key=f"map_{field}",
                                help=QMS_FIELDS[field]["hint"],
                            )
                            if sel != "（略過）":
                                mapping[field] = sel

                    # ── 對應欄位摘要 ─────────────────
                    mapped_count = len(mapping)
                    req_mapped   = [f for f in REQUIRED_FIELDS if f in mapping]
                    req_missing  = [f for f in REQUIRED_FIELDS if f not in mapping]

                    match_html = (
                        '<div style="background:#f8f9fa;border:1px solid #dee2e6;'
                        'border-radius:8px;padding:10px 14px;margin-top:10px;'
                        'font-size:12px;display:flex;gap:20px;flex-wrap:wrap">'
                        f'<span>📌 已對應 <b>{mapped_count}</b> 個欄位</span>'
                        f'<span style="color:#2e7d32">✅ 必填已對應 <b>{len(req_mapped)}</b>/{len(REQUIRED_FIELDS)}</span>'
                    )
                    if req_missing:
                        match_html += (
                            f'<span style="color:#c62828">❌ 缺少：'
                            f'<b>{"、".join(req_missing)}</b></span>'
                        )
                    match_html += "</div>"
                    st.markdown(match_html, unsafe_allow_html=True)

                    st.divider()

                    # ────────────────────────────────
                    # ③ 資料驗證
                    # ────────────────────────────────
                    st.markdown(
                        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
                        'border-left:4px solid #e65100;padding-left:10px;margin:0 0 10px">'
                        '③ 資料驗證結果</div>',
                        unsafe_allow_html=True,
                    )

                    if req_missing:
                        st.error(
                            f"❌ 以下必填欄位尚未對應，請回步驟②設定：**{'、'.join(req_missing)}**"
                        )
                    else:
                        # 建立對應後 DataFrame
                        mapped_rows = []
                        for _, row in df_raw.iterrows():
                            mapped_row = {
                                qf: str(row.get(ec, "")).strip()
                                for qf, ec in mapping.items()
                            }
                            mapped_rows.append(mapped_row)
                        df_mapped = pd.DataFrame(mapped_rows)

                        df_validated = _validate_df(df_mapped)
                        n_errors = int((df_validated["_errors"] != "").sum())
                        n_ok     = len(df_validated) - n_errors

                        vc1, vc2, vc3 = st.columns(3)
                        with vc1:
                            st.metric("總筆數", len(df_validated))
                        with vc2:
                            st.metric("✅ 可匯入", n_ok)
                        with vc3:
                            st.metric("❌ 有錯誤", n_errors)

                        if n_errors > 0:
                            with st.expander(
                                f"⚠️ 查看 {n_errors} 筆錯誤詳情（可跳過錯誤，僅匯入正確資料）",
                                expanded=True,
                            ):
                                df_err = df_validated[df_validated["_errors"] != ""].copy()
                                df_err.insert(0, "Excel行號", df_err.index + 2)
                                display_cols = ["Excel行號"] + [
                                    c for c in df_err.columns
                                    if c not in ("_errors", "Excel行號")
                                ] + ["_errors"]
                                st.dataframe(
                                    df_err[display_cols].rename(columns={"_errors": "錯誤說明"}),
                                    use_container_width=True,
                                    height=min(240, 35 * n_errors + 40),
                                )
                            st.warning(
                                f"共 {n_errors} 筆有錯誤將自動跳過，"
                                f"繼續匯入 **{n_ok}** 筆正確資料。\n\n"
                                "如需修正全部，請更新 Excel 後重新上傳。"
                            )

                        if n_ok == 0:
                            st.error("❌ 無可匯入資料，請修正 Excel 後重新上傳。")
                        else:
                            # 僅取正確資料
                            df_to_import = (
                                df_validated[df_validated["_errors"] == ""]
                                .drop(columns=["_errors"])
                                .reset_index(drop=True)
                            )

                            st.divider()

                            # ────────────────────────
                            # ④ 預覽 & 確認匯入
                            # ────────────────────────
                            st.markdown(
                                '<div style="font-size:13px;font-weight:700;color:var(--navy);'
                                'border-left:4px solid #2e7d32;padding-left:10px;margin:0 0 10px">'
                                '④ 匯入預覽與確認</div>',
                                unsafe_allow_html=True,
                            )

                            st.dataframe(
                                df_to_import,
                                use_container_width=True,
                                height=min(420, 35 * (len(df_to_import) + 1) + 20),
                            )

                            # 補充資訊
                            sup_col1, sup_col2 = st.columns(2)
                            with sup_col1:
                                if "建立人員" not in mapping:
                                    creator_input = st.text_input(
                                        "建立人員（統一套用至所有匯入筆數）",
                                        placeholder="請輸入姓名",
                                        key="import_creator",
                                    )
                                else:
                                    creator_input = None
                            with sup_col2:
                                batch_remark = st.text_input(
                                    "批次備註（選填）",
                                    placeholder="例：2025年5月批次匯入",
                                    key="import_remark",
                                )

                            confirm_check = st.checkbox(
                                f"✅ 我已核對上方 **{n_ok}** 筆資料，確認匯入至 Google Sheet",
                                value=False,
                                key="import_confirm",
                            )

                            # ── 重複偵測 ─────────────────
                            from utils.gsheet import load_sqm_defects as _load_existing
                            try:
                                _exist = _load_existing()
                                if not _exist.empty:
                                    _dup_keys = set(
                                        zip(
                                            _exist.get("零件編號（單據號碼）", pd.Series(dtype=str)).astype(str),
                                            _exist.get("廠商",               pd.Series(dtype=str)).astype(str),
                                            _exist.get("發生日期",           pd.Series(dtype=str)).astype(str),
                                        )
                                    )
                                    _dup_rows = []
                                    for _i, _r in df_to_import.iterrows():
                                        _k = (
                                            str(_r.get("零件編號（單據號碼）", "")).strip(),
                                            str(_r.get("廠商", "")).strip(),
                                            _coerce_date(str(_r.get("發生日期", ""))),
                                        )
                                        if _k in _dup_keys:
                                            _dup_rows.append(_i + 2)
                                    if _dup_rows:
                                        st.warning(
                                            f"⚠️ 偵測到 **{len(_dup_rows)}** 筆可能重複的資料（Excel 第 {_dup_rows} 行）：\n\n"
                                            "零件編號 + 廠商 + 發生日期 與現有記錄相同。\n\n"
                                            "如確定是不同批次，可繼續匯入；若是重複匯入請取消。"
                                        )
                            except Exception:
                                pass

                            if st.button(
                                f"🚀 確認匯入 {n_ok} 筆 IQC 異常記錄",
                                type="primary",
                                use_container_width=True,
                                disabled=not confirm_check,
                            ):
                                from utils.gsheet import append_sqm_defect

                                progress = st.progress(0, text="準備匯入...")
                                success_ids: list[str] = []
                                fail_msgs:  list[str] = []

                                for i, (_, row) in enumerate(df_to_import.iterrows()):
                                    progress.progress(
                                        (i) / len(df_to_import),
                                        text=f"匯入中... {i+1} / {len(df_to_import)}",
                                    )
                                    try:
                                        def _s(k): return str(row.get(k, "")).strip()
                                        # 批次備註附加到廠商稽核欄位
                                        audit_val = _s("廠商稽核")
                                        if batch_remark:
                                            audit_val = f"{audit_val}｜{batch_remark}" if audit_val else batch_remark
                                        rec_id = append_sqm_defect({
                                            "發生日期":             _coerce_date(_s("發生日期")),
                                            "來源":                 _s("來源"),
                                            "機種":                 _s("機種"),
                                            "零件名稱":             _s("零件名稱"),
                                            "零件編號（單據號碼）": _s("零件編號（單據號碼）"),
                                            "廠商":                 _s("廠商"),
                                            "不良數":               _coerce_num(_s("不良數")),
                                            "P問題點":              _s("P問題點"),
                                            "原因分析":             _s("原因分析"),
                                            "D改善對策":            _s("D改善對策"),
                                            "C效果確認":            _s("C效果確認"),
                                            "A標準化":              _s("A標準化"),
                                            "責任歸屬":             _s("責任歸屬"),
                                            "完成日期":             _coerce_date(_s("完成日期")),
                                            "負責人": (
                                                (creator_input or "").strip()
                                                if creator_input is not None
                                                else _s("負責人")
                                            ),
                                            "狀態":                 _s("狀態") or "處理中",
                                            "照片":                 _s("照片"),
                                            "廠商稽核":             audit_val,
                                            "處理狀態":             "待處理",
                                            "異常類別":             _s("異常類別"),
                                        })
                                        success_ids.append(rec_id)
                                    except Exception as e:
                                        fail_msgs.append(f"第 {i+2} 行：{e}")

                                progress.progress(1.0, text="完成！")
                                progress.empty()

                                if success_ids:
                                    st.success(
                                        f"🎉 成功匯入 **{len(success_ids)}** 筆 IQC 異常記錄！\n\n"
                                        f"記錄編號：`{success_ids[0]}` ～ `{success_ids[-1]}`"
                                    )
                                    # 匯入結果報告
                                    df_result = df_to_import.iloc[:len(success_ids)].copy()
                                    df_result.insert(0, "記錄編號", success_ids)
                                    buf = io.BytesIO()
                                    df_result.to_excel(buf, index=False)
                                    rc1, rc2 = st.columns(2)
                                    with rc1:
                                        st.download_button(
                                            "⬇️ 下載匯入結果報告",
                                            data=buf.getvalue(),
                                            file_name=f"IQC匯入結果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            use_container_width=True,
                                        )
                                    with rc2:
                                        if st.button("🏭 前往 SQM 異常管理", use_container_width=True):
                                            st.switch_page("pages/40_🏭_SQM異常登錄.py")

                                if fail_msgs:
                                    st.error(
                                        f"❌ {len(fail_msgs)} 筆寫入失敗：\n"
                                        + "\n".join(fail_msgs[:10])
                                        + ("…" if len(fail_msgs) > 10 else "")
                                    )
