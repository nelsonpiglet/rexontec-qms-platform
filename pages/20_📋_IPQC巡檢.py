"""
REXONTEC — IPQC 製程巡檢記錄
巡檢表填寫 + 首台FAI確認 + 一鍵生成PDF + 儲存至雲端
"""
import streamlit as st
from datetime import date
from io import BytesIO

from utils.style import QMS_CSS, topbar, page_header
from utils.auth import require_login, user_info_bar
from utils.ipqc import get_models, get_model
from utils.gsheet import append_ipqc_record

st.set_page_config(
    page_title="REXONTEC 力科 | IPQC 巡檢",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()
user_info_bar()

# ── 導覽列 ────────────────────────────────────────────
_n1, _n2, _n3, _n4, _n5, _n6, _n7, _n8 = st.columns([1, 1, 1, 1, 1, 1, 1, 2])
with _n1:
    if st.button("🏠 指揮平台",  use_container_width=True): st.switch_page("app.py")
with _n2:
    if st.button("📋 檢驗輸入",  use_container_width=True): st.switch_page("pages/01_出廠檢驗輸入.py")
with _n3:
    if st.button("🔬 IQC 進料",  use_container_width=True): st.switch_page("pages/06_IQC進料檢驗.py")
with _n4:
    if st.button("📊 儀表板",    use_container_width=True): st.switch_page("pages/02_儀表板.py")
with _n5:
    if st.button("🔍 追蹤查詢",  use_container_width=True): st.switch_page("pages/05_追蹤查詢.py")
with _n6:
    if st.button("🤖 AI 分析",   use_container_width=True): st.switch_page("pages/07_AI異常分析.py")
with _n7:
    if st.button("⚙️ 系統設定",  use_container_width=True): st.switch_page("pages/03_系統設定.py")

st.markdown(page_header("IPQC 製程巡檢",
                         "製程巡檢記錄 / 首台FAI確認 / 一鍵生成PDF / 雲端追蹤查詢", "IPC"),
            unsafe_allow_html=True)

# ── 額外 CSS ─────────────────────────────────────────
st.markdown("""
<style>
.ipqc-col-hdr {
  font-size:11px; font-weight:700; color:var(--muted);
  padding:4px 0 6px; border-bottom:1px solid var(--border2);
}
.grade-cr { background:#e74c3c; color:#fff; padding:2px 8px;
            border-radius:4px; font-size:10px; font-weight:800; }
.grade-ma { background:#e67e22; color:#fff; padding:2px 8px;
            border-radius:4px; font-size:10px; font-weight:800; }
.grade-mi { background:#27ae60; color:#fff; padding:2px 8px;
            border-radius:4px; font-size:10px; font-weight:800; }
.item-text { font-size:12px; color:var(--text); line-height:1.5; padding-top:5px; }
</style>
""", unsafe_allow_html=True)

# ── 載入機種 ──────────────────────────────────────────
models = get_models()
if not models:
    st.warning("尚未設定任何巡檢機種，請至「⚙️ 系統設定 → IPQC 巡檢設定」新增機種。")
    if st.button("⚙️ 前往系統設定"):
        st.switch_page("pages/03_系統設定.py")
    st.stop()

model_options = {m["name"]: m["id"] for m in models}

# ── 表頭資訊 ─────────────────────────────────────────
st.markdown("#### 📝 巡檢表頭")
h1, h2, h3, h4, h5 = st.columns([2, 2, 2, 2, 2])
with h1:
    sel_model_name = st.selectbox("機種 *", list(model_options.keys()), key="ipqc_model")
with h2:
    sel_date = st.date_input("日期 *", value=date.today(), key="ipqc_date")
with h3:
    mfg_no = st.text_input("製造編號", placeholder="例：2026051301", key="ipqc_mfg_no")
with h4:
    batch_qty = st.number_input("本批數量", min_value=0, value=0, step=1, key="ipqc_batch_qty")
with h5:
    inspector = st.text_input("巡查員 *", placeholder="例：蔡承叡", key="ipqc_inspector")

h6, h7, h8, h9, _ = st.columns([2, 2, 2, 2, 2])
with h6:
    inspect_qty = st.number_input("檢查件數", min_value=0, value=0, step=1, key="ipqc_inspect_qty")
with h7:
    defect_qty = st.number_input("不良件數", min_value=0, value=0, step=1, key="ipqc_defect_qty")
with h8:
    defect_rate_str = f"{defect_qty / inspect_qty * 100:.1f}%" if inspect_qty > 0 else "─"
    st.markdown(
        f'<div style="margin-top:28px;font-size:13px;font-weight:700;color:var(--navy)">'
        f'不良率：{defect_rate_str}</div>',
        unsafe_allow_html=True,
    )
with h9:
    freq = (get_model(model_options[sel_model_name]) or {}).get("inspection_freq", "每4小時巡查1次")
    st.markdown(
        f'<div style="margin-top:28px;font-size:11px;color:var(--muted)">{freq}</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

model = get_model(model_options[sel_model_name]) or {}

# ═══════════════════════════════════════════════════════
# 常數
# ═══════════════════════════════════════════════════════
PATROL_OPTIONS = ["─", "OK", "NG", "NA"]
FAI_OPTIONS    = ["─", "○", "×", "待確認"]
GRADE_COLOR    = {"CR": "#e74c3c", "MA": "#e67e22", "MI": "#27ae60"}


# ═══════════════════════════════════════════════════════
# PDF 輔助函式（必須定義在呼叫之前）
# ═══════════════════════════════════════════════════════
def _register_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        return 'STSong-Light'
    except Exception:
        return 'Helvetica'


def _P(text, font, size=8, bold=False, align=0, color=None):
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors as rlc
    style = ParagraphStyle(
        'z', fontName=font, fontSize=size, leading=size * 1.45,
        alignment=align, wordWrap='CJK',
        textColor=color or rlc.black, spaceAfter=0,
    )
    return Paragraph(str(text).replace('\n', '<br/>'), style)


def _gen_patrol_pdf(header: dict, model: dict) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors as rlc
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer

    FONT = _register_font()
    GRADE_BG = {
        "CR": rlc.HexColor('#fadbd8'),
        "MA": rlc.HexColor('#fdebd0'),
        "MI": rlc.HexColor('#d5f5e3'),
    }
    RESULT_BG = {
        "OK": rlc.HexColor('#d5f5e3'),
        "NG": rlc.HexColor('#fadbd8'),
        "NA": rlc.HexColor('#eaecee'),
        "─":  rlc.white,
    }
    HDR_BG = rlc.HexColor('#dce6f1')

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=8*mm, rightMargin=8*mm,
        topMargin=8*mm, bottomMargin=8*mm,
    )
    story = []

    doc_info = (f"文件 {header['doc_no']}  {header['version']}\n"
                f"版次 {header['released']}\nISO 9001:2016")
    title_tbl = Table([[
        _P("力山科技股份有限公司", FONT, 9, align=1),
        _P(f"{header['model_name']}  IPQC 巡檢記錄表", FONT, 12, align=1),
        _P(doc_info, FONT, 7, align=2),
    ]], colWidths=[65*mm, 149*mm, 63*mm])
    title_tbl.setStyle(TableStyle([
        ('FONT',        (0,0),(-1,-1), FONT),
        ('GRID',        (0,0),(-1,-1), 0.5, rlc.black),
        ('BACKGROUND',  (0,0),(-1,-1), HDR_BG),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ]))
    story.append(title_tbl)

    info_tbl = Table([[
        _P(f"機種：{header['model_name']}", FONT, 8),
        _P(f"日期：{header['date']}", FONT, 8),
        _P(f"製造編號：{header['mfg_no']}", FONT, 8),
        _P(f"本批數量：{header['batch_qty']}", FONT, 8),
        _P(f"檢查件數：{header['inspect_qty']}", FONT, 8),
        _P(f"不良件數：{header['defect_qty']}", FONT, 8),
        _P(f"不良率：{header['defect_rate']}", FONT, 8),
        _P(f"巡查員：{header['inspector']}", FONT, 8),
    ]], colWidths=[40*mm, 28*mm, 38*mm, 30*mm, 28*mm, 28*mm, 24*mm, 61*mm])
    info_tbl.setStyle(TableStyle([
        ('FONT',        (0,0),(-1,-1), FONT, 8),
        ('GRID',        (0,0),(-1,-1), 0.5, rlc.black),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),(-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 1*mm))

    col_w    = [22*mm, 84*mm, 16*mm, 22*mm, 22*mm, 54*mm, 57*mm]
    tbl_data = [[
        _P("工序", FONT, 8, align=1),
        _P("檢查項目 / 檢驗基準", FONT, 8, align=1),
        _P("等級", FONT, 8, align=1),
        _P("AM\n08:00~12:00", FONT, 8, align=1),
        _P("PM\n13:00~17:00", FONT, 8, align=1),
        _P("異常描述", FONT, 8, align=1),
        _P("對策 / 確認", FONT, 8, align=1),
    ]]

    span_cmds   = []
    cell_styles = []
    row = 1

    for station in model.get("patrol_stations", []):
        st_id   = station["id"]
        st_name = station["name"]
        items   = station.get("items", [])
        n       = len(items)
        if n == 0:
            continue
        if n > 1:
            span_cmds.append(('SPAN', (0, row), (0, row + n - 1)))

        for i_idx, it in enumerate(items):
            grade  = it.get("grade", "MA")
            am_val = st.session_state.get(f"am_{st_id}_{i_idx}", "─")
            pm_val = st.session_state.get(f"pm_{st_id}_{i_idx}", "─")
            note   = st.session_state.get(f"note_{st_id}_{i_idx}", "")
            action = st.session_state.get(f"action_{st_id}_{i_idx}", "")
            st_cell = _P(f"{st_id}\n{st_name}", FONT, 7, align=1) if i_idx == 0 else _P("", FONT, 7)

            tbl_data.append([
                st_cell,
                _P(it["item"], FONT, 7),
                _P(grade, FONT, 8, align=1),
                _P(am_val, FONT, 8, align=1),
                _P(pm_val, FONT, 8, align=1),
                _P(note, FONT, 7),
                _P(action, FONT, 7),
            ])
            cell_styles += [
                ('BACKGROUND', (2, row+i_idx), (2, row+i_idx), GRADE_BG.get(grade, rlc.white)),
                ('BACKGROUND', (3, row+i_idx), (3, row+i_idx), RESULT_BG.get(am_val, rlc.white)),
                ('BACKGROUND', (4, row+i_idx), (4, row+i_idx), RESULT_BG.get(pm_val, rlc.white)),
            ]
        row += n

    base_style = [
        ('FONT',         (0,0),(-1,-1), FONT, 7),
        ('GRID',         (0,0),(-1,-1), 0.5, rlc.black),
        ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
        ('ALIGN',        (0,0),(0,-1),  'CENTER'),
        ('ALIGN',        (2,0),(4,-1),  'CENTER'),
        ('BACKGROUND',   (0,0),(-1,0),  HDR_BG),
        ('FONTSIZE',     (0,0),(-1,0),  8),
        ('TOPPADDING',   (0,0),(-1,-1), 2),
        ('BOTTOMPADDING',(0,0),(-1,-1), 2),
        ('LEFTPADDING',  (0,0),(-1,-1), 3),
        ('RIGHTPADDING', (0,0),(-1,-1), 3),
    ]
    main_tbl = Table(tbl_data, colWidths=col_w, repeatRows=1)
    main_tbl.setStyle(TableStyle(base_style + span_cmds + cell_styles))
    story.append(main_tbl)

    story.append(Spacer(1, 1.5*mm))
    legend_tbl = Table([[
        _P("圖例：OK 合格　NG 不合格　NA 不適用　─ 未檢查", FONT, 7),
        _P("CR = 重大不良（立即停線）　MA = 主要不良　MI = 次要不良", FONT, 7),
    ]], colWidths=[138*mm, 139*mm])
    legend_tbl.setStyle(TableStyle([
        ('FONT',        (0,0),(-1,-1), FONT, 7),
        ('GRID',        (0,0),(-1,-1), 0.5, rlc.black),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),(-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
    ]))
    story.append(legend_tbl)

    mfg = header.get('mfg_sig') or '_______________'
    qc  = header.get('qc_sig')  or '_______________'
    mgr = header.get('mgr_sig') or '_______________'
    sig_tbl = Table([[
        _P(f"製造確認：{mfg}", FONT, 8, align=1),
        _P(f"品保確認：{qc}",  FONT, 8, align=1),
        _P(f"主管審核：{mgr}", FONT, 8, align=1),
    ]], colWidths=[92*mm, 92*mm, 93*mm])
    sig_tbl.setStyle(TableStyle([
        ('FONT',        (0,0),(-1,-1), FONT, 8),
        ('GRID',        (0,0),(-1,-1), 0.5, rlc.black),
        ('ALIGN',       (0,0),(-1,-1), 'CENTER'),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ]))
    story.append(sig_tbl)

    doc.build(story)
    return buffer.getvalue()


def _gen_fai_pdf(header: dict, model: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rlc
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer

    FONT   = _register_font()
    HDR_BG = rlc.HexColor('#dce6f1')

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )
    story = []

    doc_info = f"文件 {header['doc_no']}  {header['version']}  版次 {header['released']}"
    title_tbl = Table([[
        _P("力山科技股份有限公司", FONT, 9, align=1),
        _P(f"{header['model_name']}  首台 FAI 品質確認表", FONT, 11, align=1),
        _P(doc_info, FONT, 7, align=2),
    ]], colWidths=[50*mm, 100*mm, 36*mm])
    title_tbl.setStyle(TableStyle([
        ('FONT',        (0,0),(-1,-1), FONT),
        ('GRID',        (0,0),(-1,-1), 0.5, rlc.black),
        ('BACKGROUND',  (0,0),(-1,-1), HDR_BG),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ]))
    story.append(title_tbl)

    info_tbl = Table([[
        _P(f"日期：{header['date']}", FONT, 8),
        _P(f"機種：{header['model_name']}", FONT, 8),
        _P(f"確認人員：{header['inspector']}", FONT, 8),
    ]], colWidths=[62*mm, 62*mm, 62*mm])
    info_tbl.setStyle(TableStyle([
        ('FONT',        (0,0),(-1,-1), FONT, 8),
        ('GRID',        (0,0),(-1,-1), 0.5, rlc.black),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),(-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 1.5*mm))

    col_w    = [16*mm, 44*mm, 50*mm, 16*mm, 34*mm, 26*mm]
    tbl_data = [[
        _P("工序", FONT, 8, align=1),
        _P("首台確認項目", FONT, 8, align=1),
        _P("判定基準", FONT, 8, align=1),
        _P("結果\n○/×", FONT, 8, align=1),
        _P("量測值 / 記錄", FONT, 8, align=1),
        _P("備註", FONT, 8, align=1),
    ]]

    span_cmds   = []
    cell_styles = []
    row = 1
    RESULT_BG = {
        "○":    rlc.HexColor('#d5f5e3'),
        "×":    rlc.HexColor('#fadbd8'),
        "待確認": rlc.HexColor('#fef9e7'),
        "─":    rlc.white,
    }

    for station in model.get("fai_stations", []):
        st_id   = station["id"]
        st_name = station["name"]
        items   = station.get("items", [])
        n       = len(items)
        if n == 0:
            continue
        if n > 1:
            span_cmds.append(('SPAN', (0, row), (0, row + n - 1)))

        for i_idx, it in enumerate(items):
            r_val   = st.session_state.get(f"fai_r_{st_id}_{i_idx}", "─")
            m_val   = st.session_state.get(f"fai_m_{st_id}_{i_idx}", "")
            n_val   = st.session_state.get(f"fai_n_{st_id}_{i_idx}", "")
            st_cell = _P(f"{st_id}\n{st_name}", FONT, 7, align=1) if i_idx == 0 else _P("", FONT, 7)

            tbl_data.append([
                st_cell,
                _P(it["item"], FONT, 7),
                _P(it.get("criteria", ""), FONT, 7),
                _P(r_val, FONT, 9, align=1),
                _P(m_val, FONT, 7),
                _P(n_val, FONT, 7),
            ])
            cell_styles.append(
                ('BACKGROUND', (3, row+i_idx), (3, row+i_idx), RESULT_BG.get(r_val, rlc.white))
            )
        row += n

    base_style = [
        ('FONT',         (0,0),(-1,-1), FONT, 7),
        ('GRID',         (0,0),(-1,-1), 0.5, rlc.black),
        ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
        ('ALIGN',        (0,0),(0,-1),  'CENTER'),
        ('ALIGN',        (3,0),(3,-1),  'CENTER'),
        ('BACKGROUND',   (0,0),(-1,0),  HDR_BG),
        ('FONTSIZE',     (0,0),(-1,0),  8),
        ('TOPPADDING',   (0,0),(-1,-1), 2),
        ('BOTTOMPADDING',(0,0),(-1,-1), 2),
        ('LEFTPADDING',  (0,0),(-1,-1), 3),
        ('RIGHTPADDING', (0,0),(-1,-1), 3),
    ]
    fai_tbl = Table(tbl_data, colWidths=col_w, repeatRows=1)
    fai_tbl.setStyle(TableStyle(base_style + span_cmds + cell_styles))
    story.append(fai_tbl)

    story.append(Spacer(1, 1.5*mm))
    legend_tbl = Table([[
        _P("○ = 合格　× = 不合格 → 停機通知品保主管　量測值欄填寫實測數值", FONT, 7),
    ]], colWidths=[186*mm])
    legend_tbl.setStyle(TableStyle([
        ('FONT',        (0,0),(-1,-1), FONT, 7),
        ('GRID',        (0,0),(-1,-1), 0.5, rlc.black),
        ('TOPPADDING',  (0,0),(-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
    ]))
    story.append(legend_tbl)

    mfg = header.get('mfg_sig') or '_______________'
    qc  = header.get('qc_sig')  or '_______________'
    mgr = header.get('mgr_sig') or '_______________'
    sig_tbl = Table([[
        _P(f"製造確認：{mfg}", FONT, 8, align=1),
        _P(f"品保確認：{qc}",  FONT, 8, align=1),
        _P(f"主管審核：{mgr}", FONT, 8, align=1),
    ]], colWidths=[62*mm, 62*mm, 62*mm])
    sig_tbl.setStyle(TableStyle([
        ('FONT',        (0,0),(-1,-1), FONT, 8),
        ('GRID',        (0,0),(-1,-1), 0.5, rlc.black),
        ('ALIGN',       (0,0),(-1,-1), 'CENTER'),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ]))
    story.append(sig_tbl)

    doc.build(story)
    return buffer.getvalue()


# ═══════════════════════════════════════════════════════
# 收集表單結果輔助函式
# ═══════════════════════════════════════════════════════
def _collect_patrol_results(mdl: dict) -> dict:
    """從 session_state 收集巡檢表單資料"""
    results = {}
    for station in mdl.get("patrol_stations", []):
        st_id = station["id"]
        results[st_id] = {}
        for i_idx in range(len(station.get("items", []))):
            results[st_id][str(i_idx)] = {
                "am":     st.session_state.get(f"am_{st_id}_{i_idx}", "─"),
                "pm":     st.session_state.get(f"pm_{st_id}_{i_idx}", "─"),
                "note":   st.session_state.get(f"note_{st_id}_{i_idx}", ""),
                "action": st.session_state.get(f"action_{st_id}_{i_idx}", ""),
            }
    return results


def _collect_fai_results(mdl: dict) -> dict:
    """從 session_state 收集 FAI 表單資料"""
    results = {}
    for station in mdl.get("fai_stations", []):
        st_id = station["id"]
        results[st_id] = {}
        for i_idx in range(len(station.get("items", []))):
            results[st_id][str(i_idx)] = {
                "result":  st.session_state.get(f"fai_r_{st_id}_{i_idx}", "─"),
                "measure": st.session_state.get(f"fai_m_{st_id}_{i_idx}", ""),
                "note":    st.session_state.get(f"fai_n_{st_id}_{i_idx}", ""),
            }
    return results


# ═══════════════════════════════════════════════════════
# 共用表頭 helper（提交用）
# ═══════════════════════════════════════════════════════
def _build_header(mfg_sig_key: str, qc_sig_key: str, mgr_sig_key: str) -> dict:
    return {
        "model_id":    model_options[sel_model_name],
        "model_name":  sel_model_name,
        "date":        str(sel_date),
        "mfg_no":      mfg_no or "─",
        "batch_qty":   batch_qty,
        "inspect_qty": inspect_qty,
        "defect_qty":  defect_qty,
        "defect_rate": defect_rate_str,
        "inspector":   inspector or "─",
        "doc_no":      model.get("doc_no", ""),
        "version":     model.get("version", ""),
        "released":    model.get("released", ""),
        "freq":        model.get("inspection_freq", "每4小時巡查1次"),
        "mfg_sig":     st.session_state.get(mfg_sig_key, ""),
        "qc_sig":      st.session_state.get(qc_sig_key, ""),
        "mgr_sig":     st.session_state.get(mgr_sig_key, ""),
    }


# ═══════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════
tab_patrol, tab_fai = st.tabs(["📋 製程巡檢記錄", "🔬 首台 FAI 確認"])


# ───────────────────────────────────────────────────────
# TAB 1：製程巡檢
# ───────────────────────────────────────────────────────
with tab_patrol:
    patrol_stations = model.get("patrol_stations", [])
    if not patrol_stations:
        st.info("此機種尚未設定巡檢工序，請至系統設定新增。")
    else:
        for s_idx, station in enumerate(patrol_stations):
            st_id   = station["id"]
            st_name = station["name"]
            items   = station.get("items", [])

            with st.expander(f"**{st_id}  ｜  {st_name}**　 ({len(items)} 項)", expanded=(s_idx == 0)):
                hdr = st.columns([0.35, 3.6, 0.65, 1, 1, 2, 2])
                for col, lbl in zip(hdr, ["No.", "檢查項目 / 檢驗基準", "等級",
                                          "上午班 AM", "下午班 PM", "異常描述", "對策 / 確認"]):
                    col.markdown(f'<div class="ipqc-col-hdr">{lbl}</div>', unsafe_allow_html=True)

                for i_idx, it in enumerate(items):
                    grade = it["grade"]
                    gc    = GRADE_COLOR.get(grade, "#888")
                    cols  = st.columns([0.35, 3.6, 0.65, 1, 1, 2, 2])
                    with cols[0]:
                        st.markdown(
                            f'<div style="font-size:11px;color:var(--muted);padding-top:8px">{i_idx+1}</div>',
                            unsafe_allow_html=True)
                    with cols[1]:
                        st.markdown(f'<div class="item-text">{it["item"]}</div>', unsafe_allow_html=True)
                    with cols[2]:
                        st.markdown(
                            f'<div style="padding-top:4px"><span style="background:{gc};color:#fff;'
                            f'padding:2px 8px;border-radius:4px;font-size:10px;font-weight:800">'
                            f'{grade}</span></div>', unsafe_allow_html=True)
                    with cols[3]:
                        st.selectbox("AM", PATROL_OPTIONS, key=f"am_{st_id}_{i_idx}",
                                     label_visibility="collapsed")
                    with cols[4]:
                        st.selectbox("PM", PATROL_OPTIONS, key=f"pm_{st_id}_{i_idx}",
                                     label_visibility="collapsed")
                    with cols[5]:
                        st.text_input("note", placeholder="異常描述…",
                                      key=f"note_{st_id}_{i_idx}",
                                      label_visibility="collapsed")
                    with cols[6]:
                        st.text_input("action", placeholder="對策 / 確認…",
                                      key=f"action_{st_id}_{i_idx}",
                                      label_visibility="collapsed")

        st.markdown("---")
        sig_cols = st.columns(3)
        with sig_cols[0]:
            st.text_input("製造確認", placeholder="簽名 / 姓名", key="patrol_mfg_sig")
        with sig_cols[1]:
            st.text_input("品保確認", placeholder="簽名 / 姓名", key="patrol_qc_sig")
        with sig_cols[2]:
            st.text_input("主管審核", placeholder="簽名 / 姓名", key="patrol_mgr_sig")

    # ── 操作列：PDF + 提交 ──────────────────────────────
    st.markdown("---")
    act_c1, act_c2, act_c3, _ = st.columns([2, 2, 2, 2])
    with act_c1:
        gen_pdf = st.button("🖨️ 生成巡檢記錄 PDF", type="primary", use_container_width=True,
                            key="btn_patrol_pdf")
    with act_c3:
        submit_patrol = st.button("💾 提交記錄至雲端", use_container_width=True,
                                  key="btn_patrol_submit")

    if gen_pdf:
        header = _build_header("patrol_mfg_sig", "patrol_qc_sig", "patrol_mgr_sig")
        pdf_bytes = _gen_patrol_pdf(header, model)
        fname = f"IPQC_{sel_model_name}_{str(sel_date)}.pdf"
        with act_c2:
            st.download_button(
                "⬇️ 下載 PDF",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
                key="dl_patrol_pdf",
            )

    if submit_patrol:
        if not inspector:
            st.warning("⚠️ 請填寫「巡查員」後再提交。")
        else:
            header  = _build_header("patrol_mfg_sig", "patrol_qc_sig", "patrol_mgr_sig")
            results = _collect_patrol_results(model)
            try:
                rec_id = append_ipqc_record(header, model, "patrol", results)
                st.success(f"✅ 巡檢記錄已儲存至雲端！記錄編號：**{rec_id}**")
            except Exception as e:
                st.error(f"❌ 儲存失敗：{e}")


# ───────────────────────────────────────────────────────
# TAB 2：首台 FAI 確認
# ───────────────────────────────────────────────────────
with tab_fai:
    fai_stations = model.get("fai_stations", [])
    if not fai_stations:
        st.info("此機種尚未設定首台FAI確認項目，請至系統設定新增。")
    else:
        for s_idx, station in enumerate(fai_stations):
            st_id   = station["id"]
            st_name = station["name"]
            items   = station.get("items", [])

            with st.expander(f"**{st_id}  ｜  {st_name}**　 ({len(items)} 項)", expanded=(s_idx == 0)):
                hdr = st.columns([0.35, 2.6, 2.6, 0.9, 2, 1.5])
                for col, lbl in zip(hdr, ["No.", "確認項目", "判定基準",
                                          "結果", "量測值 / 記錄", "備註"]):
                    col.markdown(f'<div class="ipqc-col-hdr">{lbl}</div>', unsafe_allow_html=True)

                for i_idx, it in enumerate(items):
                    cols = st.columns([0.35, 2.6, 2.6, 0.9, 2, 1.5])
                    with cols[0]:
                        st.markdown(
                            f'<div style="font-size:11px;color:var(--muted);padding-top:8px">{i_idx+1}</div>',
                            unsafe_allow_html=True)
                    with cols[1]:
                        st.markdown(f'<div class="item-text">{it["item"]}</div>', unsafe_allow_html=True)
                    with cols[2]:
                        st.markdown(
                            f'<div style="font-size:11.5px;color:var(--muted);padding-top:6px">'
                            f'{it.get("criteria","")}</div>', unsafe_allow_html=True)
                    with cols[3]:
                        st.selectbox("r", FAI_OPTIONS, key=f"fai_r_{st_id}_{i_idx}",
                                     label_visibility="collapsed")
                    with cols[4]:
                        st.text_input("m", placeholder="量測值…",
                                      key=f"fai_m_{st_id}_{i_idx}",
                                      label_visibility="collapsed")
                    with cols[5]:
                        st.text_input("n", placeholder="備註…",
                                      key=f"fai_n_{st_id}_{i_idx}",
                                      label_visibility="collapsed")

        st.markdown("---")
        fai_sigs = st.columns(3)
        with fai_sigs[0]:
            st.text_input("製造確認", placeholder="簽名 / 姓名", key="fai_mfg_sig")
        with fai_sigs[1]:
            st.text_input("品保確認", placeholder="簽名 / 姓名", key="fai_qc_sig")
        with fai_sigs[2]:
            st.text_input("主管審核", placeholder="簽名 / 姓名", key="fai_mgr_sig")

    # ── 操作列：PDF + 提交 ──────────────────────────────
    st.markdown("---")
    fai_c1, fai_c2, fai_c3, _ = st.columns([2, 2, 2, 2])
    with fai_c1:
        gen_fai = st.button("🖨️ 生成 FAI 確認 PDF", type="primary", use_container_width=True,
                            key="btn_fai_pdf")
    with fai_c3:
        submit_fai = st.button("💾 提交記錄至雲端", use_container_width=True,
                               key="btn_fai_submit")

    if gen_fai:
        header = _build_header("fai_mfg_sig", "fai_qc_sig", "fai_mgr_sig")
        pdf_bytes = _gen_fai_pdf(header, model)
        fname = f"FAI_{sel_model_name}_{str(sel_date)}.pdf"
        with fai_c2:
            st.download_button(
                "⬇️ 下載 FAI PDF",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
                key="dl_fai_pdf",
            )

    if submit_fai:
        if not inspector:
            st.warning("⚠️ 請填寫「巡查員」後再提交。")
        else:
            header  = _build_header("fai_mfg_sig", "fai_qc_sig", "fai_mgr_sig")
            results = _collect_fai_results(model)
            try:
                rec_id = append_ipqc_record(header, model, "fai", results)
                st.success(f"✅ FAI 記錄已儲存至雲端！記錄編號：**{rec_id}**")
            except Exception as e:
                st.error(f"❌ 儲存失敗：{e}")
