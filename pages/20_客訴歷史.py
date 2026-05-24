"""
REXONTEC 力科品質指揮平台 — 客訴與8D管理系統
客訴歷史查詢
"""
import streamlit as st
import pandas as pd
import io
from datetime import datetime, date
from utils.cs_gsheet import (
    load_all_complaints, load_all_8d, CS_STATUS_LIST,
)
from utils.style import QMS_CSS, topbar, page_header

st.set_page_config(
    page_title="REXONTEC 力科 | 客訴歷史",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)

# ── 導覽列 ────────────────────────────────────────────
c0, c1, c2, c3, c4, c5, c6, _ = st.columns([1,1,1,1,1,1,1,2])
with c0:
    if st.button("🏠 指揮平台", use_container_width=True):
        st.switch_page("app.py")
with c1:
    if st.button("📢 客訴首頁", use_container_width=True):
        st.switch_page("pages/15_客訴8D系統.py")
with c2:
    if st.button("📝 客訴輸入", use_container_width=True):
        st.switch_page("pages/16_客訴輸入.py")
with c3:
    if st.button("📋 案件追蹤", use_container_width=True):
        st.switch_page("pages/17_客訴追蹤.py")
with c4:
    if st.button("📑 8D管理", use_container_width=True):
        st.switch_page("pages/18_8D管理.py")
with c5:
    if st.button("📊 KPI", use_container_width=True):
        st.switch_page("pages/19_客訴KPI.py")
with c6:
    if st.button("🔍 歷史查詢", use_container_width=True):
        st.switch_page("pages/20_客訴歷史.py")

st.markdown(
    page_header("客訴歷史查詢", "REXONTEC 力科 | Complaint History", "HST"),
    unsafe_allow_html=True,
)

# ── CSS ───────────────────────────────────────────────
st.markdown("""
<style>
.detail-field { padding:8px 0; border-bottom:1px solid var(--border); font-size:12.5px; }
.detail-label { width:100px; display:inline-block; font-weight:700;
                color:var(--muted); font-size:11px; }
.detail-val   { color:var(--text); font-weight:600; }
.d8-block     { background:#f8f9fa; border-left:4px solid var(--accent);
                border-radius:6px; padding:10px 14px; margin-top:6px;
                font-size:12px; line-height:1.8; }
.d8-line-lbl  { font-weight:700; color:var(--navy); }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=30, show_spinner="載入歷史資料...")
def get_data():
    return load_all_complaints(), load_all_8d()


_, ref_col = st.columns([10, 1])
with ref_col:
    if st.button("🔄", use_container_width=True, help="重新整理"):
        st.cache_data.clear(); st.rerun()

df_cs, df_8d = get_data()

if df_cs.empty:
    st.info("📭 尚無客訴資料。")
    if st.button("➕ 前往建立客訴"):
        st.switch_page("pages/16_客訴輸入.py")
    st.stop()

def _to_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y/%m/%d").date()
    except Exception:
        return None

df_cs["_d"] = df_cs["建立日期"].apply(_to_date)

# ════════════════════════════════════════════════════
# 篩選區
# ════════════════════════════════════════════════════
st.markdown('<div class="card"><div class="card-header"><div class="card-title">'
            '<span class="card-dot" style="background:var(--accent)"></span>'
            '進階篩選</div></div></div>', unsafe_allow_html=True)

f1, f2, f3 = st.columns([3, 2, 2])
with f1:
    kw = st.text_input("🔍 關鍵字", placeholder="客訴編號 / 客戶 / 機型 / SN/Lot",
                        label_visibility="collapsed")
with f2:
    sel_status = st.multiselect("流程狀態", CS_STATUS_LIST, placeholder="全部狀態",
                                 label_visibility="collapsed")
with f3:
    sel_type = st.multiselect(
        "客訴類型",
        ["機構異常","電子異常","軟體異常","性能異常","包裝標示","安全疑慮","服務品質","其他"],
        placeholder="全部類型", label_visibility="collapsed",
    )

f4, f5, f6 = st.columns([2, 2, 2])
with f4:
    sel_level = st.multiselect("客訴等級",
                                ["S1 重大","S2 高","S3 中","S4 低"],
                                placeholder="全部等級", label_visibility="collapsed")
with f5:
    sel_major = st.selectbox("重大客訴", ["全部","是","否"],
                              label_visibility="collapsed")
with f6:
    date_range = st.date_input(
        "日期範圍",
        value=[],
        label_visibility="collapsed",
        help="選擇建立日期範圍",
    )

# ── 套用篩選 ──────────────────────────────────────────
view = df_cs.copy()
if kw:
    mask = (
        view["客訴編號"].astype(str).str.contains(kw, case=False, na=False) |
        view["客戶名稱"].astype(str).str.contains(kw, case=False, na=False) |
        view["機型"].astype(str).str.contains(kw, case=False, na=False)     |
        view.get("SN/Lot", pd.Series(dtype=str)).astype(str).str.contains(kw, case=False, na=False)
    )
    view = view[mask]
if sel_status:
    view = view[view["流程狀態"].isin(sel_status)]
if sel_type:
    view = view[view["客訴類型"].isin(sel_type)]
if sel_level:
    view = view[view["客訴等級"].isin(sel_level)]
if sel_major != "全部":
    view = view[view["是否重大客訴"] == sel_major]
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    d_from, d_to = date_range
    view = view[(view["_d"] >= d_from) & (view["_d"] <= d_to)]

# ════════════════════════════════════════════════════
# 結果列表
# ════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f'<div style="font-size:12px;color:var(--muted);margin-bottom:8px">'
            f'找到 <b>{len(view)}</b> 筆 / 共 {len(df_cs)} 筆</div>',
            unsafe_allow_html=True)

# Excel 匯出
def _to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    try:
        import openpyxl
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            export_df = df.drop(columns=["_d"], errors="ignore")
            export_df.to_excel(writer, index=False, sheet_name="客訴清單")
    except ImportError:
        df.drop(columns=["_d"], errors="ignore").to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()

_, dl_col = st.columns([8, 2])
with dl_col:
    if not view.empty:
        excel_bytes = _to_excel(view)
        ext = "xlsx" if excel_bytes[:4] == b"PK\x03\x04" else "csv"
        st.download_button(
            f"⬇️ 匯出 {len(view)} 筆",
            data=excel_bytes,
            file_name=f"客訴歷史_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

if view.empty:
    st.info("沒有符合條件的資料。")
    st.stop()

DISPLAY_COLS = ["客訴編號","客戶名稱","機型","SN/Lot","客訴類型","客訴等級",
                "是否重大客訴","流程狀態","8D編號","建立日期","結案日期"]
show_df = view[[c for c in DISPLAY_COLS if c in view.columns]].reset_index(drop=True)

st.dataframe(
    show_df,
    use_container_width=True,
    hide_index=True,
    height=min(50 + len(show_df) * 35, 420),
    column_config={
        "客訴編號":     st.column_config.TextColumn("客訴編號", width=140),
        "客戶名稱":     st.column_config.TextColumn("客戶名稱", width=150),
        "是否重大客訴": st.column_config.TextColumn("重大", width=60),
        "流程狀態":     st.column_config.TextColumn("狀態", width=100),
        "8D編號":       st.column_config.TextColumn("8D編號", width=120),
        "建立日期":     st.column_config.TextColumn("建立日期", width=130),
        "結案日期":     st.column_config.TextColumn("結案日期", width=130),
    },
)

# ════════════════════════════════════════════════════
# 案件詳情展開
# ════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="card"><div class="card-header"><div class="card-title">'
            '<span class="card-dot" style="background:var(--orange)"></span>'
            '案件詳情</div></div></div>', unsafe_allow_html=True)

cs_options = view["客訴編號"].dropna().tolist()
sel_detail = st.selectbox(
    "選擇查看詳情",
    cs_options,
    format_func=lambda x: (
        f"{x}  ―  "
        + str(view[view["客訴編號"]==x]["客戶名稱"].values[0] if not view[view["客訴編號"]==x].empty else "")
    ),
    label_visibility="collapsed",
)

dr = view[view["客訴編號"] == sel_detail]
if dr.empty:
    st.stop()
r = dr.iloc[0].to_dict()

def _df(label, val, color="var(--text)"):
    return (f'<div class="detail-field">'
            f'<span class="detail-label">{label}</span>'
            f'<span class="detail-val" style="color:{color}">{val or "—"}</span>'
            f'</div>')

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        _df("客訴編號", r.get("客訴編號",""), "var(--accent)") +
        _df("客戶名稱", r.get("客戶名稱","")) +
        _df("機型",     r.get("機型",""))     +
        _df("SN/Lot",  r.get("SN/Lot",""))  +
        _df("飛行時數", r.get("飛行時數","")),
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        _df("客訴類型", r.get("客訴類型","")) +
        _df("客訴等級", r.get("客訴等級","")) +
        _df("重大客訴", "⚠️ 是" if r.get("是否重大客訴")=="是" else "否") +
        _df("負責人",   r.get("負責人",""))   +
        _df("8D編號",   r.get("8D編號",""), "var(--ma)"),
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        _df("流程狀態", r.get("流程狀態",""), "var(--teal)") +
        _df("客訴日期", r.get("客訴日期","")) +
        _df("建立日期", str(r.get("建立日期",""))[:16]) +
        _df("結案日期", str(r.get("結案日期",""))[:16]) +
        _df("備註",     r.get("備註","")),
        unsafe_allow_html=True,
    )

# 客訴描述
if r.get("客訴描述"):
    st.markdown(f"""
    <div style="background:#f8f9fa;border-left:4px solid var(--accent);border-radius:6px;
                padding:12px 16px;margin:12px 0;font-size:13px">
      <div style="font-size:10px;font-weight:700;color:var(--muted);margin-bottom:6px">客訴描述</div>
      {r['客訴描述']}
    </div>""", unsafe_allow_html=True)

# 附件連結
links_html = ""
if r.get("照片連結"):
    links_html += f'<a href="{r["照片連結"]}" target="_blank" style="margin-right:16px;font-size:12px">📷 查看照片</a>'
if r.get("影片連結"):
    links_html += f'<a href="{r["影片連結"]}" target="_blank" style="font-size:12px">🎥 查看影片</a>'
if links_html:
    st.markdown(links_html, unsafe_allow_html=True)

# 8D 詳情（若有）
d8_id = r.get("8D編號","")
if d8_id and not df_8d.empty:
    d8_row = df_8d[df_8d["8D編號"] == d8_id]
    if not d8_row.empty:
        d8 = d8_row.iloc[0].to_dict()
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;font-weight:800;color:var(--navy);margin-bottom:8px">'
                    f'📑 8D 記錄：{d8_id} '
                    f'<span style="font-size:11px;background:#e8f0fe;color:#1565c0;'
                    f'border:1px solid #90caf9;padding:2px 10px;border-radius:20px;font-weight:700">'
                    f'CAPA {d8.get("CAPA狀態","─")}</span></div>',
                    unsafe_allow_html=True)

        D8_FIELDS = [
            ("D1_團隊成員","D1 團隊組建"), ("D2_問題描述","D2 問題描述"),
            ("D3_臨時對策","D3 臨時對策"), ("D4_根因分析","D4 根因分析"),
            ("D5_永久改善","D5 永久改善"), ("D6_改善驗證","D6 改善驗證"),
            ("D7_預防措施","D7 預防再發"), ("D8_結案表揚","D8 結案表揚"),
        ]
        d8_html = '<div class="d8-block">'
        for col_name, label in D8_FIELDS:
            val = d8.get(col_name,"")
            if val:
                d8_html += f'<div style="margin-bottom:6px"><span class="d8-line-lbl">{label}：</span>{val}</div>'
        d8_html += "</div>"
        st.markdown(d8_html, unsafe_allow_html=True)

        # 8D 附件連結
        d8_links = ""
        if d8.get("驗證附件連結"):
            d8_links += f'<a href="{d8["驗證附件連結"]}" target="_blank" style="margin-right:14px;font-size:12px">📎 驗證附件</a>'
        if d8.get("熱像圖連結"):
            d8_links += f'<a href="{d8["熱像圖連結"]}" target="_blank" style="margin-right:14px;font-size:12px">🌡️ 熱像圖</a>'
        if d8.get("測試資料連結"):
            d8_links += f'<a href="{d8["測試資料連結"]}" target="_blank" style="font-size:12px">📊 測試資料</a>'
        if d8_links:
            st.markdown(d8_links, unsafe_allow_html=True)
