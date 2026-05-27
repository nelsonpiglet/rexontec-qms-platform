"""
REXONTEC 力科品質指揮平台 — 全域 CSS 樣式
Quality Command Platform — 統一深海軍藍主題
"""

QMS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&family=DM+Mono:wght@400;500&display=swap');

/* ── 變數 ─────────────────────────────── */
:root {
  --navy:   #0d1b2a;
  --blue:   #1a5276;
  --blue2:  #2980b9;
  --accent: #1e88e5;
  --accent2:#1565c0;
  --orange: #f0a500;
  --teal:   #117a65;
  --bg:     #f0f4f8;
  --white:  #fff;
  --border: #dce3ec;
  --border2:#c5cfe0;
  --text:   #1a2332;
  --muted:  #6b7c93;
  --dim:    #9aafc4;
  --sh:     0 2px 8px rgba(13,27,42,.10);
  --sh-md:  0 4px 16px rgba(13,27,42,.14);
  --pass:   #27ae60;  --pass-bg: #eafaf1; --pass-bd: #a9dfbf;
  --fail:   #e74c3c;  --fail-bg: #fdedec; --fail-bd: #f5b7b1;
  --warn:   #f39c12;  --warn-bg: #fef9e7;
  --cr:     #c0392b;  --cr-bg:   #fdf0ee; --cr-bd:   #f5b7b1;
  --ma:     #d68910;  --ma-bg:   #fef9e7; --ma-bd:   #f9e79f;
  --mi:     #1e8449;  --mi-bg:   #eafaf1; --mi-bd:   #a9dfbf;
}

/* ── 基礎 ─────────────────────────────── */
html, body, [class*="css"] {
  font-family: 'Noto Sans TC', sans-serif !important;
  background: var(--bg) !important;
  color: var(--text) !important;
}
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
[data-testid="stToolbar"] { display: none; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }

/* ── 頂欄 ─────────────────────────────── */
.qms-topbar {
  background: var(--navy);
  padding: 0 20px;
  height: 52px;
  display: flex;
  align-items: center;
  gap: 0;
  margin: -1rem -1rem 0 -1rem;
  box-shadow: 0 2px 16px rgba(0,0,0,.4);
  position: sticky; top: 0; z-index: 100;
}
.qms-logo  { font-size:15px; font-weight:900; color:var(--orange); letter-spacing:2px; flex-shrink:0; }
.qms-sep   { width:1px; height:22px; background:rgba(255,255,255,.14); margin:0 14px; flex-shrink:0; }
.qms-sys   { font-size:10px; font-weight:700; letter-spacing:2px; color:rgba(255,255,255,.4); text-transform:uppercase; }
.qms-mod   {
  display:flex; align-items:center; gap:6px; padding:0 16px; height:52px;
  font-size:11.5px; font-weight:600; color:rgba(255,255,255,.5);
  cursor:pointer; border-bottom:3px solid transparent;
  white-space:nowrap; margin-left:8px; text-decoration:none;
}
.qms-mod:hover { color:rgba(255,255,255,.85); background:rgba(255,255,255,.05); }
.qms-mod.active { color:#fff; border-bottom-color:var(--orange); background:rgba(255,255,255,.06); }
.qms-clock { margin-left:auto; font-size:11px; font-family:'DM Mono',monospace; color:rgba(255,255,255,.35); }

/* ── 頁面標題卡 ─────────────────────── */
.page-hdr {
  background: linear-gradient(135deg, var(--navy) 0%, var(--blue) 100%);
  border-radius: 10px; padding: 20px 24px; margin-bottom: 18px;
  position: relative; overflow: hidden; box-shadow: var(--sh-md);
}
.page-hdr-wm {
  position: absolute; right: -4px; top: -14px;
  font-size: 88px; font-weight: 900;
  color: rgba(255,255,255,.05); line-height: 1;
  pointer-events: none; font-family: 'DM Mono', monospace;
}
.page-hdr-doc  { font-size:10.5px; color:rgba(255,255,255,.45); margin-bottom:4px; letter-spacing:1px; }
.page-hdr-title { font-size:20px; font-weight:900; color:#fff; letter-spacing:.5px; }
.page-hdr-sub  { font-size:12px; color:rgba(255,255,255,.6); margin-top:4px; }

/* ── 卡片 ─────────────────────────────── */
.card {
  background: var(--white); border: 1px solid var(--border);
  border-radius: 8px; margin-bottom: 14px;
  overflow: hidden; box-shadow: var(--sh);
}
.card-header {
  padding: 11px 16px; background: #f7f9fc;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
}
.card-title {
  font-size: 12px; font-weight: 700; color: var(--text);
  display: flex; align-items: center; gap: 7px;
}
.card-dot  { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.card-body { padding: 16px; }

/* ── Section 標題 ─────────────────────── */
.sec-title {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 0; margin-bottom: 8px;
  border-left: 4px solid var(--blue2); padding-left: 12px;
}
.sec-num {
  width:26px; height:26px; border-radius:50%;
  background:var(--blue2); color:#fff;
  display:flex; align-items:center; justify-content:center;
  font-size:11.5px; font-weight:700; flex-shrink:0;
}
.sec-text  { font-size:13px; font-weight:700; color:var(--text); }
.sec-sub   { font-size:11px; color:var(--muted); margin-top:2px; }

/* ── 等級徽章 ─────────────────────────── */
.grade-cr { background:var(--cr); color:#fff; padding:1px 7px; border-radius:4px; font-size:10px; font-weight:800; letter-spacing:.5px; }
.grade-ma { background:var(--ma); color:#fff; padding:1px 7px; border-radius:4px; font-size:10px; font-weight:800; letter-spacing:.5px; }
.grade-mi { background:var(--mi); color:#fff; padding:1px 7px; border-radius:4px; font-size:10px; font-weight:800; letter-spacing:.5px; }

/* ── 統計卡 ─────────────────────────── */
.stats-row {
  display: grid; grid-template-columns: repeat(5, 1fr);
  gap: 10px; margin-bottom: 16px;
}
@media (max-width:768px) { .stats-row { grid-template-columns: repeat(3,1fr); } }
.stat-card {
  background: var(--white); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px 16px; box-shadow: var(--sh);
  position: relative; overflow: hidden;
}
.stat-card::before { content:''; position:absolute; top:0; left:0; width:3px; height:100%; background:var(--accent); }
.stat-card.sc-red::before    { background:var(--cr); }
.stat-card.sc-orange::before { background:var(--ma); }
.stat-card.sc-green::before  { background:var(--pass); }
.stat-card.sc-teal::before   { background:var(--teal); }
.stat-label { font-size:10px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }
.stat-value { font-size:26px; font-weight:700; color:var(--text); font-family:'DM Mono',monospace; line-height:1; }
.stat-sub   { font-size:11px; color:var(--muted); margin-top:3px; }

/* ── 판정 배너 ─────────────────────────── */
.verdict-pass {
  background: var(--pass-bg); border: 2px solid var(--pass-bd);
  border-radius: 8px; padding: 14px 20px; margin-bottom: 14px;
  display: flex; align-items: center; gap: 12px;
}
.verdict-fail {
  background: var(--fail-bg); border: 2px solid var(--fail-bd);
  border-radius: 8px; padding: 14px 20px; margin-bottom: 14px;
  display: flex; align-items: center; gap: 12px;
  animation: pulse-fail 1.6s ease-in-out infinite;
}
.verdict-pend {
  background: var(--bg); border: 2px solid var(--border2);
  border-radius: 8px; padding: 14px 20px; margin-bottom: 14px;
  display: flex; align-items: center; gap: 12px;
}
@keyframes pulse-fail {
  0%,100% { box-shadow: 0 0 0 0 rgba(231,76,60,0); }
  50%      { box-shadow: 0 0 0 6px rgba(231,76,60,.15); }
}
.verdict-icon  { font-size:28px; flex-shrink:0; }
.verdict-label { font-size:18px; font-weight:900; letter-spacing:1.5px; }
.verdict-sub   { font-size:11.5px; color:var(--muted); margin-top:2px; }

/* ── NG 警示條 ─────────────────────────── */
.ng-alert {
  background: var(--cr-bg); border: 1px solid var(--cr-bd);
  border-radius: 7px; padding: 10px 16px; margin-bottom: 12px;
}
.ng-alert-title { font-size:12px; font-weight:700; color:var(--cr); margin-bottom:6px; }
.ng-item { font-size:12px; color:var(--cr); padding:2px 0; display:flex; align-items:center; gap:8px; }

/* ── 表格 ─────────────────────────────── */
.insp-table { width:100%; border-collapse:collapse; font-size:12px; }
.insp-table th {
  background:var(--navy); color:rgba(255,255,255,.75);
  padding:8px 10px; font-size:10px; font-weight:700;
  letter-spacing:1px; text-transform:uppercase; text-align:left; white-space:nowrap;
}
.insp-table th.tc { text-align:center; }
.insp-table td { padding:8px 10px; border-bottom:1px solid var(--border); vertical-align:middle; }
.insp-table tr:last-child td { border-bottom:none; }
.insp-table tr:nth-child(even) td { background:#fafbfc; }
.insp-table tr.ng-row td { background:#fff8f7 !important; }

/* ── 按鈕 ─────────────────────────────── */
.btn-pass { background:var(--pass); color:#fff; border:none; border-radius:5px; padding:5px 12px; font-size:12px; font-weight:700; cursor:pointer; width:100%; }
.btn-fail { background:var(--fail); color:#fff; border:none; border-radius:5px; padding:5px 12px; font-size:12px; font-weight:700; cursor:pointer; width:100%; }
.btn-pend { background:var(--bg); color:var(--muted); border:1px solid var(--border); border-radius:5px; padding:5px 12px; font-size:12px; font-weight:700; cursor:pointer; width:100%; }

/* ── 導覽按鈕：強制單行，不換行 ─────────── */
[data-testid*="stBaseButton"] p,
[data-testid*="stBaseButton-secondary"] p,
[data-testid*="stBaseButton-primary"] p,
.stButton > button p {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  font-size: 14px !important;
  font-weight: 600 !important;
}

/* ── RMA 成功卡 ─────────────────────────── */
.rma-card {
  background: var(--white); border: 1px solid var(--border);
  border-radius: 12px; padding: 28px 24px; text-align: center;
  box-shadow: var(--sh-md); margin-bottom: 16px;
}

/* ── 進度條 ─────────────────────────────── */
.prog-wrap { background: var(--white); border: 1px solid var(--border); border-radius: 8px; padding: 14px 18px; margin-bottom: 14px; display:flex; align-items:center; gap:18px; box-shadow:var(--sh); flex-wrap:wrap; }
.prog-nums { display:flex; gap:20px; }
.prog-num-item { display:flex; flex-direction:column; align-items:center; gap:1px; }
.prog-num  { font-size:22px; font-weight:700; line-height:1; font-family:'DM Mono',monospace; }
.prog-num.pass  { color:var(--pass); }
.prog-num.fail  { color:var(--fail); }
.prog-num.pend  { color:var(--muted); }
.prog-bar-wrap  { flex:1; min-width:120px; }
.prog-track     { height:6px; background:var(--bg); border-radius:99px; overflow:hidden; }
.prog-fill-pass { height:100%; border-radius:99px; background:linear-gradient(90deg,var(--pass),#2ecc71); transition:width .4s; }
.prog-pct       { font-size:10px; color:var(--muted); text-align:right; margin-top:3px; }

/* ── 維修系統 Stat 值顏色 ──────────────── */
.stat-card.sc-purple::before { background: #7b1fa2; }
.stat-value.v-red    { color: var(--cr); }
.stat-value.v-orange { color: var(--ma); }
.stat-value.v-green  { color: var(--pass); }
.stat-value.v-purple { color: #7b1fa2; }

/* ── Badge（維修系統狀態）──────────────── */
.badge {
  display: inline-flex; align-items: center;
  padding: 2px 9px; border-radius: 99px;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: .5px; white-space: nowrap;
}
.b-wait     { background:#fff3e0; color:#e65100;  border:1px solid #ffcc80; }
.b-recv     { background:#e3f2fd; color:#1565c0;  border:1px solid #90caf9; }
.b-working  { background:#fff8e1; color:#f57f17;  border:1px solid #ffe082; }
.b-qc       { background:#f3e5f5; color:#6a1b9a;  border:1px solid #ce93d8; }
.b-done     { background:var(--pass-bg); color:var(--pass); border:1px solid var(--pass-bd); }
.b-scrap    { background:var(--cr-bg);   color:var(--cr);   border:1px solid var(--cr-bd); }

/* ── RMA 成功卡 ─────────────────────────── */
.rma-badge {
  display: inline-block; background: var(--navy); color: #fff;
  font-size: 26px; font-weight: 900; letter-spacing: 3px;
  padding: 12px 32px; border-radius: 6px; margin: 12px 0;
  font-family: 'DM Mono', monospace; border-left: 4px solid var(--orange);
}
</style>
"""


def topbar():
    return """
<div class="qms-topbar">
  <span class="qms-logo">REXONTEC</span>
  <div class="qms-sep"></div>
  <span class="qms-sys">品質指揮平台</span>
  <div class="qms-clock" id="clk">──:──:──</div>
</div>
<script>
(function tick(){
  var d=new Date();
  var t=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')+':'+String(d.getSeconds()).padStart(2,'0');
  var el=document.getElementById('clk'); if(el) el.textContent=t;
  setTimeout(tick,1000);
})();
</script>
"""


def page_header(title: str, subtitle: str, watermark: str = "OQC") -> str:
    return f"""
<div class="page-hdr">
  <div class="page-hdr-wm">{watermark}</div>
  <div class="page-hdr-doc">REXONTEC 力科 | 品質管理系統 QMS</div>
  <div class="page-hdr-title">{title}</div>
  <div class="page-hdr-sub">{subtitle}</div>
</div>
"""


def gsheet_error_banner(err: Exception = None):
    """Streamlit Cloud 上 Google Sheets 連線失敗時顯示的友善錯誤畫面"""
    import streamlit as st
    st.error("⚠️ Google Sheets 連線失敗，無法載入資料。")
    st.markdown("""
<div style="background:#fff8e1;border:1px solid #ffe082;border-radius:8px;
            padding:16px 20px;margin:8px 0;font-size:13px;line-height:1.8">
  <div style="font-weight:700;color:#e65100;margin-bottom:8px">🔧 Streamlit Cloud 設定方式</div>
  <ol style="margin:0;padding-left:20px">
    <li>右下角 <b>Manage app</b> → <b>Settings</b> → <b>Secrets</b></li>
    <li>貼入 <code>[gcp_service_account]</code> 的完整 TOML 內容</li>
    <li>確認 <code>private_key</code> 值用雙引號 <code>"..."</code>，換行符為 <code>\\n</code>（非真正換行）</li>
    <li>點 <b>Save</b> — App 自動重啟即可連線</li>
  </ol>
</div>
""", unsafe_allow_html=True)
    if err is not None:
        st.caption(f"錯誤類型：{type(err).__name__}")
    st.stop()


def render_navbar(current: str = ""):
    import streamlit as st
    pages = [
        ("01_出廠檢驗輸入", "📋", "檢驗輸入"),
        ("02_儀表板",       "📊", "Dashboard"),
    ]
    links = ""
    for pg, icon, label in pages:
        active = "active" if current == pg else ""
        links += f'<a href="/{pg}" target="_self" class="qms-mod {active}">{icon} {label}</a>'
    st.markdown(f"""
<div style="background:var(--navy);margin:-1rem -1rem 16px -1rem;
            padding:0 20px;display:flex;align-items:center;gap:0;
            border-top:1px solid rgba(255,255,255,.08)">
  {links}
</div>
""", unsafe_allow_html=True)


def grade_badge(grade: str) -> str:
    cls = {"CR": "grade-cr", "MA": "grade-ma", "MI": "grade-mi"}.get(grade, "grade-mi")
    return f'<span class="{cls}">{grade}</span>'


def section_header(letter: str, title: str, subtitle: str = "") -> str:
    sub_html = f'<div class="sec-sub">{subtitle}</div>' if subtitle else ""
    return f"""
<div class="sec-title">
  <div class="sec-num">{letter}</div>
  <div>
    <div class="sec-text">{title}</div>
    {sub_html}
  </div>
</div>
"""


# ── 維修系統共用元件 ─────────────────────────────

def stat_cards(items: list) -> str:
    """
    items = [
      {"label":"總案件", "value":12, "sub":"全部",   "cls":""},
      {"label":"逾期",   "value":2,  "sub":"需處理", "cls":"sc-red", "vcls":"v-red"},
    ]
    """
    cards = ""
    for it in items:
        cards += f"""
        <div class="stat-card {it.get('cls','')}">
          <div class="stat-label">{it['label']}</div>
          <div class="stat-value {it.get('vcls','')}">{it['value']}</div>
          <div class="stat-sub">{it.get('sub','')}</div>
        </div>"""
    return f'<div class="stats-row">{cards}</div>'


def card(title: str, dot_color: str, body_html: str) -> str:
    return f"""
    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <span class="card-dot" style="background:{dot_color}"></span>
          {title}
        </div>
      </div>
      <div class="card-body">{body_html}</div>
    </div>"""


STATUS_BADGE = {
    "待收件":   "b-wait",
    "已收件":   "b-recv",
    "初診中":   "b-recv",
    "待檢測":   "b-recv",
    "待零件":   "b-working",
    "等待零件": "b-working",   # 向下相容
    "維修中":   "b-working",
    "待QC":     "b-qc",
    "已完成":   "b-done",
    "已出廠":   "b-done",
    "報廢通知": "b-scrap",
    "已取消":   "b-scrap",
}

STATUS_EMOJI = {
    "待收件":   "⏳",
    "已收件":   "📦",
    "初診中":   "🔎",
    "待檢測":   "🔬",
    "待零件":   "🔩",
    "等待零件": "🔩",   # 向下相容
    "維修中":   "🔧",
    "待QC":     "🔍",
    "已完成":   "✅",
    "已出廠":   "✅",
    "報廢通知": "⚠️",
    "已取消":   "🚫",
}


def status_badge(status: str) -> str:
    cls   = STATUS_BADGE.get(status, "")
    emoji = STATUS_EMOJI.get(status, "")
    return f'<span class="badge {cls}">{emoji} {status}</span>'
