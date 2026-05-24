"""
REXONTEC 力科品質指揮平台 — 客訴與8D管理系統首頁
Customer Complaint & 8D Management System
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from utils.style import QMS_CSS, topbar, page_header

st.set_page_config(
    page_title="REXONTEC 力科 | 客訴與8D管理",
    page_icon="📢",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)

# ── 導覽列 ────────────────────────────────────
def _nav():
    c0, c1, c2, c3, c4, c5, _ = st.columns([1,1,1,1,1,1,2])
    with c0:
        if st.button("🏠 指揮平台", use_container_width=True):
            st.switch_page("app.py")
    with c1:
        if st.button("📝 客訴輸入", use_container_width=True):
            st.switch_page("pages/16_客訴輸入.py")
    with c2:
        if st.button("📋 案件追蹤", use_container_width=True):
            st.switch_page("pages/17_客訴追蹤.py")
    with c3:
        if st.button("📑 8D管理", use_container_width=True):
            st.switch_page("pages/18_8D管理.py")
    with c4:
        if st.button("📊 KPI", use_container_width=True):
            st.switch_page("pages/19_客訴KPI.py")
    with c5:
        if st.button("🔍 歷史查詢", use_container_width=True):
            st.switch_page("pages/20_客訴歷史.py")

_nav()

st.markdown(
    page_header("客訴與8D管理系統",
                "REXONTEC 力科 | Customer Complaint & 8D Management System", "CS"),
    unsafe_allow_html=True,
)

# ── 儀表板 CSS ────────────────────────────────
st.markdown("""
<style>
.cs-kpi {
  background:#fff; border:1px solid var(--border);
  border-radius:10px; padding:16px 18px 14px;
  box-shadow:var(--sh); position:relative; overflow:hidden;
}
.cs-kpi::before {
  content:''; position:absolute; top:0; left:0;
  width:4px; height:100%; background:var(--accent);
}
.cs-kpi.k-red::before    { background:var(--cr); }
.cs-kpi.k-orange::before { background:var(--ma); }
.cs-kpi.k-green::before  { background:var(--pass); }
.cs-kpi.k-purple::before { background:#7b1fa2; }
.cs-kpi.k-navy::before   { background:var(--navy); }
.cs-kpi-label { font-size:10px; font-weight:700; color:var(--muted);
                text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }
.cs-kpi-val   { font-size:30px; font-weight:700; color:var(--text);
                font-family:'DM Mono',monospace; line-height:1; }
.cs-kpi-sub   { font-size:11px; color:var(--muted); margin-top:4px; }
.cs-kpi-dim   { font-size:9px; color:var(--dim); margin-top:3px; letter-spacing:.5px; }

.flow-step {
  display:flex; align-items:center; gap:0;
}
.flow-box {
  flex:1; text-align:center; padding:8px 4px;
  background:#fff; border:1px solid var(--border);
  border-radius:6px; font-size:11px; font-weight:700; color:var(--muted);
}
.flow-box.active { background:var(--accent); color:#fff; border-color:var(--accent); }
.flow-box.done   { background:var(--pass);   color:#fff; border-color:var(--pass); }
.flow-arrow { color:var(--border2); font-size:14px; padding:0 2px; flex-shrink:0; }

.cs-entry-card {
  background:#fff; border:1px solid var(--border); border-radius:12px;
  padding:22px 18px 16px; box-shadow:var(--sh);
  border-left:5px solid var(--accent);
}
.cs-entry-card .ce-icon  { font-size:30px; margin-bottom:8px; }
.cs-entry-card .ce-title { font-size:14px; font-weight:800; color:var(--navy); margin-bottom:5px; }
.cs-entry-card .ce-desc  { font-size:12px; color:var(--muted); line-height:1.6; }
</style>
""", unsafe_allow_html=True)

# ── 資料載入 ─────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def _load():
    try:
        from utils.cs_gsheet import load_all_complaints, load_all_8d, DONE_STATUS
        df_cs = load_all_complaints()
        df_8d = load_all_8d()
        return df_cs, df_8d, True
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), False

df_cs, df_8d, data_ok = _load()

col_ref, col_btn = st.columns([10, 1])
with col_btn:
    if st.button("🔄", use_container_width=True, help="重新整理"):
        st.cache_data.clear(); st.rerun()

# ── KPI 計算 ──────────────────────────────────
if data_ok and not df_cs.empty:
    from utils.cs_gsheet import DONE_STATUS
    today = datetime.now()
    try:
        df_cs["_date"] = pd.to_datetime(df_cs["建立日期"].astype(str).str[:10], errors="coerce")
        month_start    = today.replace(day=1)
        this_month     = df_cs[df_cs["_date"] >= pd.Timestamp(month_start)]
    except Exception:
        this_month = df_cs

    total_month = len(this_month)
    open_cs     = df_cs[~df_cs["流程狀態"].isin(DONE_STATUS)]
    major_cs    = df_cs[df_cs["是否重大客訴"] == "是"]
    open_8d     = df_8d[~df_8d["CAPA狀態"].isin({"完成","關閉"})] if not df_8d.empty else pd.DataFrame()

    # 超期（超過7天未結案）
    def _overdue(row):
        if row.get("流程狀態") in DONE_STATUS: return False
        try:
            dt = pd.to_datetime(str(row.get("建立日期",""))[:10], errors="coerce")
            return (today - dt.to_pydatetime()).days > 7
        except Exception:
            return False
    overdue_cs = open_cs[open_cs.apply(_overdue, axis=1)] if not open_cs.empty else pd.DataFrame()

    kpi_vals = {
        "本月客訴": total_month,
        "未結案":   len(open_cs),
        "重大客訴": len(major_cs),
        "未結案8D": len(open_8d),
        "超期案件": len(overdue_cs),
    }
    has_data = True
else:
    kpi_vals = {k: "─" for k in ["本月客訴","未結案","重大客訴","未結案8D","超期案件"]}
    has_data = False

# ── ① KPI 統計卡 ──────────────────────────────
st.markdown("""
<div style="font-size:13px;font-weight:700;color:var(--navy);
border-left:4px solid var(--accent);padding-left:10px;margin:4px 0 14px">
📊 客訴指標總覽
</div>""", unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)
_kpi_defs = [
    (k1, "本月客訴",  "本月新增案件", ""),
    (k2, "未結案",    "進行中案件",   "k-orange"),
    (k3, "重大客訴",  "S1/S2 等級",   "k-red"),
    (k4, "未結案8D",  "進行中改善",   "k-purple"),
    (k5, "超期案件",  "超過 7 天",    "k-navy"),
]
for col, key, sub, cls in _kpi_defs:
    val = kpi_vals[key]
    with col:
        pending = "" if has_data else '<div class="cs-kpi-dim">等待資料累積中</div>'
        st.markdown(f"""
        <div class="cs-kpi {cls}">
          <div class="cs-kpi-label">{key}</div>
          <div class="cs-kpi-val">{val}</div>
          <div class="cs-kpi-sub">{sub}</div>
          {pending}
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── ② 流程狀態追蹤示意 ───────────────────────
st.markdown("""
<div style="font-size:13px;font-weight:700;color:var(--navy);
border-left:4px solid var(--blue2);padding-left:10px;margin:4px 0 12px">
🔄 標準處理流程
</div>""", unsafe_allow_html=True)

_steps = ["客訴建立","品保確認","RD分析","原因分析","8D開立","改善驗證","客戶回覆","結案"]
_flow_html = '<div style="display:flex;align-items:center;gap:0;margin-bottom:18px">'
for i, step in enumerate(_steps):
    _flow_html += f'<div style="flex:1;text-align:center;padding:9px 4px;background:#fff;border:1px solid var(--border);border-radius:6px;font-size:11px;font-weight:700;color:var(--muted)">{step}</div>'
    if i < len(_steps) - 1:
        _flow_html += '<div style="color:var(--border2);font-size:16px;padding:0 3px;flex-shrink:0">›</div>'
_flow_html += '</div>'
st.markdown(_flow_html, unsafe_allow_html=True)

# ── ③ 趨勢 & Pareto 佔位 ──────────────────────
_t_col, _p_col = st.columns(2)

_placeholder = """
<div style="background:#fafbfc;border:1px dashed var(--border2);border-radius:8px;
            padding:44px 20px;text-align:center;color:var(--dim)">
  <div style="font-size:36px;margin-bottom:10px">{icon}</div>
  <div style="font-size:12px;font-weight:600;color:var(--muted)">{title}</div>
  <div style="font-size:11px;margin-top:5px">等待資料累積中</div>
</div>"""

with _t_col:
    st.markdown("""<div style="font-size:13px;font-weight:700;color:var(--navy);
    border-left:4px solid var(--blue2);padding-left:10px;margin:4px 0 10px">
    📈 月趨勢分析</div>""", unsafe_allow_html=True)

    if has_data and not df_cs.empty and "_date" in df_cs.columns:
        import plotly.graph_objects as go
        mc = df_cs.dropna(subset=["_date"])
        mc["_m"] = mc["_date"].dt.strftime("%Y-%m")
        mc2 = mc.groupby("_m").size().reset_index(name="cnt").sort_values("_m")
        fig = go.Figure()
        fig.add_bar(x=mc2["_m"].tolist(), y=mc2["cnt"].tolist(),
                    marker_color="#1e88e5", name="客訴量")
        fig.update_layout(
            paper_bgcolor="#fff", plot_bgcolor="#f7f9fc",
            height=240, margin=dict(l=40,r=10,t=10,b=40),
            font=dict(color="#1a2332",size=11),
            xaxis=dict(type="category", tickangle=-30),
            yaxis_title="件數",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    else:
        st.markdown(_placeholder.format(icon="📈", title="客訴月趨勢圖"), unsafe_allow_html=True)

with _p_col:
    st.markdown("""<div style="font-size:13px;font-weight:700;color:var(--navy);
    border-left:4px solid var(--orange);padding-left:10px;margin:4px 0 10px">
    📉 客訴類型 Pareto</div>""", unsafe_allow_html=True)

    if has_data and not df_cs.empty and "客訴類型" in df_cs.columns:
        import plotly.graph_objects as go
        tc = df_cs["客訴類型"].value_counts().reset_index()
        tc.columns = ["類型","數量"]
        tc["累積%"] = (tc["數量"].cumsum() / tc["數量"].sum() * 100).round(1)
        fig2 = go.Figure()
        fig2.add_bar(x=tc["類型"].tolist(), y=tc["數量"].tolist(),
                     marker_color="#1e88e5", name="件數")
        fig2.add_scatter(x=tc["類型"].tolist(), y=tc["累積%"].tolist(),
                         mode="lines+markers", name="累積%",
                         line=dict(color="#c0392b",width=2),
                         yaxis="y2")
        fig2.update_layout(
            paper_bgcolor="#fff", plot_bgcolor="#f7f9fc",
            height=240, margin=dict(l=40,r=60,t=10,b=40),
            font=dict(color="#1a2332",size=11),
            xaxis=dict(tickangle=-30),
            yaxis=dict(title="件數"),
            yaxis2=dict(overlaying="y",side="right",range=[0,105],ticksuffix="%"),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
    else:
        st.markdown(_placeholder.format(icon="📉", title="客訴類型 Pareto 分析"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── ④ 品質風險警示 ───────────────────────────
st.markdown("""<div style="font-size:13px;font-weight:700;color:var(--navy);
border-left:4px solid var(--cr);padding-left:10px;margin:4px 0 12px">
⚠️ 品質風險警示</div>""", unsafe_allow_html=True)

if has_data and not df_cs.empty and len(overdue_cs) > 0:
    for _, row in overdue_cs.head(3).iterrows():
        lvl = row.get("客訴等級","")
        clr = {"S1 重大":"var(--cr)","S2 高":"var(--ma)"}.get(lvl, "var(--accent)")
        st.markdown(f"""
        <div style="background:#fff8f7;border:1px solid var(--cr-bd);border-left:4px solid var(--cr);
                    border-radius:6px;padding:10px 16px;margin-bottom:8px;
                    display:flex;align-items:center;gap:12px">
          <span style="font-size:18px">🚨</span>
          <div style="flex:1">
            <span style="font-weight:700;color:var(--cr);font-size:13px">{row.get('客訴編號','')}</span>
            &nbsp;<span style="font-size:11px;color:var(--muted)">{row.get('客戶名稱','')} | {row.get('客訴類型','')}</span>
          </div>
          <span style="background:{clr};color:#fff;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700">{lvl}</span>
          <span style="font-size:11px;color:var(--cr);font-weight:700">{row.get('流程狀態','')}</span>
        </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:#fafbfc;border:1px dashed var(--border2);border-radius:8px;
                padding:24px;text-align:center;color:var(--dim);margin-bottom:16px">
      <div style="font-size:28px;margin-bottom:8px">🔄</div>
      <div style="font-size:13px;font-weight:600;color:var(--muted)">等待資料累積中</div>
      <div style="font-size:11px;margin-top:4px">當超期或重大客訴發生，警示將自動顯示於此區塊</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── ⑤ 功能入口卡片 ───────────────────────────
st.markdown("""<div style="font-size:13px;font-weight:700;color:var(--navy);
border-left:4px solid var(--teal);padding-left:10px;margin:4px 0 14px">
🚀 功能入口</div>""", unsafe_allow_html=True)

_cards = [
    ("pages/16_客訴輸入.py",  "📝","客訴案件輸入",   "新增客訴申請，自動生成案件編號<br>填寫客戶資訊、機型、故障描述、上傳照片影片",  "var(--accent)"),
    ("pages/17_客訴追蹤.py",  "📋","案件流程追蹤",   "查詢客訴進度、更新處理狀態<br>逾期警示、流程步驟可視化追蹤",               "var(--orange)"),
    ("pages/18_8D管理.py",    "📑","8D 改善管理",    "D1~D8 完整填寫，根因分析與改善驗證<br>CAPA 追蹤、附件上傳、PDF 輸出（預留）", "#7b1fa2"),
    ("pages/19_客訴KPI.py",   "📊","KPI 策略儀表板", "月度趨勢、客訴 Pareto、客戶排名<br>重複異常分析、超期統計",                  "var(--pass)"),
    ("pages/20_客訴歷史.py",  "🔍","歷史查詢",       "進階篩選查詢全部客訴記錄<br>匯出 Excel、案件完整詳情",                       "var(--blue2)"),
]

cols = st.columns(5)
for col, (page, icon, title, desc, clr) in zip(cols, _cards):
    with col:
        st.markdown(f"""
        <div class="cs-entry-card" style="border-left-color:{clr}">
          <div class="ce-icon">{icon}</div>
          <div class="ce-title">{title}</div>
          <div class="ce-desc">{desc}</div>
        </div>""", unsafe_allow_html=True)
        if st.button(f"{icon} 進入", key=f"go_{page}", use_container_width=True):
            st.switch_page(page)

st.markdown(
    '<p style="font-size:11px;color:var(--dim);text-align:right;margin-top:12px">'
    'REXONTEC 力科品質指揮平台 v2.0 &nbsp;|&nbsp; 客訴與8D管理模組</p>',
    unsafe_allow_html=True,
)
