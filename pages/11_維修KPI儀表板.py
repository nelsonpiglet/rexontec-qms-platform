"""
REXONTEC 力科品質指揮平台 — 維修保養系統
KPI 策略儀表板
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from utils.rma_detail_gsheet import load_all_details
from utils.style             import QMS_CSS, topbar, page_header, gsheet_error_banner

st.set_page_config(
    page_title="REXONTEC 力科 | KPI 儀表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)

# ── 導覽列 ────────────────────────────────────
c0, c1, c2, c3, c4, c5, c6, _ = st.columns([1,1,1,1,1,1,1,2])
with c0:
    if st.button("🏠 指揮平台", use_container_width=True):
        st.switch_page("app.py")
with c1:
    if st.button("📝 維修輸入", use_container_width=True):
        st.switch_page("pages/09_維修輸入.py")
with c2:
    if st.button("📋 狀態追蹤", use_container_width=True):
        st.switch_page("pages/10_維修狀態追蹤.py")
with c3:
    if st.button("📊 KPI", use_container_width=True):
        st.switch_page("pages/11_維修KPI儀表板.py")
with c4:
    if st.button("🔍 歷史", use_container_width=True):
        st.switch_page("pages/12_維修歷史查詢.py")
with c5:
    if st.button("⚙️ 設定", use_container_width=True):
        st.switch_page("pages/13_維修系統設定.py")
with c6:
    if st.button("📄 報告", use_container_width=True):
        st.switch_page("pages/14_維修報告.py")

st.markdown(
    page_header("維修 KPI 策略儀表板",
                "REXONTEC 力科 | Repair KPI Strategic Dashboard", "KPI"),
    unsafe_allow_html=True,
)

# ── 儀表板 CSS ────────────────────────────────
st.markdown("""
<style>
.kpi-stat {
  background: #ffffff; border: 1px solid #dce3ec;
  border-top: 4px solid var(--accent); border-radius: 8px;
  padding: 14px 16px 12px; text-align: center;
  box-shadow: 0 2px 8px rgba(13,27,42,.08); margin-bottom: 14px;
}
.kpi-stat-en { font-size:9px; font-weight:700; color:#9aafc4; letter-spacing:2px;
               text-transform:uppercase; font-family:'DM Mono',monospace; }
.kpi-stat-val { font-size:30px; font-weight:700; font-family:'DM Mono',monospace;
                line-height:1.1; margin:4px 0 2px; }
.kpi-stat-cn { font-size:11px; color:#6b7c93; }
.kpi-panel { background:#ffffff; border:1px solid #dce3ec; border-radius:8px;
             overflow:hidden; box-shadow:0 2px 10px rgba(13,27,42,.08); margin-bottom:14px; }
.kpi-ph { background:linear-gradient(90deg,#0d1b2a 0%,#1a3a5c 100%);
          padding:9px 16px 8px; border-bottom:1px solid #0d1b2a; }
.kpi-ph-en { font-size:10px; font-weight:700; color:#ffffff; letter-spacing:2.5px;
             text-transform:uppercase; font-family:'DM Mono',monospace; }
.kpi-ph-cn { font-size:12px; color:rgba(255,255,255,.6); margin-top:2px; }
</style>
""", unsafe_allow_html=True)

_BG   = "#ffffff"; _PBG  = "#f7f9fc"; _LINE = "#e5eaf0"
_TXT  = "#1a2332"; _MUTE = "#6b7c93"
GREEN  = "#27ae60"; RED    = "#c0392b"
ORANGE = "#f0a500"; BLUE   = "#1e88e5"
PURPLE = "#7b1fa2"; TEAL   = "#00897b"

STATUS_COLORS = {
    "待收件":"#f0a500","已收件":"#1e88e5","初診中":"#1e88e5",
    "待檢測":"#e67e22","待零件":"#e67e22","維修中":"#f57f17",
    "待QC":"#7b1fa2","已完成":"#27ae60","已出廠":"#27ae60","已取消":"#c0392b",
}
PRIORITY_DAYS = {"P1":2,"P2":5,"P3":7,"P4":14}
DONE_STATUS   = {"已完成","已出廠","已取消"}
FAULT_ALL = [
    "運轉異音", "過熱", "轉速不穩", "完全不轉",
    "震動異常", "電流異常", "外殼損傷", "線材問題",
    "重落地損傷", "摔落檢測", "試轉卡頓", "上電燒毀", "異物", "其他",
]


def base_layout(**kw):
    d = dict(
        paper_bgcolor=_BG, plot_bgcolor=_PBG,
        font=dict(color=_TXT, family="Noto Sans TC, sans-serif", size=11),
        margin=dict(l=48, r=16, t=14, b=40),
        showlegend=kw.pop("showlegend", False),
        xaxis=dict(gridcolor=_LINE, linecolor="#c8d0dc",
                   tickfont=dict(size=10, color=_MUTE), zeroline=False),
        yaxis=dict(gridcolor=_LINE, linecolor="#c8d0dc",
                   tickfont=dict(size=10, color=_MUTE), zeroline=False),
    )
    d.update(kw)
    return d


@st.cache_data(ttl=30, show_spinner="載入 KPI 資料...")
def get_data():
    return load_all_details()


_, col_btn = st.columns([10, 1])
with col_btn:
    if st.button("🔄", use_container_width=True, help="重新整理"):
        st.cache_data.clear(); st.rerun()

try:
    df = get_data()
except Exception as _e:
    gsheet_error_banner(_e)


def parse_month(s):
    try:
        return pd.to_datetime(str(s)[:10], format="%Y/%m/%d").strftime("%Y-%m")
    except Exception:
        return None

def calc_overdue(row):
    if row.get("維修狀態") in DONE_STATUS: return 0
    recv = row.get("收件日期","")
    pri  = str(row.get("優先等級","P3"))[:2]
    days = PRIORITY_DAYS.get(pri, 7)
    try:
        dt = datetime.strptime(str(recv)[:16], "%Y/%m/%d %H:%M")
        return max(0, (datetime.now() - dt).days - days)
    except Exception:
        return 0

if not df.empty:
    # 子件用「主單收件日期」不存在時退回子件本身無日期欄；KPI 改用主單日期
    # 子件沒有獨立收件日期，以建立時用的「主單編號」對應主單 → 這裡直接用空 month
    df["_month"]   = df.get("收件日期", pd.Series(dtype=str)).apply(parse_month) if "收件日期" in df.columns else None
    df["_overdue"] = 0   # 子件不計算逾期（主單層級），KPI 只統計數量
    df["_pri"]     = "P3"

total   = len(df) if not df.empty else 0
active  = df[~df["維修狀態"].isin(DONE_STATUS)]        if not df.empty else pd.DataFrame()
done_df = df[df["維修狀態"].isin({"已出廠","已完成"})] if not df.empty else pd.DataFrame()
overdue = pd.DataFrame()
pct     = f"{int(len(done_df)/total*100)}%" if total else "—"

# ── KPI 統計卡 ───────────────────────────────
cards = [
    ("TOTAL CASES",    total,        "總案件數",   BLUE),
    ("IN PROGRESS",    len(active),  "進行中",     ORANGE),
    ("COMPLETED",      len(done_df), "已出廠",     GREEN),
    ("OVERDUE CASES",  len(overdue), "逾期需處理", RED),
    ("COMPLETION RATE",pct,          "完成率",     PURPLE),
]
stat_cols = st.columns(5)
for col, (en, val, cn, clr) in zip(stat_cols, cards):
    col.markdown(f"""
    <div class="kpi-stat" style="border-top-color:{clr}">
      <div class="kpi-stat-en">{en}</div>
      <div class="kpi-stat-val" style="color:{clr}">{val}</div>
      <div class="kpi-stat-cn">{cn}</div>
    </div>""", unsafe_allow_html=True)

# ── 上排圖表 ──────────────────────────────────
r1l, r1r = st.columns(2, gap="medium")

with r1l:
    st.markdown("""<div class="kpi-panel">
      <div class="kpi-ph">
        <div class="kpi-ph-en">MONTHLY REPAIR VOLUME TREND</div>
        <div class="kpi-ph-cn">月度維修案件量趨勢</div>
      </div>
    </div>""", unsafe_allow_html=True)

    if not df.empty and "_month" in df.columns:
        mc     = df.groupby("_month").size().reset_index(name="cnt").sort_values("_month")
        months = mc["_month"].tolist()
        counts = mc["cnt"].tolist()
        avg    = sum(counts) / len(counts) if counts else 0
        bcolors = [RED if c >= avg * 1.5 else "#1e88e5" for c in counts]
    else:
        months = [datetime.now().strftime("%Y-%m")]
        counts = [total]; avg = total; bcolors = ["#1e88e5"]

    fig1 = go.Figure()
    fig1.add_bar(x=months, y=counts, marker_color=bcolors,
                 marker_line_color="rgba(255,255,255,.6)", marker_line_width=1, name="案件量")
    if len(months) > 1:
        fig1.add_scatter(x=months, y=[avg]*len(months), mode="lines", name="月均線",
                         line=dict(color="#0d1b2a", width=1.8, dash="dot"))
        fig1.add_annotation(x=months[0], y=avg, text=f" 月均 {avg:.1f}",
                            showarrow=False, xanchor="left",
                            font=dict(color="#0d1b2a", size=9), yshift=8)
    if counts and max(counts) > 0:
        pi = counts.index(max(counts))
        fig1.add_annotation(x=months[pi], y=counts[pi], text=f"<b>PEAK {counts[pi]}</b>",
                            showarrow=True, arrowhead=2, arrowcolor=RED,
                            font=dict(color=RED, size=9),
                            bgcolor="rgba(255,255,255,.85)", ay=-28)
    fig1.update_layout(**base_layout(
        height=265, yaxis_title="案件數",
        showlegend=len(months)>1,
        legend=dict(font=dict(size=9,color=_MUTE), bgcolor="rgba(255,255,255,.7)", x=0.02, y=0.98),
        xaxis=dict(type="category", gridcolor=_LINE, linecolor="#c8d0dc",
                   tickfont=dict(size=10,color=_MUTE), tickangle=-30, zeroline=False),
    ))
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar":False})

with r1r:
    st.markdown("""<div class="kpi-panel">
      <div class="kpi-ph">
        <div class="kpi-ph-en">REPAIR STATUS DISTRIBUTION</div>
        <div class="kpi-ph-cn">維修狀態分佈</div>
      </div>
    </div>""", unsafe_allow_html=True)

    if not df.empty:
        sc = df["維修狀態"].value_counts().reset_index()
        sc.columns = ["狀態","數量"]
        slabels = sc["狀態"].tolist(); svals = sc["數量"].tolist()
        scolors = [STATUS_COLORS.get(s, BLUE) for s in slabels]
    else:
        slabels = ["無資料"]; svals = [1]; scolors = ["#dce3ec"]

    fig2 = go.Figure(go.Pie(
        labels=slabels, values=svals, hole=0.55,
        marker=dict(colors=scolors, line=dict(color="white", width=2)),
        textfont=dict(size=10, color="white"), textposition="outside",
        pull=[0.05 if s in DONE_STATUS else 0 for s in slabels],
    ))
    fig2.update_layout(**base_layout(
        showlegend=True,
        legend=dict(font=dict(color=_TXT,size=9), bgcolor="rgba(255,255,255,.7)",
                    orientation="v", x=1.01, y=0.5, xanchor="left", yanchor="middle"),
        margin=dict(l=10, r=120, t=14, b=14), height=265,
        annotations=[dict(text=f"<b>{total}</b><br><span style='font-size:10px;color:{_MUTE}'>件</span>",
                          x=0.38, y=0.5, showarrow=False,
                          font=dict(color=_TXT, size=22))],
    ))
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

# ── 下排圖表 ──────────────────────────────────
r2l, r2r = st.columns(2, gap="medium")

with r2l:
    st.markdown("""<div class="kpi-panel">
      <div class="kpi-ph">
        <div class="kpi-ph-en">FAULT TYPE PARETO ANALYSIS</div>
        <div class="kpi-ph-cn">故障類別 Pareto 分析</div>
      </div>
    </div>""", unsafe_allow_html=True)

    if not df.empty and "故障類別" in df.columns:
        fc = df["故障類別"].value_counts().reset_index()
        fc.columns = ["類別","數量"]
        fc = fc.sort_values("數量", ascending=False)
        fc["累積%"] = (fc["數量"].cumsum() / fc["數量"].sum() * 100).round(1)
    else:
        fc = pd.DataFrame({"類別":FAULT_ALL[:5],"數量":[0]*5,"累積%":[0]*5})

    threshold_idx = next((i for i,v in enumerate(fc["累積%"]) if v>=80), len(fc)-1)
    bcolors3 = [BLUE if i<=threshold_idx else "#90caf9" for i in range(len(fc))]

    fig3 = go.Figure()
    fig3.add_bar(x=fc["類別"], y=fc["數量"], marker_color=bcolors3,
                 marker_line_color="white", marker_line_width=1, name="件數", yaxis="y")
    fig3.add_scatter(x=fc["類別"], y=fc["累積%"], mode="lines+markers", name="累積%",
                     line=dict(color=RED, width=2.2),
                     marker=dict(color=RED, size=5, line=dict(color="white", width=1)),
                     yaxis="y2")
    if fc["數量"].sum() > 0:
        fig3.add_hline(y=80, line_dash="dot", line_color="rgba(200,0,0,.35)", line_width=1.2,
                       yref="y2", annotation_text="80%",
                       annotation_font_color="rgba(192,57,43,.7)", annotation_font_size=9)
    fig3.update_layout(**base_layout(
        showlegend=True, height=265,
        legend=dict(font=dict(color=_TXT,size=9), bgcolor="rgba(255,255,255,.7)", x=0.02, y=0.98),
        yaxis=dict(gridcolor=_LINE, linecolor="#c8d0dc",
                   tickfont=dict(size=10,color=_MUTE), title="件數", title_font=dict(size=10,color=_MUTE)),
        yaxis2=dict(overlaying="y", side="right", range=[0,105], ticksuffix="%",
                    gridcolor="rgba(0,0,0,0)", linecolor="#c8d0dc",
                    tickfont=dict(size=10,color=RED), title="累積%", title_font=dict(size=10,color=RED)),
        xaxis_tickangle=-20,
    ))
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar":False})

with r2r:
    st.markdown("""<div class="kpi-panel">
      <div class="kpi-ph">
        <div class="kpi-ph-en">PRIORITY vs. OVERDUE RISK MATRIX</div>
        <div class="kpi-ph-cn">優先等級逾期風險矩陣</div>
      </div>
    </div>""", unsafe_allow_html=True)

    PRIO_ORDER = ["P1","P2","P3","P4"]
    PRIO_LABEL = {"P1":"P1 緊急","P2":"P2 高","P3":"P3 一般","P4":"P4 低"}

    if not df.empty and "_pri" in df.columns:
        on_time_v = [int((df[df["_pri"]==p]["_overdue"]==0).sum()) for p in PRIO_ORDER]
        overdue_v = [int((df[df["_pri"]==p]["_overdue"]>0).sum()) for p in PRIO_ORDER]
    else:
        on_time_v = [0,0,0,0]; overdue_v = [0,0,0,0]

    xlabels = [PRIO_LABEL[p] for p in PRIO_ORDER]
    fig4 = go.Figure()
    fig4.add_bar(x=xlabels, y=on_time_v, name="準時完成", marker_color=GREEN,
                 marker_line_color="white", marker_line_width=1,
                 text=[v if v>0 else "" for v in on_time_v],
                 textposition="inside", textfont=dict(color="white", size=11, family="DM Mono"))
    fig4.add_bar(x=xlabels, y=overdue_v, name="逾期", marker_color=RED,
                 marker_line_color="white", marker_line_width=1,
                 text=[v if v>0 else "" for v in overdue_v],
                 textposition="inside", textfont=dict(color="white", size=11, family="DM Mono"))
    if overdue_v[0] > 0:
        fig4.add_annotation(x=xlabels[0], y=on_time_v[0]+overdue_v[0], text="⚠ HIGH RISK",
                            showarrow=False, yshift=12,
                            font=dict(color=RED, size=9, family="DM Mono"))
    fig4.update_layout(**base_layout(
        showlegend=True, barmode="stack", height=265,
        legend=dict(font=dict(color=_TXT,size=9), bgcolor="rgba(255,255,255,.7)", x=0.02, y=0.98),
        yaxis_title="案件數",
    ))
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar":False})

st.markdown(
    f'<p style="font-size:10px;color:var(--dim);text-align:right;margin-top:2px">'
    f'REXONTEC 力科 | KPI Dashboard &nbsp;·&nbsp; '
    f'資料更新：{datetime.now().strftime("%Y/%m/%d %H:%M")}</p>',
    unsafe_allow_html=True,
)
