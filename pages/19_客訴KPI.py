"""
REXONTEC 力科品質指揮平台 — 客訴與8D管理系統
客訴 KPI 儀表板
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils.cs_gsheet import load_all_complaints, load_all_8d, DONE_STATUS
from utils.style import QMS_CSS, topbar, page_header

st.set_page_config(
    page_title="REXONTEC 力科 | 客訴KPI",
    page_icon="📊",
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
    page_header("客訴 KPI 儀表板", "REXONTEC 力科 | Complaint KPI Dashboard", "KPI"),
    unsafe_allow_html=True,
)

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

PLACEHOLDER = """
<div style="background:#fafbfc;border:1px dashed var(--border2);border-radius:8px;
            padding:40px 20px;text-align:center;color:var(--dim)">
  <div style="font-size:32px;margin-bottom:8px">{icon}</div>
  <div style="font-size:12px;font-weight:600;color:var(--muted)">{title}</div>
  <div style="font-size:11px;margin-top:4px">等待資料累積中</div>
</div>"""


@st.cache_data(ttl=60, show_spinner="載入 KPI 資料...")
def get_data():
    df_cs = load_all_complaints()
    df_8d = load_all_8d()
    return df_cs, df_8d


_, ref_col = st.columns([10, 1])
with ref_col:
    if st.button("🔄", use_container_width=True, help="重新整理"):
        st.cache_data.clear(); st.rerun()

df_cs, df_8d = get_data()

def _to_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y/%m/%d").date()
    except Exception:
        return None

def _to_month(s):
    """回傳排序用 key (YYYY-MM) 和顯示用 label (M月/YYYY) 的 tuple"""
    try:
        dt = datetime.strptime(str(s)[:7], "%Y/%m")
        return (dt.strftime("%Y-%m"), f"{dt.month}月/{dt.year}")
    except Exception:
        return None

def _to_month_label(s):
    """直接回傳顯示用中文月份標籤"""
    try:
        dt = datetime.strptime(str(s)[:7], "%Y/%m")
        return f"{dt.month}月/{dt.year}"
    except Exception:
        return None

def _to_month_key(s):
    """排序用 YYYY-MM"""
    try:
        return datetime.strptime(str(s)[:7], "%Y/%m").strftime("%Y-%m")
    except Exception:
        return None

today = date.today()
month_start = date(today.year, today.month, 1)

# ════════════════════════════════════════════════════
# KPI 卡片
# ════════════════════════════════════════════════════
if df_cs.empty:
    total_cs   = 0; this_month = 0; open_cs = 0
    major_cs   = 0; closure_rt = "─"
    avg_days   = "─"; d8_done = 0; d8_total = 0
else:
    df_cs["_d"] = df_cs["建立日期"].apply(_to_date)
    total_cs    = len(df_cs)
    this_month  = len(df_cs[df_cs["_d"] >= month_start])
    open_cs     = len(df_cs[~df_cs["流程狀態"].isin(DONE_STATUS)])
    major_cs    = len(df_cs[df_cs["是否重大客訴"] == "是"])
    closed      = df_cs[df_cs["流程狀態"] == "結案"].copy()
    closure_rt  = f"{len(closed)/total_cs*100:.0f}%" if total_cs else "─"

    # 平均結案天數
    def _days(row):
        try:
            s = datetime.strptime(str(row["建立日期"])[:16], "%Y/%m/%d %H:%M")
            e = datetime.strptime(str(row["結案日期"])[:16], "%Y/%m/%d %H:%M")
            return (e - s).days
        except Exception:
            return None
    if not closed.empty and "結案日期" in closed.columns:
        day_list = [_days(r) for r in closed.to_dict("records")]
        day_list = [d for d in day_list if d is not None]
        avg_days = f"{sum(day_list)/len(day_list):.1f}天" if day_list else "─"
    else:
        avg_days = "─"

if df_8d.empty:
    d8_done = 0; d8_total = 0
else:
    d8_total = len(df_8d)
    d8_done  = len(df_8d[df_8d["CAPA狀態"] == "完成"])

kpi_html = '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:20px">'
for label, val, sub, clr in [
    ("本月客訴",   this_month, f"累計 {total_cs} 件",          "var(--accent)"),
    ("未結案",     open_cs,    "進行中案件",                    "var(--orange)"),
    ("重大客訴",   major_cs,   "S1 / S2 等級",                 "var(--cr)"),
    ("結案率",     closure_rt, f"{total_cs-open_cs}/{total_cs} 件", "var(--pass)"),
    ("平均結案天", avg_days,   "結案案件統計",                  "var(--teal)"),
    ("8D完成率",
     f"{d8_done/d8_total*100:.0f}%" if d8_total else "─",
     f"{d8_done} / {d8_total} 件",                            "var(--ma)"),
]:
    kpi_html += f"""
  <div style="background:#fff;border:1px solid var(--border);border-radius:8px;
              padding:14px 16px;box-shadow:var(--sh);border-top:3px solid {clr}">
    <div style="font-size:10px;font-weight:700;color:var(--muted);
                text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">{label}</div>
    <div style="font-size:24px;font-weight:700;font-family:'DM Mono',monospace;
                color:{clr};line-height:1">{val}</div>
    <div style="font-size:11px;color:var(--muted);margin-top:4px">{sub}</div>
  </div>"""
kpi_html += "</div>"
st.markdown(kpi_html, unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# 圖表區
# ════════════════════════════════════════════════════
ch1, ch2 = st.columns(2)

# ── 圖1：月趨勢 ──────────────────────────────────────
with ch1:
    st.markdown('<div style="font-size:13px;font-weight:700;color:var(--navy);'
                'border-left:4px solid var(--accent);padding-left:10px;margin-bottom:10px">'
                '📈 月客訴趨勢</div>', unsafe_allow_html=True)
    if df_cs.empty or not HAS_PLOTLY:
        st.markdown(PLACEHOLDER.format(icon="📈", title="月客訴趨勢圖"), unsafe_allow_html=True)
    else:
        # 排序 key（YYYY-MM）和顯示 label（M月/YYYY）分開處理
        df_cs["_mk"] = df_cs["建立日期"].apply(_to_month_key)   # 排序用
        df_cs["_ml"] = df_cs["建立日期"].apply(_to_month_label) # 顯示用
        monthly = (df_cs.dropna(subset=["_mk","_ml"])
                   .groupby(["_mk","_ml"])
                   .size().reset_index(name="件數"))
        monthly = monthly.sort_values("_mk").tail(12)  # 按 YYYY-MM 排序取最近12個月
        if monthly.empty:
            st.markdown(PLACEHOLDER.format(icon="📈", title="月客訴趨勢圖"), unsafe_allow_html=True)
        else:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=monthly["_ml"],   # 顯示「5月/2026」格式
                y=monthly["件數"],
                marker_color="#1565c0", name="客訴件數",
                text=monthly["件數"], textposition="outside",
            ))
            fig.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=30, b=10, l=30, r=10),
                xaxis=dict(
                    type="category",        # 強制文字類別，不被當日期解析
                    showgrid=False,
                    tickfont=dict(size=11),
                    tickangle=0,
                ),
                yaxis=dict(
                    gridcolor="#f0f0f0",
                    tickfont=dict(size=11),
                    rangemode="tozero",
                ),
                showlegend=False, height=280,
            )
            st.plotly_chart(fig, use_container_width=True)

# ── 圖2：類型分布 ─────────────────────────────────────
with ch2:
    st.markdown('<div style="font-size:13px;font-weight:700;color:var(--navy);'
                'border-left:4px solid var(--orange);padding-left:10px;margin-bottom:10px">'
                '🥧 客訴類型分布</div>', unsafe_allow_html=True)
    if df_cs.empty or not HAS_PLOTLY:
        st.markdown(PLACEHOLDER.format(icon="🥧", title="客訴類型分布"), unsafe_allow_html=True)
    else:
        type_cnt = df_cs["客訴類型"].value_counts().reset_index()
        type_cnt.columns = ["類型", "件數"]
        if type_cnt.empty:
            st.markdown(PLACEHOLDER.format(icon="🥧", title="客訴類型分布"), unsafe_allow_html=True)
        else:
            COLORS = ["#1565c0","#e65100","#6a1b9a","#2e7d32",
                      "#c62828","#f57f17","#00695c","#37474f"]
            fig2 = go.Figure(go.Pie(
                labels=type_cnt["類型"], values=type_cnt["件數"],
                marker_colors=COLORS[:len(type_cnt)],
                textinfo="label+percent", hole=0.4,
            ))
            fig2.update_layout(
                margin=dict(t=20, b=10, l=10, r=10), height=280,
                showlegend=False, paper_bgcolor="white",
            )
            st.plotly_chart(fig2, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
ch3, ch4 = st.columns(2)

# ── 圖3：Pareto（類型×件數）────────────────────────────
with ch3:
    st.markdown('<div style="font-size:13px;font-weight:700;color:var(--navy);'
                'border-left:4px solid var(--cr);padding-left:10px;margin-bottom:10px">'
                '📉 客訴類型 Pareto 分析</div>', unsafe_allow_html=True)
    if df_cs.empty or not HAS_PLOTLY:
        st.markdown(PLACEHOLDER.format(icon="📉", title="Pareto 分析"), unsafe_allow_html=True)
    else:
        pareto = df_cs["客訴類型"].value_counts().reset_index()
        pareto.columns = ["類型", "件數"]
        pareto = pareto.sort_values("件數", ascending=False)
        if pareto.empty:
            st.markdown(PLACEHOLDER.format(icon="📉", title="Pareto 分析"), unsafe_allow_html=True)
        else:
            pareto["累計%"] = pareto["件數"].cumsum() / pareto["件數"].sum() * 100
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                x=pareto["類型"], y=pareto["件數"],
                marker_color="#e65100", name="件數", yaxis="y",
                text=pareto["件數"], textposition="outside",
            ))
            fig3.add_trace(go.Scatter(
                x=pareto["類型"], y=pareto["累計%"],
                mode="lines+markers", name="累計%",
                yaxis="y2", line=dict(color="#1565c0", width=2),
                marker=dict(size=7),
            ))
            fig3.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=20, b=20, l=30, r=60),
                yaxis=dict(title="件數", gridcolor="#f0f0f0"),
                yaxis2=dict(title="累計%", overlaying="y", side="right",
                            range=[0, 110], ticksuffix="%"),
                xaxis=dict(showgrid=False),
                height=280, showlegend=False,
            )
            st.plotly_chart(fig3, use_container_width=True)

# ── 圖4：客戶排名 ──────────────────────────────────────
with ch4:
    st.markdown('<div style="font-size:13px;font-weight:700;color:var(--navy);'
                'border-left:4px solid var(--teal);padding-left:10px;margin-bottom:10px">'
                '🏆 客戶客訴件數排名</div>', unsafe_allow_html=True)
    if df_cs.empty or not HAS_PLOTLY:
        st.markdown(PLACEHOLDER.format(icon="🏆", title="客戶排名"), unsafe_allow_html=True)
    else:
        cust_cnt = df_cs["客戶名稱"].value_counts().head(10).reset_index()
        cust_cnt.columns = ["客戶", "件數"]
        cust_cnt = cust_cnt.sort_values("件數")
        if cust_cnt.empty:
            st.markdown(PLACEHOLDER.format(icon="🏆", title="客戶排名"), unsafe_allow_html=True)
        else:
            fig4 = go.Figure(go.Bar(
                x=cust_cnt["件數"], y=cust_cnt["客戶"],
                orientation="h", marker_color="#00695c",
                text=cust_cnt["件數"], textposition="outside",
            ))
            fig4.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=20, b=20, l=10, r=30),
                xaxis=dict(gridcolor="#f0f0f0"),
                yaxis=dict(showgrid=False, tickfont=dict(size=11)),
                height=280, showlegend=False,
            )
            st.plotly_chart(fig4, use_container_width=True)

# ════════════════════════════════════════════════════
# 等級 & CAPA 統計
# ════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div style="font-size:13px;font-weight:700;color:var(--navy);'
            'border-left:4px solid var(--ma);padding-left:10px;margin-bottom:12px">'
            '📋 等級分布 & CAPA 狀態</div>', unsafe_allow_html=True)

sl1, sl2 = st.columns(2)
with sl1:
    if not df_cs.empty:
        level_cnt = df_cs["客訴等級"].value_counts().reset_index()
        level_cnt.columns = ["等級", "件數"]
        level_colors = {"S1 重大":"#b71c1c","S2 高":"#e65100","S3 中":"#f9a825","S4 低":"#2e7d32"}
        rows_html = ""
        for _, row in level_cnt.iterrows():
            clr = level_colors.get(row["等級"],"#90a4ae")
            pct = row["件數"]/len(df_cs)*100
            rows_html += f"""
            <div style="margin-bottom:10px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px">
                <span style="font-weight:700;color:{clr}">{row['等級']}</span>
                <span style="color:var(--muted)">{row['件數']} 件 ({pct:.0f}%)</span>
              </div>
              <div style="background:#f0f0f0;border-radius:4px;height:8px">
                <div style="background:{clr};width:{pct}%;height:8px;border-radius:4px"></div>
              </div>
            </div>"""
        st.markdown(rows_html, unsafe_allow_html=True)
    else:
        st.info("尚無資料")

with sl2:
    if not df_8d.empty:
        capa_cnt = df_8d["CAPA狀態"].value_counts().reset_index()
        capa_cnt.columns = ["狀態", "件數"]
        capa_colors = {"完成":"#27ae60","進行中":"#1565c0","待驗證":"#f57f17"}
        rows_html2 = ""
        for _, row in capa_cnt.iterrows():
            clr = capa_colors.get(row["狀態"],"#90a4ae")
            pct = row["件數"]/len(df_8d)*100
            rows_html2 += f"""
            <div style="margin-bottom:10px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px">
                <span style="font-weight:700;color:{clr}">CAPA {row['狀態']}</span>
                <span style="color:var(--muted)">{row['件數']} 件 ({pct:.0f}%)</span>
              </div>
              <div style="background:#f0f0f0;border-radius:4px;height:8px">
                <div style="background:{clr};width:{pct}%;height:8px;border-radius:4px"></div>
              </div>
            </div>"""
        st.markdown(rows_html2, unsafe_allow_html=True)
    else:
        st.info("尚無 8D 記錄")
