"""
REXONTEC — SQM 供應商品質儀表板
供應商異常排行 / Pareto / 月趨勢 / 風險供應商 / 狀態分布
欄位比照 IQC問題點病歷 Excel 格式
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.style  import QMS_CSS, topbar, page_header
from utils.auth   import require_login, user_info_bar
from utils.sqm    import STATUS_COLOR
from utils.gsheet import load_sqm_defects, load_scars

st.set_page_config(
    page_title="REXONTEC 力科 | SQM 儀表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()
user_info_bar()

# ── 導覽列 ────────────────────────────────────────────
n1,n2,n3,n4,n5,n6,n7,n8 = st.columns([1,1,1,1,1,1,1,2])
with n1:
    if st.button("🏠 指揮平台",  use_container_width=True): st.switch_page("app.py")
with n2:
    if st.button("🔬 IQC 進料",  use_container_width=True): st.switch_page("pages/06_IQC進料檢驗.py")
with n3:
    if st.button("🏭 SQM 異常",  use_container_width=True): st.switch_page("pages/40_🏭_SQM異常登錄.py")
with n4:
    if st.button("📝 SCAR 管理", use_container_width=True): st.switch_page("pages/41_📝_SCAR管理.py")
with n5:
    if st.button("📊 SQM 儀表板",use_container_width=True): st.switch_page("pages/42_📊_SQM儀表板.py")
with n6:
    if st.button("📥 文件匯入",  use_container_width=True): st.switch_page("pages/50_📥_文件匯入中心.py")
with n7:
    if st.button("⚙️ 系統設定",  use_container_width=True): st.switch_page("pages/03_系統設定.py")

st.markdown(page_header(
    "SQM 供應商品質儀表板",
    "Supplier Quality Management Dashboard — KPI / Pareto / 趨勢 / 風險供應商",
    "SDB",
), unsafe_allow_html=True)

# ── 圖表庫 ────────────────────────────────────────────
try:
    import plotly.express as px
    import plotly.graph_objects as go
    _PLOTLY = True
except ImportError:
    _PLOTLY = False

# ── 資料載入 ──────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner="載入 SQM 資料中…")
def _load():
    try:
        df = load_sqm_defects()
        if not df.empty and "發生日期" in df.columns:
            df["發生日期_dt"] = pd.to_datetime(df["發生日期"], errors="coerce")
        if not df.empty and "建立時間" in df.columns:
            df["建立時間"] = pd.to_datetime(df["建立時間"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def _load_scar():
    try:
        df = load_scars()
        return df
    except Exception:
        return pd.DataFrame()

# 重新整理按鈕
_rc1, _rc2 = st.columns([1, 7])
with _rc1:
    if st.button("🔄 重新整理", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with _rc2:
    st.caption("資料每 60 秒自動更新，或點擊「重新整理」即時載入最新資料。")

df_all  = _load()
df_scar = _load_scar()

if df_all.empty:
    st.info("ℹ️ 尚無 SQM 異常資料，請先在「SQM 異常登錄」頁面輸入資料後再查看儀表板。")
    if st.button("🏭 前往 SQM 異常登錄"):
        st.switch_page("pages/40_🏭_SQM異常登錄.py")
    st.stop()

# ── 日期篩選（依發生日期） ────────────────────────────
st.markdown("#### 📅 日期範圍")
d1, d2, d3 = st.columns([2, 2, 4])
today = date.today()
with d1:
    d_from = st.date_input("起始日期",
                            value=date(today.year, today.month, 1),
                            key="sqm_db_df", format="YYYY/MM/DD")
with d2:
    d_to = st.date_input("結束日期", value=today,
                          key="sqm_db_dt", format="YYYY/MM/DD")
with d3:
    quick = st.radio("快速選擇", ["本月", "近3個月", "今年", "全部"],
                     horizontal=True, key="sqm_db_q")
    if   quick == "本月":    d_from = date(today.year, today.month, 1); d_to = today
    elif quick == "近3個月": d_from = today - timedelta(days=90);       d_to = today
    elif quick == "今年":    d_from = date(today.year, 1, 1);           d_to = today

# 套用日期篩選
df = df_all.copy()
if quick != "全部" and "發生日期_dt" in df.columns and not df.empty:
    df_dated = df.dropna(subset=["發生日期_dt"])
    mask = (df_dated["發生日期_dt"].dt.date >= d_from) & (df_dated["發生日期_dt"].dt.date <= d_to)
    df = df_dated[mask].copy()

if df.empty:
    st.warning("此期間無資料，請調整日期範圍或選「全部」。")
    st.stop()

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# KPI 卡片
# ═══════════════════════════════════════════════════════
def _safe_int(series):
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)

total_def  = len(df)
total_sup  = df["廠商"].nunique()                                          if "廠商"  in df.columns else 0
total_ng   = _safe_int(df["不良數"]).sum()                                 if "不良數" in df.columns else 0
open_scar  = int((df_scar["結案狀態"] == "Open").sum())                    if not df_scar.empty else 0
n_reopen   = int((df["狀態"] == "再發").sum())                             if "狀態"  in df.columns else 0

kpi_items = [
    ("異常件數",      str(total_def),  "var(--cr)",     "此期間登錄總筆數"),
    ("異常供應商數",  str(total_sup),  "var(--orange)", "涉及廠商家數"),
    ("不良品總數",    str(total_ng),   "#c0392b",       "累計不良品數量"),
    ("Open SCAR",    str(open_scar),  "var(--ma)",     "未結案 SCAR"),
    ("再發異常",      str(n_reopen),   "#9b59b6",       "狀態標記「再發」筆數"),
]

_kpi_html = '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:20px">'
for lbl, val, color, sub in kpi_items:
    _kpi_html += f"""
  <div style="background:#fff;border:1px solid var(--border);border-radius:8px;
              padding:14px 16px;box-shadow:var(--sh);border-top:3px solid {color}">
    <div style="font-size:10px;font-weight:700;color:var(--muted);letter-spacing:1px">{lbl}</div>
    <div style="font-size:28px;font-weight:700;color:{color};font-family:'DM Mono',monospace;
                line-height:1;margin:6px 0">{val}</div>
    <div style="font-size:11px;color:var(--muted)">{sub}</div>
  </div>"""
_kpi_html += "</div>"
st.markdown(_kpi_html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# 圖表列 1：廠商異常排行 + 來源別 Pareto
# ═══════════════════════════════════════════════════════
ch1, ch2 = st.columns(2)

SOURCE_COLORS = {
    "進料退貨":    "#e74c3c",
    "產線無效工時":"#e67e22",
    "客訴回應":    "#f39c12",
    "保固維修":    "#9b59b6",
    "稽核發現":    "#3498db",
    "自主檢驗":    "#1abc9c",
    "其他":        "#95a5a6",
}

with ch1:
    st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🏭 廠商異常排行 Top 10
  </div>""", unsafe_allow_html=True)

    if "廠商" in df.columns:
        sup_cnt = (df.groupby("廠商").size()
                     .reset_index(name="異常件數")
                     .sort_values("異常件數", ascending=False)
                     .head(10))
        if _PLOTLY:
            fig1 = go.Figure(go.Bar(
                x=sup_cnt["異常件數"], y=sup_cnt["廠商"],
                orientation="h",
                marker_color="#e74c3c",
                text=sup_cnt["異常件數"],
                textposition="outside",
            ))
            fig1.update_layout(
                height=300, margin=dict(l=10,r=40,t=10,b=10),
                xaxis_title="", yaxis_title="",
                plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(autorange="reversed"), font=dict(size=11),
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.bar_chart(sup_cnt.set_index("廠商")["異常件數"])
    else:
        st.info("無廠商欄位資料")
    st.markdown("</div>", unsafe_allow_html=True)

with ch2:
    st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📊 異常來源別 Pareto
  </div>""", unsafe_allow_html=True)

    src_col = "來源" if "來源" in df.columns else None
    if src_col:
        cat_cnt = (df.groupby(src_col).size()
                     .reset_index(name="件數")
                     .sort_values("件數", ascending=False))
        if _PLOTLY:
            cat_colors = [SOURCE_COLORS.get(c, "#888") for c in cat_cnt[src_col]]
            fig2 = go.Figure(go.Bar(
                x=cat_cnt[src_col], y=cat_cnt["件數"],
                marker_color=cat_colors,
                text=cat_cnt["件數"], textposition="outside",
            ))
            fig2.update_layout(
                height=300, margin=dict(l=10,r=10,t=10,b=10),
                xaxis_title="", yaxis_title="",
                plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.bar_chart(cat_cnt.set_index(src_col)["件數"])
    else:
        st.info("無來源欄位資料")
    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# 圖表列 2：月趨勢 + 狀態分布
# ═══════════════════════════════════════════════════════
ch3, ch4 = st.columns(2)

with ch3:
    st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📈 月度異常件數趨勢（依發生日期）
  </div>""", unsafe_allow_html=True)

    if "發生日期_dt" in df.columns:
        df_m = df.dropna(subset=["發生日期_dt"]).copy()
        df_m["月份"] = df_m["發生日期_dt"].dt.to_period("M").astype(str)
        monthly = df_m.groupby("月份").size().reset_index(name="件數")
        if _PLOTLY:
            fig3 = px.line(monthly, x="月份", y="件數",
                           markers=True, text="件數",
                           color_discrete_sequence=["#e67e22"])
            fig3.update_traces(textposition="top center", line_width=2.5, marker_size=8)
            fig3.update_layout(
                height=260, margin=dict(l=10,r=10,t=10,b=10),
                xaxis_title="", yaxis_title="",
                plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.line_chart(monthly.set_index("月份")["件數"])
    else:
        st.info("無發生日期資料")
    st.markdown("</div>", unsafe_allow_html=True)

with ch4:
    st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🥧 處理狀態分布
  </div>""", unsafe_allow_html=True)

    STATUS_PIE_COLORS = {
        "處理中": "#e67e22",
        "結案":   "#27ae60",
        "再發":   "#e74c3c",
        "暫緩":   "#95a5a6",
    }
    if "狀態" in df.columns:
        jud_cnt = df["狀態"].value_counts().reset_index()
        jud_cnt.columns = ["狀態", "件數"]
        if _PLOTLY:
            pie_colors = [STATUS_PIE_COLORS.get(s, "#888") for s in jud_cnt["狀態"]]
            fig4 = px.pie(jud_cnt, names="狀態", values="件數",
                          color_discrete_sequence=pie_colors,
                          hole=0.42)
            fig4.update_traces(textinfo="label+percent", textfont_size=11)
            fig4.update_layout(
                height=260, margin=dict(l=10,r=10,t=10,b=10),
                paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.bar_chart(jud_cnt.set_index("狀態"))
    else:
        st.info("無狀態欄位資料")
    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# Top 風險供應商表
# ═══════════════════════════════════════════════════════
st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    ⚠️ Top 風險廠商分析
  </div>""", unsafe_allow_html=True)

if "廠商" in df.columns:
    agg_dict = {"記錄編號": "count"}
    if "不良數"  in df.columns: agg_dict["不良數"]  = lambda x: _safe_int(x).sum()
    if "狀態"    in df.columns: agg_dict["再發次數"] = ("狀態", lambda x: (x == "再發").sum())
    if "來源"    in df.columns: agg_dict["來源數"]   = ("來源", "nunique")

    # 用基本 groupby 避免 lambda 衝突
    risk_base = df.groupby("廠商").agg(異常件數=("記錄編號", "count")).reset_index()
    if "不良數" in df.columns:
        ng_sum = df.groupby("廠商")["不良數"].apply(lambda x: _safe_int(x).sum()).reset_index(name="不良品數")
        risk_base = risk_base.merge(ng_sum, on="廠商", how="left")
    if "狀態" in df.columns:
        reopen = df[df["狀態"] == "再發"].groupby("廠商").size().reset_index(name="再發次數")
        risk_base = risk_base.merge(reopen, on="廠商", how="left").fillna({"再發次數": 0})
        risk_base["再發次數"] = risk_base["再發次數"].astype(int)
    if "機種" in df.columns:
        models = df.groupby("廠商")["機種"].nunique().reset_index(name="涉及機種數")
        risk_base = risk_base.merge(models, on="廠商", how="left")

    # SCAR 關聯
    if not df_scar.empty and "供應商" in df_scar.columns:
        scar_by_sup = (df_scar.groupby("供應商")
                       .agg(SCAR數=("SCAR編號","count"),
                            Open數=("結案狀態", lambda x:(x=="Open").sum()))
                       .reset_index()
                       .rename(columns={"供應商": "廠商"}))
        risk_base = risk_base.merge(scar_by_sup, on="廠商", how="left").fillna(0)
        risk_base["SCAR數"] = risk_base["SCAR數"].astype(int)
        risk_base["Open數"] = risk_base["Open數"].astype(int)

    risk_base = risk_base.sort_values("異常件數", ascending=False).head(15).reset_index(drop=True)
    risk_base.index = risk_base.index + 1

    def _highlight_risk(row):
        if row.get("再發次數", 0) > 1 or row["異常件數"] > 3:
            return ["background-color:#fff0ee"] * len(row)
        return [""] * len(row)

    try:
        st.dataframe(risk_base.style.apply(_highlight_risk, axis=1),
                     use_container_width=True,
                     height=min(500, 56 + len(risk_base)*38))
    except Exception:
        st.dataframe(risk_base, use_container_width=True,
                     height=min(500, 56 + len(risk_base)*38))
else:
    st.info("無廠商欄位資料")

st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# 再發異常警示
# ═══════════════════════════════════════════════════════
if "狀態" in df.columns and "廠商" in df.columns:
    reopen_df = df[df["狀態"] == "再發"][
        [c for c in ["記錄編號","發生日期","廠商","零件名稱","P問題點","負責人"] if c in df.columns]
    ].head(15)
    if not reopen_df.empty:
        st.markdown("""
<div style="background:#fef9e7;border:1px solid #f9ca24;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#7f6d2c;margin-bottom:10px">
    🔁 再發異常警示（需優先處理）
  </div>""", unsafe_allow_html=True)
        st.dataframe(reopen_df, use_container_width=True, hide_index=True,
                     height=min(300, 56 + len(reopen_df)*38))
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# AI 功能預留
# ═══════════════════════════════════════════════════════
st.markdown("""
<div style="background:#f8f4ff;border:1px dashed #9b59b6;border-radius:8px;
            padding:20px 24px;text-align:center;color:#7d3c98;margin-bottom:14px">
  <div style="font-size:24px;margin-bottom:8px">🤖</div>
  <div style="font-size:14px;font-weight:700;margin-bottom:6px">AI 智慧分析（Phase 2 預留）</div>
  <div style="font-size:12px;line-height:1.8;color:#9b59b6">
    AI 異常自動分類 &nbsp;·&nbsp; AI Pareto 根本原因分析 &nbsp;·&nbsp;
    AI 風險供應商預警 &nbsp;·&nbsp; AI CAPA 對策建議 &nbsp;·&nbsp; AI 8D 協助生成
  </div>
</div>
""", unsafe_allow_html=True)

# ── 最近記錄 ──────────────────────────────────────────
st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📋 最近 20 筆異常記錄
  </div>""", unsafe_allow_html=True)

recent_cols = [c for c in [
    "記錄編號", "發生日期", "來源", "機種",
    "廠商", "零件名稱", "零件編號（單據號碼）",
    "不良數", "P問題點", "負責人", "狀態", "SCAR編號",
] if c in df.columns]

recent = df[recent_cols].head(20).copy()
st.dataframe(recent, use_container_width=True, hide_index=True,
             height=min(500, 56 + len(recent)*38))
st.markdown("</div>", unsafe_allow_html=True)
