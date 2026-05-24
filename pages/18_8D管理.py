"""
REXONTEC 力科品質指揮平台 — 客訴與8D管理系統
8D 改善管理（完整版）
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date

from utils.cs_gsheet import (
    load_all_complaints, load_all_8d,
    append_8d, update_8d, update_cs_status, DONE_STATUS,
)
from utils.style import QMS_CSS, topbar, page_header

try:
    from utils.cs_pdf_report import generate_8d_pdf
    HAS_PDF = True
except Exception:
    HAS_PDF = False

try:
    from utils.cs_drive_upload import upload_8d_files, get_folder_link, HAS_DRIVE
except Exception:
    HAS_DRIVE = False
    def upload_8d_files(*a, **k): return []
    def get_folder_link(*a, **k): return ""

st.set_page_config(
    page_title="REXONTEC 力科 | 8D管理",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)

# ── 導覽列 ────────────────────────────────────────────
c0,c1,c2,c3,c4,c5,c6,_ = st.columns([1,1,1,1,1,1,1,2])
with c0:
    if st.button("🏠 指揮平台", use_container_width=True): st.switch_page("app.py")
with c1:
    if st.button("📢 客訴首頁", use_container_width=True): st.switch_page("pages/15_客訴8D系統.py")
with c2:
    if st.button("📝 客訴輸入", use_container_width=True): st.switch_page("pages/16_客訴輸入.py")
with c3:
    if st.button("📋 案件追蹤", use_container_width=True): st.switch_page("pages/17_客訴追蹤.py")
with c4:
    if st.button("📑 8D管理",   use_container_width=True): st.switch_page("pages/18_8D管理.py")
with c5:
    if st.button("📊 KPI",      use_container_width=True): st.switch_page("pages/19_客訴KPI.py")
with c6:
    if st.button("🔍 歷史查詢", use_container_width=True): st.switch_page("pages/20_客訴歷史.py")

st.markdown(page_header("8D 改善管理", "REXONTEC 力科 | 8D Problem Solving", "8D"),
            unsafe_allow_html=True)

# ── CSS ───────────────────────────────────────────────
st.markdown("""
<style>
.d8-section { background:#fff; border:1px solid var(--border);
  border-radius:10px; padding:14px 18px 10px; margin-bottom:12px;
  box-shadow:var(--sh); }
.d8-hdr { display:flex; align-items:center; gap:10px; margin-bottom:10px;
  padding-bottom:8px; border-bottom:2px solid var(--border); }
.d8-badge { width:32px; height:32px; border-radius:50%; display:flex;
  align-items:center; justify-content:center; color:#fff;
  font-weight:900; font-size:13px; flex-shrink:0; }
.d8-htitle { font-size:13px; font-weight:800; color:var(--navy); }
.d8-hsub   { font-size:10px; color:var(--muted); }
.info-lbl  { font-size:10px; font-weight:700; color:var(--muted);
  text-transform:uppercase; letter-spacing:.8px; margin-bottom:3px; }
.bind-badge { background:#e8f0fe; color:#1565c0; border:1px solid #90caf9;
  padding:4px 14px; border-radius:20px; font-size:12px; font-weight:700;
  display:inline-block; }
.upload-chip { background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px;
  padding:4px 10px; font-size:11px; color:#15803d; margin:2px 2px 2px 0; display:inline-block; }
</style>
""", unsafe_allow_html=True)

D8_CFG = [
    ("D1","問題處理小組","PROBLEM SOLVING TEAM",          "d1",(21,101,192),
     "列出8D團隊成員與各單位職責，例：\n製造單位：○○○\n開發單位：○○○\n品保單位：○○○"),
    ("D2","問題敘述",    "PROBLEM DESCRIPTION",           "d2",(40,53,147),
     "事故原因 / 飛行條件 / 失效現象（5W2H 具體描述）"),
    ("D3","緊急對策",    "CONTAINMENT ACTION",            "d3",(106,27,154),
     "立即防止問題擴大的應急措施，例：庫存管制、出貨加固…"),
    ("D4","問題真因",    "ROOT CAUSE",                    "d4",(173,20,87),
     "魚骨圖 / 5Why / FMEA 分析根本原因"),
    ("D5","矯正措施",    "CORRECTIVE ACTION",             "d5",(183,28,28),
     "針對根因制定長期解決方案"),
    ("D6","改善驗證",    "CORRECTIVE ACTION VERIFICATION","d6",(230,101,0),
     "實驗條件 / 測試結果 / 結論"),
    ("D7","永久預防",    "PERMANENT PREVENTIVE ACTION",   "d7",(46,125,50),
     "SOP更新 / 品質看板 / 巡檢稽核"),
    ("D8","小組評論",    "TEAM MEMBER COMMENTS",          "d8",(0,105,92),
     "改善成效總結 / 感謝詞 / 結案日期"),
]


def _badge(code, rgb):
    r,g,b = rgb
    return (f'<div class="d8-badge" style="background:rgb({r},{g},{b})">{code}</div>')

def _sec_hdr(code, zh, en, rgb):
    r,g,b = rgb
    return (f'<div class="d8-hdr">'
            f'{_badge(code,rgb)}'
            f'<div><div class="d8-htitle">{zh}</div>'
            f'<div class="d8-hsub" style="color:rgb({r},{g},{b})">{en}</div></div>'
            f'</div>')


@st.cache_data(ttl=30, show_spinner="載入資料…")
def _load():
    return load_all_complaints(), load_all_8d()


_, ref_col = st.columns([11,1])
with ref_col:
    if st.button("🔄", help="重新整理", use_container_width=True):
        st.cache_data.clear(); st.rerun()

df_cs, df_8d = _load()

if df_cs.empty:
    st.info("尚無客訴案件，請先建立客訴。")
    if st.button("➕ 前往建立客訴"):
        st.switch_page("pages/16_客訴輸入.py")
    st.stop()

# ════════════════════════════════════════════════════
# 版面：左側選案件 | 右側 Tabs
# ════════════════════════════════════════════════════
left, right = st.columns([1, 2.5])

# ── 左側：客訴案件列表 ──────────────────────────────
with left:
    st.markdown('<div class="card"><div class="card-header"><div class="card-title">'
                '<span class="card-dot" style="background:var(--accent)"></span>'
                '選擇客訴案件</div></div></div>', unsafe_allow_html=True)

    show_all = st.checkbox("含已結案", value=False)
    kw_cs    = st.text_input("🔍", placeholder="搜尋客訴/客戶/機型",
                              label_visibility="collapsed")

    vcs = df_cs.copy()
    if not show_all:
        vcs = vcs[~vcs["流程狀態"].isin(DONE_STATUS)]
    if kw_cs:
        m = (vcs["客訴編號"].astype(str).str.contains(kw_cs,case=False,na=False) |
             vcs["客戶名稱"].astype(str).str.contains(kw_cs,case=False,na=False) |
             vcs["機型"].astype(str).str.contains(kw_cs,case=False,na=False))
        vcs = vcs[m]

    if vcs.empty:
        st.info("無符合案件。"); st.stop()

    sel_cs = st.radio(
        "案件",
        vcs["客訴編號"].tolist(),
        format_func=lambda x: (
            f"{x}\n"
            + str(vcs[vcs["客訴編號"]==x]["客戶名稱"].values[0] if not vcs[vcs["客訴編號"]==x].empty else "")
            + "  "
            + str(vcs[vcs["客訴編號"]==x]["流程狀態"].values[0] if not vcs[vcs["客訴編號"]==x].empty else "")
        ),
        label_visibility="collapsed",
    )

# ── 右側 ──────────────────────────────────────────────
with right:
    cs_row = df_cs[df_cs["客訴編號"] == sel_cs]
    if cs_row.empty:
        st.warning("找不到案件資料。"); st.stop()
    cs = cs_row.iloc[0].to_dict()

    # 取現有 8D
    d8_id_exist = cs.get("8D編號","")
    ex8d: dict = {}
    if d8_id_exist and not df_8d.empty:
        rows = df_8d[df_8d["8D編號"] == d8_id_exist]
        if not rows.empty:
            ex8d = rows.iloc[0].to_dict()

    is_edit = bool(ex8d)
    mode_label = "✏️ 編輯" if is_edit else "🆕 新建"

    # 綁定資訊
    if is_edit:
        st.markdown(
            f'<div style="margin-bottom:10px">'
            f'<span class="bind-badge">CS ↔ 8D</span>&nbsp;'
            f'<span style="font-family:monospace;font-weight:700;color:var(--accent)">{sel_cs}</span>'
            f' &nbsp;↔&nbsp; '
            f'<span style="font-family:monospace;font-weight:700;color:#6a1b9a">{d8_id_exist}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Tabs ────────────────────────────────────────
    tab_form, tab_pdf, tab_overview = st.tabs(["📋 8D 表單", "📄 PDF 輸出", "📊 記錄總覽"])

    # ════════════════════════════════════════════════
    # TAB 1：8D 表單
    # ════════════════════════════════════════════════
    with tab_form:

        with st.form(f"d8_full_{sel_cs}", clear_on_submit=False):

            # ── 基本資訊（比照 Excel 表頭）─────────────
            st.markdown('<div class="d8-section">'
                        '<div class="d8-hdr"><div class="d8-htitle">📋 基本資訊</div></div>',
                        unsafe_allow_html=True)

            bi1,bi2,bi3 = st.columns([2,2,1])
            with bi1:
                st.markdown('<div class="info-lbl">客戶名稱</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-weight:700;padding:4px 0">{cs.get("客戶名稱","")}</div>',
                            unsafe_allow_html=True)
            with bi2:
                st.markdown('<div class="info-lbl">機種 / 型號</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:12px;padding:4px 0">{cs.get("機型","")}</div>',
                            unsafe_allow_html=True)
            with bi3:
                st.markdown('<div class="info-lbl">客訴等級</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-weight:700;padding:4px 0">{cs.get("客訴等級","")}</div>',
                            unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            bi4,bi5,bi6,bi7,bi8 = st.columns([2,2,1,2,2])
            with bi4:
                mo_number = st.text_input("M/O 編號",
                    value=ex8d.get("M/O編號","") or cs.get("SN/Lot",""),
                    placeholder="製造工單編號")
            with bi5:
                batch = st.text_input("批量",
                    value=ex8d.get("批量","1"), placeholder="1")
            with bi6:
                ship_date = st.text_input("出貨日期",
                    value=ex8d.get("出貨日期","") or cs.get("客訴日期",""),
                    placeholder="2026.3.20")
            with bi7:
                complaint_method = st.selectbox("抱怨方式",
                    ["E-mail","電話","書面報告","現場反映","其他"],
                    index=0 if not ex8d.get("抱怨方式") else
                          ["E-mail","電話","書面報告","現場反映","其他"].index(ex8d.get("抱怨方式","E-mail"))
                          if ex8d.get("抱怨方式","E-mail") in ["E-mail","電話","書面報告","現場反映","其他"] else 0)
            with bi8:
                first_recur = st.radio("首發 / 再發",
                    ["首發","再發"], horizontal=True,
                    index=0 if ex8d.get("首發再發","首發")=="首發" else 1)

            st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:4px 0'>",
                        unsafe_allow_html=True)

            # ── D1–D8 ───────────────────────────────
            d_vals = {}
            for code, zh, en, key, rgb, ph in D8_CFG:
                st.markdown(f'<div class="d8-section">'
                            f'{_sec_hdr(code,zh,en,rgb)}',
                            unsafe_allow_html=True)

                col_name = {
                    "d1":"D1_團隊成員","d2":"D2_問題描述","d3":"D3_臨時對策",
                    "d4":"D4_根因分析","d5":"D5_永久改善","d6":"D6_改善驗證",
                    "d7":"D7_預防措施","d8":"D8_結案表揚",
                }[key]

                d_vals[key] = st.text_area(
                    f"{code} 內容",
                    value=ex8d.get(col_name,""),
                    height=110,
                    placeholder=ph,
                    label_visibility="collapsed",
                    key=f"{key}_{sel_cs}",
                )
                st.markdown("</div>", unsafe_allow_html=True)

            # ── 附件上傳 ────────────────────────────
            st.markdown('<div class="d8-section"><div class="d8-hdr">'
                        '<div class="d8-htitle">📎 附件上傳</div></div>',
                        unsafe_allow_html=True)

            ua1, ua2 = st.columns(2)
            with ua1:
                st.markdown("**📷 照片**（D2/D3 現場/改善照）")
                photo_files = st.file_uploader(
                    "照片", type=["jpg","jpeg","png","gif","bmp"],
                    accept_multiple_files=True, label_visibility="collapsed",
                    key=f"photo_{sel_cs}")
                photo_url_manual = st.text_input(
                    "或貼上 Drive 連結",
                    value=ex8d.get("照片連結",""),
                    placeholder="https://drive.google.com/...",
                    key=f"photo_url_{sel_cs}")

                st.markdown("**🌡️ 熱像圖**（FLIR 熱顯像）")
                thermal_files = st.file_uploader(
                    "熱像圖", type=["jpg","jpeg","png","pdf","csv"],
                    accept_multiple_files=True, label_visibility="collapsed",
                    key=f"thermal_{sel_cs}")
                thermal_url_manual = st.text_input(
                    "或貼上 Drive 連結",
                    value=ex8d.get("熱像圖連結",""),
                    placeholder="https://drive.google.com/...",
                    key=f"thermal_url_{sel_cs}")

            with ua2:
                st.markdown("**📎 驗證附件**（D6 實驗報告）")
                attach_files = st.file_uploader(
                    "驗證附件", type=["pdf","xlsx","docx","jpg","png","csv","zip"],
                    accept_multiple_files=True, label_visibility="collapsed",
                    key=f"attach_{sel_cs}")
                attach_url_manual = st.text_input(
                    "或貼上 Drive 連結",
                    value=ex8d.get("驗證附件連結",""),
                    placeholder="https://drive.google.com/...",
                    key=f"attach_url_{sel_cs}")

                st.markdown("**📊 測試資料**（量測數據）")
                test_files = st.file_uploader(
                    "測試資料", type=["pdf","xlsx","csv","txt","zip"],
                    accept_multiple_files=True, label_visibility="collapsed",
                    key=f"test_{sel_cs}")
                test_url_manual = st.text_input(
                    "或貼上 Drive 連結",
                    value=ex8d.get("測試資料連結",""),
                    placeholder="https://drive.google.com/...",
                    key=f"test_url_{sel_cs}")

            st.markdown("</div>", unsafe_allow_html=True)

            # ── CAPA & 簽核 ─────────────────────────
            st.markdown('<div class="d8-section"><div class="d8-hdr">'
                        '<div class="d8-htitle">✅ CAPA 追蹤 & 簽核</div></div>',
                        unsafe_allow_html=True)

            ca1,ca2,ca3 = st.columns(3)
            with ca1:
                capa_status = st.selectbox("CAPA 狀態",
                    ["進行中","待驗證","完成"],
                    index=["進行中","待驗證","完成"].index(ex8d.get("CAPA狀態","進行中"))
                          if ex8d.get("CAPA狀態","進行中") in ["進行中","待驗證","完成"] else 0)
                owner_8d = st.text_input("負責人",
                    value=ex8d.get("負責人","") or cs.get("負責人",""))
            with ca2:
                approver = st.text_input("核准人",  value=ex8d.get("核准人",""))
                reviewer = st.text_input("審核人",  value=ex8d.get("審核人",""))
            with ca3:
                handler  = st.text_input("經辦人",  value=ex8d.get("經辦人",""))
                sop_ref  = st.text_input("SOP 參考",
                    value=ex8d.get("SOP參考",""),
                    placeholder="SOP-SL4010")

            st.markdown("</div>", unsafe_allow_html=True)

            # ── 提交 ────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            b1, b2, b3 = st.columns([1,2,1])
            with b2:
                lbl = "💾 儲存 8D" if is_edit else "📋 建立 8D 報告"
                do_submit = st.form_submit_button(lbl, type="primary",
                                                   use_container_width=True)

        # ── 表單提交處理 ──────────────────────────────
        if do_submit:
            d8_target = d8_id_exist if is_edit else None

            with st.spinner("上傳附件中..."):
                # Drive 上傳
                folder_key = d8_target or f"8D-TEMP-{sel_cs}"
                p_urls  = upload_8d_files(photo_files,   folder_key, "照片")   if photo_files  else []
                a_urls  = upload_8d_files(attach_files,  folder_key, "驗證附件") if attach_files else []
                th_urls = upload_8d_files(thermal_files, folder_key, "熱像圖")  if thermal_files else []
                te_urls = upload_8d_files(test_files,    folder_key, "測試資料") if test_files  else []

            # 合併 URL（Drive上傳 優先；否則用手填）
            def _merge(drive_list, manual_val):
                if drive_list:
                    return " , ".join(drive_list)
                return manual_val.strip()

            payload = {
                "d1": d_vals["d1"], "d2": d_vals["d2"], "d3": d_vals["d3"],
                "d4": d_vals["d4"], "d5": d_vals["d5"], "d6": d_vals["d6"],
                "d7": d_vals["d7"], "d8": d_vals["d8"],
                "capa_status":      capa_status,
                "owner":            owner_8d,
                "photo_url":        _merge(p_urls,  photo_url_manual),
                "attach_url":       _merge(a_urls,  attach_url_manual),
                "thermal_url":      _merge(th_urls, thermal_url_manual),
                "test_url":         _merge(te_urls, test_url_manual),
                "mo_number":        mo_number,
                "batch":            batch,
                "ship_date":        ship_date,
                "complaint_method": complaint_method,
                "first_recur":      first_recur,
                "approver":         approver,
                "reviewer":         reviewer,
                "handler":          handler,
                "sop_ref":          sop_ref,
            }

            with st.spinner("寫入 Google Sheet..."):
                try:
                    if is_edit:
                        ok = update_8d(d8_target, payload)
                        if capa_status == "完成":
                            update_cs_status(sel_cs, "改善驗證")
                        if ok:
                            st.success(f"✅ 8D【{d8_target}】已更新！")
                    else:
                        new_id = append_8d(sel_cs, payload)
                        update_cs_status(sel_cs, "8D開立")
                        st.success(f"✅ 8D【{new_id}】建立成功！已關聯 {sel_cs}")
                        # 顯示綁定
                        st.markdown(
                            f'<div style="margin:8px 0">'
                            f'<span class="bind-badge">{sel_cs} ↔ {new_id}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    st.cache_data.clear()
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ 操作失敗：{ex}")
                    st.exception(ex)

    # ════════════════════════════════════════════════
    # TAB 2：PDF 輸出
    # ════════════════════════════════════════════════
    with tab_pdf:
        if not is_edit:
            st.info("請先建立 8D 記錄，再產生 PDF。")
        elif not HAS_PDF:
            st.error("❌ PDF 套件未安裝（fpdf2）")
        else:
            st.markdown(f"""
            <div style="background:#f8f9fa;border:1px solid var(--border);border-radius:10px;
                        padding:18px 20px;margin-bottom:16px">
              <div style="font-size:12px;font-weight:700;color:var(--muted);margin-bottom:10px">PDF 預覽資訊</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12.5px">
                <div><span style="color:var(--muted)">8D 編號：</span><b style="color:#6a1b9a">{d8_id_exist}</b></div>
                <div><span style="color:var(--muted)">客訴編號：</span><b style="color:var(--accent)">{sel_cs}</b></div>
                <div><span style="color:var(--muted)">客戶：</span><b>{cs.get('客戶名稱','')}</b></div>
                <div><span style="color:var(--muted)">CAPA：</span><b>{ex8d.get('CAPA狀態','')}</b></div>
                <div><span style="color:var(--muted)">負責人：</span><b>{ex8d.get('負責人','')}</b></div>
                <div><span style="color:var(--muted)">結案日期：</span><b>{str(ex8d.get('結案日期',''))[:10]}</b></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # 從 ex8d 組合 cs_data（含 PDF 需要的額外欄位）
            cs_for_pdf = {
                **cs,
                "mo_number":  ex8d.get("M/O編號","") or cs.get("SN/Lot",""),
                "批量":        ex8d.get("批量",""),
                "出貨日期":    ex8d.get("出貨日期",""),
                "抱怨方式":    ex8d.get("抱怨方式",""),
                "首發再發":    ex8d.get("首發再發",""),
                "核准":        ex8d.get("核准人",""),
                "審核":        ex8d.get("審核人",""),
                "經辦":        ex8d.get("經辦人",""),
                "SOP參考":     ex8d.get("SOP參考",""),
            }

            if st.button("📄　產生完整 8D PDF 報告", type="primary",
                         use_container_width=True):
                with st.spinner("產生 PDF 中..."):
                    try:
                        pdf_bytes = generate_8d_pdf(cs_for_pdf, ex8d)
                        fname = (f"8D報告_{d8_id_exist}_"
                                 f"{cs.get('客戶名稱','')}_{datetime.now().strftime('%Y%m%d')}.pdf")
                        st.download_button(
                            f"⬇️  下載 {fname}",
                            data=pdf_bytes,
                            file_name=fname,
                            mime="application/pdf",
                            use_container_width=True,
                        )
                        st.success(f"✅ PDF 已產生！大小：{len(pdf_bytes)/1024:.1f} KB")
                    except Exception as ex:
                        st.error(f"❌ PDF 產生失敗：{ex}")
                        st.exception(ex)

            # Drive 資料夾連結
            if HAS_DRIVE and d8_id_exist:
                folder_url = get_folder_link(d8_id_exist)
                if folder_url:
                    st.markdown(f"""
                    <div style="background:#e8f4fd;border:1px solid #90caf9;border-radius:8px;
                                padding:10px 16px;margin-top:10px;font-size:12px">
                      📁 <b>Drive 附件資料夾：</b>
                      <a href="{folder_url}" target="_blank">{folder_url}</a>
                    </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════
    # TAB 3：8D 記錄總覽
    # ════════════════════════════════════════════════
    with tab_overview:
        if df_8d.empty:
            st.info("尚無 8D 記錄。")
        else:
            show_cols = ["8D編號","客訴編號","CAPA狀態","負責人",
                         "M/O編號","批量","出貨日期","建立日期","結案日期"]
            disp = df_8d[[c for c in show_cols if c in df_8d.columns]].copy()

            # CAPA 顏色標記
            def _capa_icon(v):
                return {"完成":"✅ 完成","進行中":"🔵 進行中","待驗證":"🟡 待驗證"}.get(v,v)
            if "CAPA狀態" in disp.columns:
                disp["CAPA狀態"] = disp["CAPA狀態"].apply(_capa_icon)

            st.dataframe(disp, use_container_width=True, hide_index=True,
                         height=min(50 + len(disp)*38, 420))

            # 選擇查看 D1-D8 全文
            if not df_8d.empty:
                st.markdown("<br>", unsafe_allow_html=True)
                sel_8d_view = st.selectbox(
                    "查看 8D 完整內容",
                    df_8d["8D編號"].tolist(),
                    label_visibility="collapsed",
                )
                d8v = df_8d[df_8d["8D編號"]==sel_8d_view]
                if not d8v.empty:
                    vr = d8v.iloc[0].to_dict()
                    D8_COLS_MAP = [
                        ("D1_團隊成員","D1 問題處理小組"),
                        ("D2_問題描述","D2 問題敘述"),
                        ("D3_臨時對策","D3 緊急對策"),
                        ("D4_根因分析","D4 問題真因"),
                        ("D5_永久改善","D5 矯正措施"),
                        ("D6_改善驗證","D6 改善驗證"),
                        ("D7_預防措施","D7 永久預防"),
                        ("D8_結案表揚","D8 小組評論"),
                    ]
                    for col_k, label in D8_COLS_MAP:
                        val = vr.get(col_k,"")
                        if val:
                            with st.expander(label, expanded=False):
                                st.text(val)
