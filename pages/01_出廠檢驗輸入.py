"""
REXONTEC 力科 OQC — 出廠檢驗輸入
支援：電調 ES1002RX / 馬達 MD1001RX
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime
import json
import copy

from utils.style import QMS_CSS, topbar, page_header, grade_badge, section_header
from utils.inspection_data import (
    get_esc_models, get_motor_models, get_customers,
    get_inspectors, get_supervisors, get_mfg_groups,
    get_all_items, get_sections,
)
from utils.oqc_template_db import has_template, get_sections as get_oqc_sections
from utils.gsheet import append_oqc_record
from utils.auth import require_login, user_info_bar

# ── 頁面設定 ────────────────────────────────────────
st.set_page_config(
    page_title="REXONTEC 力科 | OQC 出廠檢驗",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()
user_info_bar()

# ── 導覽列 ──────────────────────────────────────────
col_nav1, col_nav2, col_nav3, col_nav4, col_nav5, col_nav6, col_nav7, col_nav8 = st.columns([1, 1, 1, 1, 1, 1, 1, 2])
with col_nav1:
    if st.button("🏠 指揮平台", use_container_width=True):
        st.switch_page("app.py")
with col_nav2:
    if st.button("📊 儀表板", use_container_width=True):
        st.switch_page("pages/02_儀表板.py")
with col_nav3:
    if st.button("🔬 IQC 進料", use_container_width=True):
        st.switch_page("pages/06_IQC進料檢驗.py")
with col_nav4:
    if st.button("📋 IPQC 巡檢", use_container_width=True):
        st.switch_page("pages/20_📋_IPQC巡檢.py")
with col_nav5:
    if st.button("🔍 追蹤查詢", use_container_width=True):
        st.switch_page("pages/05_追蹤查詢.py")
with col_nav6:
    if st.button("🤖 AI 分析", use_container_width=True):
        st.switch_page("pages/07_AI異常分析.py")
with col_nav7:
    if st.button("⚙️ 系統設定", use_container_width=True):
        st.switch_page("pages/03_系統設定.py")

st.markdown(page_header(
    "OQC 出廠檢驗輸入",
    "Outgoing Quality Control — 電調 / 馬達",
    "OQC",
), unsafe_allow_html=True)

# ── 額外 CSS（行動裝置優化）─────────────────────────
st.markdown("""
<style>
/* 行動裝置讓表格橫向捲動 */
[data-testid="stDataFrame"] { overflow-x: auto !important; }
div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; overflow-x: auto; }

/* 未判定按鈕 — 淺灰（secondary type）*/
button[data-testid$="secondary"] {
    background: #f0f4f8 !important;
    color: #9aafc4 !important;
    border: 1px solid #dce3ec !important;
}
/* primary 預設白底，JS 會覆蓋綠/紅 */
button[data-testid$="primary"] {
    color: #fff !important;
}

/* 表格 row 高度 */
.insp-row { display:flex; align-items:center; padding:7px 6px;
            border-bottom:1px solid var(--border); gap:6px; flex-wrap:wrap; }
.insp-row:nth-child(even) { background:#fafbfc; }
.insp-row.ng-row { background:#fff8f7 !important; border-left:3px solid var(--fail); }
.item-name { font-size:12.5px; font-weight:600; flex:1; min-width:140px; }
.item-spec { font-size:11px; color:var(--muted); }

/* 進度條容器 */
.prog-outer { background:#e8edf4; border-radius:99px; height:7px; overflow:hidden; margin:4px 0; }
.prog-inner { height:100%; border-radius:99px; background:linear-gradient(90deg,#27ae60,#2ecc71); transition:width .4s; }

/* 全部OK checkbox 欄：置中、縮小 */
[data-testid="stCheckbox"] { justify-content: center !important; }
[data-testid="stCheckbox"] > label { padding: 0 !important; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════
# SESSION STATE 初始化
# ════════════════════════════════════════════════════
def _init_state():
    if "product_type" not in st.session_state:
        st.session_state.product_type = "esc"
    if "units" not in st.session_state:
        st.session_state.units = []          # list of SN strings
    if "results" not in st.session_state:
        st.session_state.results = {}        # {item_id: {unit_sn: {result, value}}}
    if "submitted_id" not in st.session_state:
        st.session_state.submitted_id = None

_init_state()


# ════════════════════════════════════════════════════
# 提交成功畫面
# ════════════════════════════════════════════════════
if st.session_state.submitted_id:
    rec_id = st.session_state.submitted_id
    st.markdown(f"""
<div style="max-width:580px;margin:0 auto;padding:20px 0;text-align:center">
  <div style="font-size:56px;margin-bottom:8px">✅</div>
  <div style="font-size:22px;font-weight:900;color:var(--navy);margin-bottom:6px">
    OQC 記錄提交成功
  </div>
  <div style="font-size:14px;font-weight:700;color:var(--accent);
              font-family:'DM Mono',monospace;letter-spacing:2px;
              background:#e3f2fd;padding:10px 20px;border-radius:8px;
              margin:12px auto;display:inline-block">
    {rec_id}
  </div>
  <div style="font-size:12.5px;color:var(--muted);margin-top:10px">
    資料已寫入 Google Sheet，可至 Dashboard 查看統計
  </div>
</div>
""", unsafe_allow_html=True)
    # PDF 匯出（提交後）
    _pdf_sections = get_sections(st.session_state.get("_last_pt", "esc"))
    _pdf_header   = st.session_state.get("_last_header", {})
    _pdf_results  = st.session_state.get("_last_results", {})
    _pdf_units    = st.session_state.get("_last_units", [])
    _pdf_note     = st.session_state.get("_last_note", "")

    if _pdf_header and _pdf_units:
        try:
            from utils.pdf_report import generate_pdf
            _pdf_bytes = generate_pdf(
                product_type = st.session_state.get("_last_pt", "esc"),
                header       = {**_pdf_header, "rec_id": rec_id},
                sections     = _pdf_sections,
                results      = _pdf_results,
                units        = _pdf_units,
                note         = _pdf_note,
            )
            st.download_button(
                "📄 下載 PDF 報告",
                data      = _pdf_bytes,
                file_name = f"{rec_id}.pdf",
                mime      = "application/pdf",
                use_container_width=True,
            )
        except Exception as _e:
            st.warning(f"PDF 生成失敗：{_e}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 繼續新增下一筆", type="primary", use_container_width=True):
            st.session_state.submitted_id = None
            st.session_state.units  = []
            st.session_state.results = {}
            st.rerun()
    with col2:
        if st.button("📊 前往 Dashboard", use_container_width=True):
            st.switch_page("pages/02_儀表板.py")
    st.stop()


# ════════════════════════════════════════════════════
# ① 產品類型選擇
# ════════════════════════════════════════════════════
tab_esc, tab_motor = st.tabs(["⚡ 電調 ESC", "🔧 馬達 Motor"])

with tab_esc:
    _type = "esc"
with tab_motor:
    _type = "motor"

# 讀取 tab 選擇（tab index 存在 session state）
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "esc"

col_t1, col_t2 = st.columns(2)
with col_t1:
    if st.button("⚡ 電調 ESC", use_container_width=True,
                 type="primary" if st.session_state.product_type == "esc" else "secondary"):
        if st.session_state.product_type != "esc":
            st.session_state.product_type = "esc"
            st.session_state.units   = []
            st.session_state.results = {}
            st.rerun()
with col_t2:
    if st.button("🔧 馬達 Motor", use_container_width=True,
                 type="primary" if st.session_state.product_type == "motor" else "secondary"):
        if st.session_state.product_type != "motor":
            st.session_state.product_type = "motor"
            st.session_state.units   = []
            st.session_state.results = {}
            st.rerun()

product_type  = st.session_state.product_type
is_esc        = (product_type == "esc")

# ── OQC 模板動態注入（馬達專用）──────────────────────────────────
_hdr_model   = st.session_state.get("hdr_model", "")
_use_oqc_tpl = (not is_esc) and has_template(_hdr_model)

# 偵測模板狀態變化 → 重置結果，避免舊資料殘留
_tpl_state_key = f"{product_type}|{_hdr_model}|{_use_oqc_tpl}"
if st.session_state.get("_last_tpl_state") != _tpl_state_key:
    st.session_state["_last_tpl_state"] = _tpl_state_key
    st.session_state.results = {}
    st.session_state.units   = []
    # 切換機種時，從 OQC 模板自動預填客戶名稱
    if _use_oqc_tpl:
        from utils.oqc_template_db import get_template as _get_tpl
        _tpl_meta = _get_tpl(_hdr_model) or {}
        _tpl_cust = _tpl_meta.get("customer", "")
        if _tpl_cust:
            # 確保 DB 有此客戶名稱（自動植入）
            try:
                from utils.signature_db import add_name as _sdb_add
                _sdb_add(_tpl_cust, "customer")
            except Exception:
                pass
            st.session_state["hdr_cust"] = _tpl_cust

if _use_oqc_tpl:
    sections = get_oqc_sections(_hdr_model)
else:
    sections = get_sections(product_type)

all_items = get_all_items(sections)

st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:8px 0 14px'>",
            unsafe_allow_html=True)

# ── OQC 模板狀態提示 ────────────────────────────────────────────────
if _use_oqc_tpl:
    _tpl_n_sec   = len(sections)
    _tpl_n_items = len(all_items)
    st.markdown(
        f'<div style="background:#e8f5e9;border:1px solid #a5d6a7;border-left:4px solid #2e7d32;'
        f'border-radius:7px;padding:9px 14px;margin-bottom:10px;font-size:12px;'
        f'display:flex;align-items:center;gap:10px">'
        f'<span style="font-size:18px">📋</span>'
        f'<div><b style="color:#2e7d32">OQC 成檢表模板已套用</b>　機種：{_hdr_model}'
        f'　{_tpl_n_sec} 區段 / {_tpl_n_items} 項目'
        f'<span style="color:var(--muted);font-size:11px;margin-left:8px">'
        f'（來自 Excel 匯入，可至系統設定 → OQC 成檢表模板管理）</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════
# ── 智慧選取元件（下拉快選 + 手填 + 自動記憶）────────
# ════════════════════════════════════════════════════
_ADD_NEW = "＋ 新增人員"

def _smart_combo(label_html: str, role: str,
                 sel_key: str, free_key: str, flag_key: str,
                 fallback: list = None) -> str:
    """
    通用 combo 元件：
      ① 顯示 HTML label
      ② selectbox：DB 現有名稱 + [＋ 新增人員]
      ③ 選到「＋ 新增人員」→ 顯示 text_input
      ④ 提交後由呼叫端負責 add_name() 寫入 DB
    回傳最終名稱字串。
    """
    from utils.signature_db import get_names, seed_if_empty

    # 首次使用：植入 config 預設名單
    if fallback:
        try:
            seed_if_empty(role, fallback)
        except Exception:
            pass

    names = get_names(role)
    if not names and fallback:
        names = [n for n in (fallback or []) if (n or "").strip() and n != "其他"]

    opts = names + [_ADD_NEW]

    st.markdown(label_html, unsafe_allow_html=True)

    if st.session_state.get(sel_key) not in opts:
        st.session_state[sel_key] = opts[0]

    sel = st.selectbox("", opts, key=sel_key, label_visibility="collapsed")

    if sel == _ADD_NEW:
        st.session_state[flag_key] = True
        typed = st.text_input(
            "", key=free_key, label_visibility="collapsed",
            placeholder="輸入新名稱，提交後自動記憶"
        )
        return (typed or "").strip()
    else:
        st.session_state[flag_key] = False
        return sel


# ════════════════════════════════════════════════════
# ② 基本資料表頭
# ════════════════════════════════════════════════════
with st.expander("📋 基本資料 / 表頭", expanded=True):
    models = get_esc_models() if is_esc else get_motor_models()
    c1, c2, c3 = st.columns(3)
    with c1:
        hdr_model    = st.selectbox("機種 *", models, key="hdr_model")
    with c2:
        hdr_part_no  = st.text_input("料號", placeholder="例：7720-057-00400", key="hdr_pn")
    with c3:
        hdr_customer = _smart_combo(
            "<div style='font-size:12px;font-weight:600;margin-bottom:2px'>"
            "客戶名稱 *</div>",
            "customer", "hdr_cust", "hdr_cust_free", "_cust_is_new",
            fallback=get_customers(),
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        hdr_batch_no = st.text_input("批號 *", placeholder="例：510-250618003", key="hdr_batch")
    with c5:
        hdr_serial   = st.text_input("序號範圍", placeholder="R2411A0001 ~ R2411A0010", key="hdr_serial")
    with c6:
        hdr_date     = st.date_input("檢驗日期 *", value=date.today(), key="hdr_date")

    c7, c8, c9 = st.columns(3)
    with c7:
        hdr_qty      = st.number_input("本批數量 *", min_value=1, value=10, step=1, key="hdr_qty")
    with c8:
        hdr_sample   = st.number_input("抽驗數量 *", min_value=1, value=5,  step=1, key="hdr_sample")
    with c9:
        hdr_insp = _smart_combo(
            "<div style='font-size:12px;font-weight:600;margin-bottom:2px'>"
            "檢驗員 *</div>",
            "inspector", "hdr_insp", "hdr_insp_free", "_hdr_insp_is_new",
            fallback=get_inspectors(),
        )

    c10, c11, _ = st.columns(3)
    with c10:
        hdr_insp_method = st.selectbox(
            "檢驗方法 *", ["正常", "加嚴", "減量"], key="hdr_method",
            help="正常 = Normal / 加嚴 = Tightened / 減量 = Reduced (MIL-STD-105E)",
        )
    with c11:
        hdr_verdict = st.selectbox(
            "判定結果 *", ["允收", "不允收"], key="hdr_verdict",
        )
    # 保留相容舊 schema（不顯示於表單，但仍傳遞給 gsheet/PDF）
    hdr_super   = ""
    hdr_mfg_grp = "─"
    hdr_mfg_ord = ""

    # 公司別 + 送樣
    st.markdown("<hr style='border:none;border-top:1px dashed var(--border);margin:8px 0'>",
                unsafe_allow_html=True)
    co_col, samp_col = st.columns([2, 3])
    with co_col:
        _co_choice = st.radio(
            "公司別",
            ["力科 REXONTEC", "力山 REXON"],
            horizontal=True,
            key="oqc_company",
        )
        oqc_company = "rexon" if "力山" in _co_choice else "rexontec"
        if oqc_company == "rexon":
            st.markdown(
                '<span style="background:#1a5276;color:#fff;padding:3px 12px;'
                'border-radius:5px;font-size:11px;font-weight:900;letter-spacing:1px">'
                'REXON 力山</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span style="background:#0d1b2a;color:#f0a500;padding:3px 12px;'
                'border-radius:5px;font-size:11px;font-weight:900;letter-spacing:1px">'
                'REXONTEC 力科</span>',
                unsafe_allow_html=True,
            )
    with samp_col:
        st.markdown("<div style='padding-top:4px'>", unsafe_allow_html=True)
        oqc_is_sample = st.checkbox(
            "🟡  **送  樣**　（勾選後 PDF 報告標題將加入「送樣」字樣）",
            key="oqc_is_sample",
        )
        if oqc_is_sample:
            st.markdown(
                '<span style="background:#f0a500;color:#0d1b2a;padding:3px 14px;'
                'border-radius:5px;font-size:11px;font-weight:900;letter-spacing:2px">'
                '送樣 SAMPLE</span>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════
# ③ 抽驗機台 SN 設定
# ════════════════════════════════════════════════════
with st.expander("🏷️ 抽驗機台序號設定", expanded=True):
    st.caption("每行輸入一個序號，或按「自動填入」依序號範圍產生")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        # 若 key 不存在（第一次或 pop 之後），先寫入 session state 再讓 widget 讀取
        # 不傳 value= 給有 key 的 widget，避免 Streamlit 在 rerun 時覆蓋 session state
        if "sn_text_area" not in st.session_state:
            st.session_state["sn_text_area"] = (
                "\n".join(st.session_state.units) if st.session_state.units else ""
            )
        sn_text = st.text_area(
            "機台序號（每行一個）",
            height=120,
            placeholder="SN-001\nSN-002\nSN-003\n…",
            key="sn_text_area",
            label_visibility="collapsed",
        )
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ 自動填入\n(依抽驗數量)", use_container_width=True):
            n = int(st.session_state.get("hdr_sample", 5))
            auto_sns = [f"SN-{str(i+1).zfill(3)}" for i in range(n)]
            st.session_state.units = auto_sns
            st.session_state.pop("sn_text_area", None)  # 清除 key，下次 rerun 重新初始化
            st.rerun()
        if st.button("🗑️ 清除序號", use_container_width=True):
            st.session_state.units = []
            st.session_state.pop("sn_text_area", None)
            st.rerun()

    # 解析 SN 輸入
    raw_sns = [s.strip() for s in sn_text.split("\n") if s.strip()]
    if raw_sns != st.session_state.units:
        st.session_state.units = raw_sns
        # 重置結果（SN 改變時）
        st.session_state.results = {}

units = st.session_state.units

if not units:
    st.warning("請先填入機台序號再開始檢驗")
    st.stop()

st.success(f"已設定 {len(units)} 台：{' | '.join(units[:8])}{'…' if len(units)>8 else ''}")


# ════════════════════════════════════════════════════
# ④ 結果初始化
# ════════════════════════════════════════════════════
def _init_results():
    for item in all_items:
        if item["id"] not in st.session_state.results:
            st.session_state.results[item["id"]] = {}
        for u in units:
            if u not in st.session_state.results[item["id"]]:
                st.session_state.results[item["id"]][u] = {
                    "result": "─",
                    "value": None,
                }

_init_results()


# ════════════════════════════════════════════════════
# ⑤ 進度統計（以「台」為單位）
# ════════════════════════════════════════════════════
def _calc_stats():
    n_units = len(units)
    n_items = len(all_items)

    units_done    = 0   # 所有項目皆已判定（PASS 或 FAIL）
    units_ng      = 0   # 至少一項 FAIL
    units_pending = 0   # 尚有任何項目未判定
    item_passed   = 0   # 項目層級：通過數
    item_failed   = 0   # 項目層級：不良數
    item_pending  = 0   # 項目層級：待判定數

    for u in units:
        u_pass = u_fail = u_pend = 0
        for item in all_items:
            r = st.session_state.results.get(item["id"], {}).get(u, {}).get("result", "─")
            if r == "PASS":
                u_pass += 1; item_passed += 1
            elif r == "FAIL":
                u_fail += 1; item_failed += 1
            else:
                u_pend += 1; item_pending += 1
        if u_pend == 0:
            units_done += 1
        else:
            units_pending += 1
        if u_fail > 0:
            units_ng += 1

    pct = round(units_done / n_units * 100) if n_units else 0
    return (n_units, units_done, units_ng, units_pending,
            item_passed, item_failed, item_pending, pct)

(n_units, units_done, units_ng, units_pending,
 item_passed, item_failed, item_pending, pct) = _calc_stats()

# ── 進度條（台數為主）─────────────────────────────
bar_color = "var(--fail)" if units_ng else "var(--pass)"
st.markdown(f"""
<div class="prog-wrap">
  <div class="prog-nums">
    <div class="prog-num-item">
      <div class="prog-num pend">{units_pending}</div>
      <div style="font-size:9.5px;color:var(--muted)">待驗台</div>
    </div>
    <div class="prog-num-item">
      <div class="prog-num pass">{units_done - units_ng}</div>
      <div style="font-size:9.5px;color:var(--muted)">完成台</div>
    </div>
    <div class="prog-num-item">
      <div class="prog-num fail">{units_ng}</div>
      <div style="font-size:9.5px;color:var(--muted)">NG 台</div>
    </div>
  </div>
  <div class="prog-bar-wrap">
    <div style="font-size:10px;color:var(--muted);margin-bottom:3px">
      共 {n_units} 台抽驗　｜　通過項目 {item_passed} / 不良項目 {item_failed} / 待判定 {item_pending}
    </div>
    <div class="prog-track">
      <div class="prog-fill-pass" style="width:{pct}%;background:{bar_color}"></div>
    </div>
    <div class="prog-pct">完成 {units_done}/{n_units} 台（{pct}%）</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 總判定（以「項目層級」判斷是否可結案）──────────
cr_ng = sum(1 for item in all_items if item["grade"] == "CR" and
            any(st.session_state.results.get(item["id"], {}).get(u, {}).get("result") == "FAIL" for u in units))
ma_ng = sum(1 for item in all_items if item["grade"] == "MA" and
            any(st.session_state.results.get(item["id"], {}).get(u, {}).get("result") == "FAIL" for u in units))
mi_ng = sum(1 for item in all_items if item["grade"] == "MI" and
            any(st.session_state.results.get(item["id"], {}).get(u, {}).get("result") == "FAIL" for u in units))

# 全部台數都完成（item_pending == 0）才顯示最終判定
pending = item_pending   # 維持後續程式碼相容

if pending == 0:
    if cr_ng > 0 or ma_ng > 0:
        verdict_html = f"""<div class="verdict-fail">
          <div class="verdict-icon">❌</div>
          <div>
            <div class="verdict-label" style="color:var(--fail)">不 合 格 FAIL</div>
            <div class="verdict-sub">CR: {cr_ng}  MA: {ma_ng}  MI: {mi_ng}</div>
          </div></div>"""
    else:
        verdict_html = f"""<div class="verdict-pass">
          <div class="verdict-icon">✅</div>
          <div>
            <div class="verdict-label" style="color:var(--pass)">合 格 PASS</div>
            <div class="verdict-sub">通過 {item_passed} 項 / 不良 {item_failed} 項</div>
          </div></div>"""
else:
    verdict_html = f"""<div class="verdict-pend">
      <div class="verdict-icon">🔬</div>
      <div>
        <div class="verdict-label" style="color:var(--muted)">待 檢 驗 ({pending})</div>
        <div class="verdict-sub">尚有 {pending} 項未判定</div>
      </div></div>"""
st.markdown(verdict_html, unsafe_allow_html=True)


# ════════════════════════════════════════════════════
# ⑥ 檢驗表格（section by section）
# ════════════════════════════════════════════════════
st.markdown("""
<div style="background:#f0f4f8;border-radius:6px;padding:7px 14px;
            font-size:11.5px;color:#6b7c93;margin-bottom:6px">
  💡 按一下 = <b style="color:#27ae60">OK</b>　再按一下 = <b style="color:#e74c3c">NG</b>　第三下 = 清除
</div>
""", unsafe_allow_html=True)

# ── 按鈕著色 JavaScript（透過 iframe 操作父頁面 DOM）─────────────────
components.html("""
<script>
(function () {
  var PASS_BG = '#27ae60';
  var FAIL_BG = '#e74c3c';

  function applyColor(marker, bg) {
    // Walk up from marker until we find the first ancestor that owns a button.
    // That ancestor is the individual stColumn container — narrowest possible scope.
    var el = marker.parentElement;
    while (el && el.tagName !== 'BODY') {
      if (el.querySelector('button') !== null) {
        var btn = el.querySelector('button');
        btn.style.setProperty('background',       bg,      'important');
        btn.style.setProperty('background-color', bg,      'important');
        btn.style.setProperty('border-color',     bg,      'important');
        btn.style.setProperty('color',            '#fff',  'important');
        return;
      }
      el = el.parentElement;
    }
  }

  function colorButtons() {
    var doc = window.parent.document;
    doc.querySelectorAll('span.pass-marker').forEach(function (m) {
      applyColor(m, PASS_BG);
    });
    doc.querySelectorAll('span.fail-marker').forEach(function (m) {
      applyColor(m, FAIL_BG);
    });
  }

  // Run immediately and after short delays to catch Streamlit's async render
  colorButtons();
  setTimeout(colorButtons, 200);
  setTimeout(colorButtons, 600);

  // Watch for any DOM mutation and reapply
  var obs = new MutationObserver(function () { colorButtons(); });
  obs.observe(window.parent.document.body, { childList: true, subtree: true });
})();
</script>
""", height=0, scrolling=False)

def _result_color(r: str) -> str:
    return {"PASS": "var(--pass)", "FAIL": "var(--fail)"}.get(r, "var(--muted)")

def _result_icon(r: str) -> str:
    return {"PASS": "✓ PASS", "FAIL": "✗ FAIL"}.get(r, "─")


# ── PASS/FAIL 按鈕 callback ────────────────────────
def toggle_result(item_id: str, unit: str):
    cur = st.session_state.results[item_id][unit]["result"]
    nxt = {"─": "PASS", "PASS": "FAIL", "FAIL": "─"}[cur]
    st.session_state.results[item_id][unit]["result"] = nxt

def set_all_ok(item_id: str, chk_key: str):
    """全選勾選：checked → 全部 PASS；unchecked → 全部清除"""
    checked = st.session_state.get(chk_key, False)
    target  = "PASS" if checked else "─"
    for u in st.session_state.get("units", []):
        if item_id in st.session_state.results and u in st.session_state.results[item_id]:
            st.session_state.results[item_id][u]["result"] = target

def set_value(item_id: str, unit: str, val):
    st.session_state.results[item_id][unit]["value"] = val
    # 自動判定
    item_def = next((i for i in all_items if i["id"] == item_id), None)
    if item_def and item_def["type"] == "num" and val is not None:
        mn = item_def.get("min")
        mx = item_def.get("max")
        ok = True
        if mn is not None and val < mn:
            ok = False
        if mx is not None and val > mx:
            ok = False
        st.session_state.results[item_id][unit]["result"] = "PASS" if ok else "FAIL"


# ── 主表格 ─────────────────────────────────────────
for sec_idx, sec in enumerate(sections):
    sec_letter = sec["id"]
    # 計算本 section 完成數
    sec_items   = sec["items"]
    sec_total   = len(sec_items) * len(units)
    sec_done    = sum(
        1 for item in sec_items for u in units
        if st.session_state.results.get(item["id"], {}).get(u, {}).get("result", "─") != "─"
    )
    sec_ng      = sum(
        1 for item in sec_items for u in units
        if st.session_state.results.get(item["id"], {}).get(u, {}).get("result") == "FAIL"
    )

    badge_color = "var(--fail)" if sec_ng else ("var(--pass)" if sec_done == sec_total else "var(--muted)")
    badge_text  = f"NG:{sec_ng}" if sec_ng else f"{sec_done}/{sec_total}"

    header_html = f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            background:#f7f9fc;border:1px solid var(--border);
            border-left:4px solid var(--blue2);border-radius:0 7px 0 0;
            padding:10px 14px;margin-top:14px;">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:26px;height:26px;border-radius:50%;background:var(--blue2);
                color:#fff;display:flex;align-items:center;justify-content:center;
                font-size:12px;font-weight:700">{sec_letter}</div>
    <div>
      <div style="font-size:13px;font-weight:700">{sec["label"]}</div>
      <div style="font-size:10.5px;color:var(--muted)">{sec.get("subtitle","")}</div>
    </div>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;color:{badge_color};
              background:var(--bg);border:1px solid var(--border);
              padding:2px 10px;border-radius:99px">{badge_text}</div>
</div>
"""
    st.markdown(header_html, unsafe_allow_html=True)

    # ── 每個 item ─────────────────────────────────
    for item in sec_items:
        iid    = item["id"]
        grade  = item["grade"]
        itype  = item["type"]

        # 計算這一項是否有 NG
        item_ng = any(
            st.session_state.results.get(iid, {}).get(u, {}).get("result") == "FAIL"
            for u in units
        )
        row_bg = "background:#fff8f7;border-left:3px solid var(--fail);" if item_ng else ""

        grade_colors = {"CR": "#c0392b", "MA": "#d68910", "MI": "#1e8449"}
        gcol = grade_colors.get(grade, "#888")

        # Item 標題列
        st.markdown(f"""
<div style="{row_bg}padding:9px 10px 4px;border-bottom:1px solid #edf0f4;display:flex;align-items:flex-start;gap:10px;flex-wrap:wrap">
  <span style="background:{gcol};color:#fff;padding:1px 8px;border-radius:4px;
               font-size:10px;font-weight:800;letter-spacing:.4px;flex-shrink:0">{grade}</span>
  <div style="flex:1;min-width:140px">
    <div style="font-size:12.5px;font-weight:700">{item["no"]} {item["name"]}</div>
    <div style="font-size:11px;color:var(--muted);margin-top:1px">
      📏 {item["spec"]} &nbsp;|&nbsp; 🔧 {item.get("tool","")}
    </div>
  </div>
  {'<span style="font-size:11px;color:var(--fail);font-weight:700">⚠ NG</span>' if item_ng else ''}
</div>
""", unsafe_allow_html=True)

        # ── PASS/FAIL 按鈕區（依 unit 分欄）─────────
        max_cols   = min(len(units), 10)   # 最多顯示 10 欄
        all_ok_key = f"chk_{iid}"
        # 第 0 欄 = 全部OK勾選框；後續欄 = 各機台按鈕
        unit_cols  = st.columns([0.75] + [1] * max_cols)

        with unit_cols[0]:
            st.markdown(
                '<div style="font-size:9px;color:#6b7c93;text-align:center;'
                'padding-top:18px;line-height:1.3">全部<br>OK</div>',
                unsafe_allow_html=True,
            )
            st.checkbox(
                "", key=all_ok_key,
                on_change=set_all_ok, args=(iid, all_ok_key),
                label_visibility="collapsed",
            )

        for u_idx, u in enumerate(units[:max_cols]):
            res_data = st.session_state.results[iid][u]
            res      = res_data["result"]
            val      = res_data.get("value")

            with unit_cols[u_idx + 1]:   # +1：跳過 checkbox 欄
                st.caption(u)   # SN label

                if itype == "pf":
                    # ── OK / NG 切換按鈕（一下=OK，再按=NG，再按=清除）─────────
                    btn_label = {"PASS": "✓ OK", "FAIL": "✗ NG", "─": "  ─  "}[res]
                    btn_type  = "primary" if res in ("PASS", "FAIL") else "secondary"

                    if res == "PASS":
                        st.markdown(
                            '<span class="pass-marker"></span>',
                            unsafe_allow_html=True,
                        )
                    elif res == "FAIL":
                        fail_id = (f"fail_{iid}_{u}"
                                   .replace(".", "_").replace("-", "_"))
                        st.markdown(
                            f'<span class="fail-marker" id="{fail_id}"></span>',
                            unsafe_allow_html=True,
                        )

                    st.button(
                        btn_label,
                        key=f"btn_{iid}_{u}",
                        on_click=toggle_result,
                        args=(iid, u),
                        use_container_width=True,
                        type=btn_type,
                    )

                else:
                    # ── 數值輸入 ──────────────────
                    mn  = item.get("min")
                    mx  = item.get("max")
                    unit_label = item.get("unit", "")

                    cur_val = val if val is not None else 0.0
                    new_val = st.number_input(
                        f"{unit_label}",
                        value=float(cur_val),
                        format="%.2f",
                        key=f"num_{iid}_{u}",
                        label_visibility="visible",
                    )
                    if new_val != cur_val:
                        set_value(iid, u, new_val)

                    # 規格顯示
                    spec_txt = ""
                    if mn is not None and mx is not None:
                        spec_txt = f"{mn}~{mx}"
                    elif mx is not None:
                        spec_txt = f"≦{mx}"
                    elif mn is not None:
                        spec_txt = f"≧{mn}"

                    auto_res = st.session_state.results[iid][u].get("result", "─")
                    if new_val != 0 or cur_val != 0:
                        ok_icon = "✅" if auto_res == "PASS" else ("❌" if auto_res == "FAIL" else "─")
                        st.markdown(
                            f'<div style="text-align:center;font-size:13px">{ok_icon}</div>'
                            f'<div style="text-align:center;font-size:9.5px;color:var(--dim)">{spec_txt}</div>',
                            unsafe_allow_html=True,
                        )

        # 若 unit 超過 10，顯示提示
        if len(units) > 10:
            st.caption(f"⚠ 僅顯示前 10 台，請分批輸入剩餘 {len(units)-10} 台")

        st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════
# ⑥-B 飛行運轉腳本測試圖示（電調專用）
# ════════════════════════════════════════════════════
if is_esc:
    import os
    script_img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "esc_test_script.png")
    script_img_jpg  = os.path.join(os.path.dirname(__file__), "..", "assets", "esc_test_script.jpg")

    st.markdown("""
<div style="background:#f7f9fc;border:1px solid var(--border);border-left:4px solid var(--orange);
            border-radius:7px;padding:12px 16px;margin:14px 0 6px">
  <div style="font-size:12px;font-weight:700;color:var(--navy);margin-bottom:8px">
    📈 飛行運轉腳本測試圖示
  </div>
</div>
""", unsafe_allow_html=True)

    found_img = None
    if os.path.exists(script_img_path):
        found_img = script_img_path
    elif os.path.exists(script_img_jpg):
        found_img = script_img_jpg

    if found_img:
        st.image(found_img, caption="運轉功能測試腳本 — 1000µs ～ 1900µs 動態響應與負載穩定性",
                 use_container_width=True)
    else:
        st.markdown("""
<div style="border:2px dashed var(--border2);border-radius:8px;padding:20px;
            text-align:center;color:var(--muted);background:var(--bg)">
  <div style="font-size:24px;margin-bottom:6px">📊</div>
  <div style="font-size:12px;font-weight:600">飛行測試腳本圖尚未放入</div>
  <div style="font-size:11px;margin-top:4px">
    請將圖片存至：<code>assets/esc_test_script.png</code>
  </div>
</div>
""", unsafe_allow_html=True)
        # 提供臨時上傳功能
        uploaded_script = st.file_uploader(
            "或於此上傳測試腳本圖（本次暫存，重啟後需重新上傳）",
            type=["png", "jpg", "jpeg"],
            key="script_img_upload",
        )
        if uploaded_script:
            st.image(uploaded_script,
                     caption="運轉功能測試腳本 — 1000µs ～ 1900µs 動態響應與負載穩定性",
                     use_container_width=True)
            # 詢問是否永久儲存
            if st.button("💾 儲存為預設腳本圖（下次自動顯示）", key="save_script_img"):
                ext = uploaded_script.name.rsplit(".", 1)[-1]
                save_path = os.path.join(
                    os.path.dirname(__file__), "..", "assets", f"esc_test_script.{ext}"
                )
                with open(save_path, "wb") as f:
                    f.write(uploaded_script.getvalue())
                st.success(f"已儲存！下次自動顯示。")
                st.rerun()

    st.caption("（註：運轉功能測試於 1000µs - 1900µs 區間之動態響應與負載穩定性）")
    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════
# ⑦ NG 警示摘要
# ════════════════════════════════════════════════════
ng_items = []
for sec in sections:
    for item in sec["items"]:
        fail_units = [
            u for u in units
            if st.session_state.results.get(item["id"], {}).get(u, {}).get("result") == "FAIL"
        ]
        if fail_units:
            ng_items.append((item, fail_units))

if ng_items:
    ng_lines = "".join(
        f'<div class="ng-item">⛔ <b>[{it["grade"]}] {it["id"]} {it["name"]}</b>'
        f'&nbsp;—&nbsp; NG 機台：{", ".join(us)}</div>'
        for it, us in ng_items
    )
    st.markdown(f"""
<div class="ng-alert" style="margin-top:14px">
  <div class="ng-alert-title">⚠ NG 項目警示 — 共 {len(ng_items)} 項不合格</div>
  {ng_lines}
</div>
""", unsafe_allow_html=True)
    ng_summary = "；".join(f"[{it['grade']}]{it['name']} ({','.join(us)})" for it, us in ng_items)
else:
    ng_summary = ""


# ════════════════════════════════════════════════════
# ⑧ 照片上傳
# ════════════════════════════════════════════════════
st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:16px 0 12px'>",
            unsafe_allow_html=True)
st.markdown("""
<div class="card-header" style="border-radius:7px 7px 0 0;border:1px solid var(--border)">
  <div class="card-title"><div class="card-dot" style="background:var(--orange)"></div>📷 照片上傳</div>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "拍攝 NG 項目照片（可多張）",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    key="photo_upload",
    label_visibility="collapsed",
)

photo_urls: list[str] = []
if uploaded_files:
    cols = st.columns(min(len(uploaded_files), 5))
    for i, f in enumerate(uploaded_files[:5]):
        with cols[i]:
            st.image(f, caption=f.name, use_container_width=True)
    if len(uploaded_files) > 5:
        st.caption(f"（另有 {len(uploaded_files)-5} 張未顯示）")

    # 若有 Google Drive 整合，可在此上傳並取得 URL
    # photo_urls = upload_to_drive(uploaded_files)  # 後續整合
    photo_urls = [f.name for f in uploaded_files]  # 暫用檔名佔位


# ════════════════════════════════════════════════════
# ⑨ 備註
# ════════════════════════════════════════════════════
note = st.text_area(
    "📝 備註 / 異常說明",
    placeholder="飛行運轉腳本測試圖示說明、特殊情況等…",
    height=90,
    key="note_input",
)


# ════════════════════════════════════════════════════
# ⑨-B 簽核確認
# ════════════════════════════════════════════════════
st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:16px 0 12px'>",
            unsafe_allow_html=True)
st.markdown("""
<div class="card-header" style="border-radius:7px 7px 0 0;border:1px solid var(--border)">
  <div class="card-title"><div class="card-dot" style="background:var(--blue)"></div>✍️ 簽核確認</div>
</div>
""", unsafe_allow_html=True)

sig_c1, sig_c2, sig_c3 = st.columns(3)
with sig_c1:
    sig_inspector = _smart_combo(
        "<div style='font-size:12px;color:var(--muted);margin-bottom:2px'>檢驗員</div>",
        "inspector", "sig_insp", "sig_insp_free", "_insp_is_new",
        fallback=get_inspectors(),
    )
    sig_insp_date = st.date_input("日期", value=date.today(),
                                   key="sig_insp_date", label_visibility="visible")
with sig_c2:
    sig_supervisor = _smart_combo(
        "<div style='font-size:12px;color:var(--muted);margin-bottom:2px'>品保主管</div>",
        "qa_manager", "sig_super", "sig_super_free", "_super_is_new",
        fallback=get_supervisors(),
    )
    sig_super_date = st.date_input("日期", value=date.today(),
                                    key="sig_super_date", label_visibility="visible")
with sig_c3:
    sig_approver = _smart_combo(
        "<div style='font-size:12px;color:var(--muted);margin-bottom:2px'>核准</div>",
        "approver", "sig_appr_sel", "sig_appr_free", "_appr_is_new",
        fallback=[],
    )
    sig_appr_date = st.date_input("日期", value=date.today(),
                                   key="sig_appr_date", label_visibility="visible")


# ════════════════════════════════════════════════════
# ⑩ 提交按鈕
# ════════════════════════════════════════════════════
# ════════════════════════════════════════════════════
# ⑩-A PDF 即時預覽匯出（提交前可用）
# ════════════════════════════════════════════════════
st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:14px 0 10px'>",
            unsafe_allow_html=True)
with st.expander("📄 匯出 PDF 報告（填寫中途亦可下載）", expanded=False):
    try:
        from utils.pdf_report import generate_pdf as _gen_pdf
        _co_raw = st.session_state.get("oqc_company", "力科 REXONTEC")
        _header_for_pdf = {
            "model":        st.session_state.get("hdr_model", "─"),
            "part_no":      st.session_state.get("hdr_pn", ""),
            "customer":     hdr_customer,
            "batch_no":     st.session_state.get("hdr_batch", ""),
            "serial_range": st.session_state.get("hdr_serial", ""),
            "qty":          st.session_state.get("hdr_qty", 0),
            "sample_qty":   st.session_state.get("hdr_sample", 0),
            "date":         str(st.session_state.get("hdr_date", "")),
            "inspector":    st.session_state.get("hdr_insp", ""),
            "supervisor":   st.session_state.get("hdr_super", ""),
            "mfg_group":    st.session_state.get("hdr_mfg", "─"),
            "mfg_order_no": st.session_state.get("hdr_ord", ""),
            "is_sample":    st.session_state.get("oqc_is_sample", False),
            "company":      "rexon" if "力山" in _co_raw else "rexontec",
            "insp_method":   st.session_state.get("hdr_method", "正常"),
            "verdict":       st.session_state.get("hdr_verdict", ""),
            "sig_inspector": sig_inspector,
            "sig_insp_date": str(st.session_state.get("sig_insp_date", "")),
            "sig_supervisor":sig_supervisor,
            "sig_super_date":str(st.session_state.get("sig_super_date", "")),
            "sig_approver":  sig_approver,
            "sig_appr_date": str(st.session_state.get("sig_appr_date", "")),
        }
        if st.button("🖨️ 生成 PDF", key="gen_pdf_btn", type="primary"):
            with st.spinner("正在生成 PDF…"):
                _fname = (
                    f"OQC-{'ESC' if product_type=='esc' else 'MTR'}"
                    f"-{_header_for_pdf.get('batch_no','') or 'DRAFT'}"
                    f"-{_header_for_pdf.get('date','')}.pdf"
                ).replace(" ", "_")
                _pdf_b = _gen_pdf(
                    product_type = product_type,
                    header       = _header_for_pdf,
                    sections     = sections,
                    results      = st.session_state.results,
                    units        = units,
                    note         = st.session_state.get("note_input", ""),
                )
                st.download_button(
                    "⬇️ 點此下載 PDF",
                    data      = _pdf_b,
                    file_name = _fname,
                    mime      = "application/pdf",
                    use_container_width=True,
                    key       = "dl_pdf_btn",
                )
    except ImportError:
        st.warning("請先安裝 reportlab：`pip install reportlab`")
    except Exception as _pdf_err:
        st.error(f"PDF 生成失敗：{_pdf_err}")

st.markdown("<br>", unsafe_allow_html=True)
col_submit, col_reset = st.columns([4, 1])

with col_reset:
    if st.button("🔄 重置全部", use_container_width=True):
        st.session_state.results = {}
        st.rerun()

with col_submit:
    submit_disabled = not hdr_batch_no or not units
    submit_clicked  = st.button(
        "✅ 提交 → 寫入 Google Sheet",
        type="primary",
        use_container_width=True,
        disabled=submit_disabled,
    )

if submit_disabled and not hdr_batch_no:
    st.warning("請填寫批號後才能提交")

if submit_clicked:
    _co_submit = st.session_state.get("oqc_company", "力科 REXONTEC")
    header = {
        "model":        hdr_model,
        "part_no":      hdr_part_no,
        "customer":     hdr_customer,
        "batch_no":     hdr_batch_no,
        "serial_range": hdr_serial,
        "qty":          hdr_qty,
        "sample_qty":   hdr_sample,
        "date":         str(hdr_date),
        "inspector":    hdr_insp,
        "supervisor":   hdr_super,
        "mfg_group":    hdr_mfg_grp,
        "mfg_order_no": hdr_mfg_ord if is_esc else "",
        "is_sample":    st.session_state.get("oqc_is_sample", False),
        "company":      "rexon" if "力山" in _co_submit else "rexontec",
        "insp_method":   hdr_insp_method,
        "verdict":       hdr_verdict,
        "sig_inspector": sig_inspector,
        "sig_insp_date": str(sig_insp_date),
        "sig_supervisor":sig_supervisor,
        "sig_super_date":str(sig_super_date),
        "sig_approver":  sig_approver,
        "sig_appr_date": str(sig_appr_date),
    }

    # ── 自動記憶新增人員 / 客戶 ──────────────────────────
    try:
        from utils.signature_db import add_name as _sig_save
        if st.session_state.get("_cust_is_new")         and hdr_customer:
            _sig_save(hdr_customer,   "customer")
        if st.session_state.get("_hdr_insp_is_new")     and hdr_insp:
            _sig_save(hdr_insp,       "inspector")
        if st.session_state.get("_insp_is_new")         and sig_inspector:
            _sig_save(sig_inspector,  "inspector")
        if st.session_state.get("_super_is_new")        and sig_supervisor:
            _sig_save(sig_supervisor, "qa_manager")
        if st.session_state.get("_appr_is_new")         and sig_approver:
            _sig_save(sig_approver,   "approver")
    except Exception:
        pass
    # ────────────────────────────────────────────────────

    with st.spinner("寫入 Google Sheet 中…"):
        try:
            rec_id = append_oqc_record(
                product_type = product_type,
                header       = header,
                results      = st.session_state.results,
                ng_summary   = ng_summary,
                photo_urls   = photo_urls,
                note         = note,
            )
            # 保存本次資料供提交成功頁面的 PDF 下載
            st.session_state._last_pt      = product_type
            st.session_state._last_header  = header
            st.session_state._last_results = dict(st.session_state.results)
            st.session_state._last_units   = list(units)
            st.session_state._last_note    = note
            st.session_state.submitted_id  = rec_id
            st.rerun()
        except Exception as e:
            st.error(f"寫入失敗：{e}")
            st.info("請確認 service_account.json 與 Google Sheet ID 設定正確")
