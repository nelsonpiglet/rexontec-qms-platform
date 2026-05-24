"""
REXONTEC 力科品質指揮平台 — 客訴與8D管理系統
客訴案件輸入
"""
import streamlit as st
from datetime import date
from utils.cs_gsheet import (
    append_complaint, get_cs_sheet, CS_STATUS_LIST,
)
from utils.style import QMS_CSS, topbar, page_header

st.set_page_config(
    page_title="REXONTEC 力科 | 客訴輸入",
    page_icon="📝",
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
    page_header("客訴案件輸入", "REXONTEC 力科 | Customer Complaint Entry", "CS"),
    unsafe_allow_html=True,
)

# ── 自訂 CSS ──────────────────────────────────────────
st.markdown("""
<style>
.form-section {
    background:#fff;border:1px solid var(--border);border-radius:10px;
    padding:18px 20px 10px;margin-bottom:14px;box-shadow:var(--sh);
}
.form-section-title {
    font-size:12px;font-weight:800;color:var(--navy);text-transform:uppercase;
    letter-spacing:1.2px;margin-bottom:14px;padding-bottom:8px;
    border-bottom:2px solid var(--border);display:flex;align-items:center;gap:8px;
}
.cs-level-badge {
    display:inline-block;padding:4px 14px;border-radius:20px;
    font-size:12px;font-weight:800;letter-spacing:.5px;
}
</style>
""", unsafe_allow_html=True)

# ── 若剛提交成功，顯示成功畫面 ───────────────────────
if st.session_state.get("cs_submitted"):
    cs_id   = st.session_state.pop("cs_submitted")
    cs_info = st.session_state.pop("cs_info", {})
    st.success(f"✅ 客訴案件已建立！")
    st.markdown(f"""
    <div style="background:#fff;border:2px solid var(--pass);border-radius:12px;
                padding:24px 28px;margin:16px 0;max-width:680px">
      <div style="font-size:11px;font-weight:700;color:var(--muted);
                  text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">客訴編號</div>
      <div style="font-size:32px;font-weight:900;color:var(--navy);
                  font-family:'DM Mono',monospace;letter-spacing:2px">{cs_id}</div>
      <hr style="border:none;border-top:1px solid var(--border);margin:14px 0">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:13px">
        <div><span style="color:var(--muted)">客戶名稱：</span><b>{cs_info.get('customer','')}</b></div>
        <div><span style="color:var(--muted)">機型：</span><b>{cs_info.get('model','')}</b></div>
        <div><span style="color:var(--muted)">客訴類型：</span><b>{cs_info.get('cs_type','')}</b></div>
        <div><span style="color:var(--muted)">客訴等級：</span><b>{cs_info.get('cs_level','')}</b></div>
        <div><span style="color:var(--muted)">負責人：</span><b>{cs_info.get('owner','')}</b></div>
        <div><span style="color:var(--muted)">是否重大：</span><b>{'⚠️ 是' if cs_info.get('is_major')=='是' else '否'}</b></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        if st.button("➕ 新增下一筆", type="primary", use_container_width=True):
            st.rerun()
    with col_b:
        if st.button("📋 前往案件追蹤", use_container_width=True):
            st.switch_page("pages/17_客訴追蹤.py")
    st.stop()

# ═══════════════════════════════════════════════════
# 客訴輸入表單
# ═══════════════════════════════════════════════════

CS_TYPES  = ["機構異常", "電子異常", "軟體異常", "性能異常",
             "包裝標示", "安全疑慮", "服務品質", "其他"]
CS_LEVELS = ["S1 重大", "S2 高", "S3 中", "S4 低"]
LEVEL_COLORS = {"S1 重大": "#b71c1c", "S2 高": "#e65100",
                "S3 中": "#f9a825",  "S4 低": "#2e7d32"}

OWNERS = ["品保部", "RD部門", "業務部", "生產部", "工程部", "其他"]

with st.form("cs_input_form", clear_on_submit=True):

    # ── 區塊 1：客戶資訊 ────────────────────────────
    st.markdown("""
    <div class="form-section">
      <div class="form-section-title">👤 客戶資訊</div>
    </div>""", unsafe_allow_html=True)

    fi1, fi2, fi3 = st.columns([2, 2, 1])
    with fi1:
        customer = st.text_input("客戶名稱 *", placeholder="例：台灣電力股份有限公司")
    with fi2:
        model = st.text_input("機型 *", placeholder="例：RX-Motor-500")
    with fi3:
        flight_hours = st.text_input("飛行時數", placeholder="例：500h")

    fi4, fi5 = st.columns([2, 2])
    with fi4:
        sn_lot = st.text_input("SN / Lot號", placeholder="例：SN2024-00123")
    with fi5:
        cs_date = st.date_input("客訴日期 *", value=date.today())

    # ── 區塊 2：客訴分類 ────────────────────────────
    st.markdown("""
    <div class="form-section" style="margin-top:8px">
      <div class="form-section-title">🏷️ 客訴分類</div>
    </div>""", unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        cs_type = st.selectbox("客訴類型 *", CS_TYPES)
    with fc2:
        cs_level = st.selectbox(
            "客訴等級 *", CS_LEVELS,
            help="S1=重大（客訴/安全） S2=高 S3=中 S4=低",
        )
    with fc3:
        is_major = st.radio(
            "是否列為重大客訴",
            ["否", "是"],
            horizontal=True,
            help="重大客訴將觸發強制8D流程",
        )

    # ── 區塊 3：問題描述 ────────────────────────────
    st.markdown("""
    <div class="form-section" style="margin-top:8px">
      <div class="form-section-title">📋 問題描述</div>
    </div>""", unsafe_allow_html=True)

    cs_desc = st.text_area(
        "客訴描述 *",
        height=120,
        placeholder="請詳細描述客戶反映的問題，包含：現象、發生時機、影響範圍、已採取動作等",
    )

    # ── 區塊 4：附件與負責人 ────────────────────────
    st.markdown("""
    <div class="form-section" style="margin-top:8px">
      <div class="form-section-title">📎 附件與負責人</div>
    </div>""", unsafe_allow_html=True)

    fa1, fa2 = st.columns(2)
    with fa1:
        photo_url = st.text_input(
            "照片連結（Google Drive URL）",
            placeholder="https://drive.google.com/...",
        )
        video_url = st.text_input(
            "影片連結",
            placeholder="https://drive.google.com/...",
        )
    with fa2:
        owner = st.selectbox("主要負責人 *", OWNERS)
        note  = st.text_area("備註", height=78, placeholder="其他補充說明")

    # ── 提交按鈕 ────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    sub_col1, sub_col2, sub_col3 = st.columns([1, 2, 1])
    with sub_col2:
        submitted = st.form_submit_button(
            "📨　建立客訴案件",
            use_container_width=True,
            type="primary",
        )

# ── 表單邏輯 ──────────────────────────────────────────
if submitted:
    errors = []
    if not customer.strip():  errors.append("請填入客戶名稱")
    if not model.strip():     errors.append("請填入機型")
    if not cs_desc.strip():   errors.append("請填入客訴描述")

    for e in errors:
        st.error(f"⚠️  {e}")

    if not errors:
        data = {
            "customer":     customer.strip(),
            "model":        model.strip(),
            "sn_lot":       sn_lot.strip(),
            "flight_hours": flight_hours.strip(),
            "cs_date":      cs_date.strftime("%Y/%m/%d"),
            "cs_type":      cs_type,
            "cs_level":     cs_level,
            "is_major":     is_major,
            "cs_desc":      cs_desc.strip(),
            "photo_url":    photo_url.strip(),
            "video_url":    video_url.strip(),
            "owner":        owner,
            "note":         note.strip(),
        }
        with st.spinner("正在建立客訴案件..."):
            try:
                cs_id = append_complaint(data)
                st.session_state["cs_submitted"] = cs_id
                st.session_state["cs_info"]      = data
                st.rerun()
            except Exception as ex:
                st.error(f"❌ 建立失敗：{ex}")
                st.exception(ex)

# ── 等級說明卡 ────────────────────────────────────────
with st.expander("📖 客訴等級說明"):
    st.markdown("""
    | 等級 | 名稱 | 定義 | 對應動作 |
    |------|------|------|---------|
    | **S1** | 重大 | 涉及人身安全、法規不符、大規模召回 | 立即回報管理層，48h 內開立8D |
    | **S2** | 高 | 功能失效、批量異常、客戶強烈不滿 | 3日內開立8D，主管知悉 |
    | **S3** | 中 | 性能偏差、單件異常、客戶有疑慮 | 7日內分析根因，品保跟進 |
    | **S4** | 低 | 外觀瑕疵、包裝問題、服務建議 | 14日內回覆處理結果 |
    """)
