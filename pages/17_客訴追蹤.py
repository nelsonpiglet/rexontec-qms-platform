"""
REXONTEC 力科品質指揮平台 — 客訴與8D管理系統
客訴案件追蹤
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from utils.cs_gsheet import (
    load_all_complaints, update_cs_status, get_complaint_by_id,
    CS_STATUS_LIST, DONE_STATUS, OVERDUE_DAYS,
)
from utils.style import QMS_CSS, topbar, page_header, gsheet_error_banner

st.set_page_config(
    page_title="REXONTEC 力科 | 客訴追蹤",
    page_icon="📋",
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
    page_header("客訴案件追蹤", "REXONTEC 力科 | Complaint Tracking", "TRK"),
    unsafe_allow_html=True,
)

# ── CSS ───────────────────────────────────────────────
st.markdown("""
<style>
.cs-row { display:flex; align-items:center; gap:10px; padding:10px 0;
           border-bottom:1px solid var(--border); font-size:12.5px; }
.cs-id  { font-weight:800; color:var(--accent); font-family:'DM Mono',monospace;
           font-size:13px; min-width:130px; }
.cs-status-badge { padding:3px 10px; border-radius:20px; font-size:11px;
                    font-weight:700; white-space:nowrap; }
.step-done   { background:#eafaf1; color:#27ae60; border:1px solid #a9dfbf; }
.step-active { background:#e8f0fe; color:#1565c0; border:1px solid #90caf9; }
.step-todo   { background:#f5f5f5; color:#9e9e9e; border:1px solid #e0e0e0; }
.overdue-tag { background:#ffebee; color:#c62828; border:1px solid #ef9a9a;
               padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700; }
.flow-step { display:inline-flex; flex-direction:column; align-items:center;
             gap:4px; font-size:10px; font-weight:700; min-width:70px; text-align:center; }
.flow-dot  { width:28px; height:28px; border-radius:50%; display:flex;
             align-items:center; justify-content:center; font-size:12px; font-weight:900; }
.progress-card {
    background: #fff;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px 12px 20px;
    margin-top: 8px;
    box-shadow: var(--sh);
    border-left: 4px solid var(--accent);
}
.progress-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}
</style>
""", unsafe_allow_html=True)

STATUS_COLOR = {
    "客訴建立": "#90a4ae", "品保確認": "#42a5f5", "RD分析": "#ab47bc",
    "原因分析": "#ffa726", "8D開立": "#ef5350", "改善驗證": "#26a69a",
    "客戶回覆": "#66bb6a", "結案": "#27ae60", "已取消": "#bdbdbd",
}
STATUS_ICON = {
    "客訴建立":"🆕", "品保確認":"🔍", "RD分析":"🔬",
    "原因分析":"🧩", "8D開立":"📑", "改善驗證":"✔️",
    "客戶回覆":"💬", "結案":"✅", "已取消":"🚫",
}


@st.cache_data(ttl=30, show_spinner="載入客訴資料...")
def get_data():
    return load_all_complaints()


def _is_overdue(row: dict) -> bool:
    status = row.get("流程狀態", "")
    if status in DONE_STATUS:
        return False
    limit = OVERDUE_DAYS.get(status, 0)
    if limit == 0:
        return False
    created = row.get("建立日期", "")
    try:
        dt = datetime.strptime(str(created)[:16], "%Y/%m/%d %H:%M")
        return (datetime.now() - dt).days > limit
    except Exception:
        return False


def _build_flow_html(cur_status: str, compact: bool = False) -> str:
    """產生流程進度 HTML。compact=True 使用較小的 dot。"""
    try:
        cur_idx = CS_STATUS_LIST.index(cur_status)
    except ValueError:
        cur_idx = -1

    dot_size  = "24px" if compact else "28px"
    font_size = "8px"  if compact else "9px"
    gap       = "12px" if compact else "16px"
    line_min  = "10px" if compact else "16px"

    html = f'<div style="display:flex;align-items:center;gap:0;overflow-x:auto;padding:6px 0">'
    for i, s in enumerate(CS_STATUS_LIST[:-1]):  # skip 已取消
        if i < cur_idx:
            dot_style  = "background:#27ae60"
            label_style = "color:#27ae60"
            icon = "✓"
        elif i == cur_idx:
            color = STATUS_COLOR.get(s, "var(--accent)")
            dot_style  = f"background:{color}"
            label_style = "color:var(--navy);font-weight:800"
            icon = "●"
        else:
            dot_style  = "background:#e0e0e0"
            label_style = "color:#9e9e9e"
            icon = str(i + 1)

        html += f"""
        <div style="display:inline-flex;flex-direction:column;align-items:center;
                    gap:4px;min-width:{gap};text-align:center">
          <div style="width:{dot_size};height:{dot_size};border-radius:50%;
                      display:flex;align-items:center;justify-content:center;
                      font-size:11px;font-weight:900;color:#fff;{dot_style}">{icon}</div>
          <div style="font-size:{font_size};{label_style};white-space:nowrap">{s}</div>
        </div>"""
        if i < len(CS_STATUS_LIST) - 2:
            html += f'<div style="flex:1;height:2px;background:#e0e0e0;min-width:{line_min};margin-bottom:14px"></div>'

    html += "</div>"
    return html


# ── 重新整理 ──────────────────────────────────────────
_, btn_col = st.columns([10, 1])
with btn_col:
    if st.button("🔄", use_container_width=True, help="重新整理"):
        st.cache_data.clear(); st.rerun()

try:
    df = get_data()
except Exception as _e:
    gsheet_error_banner(_e)

if df.empty:
    st.info("📭 目前尚無客訴案件，請先於【客訴輸入】建立案件。")
    if st.button("➕ 前往建立客訴", type="primary"):
        st.switch_page("pages/16_客訴輸入.py")
    st.stop()

# ═══════════════════════════════════════════════════
# KPI 卡片
# ═══════════════════════════════════════════════════
today = date.today()
month_start = date(today.year, today.month, 1)

def _to_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y/%m/%d").date()
    except Exception:
        return None

df["_d"] = df["建立日期"].apply(_to_date)
total_cs    = len(df)
this_month  = len(df[df["_d"] >= month_start]) if "_d" in df.columns else 0
open_cs     = len(df[~df["流程狀態"].isin(["結案", "已取消"])])
major_cs    = len(df[df["是否重大客訴"] == "是"])
overdue_cs  = sum(_is_overdue(r) for r in df.to_dict("records"))

kpi_html = (
    '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:18px">'
)
for label, val, sub, clr in [
    ("本月客訴",   this_month, f"累計 {total_cs} 件",        "var(--accent)"),
    ("未結案",     open_cs,    "進行中案件",                  "var(--orange)"),
    ("重大客訴",   major_cs,   "S1/S2 等級",                 "var(--cr)"),
    ("超期案件",   overdue_cs, "需立即關注",                  "#b71c1c"),
    ("結案率",
     f"{(total_cs-open_cs)/total_cs*100:.0f}%" if total_cs else "─",
     f"{total_cs-open_cs} / {total_cs}",                    "var(--pass)"),
]:
    kpi_html += f"""
  <div style="background:#fff;border:1px solid var(--border);border-radius:8px;
              padding:14px 16px;box-shadow:var(--sh);border-top:3px solid {clr}">
    <div style="font-size:10px;font-weight:700;color:var(--muted);
                text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">{label}</div>
    <div style="font-size:26px;font-weight:700;font-family:'DM Mono',monospace;
                color:{clr};line-height:1">{val}</div>
    <div style="font-size:11px;color:var(--muted);margin-top:4px">{sub}</div>
  </div>"""
kpi_html += "</div>"
st.markdown(kpi_html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# 篩選列
# ═══════════════════════════════════════════════════
st.markdown('<div class="card"><div class="card-header"><div class="card-title"><span class="card-dot" style="background:var(--accent)"></span>篩選條件</div></div></div>', unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
with f1:
    kw = st.text_input("🔍 搜尋", placeholder="客訴編號 / 客戶 / 機型 / SN",
                        label_visibility="collapsed")
with f2:
    sel_status = st.multiselect("狀態", CS_STATUS_LIST, placeholder="全部狀態",
                                 label_visibility="collapsed")
with f3:
    sel_level = st.multiselect("等級", ["S1 重大","S2 高","S3 中","S4 低"],
                                placeholder="全部等級", label_visibility="collapsed")
with f4:
    show_closed = st.checkbox("顯示已結案 / 已取消", value=False)

view = df.copy()
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
if sel_level:
    view = view[view["客訴等級"].isin(sel_level)]
if not show_closed:
    view = view[~view["流程狀態"].isin(DONE_STATUS)]

st.caption(f"顯示 {len(view)} 筆 / 共 {len(df)} 筆")

if view.empty:
    st.info("沒有符合條件的案件。")
    st.stop()

# ═══════════════════════════════════════════════════
# 案件清單
# ═══════════════════════════════════════════════════
st.markdown('<div class="card" style="margin-top:8px"><div class="card-header"><div class="card-title"><span class="card-dot" style="background:var(--orange)"></span>案件清單</div></div></div>', unsafe_allow_html=True)

DISPLAY_COLS = ["客訴編號","客戶名稱","機型","客訴類型","客訴等級","是否重大客訴","流程狀態","8D編號","建立日期"]
show_df = view[[c for c in DISPLAY_COLS if c in view.columns]].copy()

# 超期標記
show_df.insert(0, "⚠️超期", [
    "⚠️" if _is_overdue(r) else "" for r in view.to_dict("records")
])

st.dataframe(
    show_df,
    use_container_width=True,
    hide_index=True,
    height=min(50 + len(show_df) * 35, 420),
    column_config={
        "⚠️超期":     st.column_config.TextColumn("", width=40),
        "客訴編號":   st.column_config.TextColumn("客訴編號", width=140),
        "客戶名稱":   st.column_config.TextColumn("客戶名稱", width=150),
        "是否重大客訴": st.column_config.TextColumn("重大", width=60),
        "流程狀態":   st.column_config.TextColumn("狀態", width=100),
        "8D編號":     st.column_config.TextColumn("8D編號", width=120),
        "建立日期":   st.column_config.TextColumn("建立日期", width=130),
    },
)

# ═══════════════════════════════════════════════════
# 案件選擇 & 流程進度（緊接案件清單下方）
# ═══════════════════════════════════════════════════
cs_options = view["客訴編號"].dropna().tolist()

sel_label_col, _ = st.columns([5, 1])
with sel_label_col:
    sel_cs = st.selectbox(
        "選擇案件查看進度",
        cs_options,
        format_func=lambda x: (
            f"{x}  ―  "
            + str(view[view["客訴編號"]==x]["客戶名稱"].values[0] if not view[view["客訴編號"]==x].empty else "")
            + "  |  "
            + str(view[view["客訴編號"]==x]["流程狀態"].values[0] if not view[view["客訴編號"]==x].empty else "")
        ),
        label_visibility="collapsed",
    )

row_s = view[view["客訴編號"] == sel_cs]
if row_s.empty:
    st.warning("找不到該案件。")
    st.stop()

r = row_s.iloc[0].to_dict()
cur_status = r.get("流程狀態", "")
is_ov      = _is_overdue(r)
status_clr = STATUS_COLOR.get(cur_status, "var(--text)")

# ── 流程進度卡（緊接案件清單下方）──────────────────
ov_badge = (
    "<span style='background:#ffebee;color:#c62828;border:1px solid #ef9a9a;"
    "padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;"
    "margin-left:8px'>⚠️ 超期</span>"
    if is_ov else ""
)
d8_badge = (
    f"<span style='background:#e8f4fd;color:#1565c0;border:1px solid #90caf9;"
    f"padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;"
    f"margin-left:8px'>🔗 {r['8D編號']}</span>"
    if r.get("8D編號") else ""
)

flow_html = _build_flow_html(cur_status, compact=False)

st.markdown(f"""
<div class="progress-card">
  <div class="progress-card-header">
    <span style="font-size:12px;font-weight:700;color:var(--muted);
                 text-transform:uppercase;letter-spacing:1px">📊 流程進度</span>
    <span style="font-family:'DM Mono',monospace;font-weight:800;
                 color:var(--accent);font-size:14px">{sel_cs}</span>
    <span style="background:{status_clr};color:#fff;padding:3px 12px;
                 border-radius:20px;font-size:11px;font-weight:700">{cur_status}</span>
    {ov_badge}{d8_badge}
  </div>
  {flow_html}
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# 案件詳情 & 狀態更新
# ═══════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="card"><div class="card-header"><div class="card-title"><span class="card-dot" style="background:var(--teal)"></span>案件詳情 & 狀態更新</div></div></div>', unsafe_allow_html=True)

# ── 詳情卡 ────────────────────────────────────────
d1, d2, d3 = st.columns(3)
def _dfield(label, val, color="var(--text)"):
    return (f'<div style="padding:7px 0;border-bottom:1px solid var(--border);font-size:12.5px">'
            f'<span style="width:90px;display:inline-block;font-weight:700;color:var(--muted);font-size:11px">{label}</span>'
            f'<span style="color:{color};font-weight:600">{val or "—"}</span></div>')

with d1:
    st.markdown(
        _dfield("客訴編號", r.get("客訴編號",""), "var(--accent)") +
        _dfield("客戶名稱", r.get("客戶名稱","")) +
        _dfield("機型",     r.get("機型",""))     +
        _dfield("SN/Lot",   r.get("SN/Lot","")),
        unsafe_allow_html=True,
    )
with d2:
    st.markdown(
        _dfield("客訴類型", r.get("客訴類型",""))  +
        _dfield("客訴等級", r.get("客訴等級",""))  +
        _dfield("重大客訴", "⚠️ 是" if r.get("是否重大客訴")=="是" else "否") +
        _dfield("負責人",   r.get("負責人","")),
        unsafe_allow_html=True,
    )
with d3:
    st.markdown(
        _dfield("流程狀態",
                f"{STATUS_ICON.get(cur_status,'')} {cur_status}",
                status_clr) +
        _dfield("8D編號", r.get("8D編號","")) +
        _dfield("建立日期", str(r.get("建立日期",""))[:16]) +
        _dfield("結案日期", str(r.get("結案日期",""))[:16]),
        unsafe_allow_html=True,
    )

# 超期警告
if is_ov:
    st.warning(f"⚠️ 此案件在「{cur_status}」階段已超期，請儘快推進或更新狀態！")

# 客訴描述
if r.get("客訴描述"):
    st.markdown(f"""
    <div style="background:#f8f9fa;border-left:4px solid var(--accent);border-radius:6px;
                padding:12px 16px;margin-top:8px;font-size:13px;color:var(--text)">
      <div style="font-size:10px;font-weight:700;color:var(--muted);margin-bottom:6px">客訴描述</div>
      {r['客訴描述']}
    </div>""", unsafe_allow_html=True)

# ── 狀態更新表單 ──────────────────────────────────
if cur_status not in DONE_STATUS:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.form(f"update_status_{sel_cs}"):
        st.markdown("##### 🔄 更新流程狀態")
        u1, u2 = st.columns([2, 3])
        with u1:
            new_status = st.selectbox(
                "新狀態",
                [s for s in CS_STATUS_LIST if s != cur_status],
            )
        with u2:
            update_note = st.text_input("備註說明", placeholder="填寫狀態更新原因或補充說明")

        _, btn_c, _ = st.columns([1, 1, 1])
        with btn_c:
            do_update = st.form_submit_button("💾 更新狀態", type="primary", use_container_width=True)

    if do_update:
        with st.spinner("更新中..."):
            ok = update_cs_status(sel_cs, new_status, update_note)
        if ok:
            st.success(f"✅ 狀態已更新為【{new_status}】")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("❌ 更新失敗，請重試。")
else:
    st.info(f"此案件已【{cur_status}】，無需更新狀態。")

# 8D 快速連結
if r.get("8D編號"):
    st.markdown(f"""
    <div style="background:#e8f4fd;border:1px solid #90caf9;border-radius:8px;
                padding:10px 16px;margin-top:10px;font-size:13px">
      <span style="font-weight:700;color:#1565c0">🔗 已關聯 8D：</span>
      <span style="font-family:'DM Mono',monospace;font-weight:700">{r['8D編號']}</span>
    </div>""", unsafe_allow_html=True)
    if st.button("📑 前往 8D 管理", use_container_width=False):
        st.switch_page("pages/18_8D管理.py")
elif cur_status not in DONE_STATUS:
    if st.button("➕ 開立 8D", type="secondary"):
        st.switch_page("pages/18_8D管理.py")
