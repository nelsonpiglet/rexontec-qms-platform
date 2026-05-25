"""
REXONTEC 力科品質指揮平台 — 維修保養系統
維修報告產生（單件 RMA PDF）
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.rma_gsheet    import load_all_cases
from utils.style         import QMS_CSS, topbar, page_header, STATUS_EMOJI, gsheet_error_banner
from utils.rma_pdf_report import generate_repair_pdf

st.set_page_config(
    page_title="REXONTEC 力科 | 維修報告",
    page_icon="📄",
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
    page_header("維修報告產生", "REXONTEC 力科 | Repair Report Generator", "RPT"),
    unsafe_allow_html=True,
)

st.markdown("""
<style>
.preview-row { display:flex; align-items:center; gap:8px; padding:7px 0; border-bottom:1px solid var(--border); font-size:12.5px; }
.preview-label { width:110px; font-weight:700; color:var(--muted); font-size:11px; flex-shrink:0; }
.preview-val { color:var(--text); font-weight:600; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=30, show_spinner="載入案件資料...")
def get_data():
    return load_all_cases()


_, btn_col = st.columns([10, 1])
with btn_col:
    if st.button("🔄", use_container_width=True, help="重新整理"):
        st.cache_data.clear(); st.rerun()

try:
    df = get_data()
except Exception as _e:
    gsheet_error_banner(_e)
if df.empty:
    st.info("目前沒有任何維修案件。")
    st.stop()

# ── 選擇 RMA ─────────────────────────────────
st.markdown("""
<div class="card">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--accent)"></span>
      選擇要產生報告的 RMA 案件
    </div>
  </div>
</div>""", unsafe_allow_html=True)

sc1, sc2, sc3 = st.columns([3, 2, 2])
with sc1:
    kw = st.text_input("🔍 搜尋", placeholder="輸入 RMA 編號 / 序號 / 客戶名",
                       label_visibility="collapsed")
with sc2:
    status_f = st.multiselect("狀態篩選", df["維修狀態"].dropna().unique().tolist(),
                               placeholder="全部狀態")
with sc3:
    model_opts = ["全部型號"] + sorted(df["產品型號"].dropna().unique().tolist())
    model_f    = st.selectbox("型號篩選", model_opts, label_visibility="collapsed")

view = df.copy()
if kw:
    mask = (
        view["RMA編號"].astype(str).str.contains(kw, case=False, na=False) |
        view["馬達序號"].astype(str).str.contains(kw, case=False, na=False) |
        view["客戶公司"].astype(str).str.contains(kw, case=False, na=False)
    )
    view = view[mask]
if status_f:       view = view[view["維修狀態"].isin(status_f)]
if model_f != "全部型號": view = view[view["產品型號"] == model_f]

if view.empty:
    st.warning("沒有符合條件的案件。")
    st.stop()

rma_options = view["RMA編號"].dropna().tolist()
sel_rma = st.selectbox(
    "選擇 RMA",
    rma_options,
    format_func=lambda r: (
        f"{r}  ―  "
        + str(view[view["RMA編號"]==r]["客戶公司"].values[0] if not view[view["RMA編號"]==r].empty else "")
        + "  |  "
        + str(view[view["RMA編號"]==r]["產品型號"].values[0] if not view[view["RMA編號"]==r].empty else "")
    ),
    label_visibility="collapsed",
)

row = view[view["RMA編號"] == sel_rma]
if row.empty:
    st.warning("找不到該案件。")
    st.stop()

r = row.iloc[0].to_dict()

# ── 案件預覽 ─────────────────────────────────
st.markdown("""
<div class="card" style="margin-top:8px">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--orange)"></span>
      案件資料預覽
    </div>
  </div>
</div>""", unsafe_allow_html=True)

p1, p2, p3 = st.columns(3)

def preview_field(label, value, color="var(--text)"):
    return (
        f'<div class="preview-row">'
        f'<span class="preview-label">{label}</span>'
        f'<span class="preview-val" style="color:{color}">{value or "—"}</span>'
        f'</div>'
    )

status_val = r.get("維修狀態","")
status_clr = {
    "已出廠":"var(--pass)","報廢通知":"var(--cr)",
    "待QC":"#7b1fa2","維修中":"var(--warn)",
}.get(status_val,"var(--text)")

with p1:
    st.markdown(
        preview_field("RMA 編號", r.get("RMA編號",""),   "var(--accent)") +
        preview_field("客戶公司", r.get("客戶公司",""))  +
        preview_field("聯絡人",   r.get("聯絡人",""))    +
        preview_field("聯絡電話", r.get("聯絡電話","")),
        unsafe_allow_html=True,
    )

with p2:
    st.markdown(
        preview_field("產品型號", r.get("產品型號","")) +
        preview_field("馬達序號", r.get("馬達序號","")) +
        preview_field("故障類別", r.get("故障類別","")) +
        preview_field("維修類型", r.get("維修類型","")),
        unsafe_allow_html=True,
    )

with p3:
    st.markdown(
        preview_field("維修狀態",
                      f"{STATUS_EMOJI.get(status_val,'')} {status_val}",
                      status_clr) +
        preview_field("優先等級", r.get("優先等級",""))  +
        preview_field("收件日期", str(r.get("收件日期",""))[:16]) +
        preview_field("送修數量", f"{r.get('馬達數量','')} 顆"),
        unsafe_allow_html=True,
    )

# ── 產生 PDF ─────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
_, mid, _ = st.columns([1, 2, 1])
with mid:
    gen_btn = st.button("📄　產生 PDF 維修報告", use_container_width=True, type="primary")

if gen_btn:
    with st.spinner("正在產生 PDF，請稍候..."):
        try:
            pdf_bytes = generate_repair_pdf(r)
            filename  = f"維修報告_{sel_rma}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

            st.success("✅ PDF 報告已產生！點下方按鈕下載。")

            _, dl_col, _ = st.columns([1, 2, 1])
            with dl_col:
                st.download_button(
                    label=f"⬇️　下載 {filename}",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )

            size_kb = len(pdf_bytes) / 1024
            st.markdown(
                f'<p style="font-size:11px;color:var(--muted);text-align:center">'
                f'檔案大小：{size_kb:.1f} KB &nbsp;|&nbsp; '
                f'RMA：{sel_rma} &nbsp;|&nbsp; '
                f'客戶：{r.get("客戶公司","")}</p>',
                unsafe_allow_html=True,
            )

        except Exception as ex:
            st.error(f"❌ PDF 產生失敗：{ex}")
            st.exception(ex)
