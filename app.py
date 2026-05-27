"""
REXONTEC 力科品質指揮平台 — QMS 總控首頁
Rexontec Quality Command Platform
"""
import streamlit as st
import pandas as pd
from datetime import date

from utils.style import QMS_CSS, topbar, page_header
from utils.auth  import require_login, user_info_bar

# ── 頁面設定 ────────────────────────────────────────
st.set_page_config(
    page_title="REXONTEC 力科 | 品質指揮平台",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()
user_info_bar()

# ── 平台導覽列 ──────────────────────────────────────
n1, n2, n3, n4, n5, n6, n7, n8, n9 = st.columns([1, 1, 1, 1, 1, 1.4, 1, 1, 1.6])
with n1:
    if st.button("🔬 檢驗品質", use_container_width=True):
        st.switch_page("pages/01_出廠檢驗輸入.py")
with n2:
    if st.button("📊 儀表板",   use_container_width=True):
        st.switch_page("pages/02_儀表板.py")
with n3:
    if st.button("🔧 維修保養", use_container_width=True):
        st.switch_page("pages/08_維修保養系統.py")
with n4:
    if st.button("📢 客訴8D",   use_container_width=True):
        st.switch_page("pages/15_客訴8D系統.py")
with n5:
    if st.button("🤖 AI 分析",  use_container_width=True):
        st.switch_page("pages/07_AI異常分析.py")
with n6:
    if st.button("🏭 SQM 供應商", use_container_width=True):
        st.switch_page("pages/40_🏭_SQM異常登錄.py")
with n7:
    if st.button("📥 文件匯入", use_container_width=True):
        st.switch_page("pages/50_📥_文件匯入中心.py")
with n8:
    if st.button("⚙️ 系統設定", use_container_width=True):
        st.switch_page("pages/03_系統設定.py")

# ── 平台頁首 ────────────────────────────────────────
st.markdown(page_header(
    "品質指揮平台",
    "Rexontec Quality Command Platform — 品質監控 · 異常追蹤 · 決策分析",
    "QMS",
), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# KPI 資料（從 Google Sheet 取 OQC 本月良率）
# ═══════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def _load_kpi():
    try:
        from utils.gsheet import load_oqc_records
        df_e = load_oqc_records("esc")
        df_m = load_oqc_records("motor")
        df = pd.concat([df_e, df_m], ignore_index=True)
        if df.empty:
            return {"fpy": "─", "sub": "尚無資料", "ok": False}
        today = date.today()
        month_start = date(today.year, today.month, 1)
        if "日期" in df.columns:
            df["_d"] = pd.to_datetime(df["日期"], errors="coerce").dt.date
            df = df[df["_d"] >= month_start]
        total  = len(df)
        n_pass = int((df.get("判定", pd.Series(dtype=str)) == "PASS").sum())
        fpy    = f"{n_pass / total * 100:.1f}%" if total > 0 else "─"
        return {"fpy": fpy, "sub": f"本月 {total} 批 · {n_pass} PASS", "ok": total > 0}
    except Exception:
        return {"fpy": "─", "sub": "資料連線中", "ok": False}

kpi = _load_kpi()

# ═══════════════════════════════════════════════════
# ① 品質總覽 KPI
# ═══════════════════════════════════════════════════
st.markdown(
    '<div style="font-size:13px;font-weight:700;color:var(--navy);'
    'border-left:4px solid var(--accent);padding-left:10px;margin:4px 0 12px">'
    '📊 品質總覽 KPI</div>',
    unsafe_allow_html=True,
)

@st.cache_data(ttl=300, show_spinner=False)
def _load_cs_kpi():
    try:
        from utils.cs_gsheet import load_all_complaints, load_all_8d, DONE_STATUS
        from datetime import date
        df_cs = load_all_complaints()
        df_8d = load_all_8d()
        if df_cs.empty:
            return {"cs_month": "─", "cs_open": "─", "d8_open": "─",
                    "cs_sub": "等待資料累積中", "ok": False}
        today = date.today()
        month_start = date(today.year, today.month, 1)
        def _d(s):
            try:
                from datetime import datetime
                return datetime.strptime(str(s)[:10], "%Y/%m/%d").date()
            except Exception:
                return None
        df_cs["_d"] = df_cs["建立日期"].apply(_d)
        cs_month = len(df_cs[df_cs["_d"] >= month_start])
        cs_open  = len(df_cs[~df_cs["流程狀態"].isin(DONE_STATUS)])
        d8_open  = len(df_8d[df_8d["CAPA狀態"] != "完成"]) if not df_8d.empty else 0
        return {"cs_month": cs_month, "cs_open": cs_open, "d8_open": d8_open,
                "cs_sub": f"累計 {len(df_cs)} 件", "ok": True}
    except Exception:
        return {"cs_month": "─", "cs_open": "─", "d8_open": "─",
                "cs_sub": "資料連線中", "ok": False}

cs_kpi = _load_cs_kpi()

_kpi_items = [
    ("FPY 首次良率",  kpi["fpy"],
     kpi["sub"], "var(--pass)", kpi["ok"]),
    ("本月客訴",      str(cs_kpi["cs_month"]),
     cs_kpi["cs_sub"], "var(--cr)", cs_kpi["ok"]),
    ("未結案件",      str(cs_kpi["cs_open"]),
     "客訴進行中", "var(--orange)", cs_kpi["ok"]),
    ("8D 未結案",     str(cs_kpi["d8_open"]),
     "CAPA 進行中", "var(--blue2)", cs_kpi["ok"]),
    ("返修率",        "─", "等待資料累積中", "var(--ma)", False),
    ("重大異常",      "─", "等待資料累積中", "#b71c1c",   False),
]

_kpi_html = (
    '<div style="display:grid;grid-template-columns:repeat(6,1fr);'
    'gap:10px;margin-bottom:20px">'
)
for _label, _val, _sub, _color, _real in _kpi_items:
    _dim     = "color:var(--dim)" if not _real else f"color:{_color}"
    _pending = (
        '<div style="font-size:9px;color:var(--dim);margin-top:4px;letter-spacing:.5px">'
        '等待資料累積</div>'
    ) if not _real else ""
    _kpi_html += f"""
  <div style="background:#fff;border:1px solid var(--border);border-radius:8px;
              padding:14px 16px;box-shadow:var(--sh);border-top:3px solid {_color}">
    <div style="font-size:10px;font-weight:700;color:var(--muted);
                text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">{_label}</div>
    <div style="font-size:28px;font-weight:700;font-family:'DM Mono',monospace;
                line-height:1;{_dim}">{_val}</div>
    <div style="font-size:11px;color:var(--muted);margin-top:4px">{_sub}</div>
    {_pending}
  </div>"""
_kpi_html += "</div>"
st.markdown(_kpi_html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# ② 品質風險警示
# ═══════════════════════════════════════════════════
st.markdown(
    '<div style="font-size:13px;font-weight:700;color:var(--navy);'
    'border-left:4px solid var(--cr);padding-left:10px;margin:4px 0 12px">'
    '⚠️ 品質風險警示</div>',
    unsafe_allow_html=True,
)
st.markdown("""
<div style="background:#fafbfc;border:1px dashed var(--border2);border-radius:8px;
            padding:24px;text-align:center;color:var(--dim);margin-bottom:20px">
  <div style="font-size:28px;margin-bottom:8px">🔄</div>
  <div style="font-size:13px;font-weight:600;color:var(--muted)">等待資料累積中</div>
  <div style="font-size:11px;margin-top:4px">當品質指標超出設定閾值，異常警示將自動顯示於此區塊</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# ③ 月趨勢分析  ④ Pareto 分析（並排）
# ═══════════════════════════════════════════════════
_trend_col, _pareto_col = st.columns(2)

_placeholder_block = """
<div style="background:#fafbfc;border:1px dashed var(--border2);border-radius:8px;
            padding:40px 20px;text-align:center;color:var(--dim)">
  <div style="font-size:32px;margin-bottom:8px">{icon}</div>
  <div style="font-size:12px;font-weight:600;color:var(--muted)">{title}</div>
  <div style="font-size:11px;margin-top:4px">等待資料累積中</div>
</div>"""

with _trend_col:
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid var(--blue2);padding-left:10px;margin:4px 0 10px">'
        '📈 月趨勢分析</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _placeholder_block.format(icon="📈", title="FPY 月趨勢圖"),
        unsafe_allow_html=True,
    )

with _pareto_col:
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid var(--orange);padding-left:10px;margin:4px 0 10px">'
        '📉 Pareto 分析</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _placeholder_block.format(icon="📉", title="NG 項目 Pareto 圖"),
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# ⑤ 系統入口
# ═══════════════════════════════════════════════════
st.markdown(
    '<div style="font-size:13px;font-weight:700;color:var(--navy);'
    'border-left:4px solid var(--teal);padding-left:10px;margin:4px 0 14px">'
    '🚀 系統入口</div>',
    unsafe_allow_html=True,
)

# ── 卡片 HTML 產生器 ───────────────────────────────
_CARD_BASE = (
    "background:#fff;border:1px solid var(--border);border-radius:12px;"
    "padding:20px 18px 14px;box-shadow:var(--sh);margin-bottom:8px;"
)

def _active_card(icon: str, name: str, desc: str, accent: str) -> str:
    return (
        f'<div style="{_CARD_BASE}border-left:5px solid {accent}">'
        f'  <div style="display:inline-flex;align-items:center;gap:5px;background:#eafaf1;'
        f'              color:var(--pass);padding:3px 10px;border-radius:20px;font-size:10px;'
        f'              font-weight:700;letter-spacing:.5px;margin-bottom:10px">✅ 運行中</div>'
        f'  <div style="font-size:32px;margin-bottom:8px">{icon}</div>'
        f'  <div style="font-size:15px;font-weight:800;color:var(--navy);margin-bottom:6px">{name}</div>'
        f'  <div style="font-size:12px;color:var(--muted);line-height:1.7">{desc}</div>'
        f'</div>'
    )

def _reserved_card(icon: str, name: str, desc: str) -> str:
    return (
        f'<div style="{_CARD_BASE}border:1px dashed var(--border2);background:#fafbfc;opacity:.8">'
        f'  <div style="display:inline-flex;align-items:center;gap:5px;background:var(--bg);'
        f'              color:var(--dim);padding:3px 10px;border-radius:20px;font-size:10px;'
        f'              font-weight:700;letter-spacing:.5px;margin-bottom:10px">🔒 預留功能</div>'
        f'  <div style="font-size:32px;margin-bottom:8px;opacity:.55">{icon}</div>'
        f'  <div style="font-size:15px;font-weight:800;color:var(--muted);margin-bottom:6px">{name}</div>'
        f'  <div style="font-size:12px;color:var(--dim);line-height:1.7">{desc}</div>'
        f'  <div style="margin-top:10px;font-size:10px;color:var(--dim);background:var(--bg);'
        f'              border:1px solid var(--border);padding:3px 10px;border-radius:4px;'
        f'              display:inline-block;letter-spacing:.5px">等待資料累積中</div>'
        f'</div>'
    )

# ── Row 1：兩套主動系統 + 一個預留 ────────────────
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(_active_card(
        "🔬", "維修保養系統",
        "馬達 · 電調返廠維修管理<br>保養記錄 · 良率追蹤 · 返修分析",
        "#00897b",
    ), unsafe_allow_html=True)
    if st.button("進入維修保養系統 →", key="go_rma", use_container_width=True):
        st.switch_page("pages/08_維修保養系統.py")

with c2:
    st.markdown(_active_card(
        "🔬", "檢驗品質系統",
        "OQC 出廠 & IQC 進料品質管制<br>檢驗輸入 · 儀表板 · AI 異常分析",
        "#1565c0",
    ), unsafe_allow_html=True)
    if st.button("進入檢驗品質系統 →", key="go_qms", type="primary", use_container_width=True):
        st.switch_page("pages/01_出廠檢驗輸入.py")

with c3:
    st.markdown(_active_card(
        "📢", "客訴與8D管理系統",
        "客訴受理 · 8D 改善追蹤<br>CAPA 管控 · 趨勢分析 · 回覆時效",
        "#6a1b9a",
    ), unsafe_allow_html=True)
    if st.button("進入客訴8D系統 →", key="go_cs", use_container_width=True):
        st.switch_page("pages/15_客訴8D系統.py")

# ── Row 2：三個預留系統 ───────────────────────────────
c4, c5, c6 = st.columns(3)

with c4:
    st.markdown(_active_card(
        "🏭", "SQM 供應商品質管理",
        "進料異常登錄 · SCAR 追蹤管理<br>供應商品質 Dashboard · CAPA 管控",
        "#d35400",
    ), unsafe_allow_html=True)
    if st.button("進入 SQM 供應商品質 →", key="go_sqm", use_container_width=True):
        st.switch_page("pages/40_🏭_SQM異常登錄.py")

with c5:
    st.markdown(_active_card(
        "📥", "文件自動匯入中心",
        "Excel 批次匯入 IQC 異常<br>欄位智能對應 · 資料驗證 · 一鍵建案",
        "#00838f",
    ), unsafe_allow_html=True)
    if st.button("進入文件匯入中心 →", key="go_import", use_container_width=True):
        st.switch_page("pages/50_📥_文件匯入中心.py")

with c6:
    st.markdown(_reserved_card(
        "🧠", "NotebookLM 知識中心",
        "品質知識庫 · SOP 文件管理<br>AI 問答 · 技術經驗傳承",
    ), unsafe_allow_html=True)

# ── 底部 ───────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<p style="font-size:11px;color:var(--dim);text-align:right;margin-top:4px">'
    'REXONTEC 力科品質指揮平台 v2.0 | Rexontec Quality Command Platform</p>',
    unsafe_allow_html=True,
)
