"""
REXONTEC 力科品質指揮平台 — 維修保養系統首頁
"""
import streamlit as st
from utils.style import QMS_CSS, topbar, page_header

st.set_page_config(
    page_title="REXONTEC 力科 | 維修保養系統",
    page_icon="🔧",
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
    page_header("馬達返廠維修保養系統",
                "REXONTEC 力科 | Motor Repair & Maintenance System", "RMA"),
    unsafe_allow_html=True,
)

st.markdown("""
<style>
.menu-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 14px; margin-top: 4px;
}
.menu-card {
  background: #fff; border: 1px solid var(--border); border-radius: 10px;
  padding: 24px 20px; box-shadow: var(--sh);
  border-left: 4px solid var(--accent); transition: box-shadow .15s;
}
.menu-card:hover { box-shadow: var(--sh-md); }
.menu-card .mc-icon  { font-size: 32px; margin-bottom: 8px; }
.menu-card .mc-title { font-size: 15px; font-weight: 700; color: var(--navy); margin-bottom: 5px; }
.menu-card .mc-desc  { font-size: 12px; color: var(--muted); line-height: 1.6; }
.menu-card.c-orange  { border-left-color: var(--orange); }
.menu-card.c-green   { border-left-color: var(--pass); }
.menu-card.c-purple  { border-left-color: #7b1fa2; }
.menu-card.c-teal    { border-left-color: var(--teal); }
.menu-card.c-red     { border-left-color: var(--cr); }
</style>

<div class="menu-grid">
  <div class="menu-card">
    <div class="mc-icon">📝</div>
    <div class="mc-title">維修案件輸入</div>
    <div class="mc-desc">新增返廠維修申請（單顆 / 批次），自動產生 RMA 編號並寫入 Google Sheet</div>
  </div>
  <div class="menu-card c-orange">
    <div class="mc-icon">📋</div>
    <div class="mc-title">維修狀態追蹤</div>
    <div class="mc-desc">查詢所有案件進度、更新維修狀態、檢視逾期警示</div>
  </div>
  <div class="menu-card c-purple">
    <div class="mc-icon">📊</div>
    <div class="mc-title">KPI 策略儀表板</div>
    <div class="mc-desc">月度趨勢、狀態分佈、Pareto 分析、優先等級風險矩陣</div>
  </div>
  <div class="menu-card c-teal">
    <div class="mc-icon">🔍</div>
    <div class="mc-title">維修歷史查詢</div>
    <div class="mc-desc">進階篩選、案件詳情查看、匯出 Excel 報表</div>
  </div>
  <div class="menu-card c-green">
    <div class="mc-icon">⚙️</div>
    <div class="mc-title">系統設定</div>
    <div class="mc-desc">設定 Email 通知信箱、測試發信功能</div>
  </div>
  <div class="menu-card c-red">
    <div class="mc-icon">📄</div>
    <div class="mc-title">維修報告產生</div>
    <div class="mc-desc">選擇 RMA 案件，一鍵產生完整 PDF 維修報告，含客戶、馬達、故障、簽核欄</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="background:#fff;border:1px solid var(--border);border-left:4px solid var(--pass);
            border-radius:8px;padding:16px 20px;box-shadow:var(--sh)">
  <div style="font-size:13px;font-weight:700;color:var(--navy);margin-bottom:8px">
    📦 客戶送修入口
  </div>
  <div style="font-size:12.5px;color:var(--muted);line-height:1.8">
    客戶專用連結僅開放「送修申請」功能，無法存取維修狀態、KPI 儀表板等內部資料。<br>
    如需提供客戶使用，請分享系統網址並指引至「維修輸入」頁面。
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<p style="font-size:11px;color:var(--dim);text-align:right;margin-top:10px">'
    'REXONTEC 力科 品質指揮平台 v2.0 &nbsp;|&nbsp; 維修保養模組</p>',
    unsafe_allow_html=True,
)
