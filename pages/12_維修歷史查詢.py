"""
REXONTEC 力科品質指揮平台 — 維修保養系統
維修歷史查詢
"""
import io
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.rma_detail_gsheet import load_all_details
from utils.rma_master_gsheet import load_all_masters
from utils.style             import QMS_CSS, topbar, page_header, STATUS_EMOJI, status_badge, gsheet_error_banner

st.set_page_config(
    page_title="REXONTEC 力科 | 維修歷史",
    page_icon="🔍",
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
    page_header("維修歷史查詢", "REXONTEC 力科 | Repair History Search", "HIS"),
    unsafe_allow_html=True,
)

STATUS_LIST   = ["待收件","已收件","初診中","等待零件","維修中","待QC","已出廠","報廢通知"]
REPAIR_TYPES  = ["保固維修（購買2年內）","自費維修","定期保養","可靠度測試"]
PRIORITY_DAYS = {"P1":2,"P2":5,"P3":7,"P4":14}


def calc_tat(row) -> str:
    recv = row.get("收件日期","")
    try:
        dt_recv = datetime.strptime(str(recv)[:16], "%Y/%m/%d %H:%M")
        return str((datetime.now() - dt_recv).days) + " 天"
    except Exception:
        return "—"


@st.cache_data(ttl=30, show_spinner="載入歷史資料...")
def get_data():
    details = load_all_details()
    masters = load_all_masters()
    if details.empty:
        return details
    if not masters.empty:
        # 從主單補入客戶資訊（join on 主單編號）
        master_slim = masters[["主單編號","客戶公司","聯絡人","聯絡電話","客戶Email",
                                "收件日期","維修類型","優先等級"]].copy()
        master_slim.columns = ["主單編號","客戶公司","聯絡人","聯絡電話","客戶Email",
                               "收件日期","維修類型","優先等級"]
        merged = details.merge(master_slim, on="主單編號", how="left",
                               suffixes=("","_master"))
        # 優先用主單欄位填充子件缺少的欄位
        for col in ["客戶公司","聯絡人","聯絡電話","客戶Email","收件日期","維修類型","優先等級"]:
            if col not in merged.columns:
                merged[col] = ""
            merged[col] = merged[col].fillna(merged.get(col+"_master",""))
        return merged
    return details


col_ref, col_btn = st.columns([10, 1])
with col_btn:
    if st.button("🔄", use_container_width=True, help="重新整理"):
        st.cache_data.clear(); st.rerun()

try:
    df = get_data()
except Exception as _e:
    gsheet_error_banner(_e)
if df.empty:
    st.info("目前沒有任何維修記錄。")
    st.stop()

def safe_date(s):
    try:
        return pd.to_datetime(str(s)[:10], format="%Y/%m/%d")
    except Exception:
        return pd.NaT

df["_date"] = df["收件日期"].apply(safe_date)

# ── 進階篩選列 ────────────────────────────────
st.markdown("""
<div class="card">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--blue2)"></span>
      進階篩選條件
    </div>
  </div>
</div>""", unsafe_allow_html=True)

fa, fb, fc = st.columns([3, 2, 2])
with fa:
    kw = st.text_input("🔍 關鍵字搜尋",
                       placeholder="RMA 編號 / 馬達序號 / 客戶公司 / 聯絡人",
                       label_visibility="collapsed")
with fb:
    status_f = st.multiselect("狀態", STATUS_LIST, placeholder="全部狀態")
with fc:
    model_opts = ["全部型號"] + sorted(df["產品型號"].dropna().unique().tolist())
    model_f    = st.selectbox("型號", model_opts, label_visibility="collapsed")

fd, fe, ff = st.columns([2, 2, 2])
with fd:
    repair_opts = ["全部類型"] + REPAIR_TYPES
    repair_f    = st.selectbox("維修類型", repair_opts, label_visibility="collapsed")
with fe:
    prio_opts = ["全部等級","P1","P2","P3","P4"]
    prio_f    = st.selectbox("優先等級", prio_opts, label_visibility="collapsed")
with ff:
    date_min = df["_date"].min()
    date_max = df["_date"].max()
    if pd.isna(date_min): date_min = datetime.now() - timedelta(days=365)
    if pd.isna(date_max): date_max = datetime.now()
    date_range = st.date_input(
        "收件日期區間",
        value=(date_min.date(), date_max.date()),
        label_visibility="collapsed",
    )

# ── 套用篩選 ─────────────────────────────────
view = df.copy()

if kw:
    id_col = "子件編號" if "子件編號" in view.columns else "RMA編號"
    sn_col = "馬達序號" if "馬達序號" in view.columns else "馬達序號"
    m = (
        view.get("主單編號",pd.Series(dtype=str)).astype(str).str.contains(kw,case=False,na=False) |
        view[id_col].astype(str).str.contains(kw, case=False, na=False) |
        view.get(sn_col,pd.Series(dtype=str)).astype(str).str.contains(kw,case=False,na=False) |
        view.get("客戶公司",pd.Series(dtype=str)).astype(str).str.contains(kw,case=False,na=False) |
        view.get("聯絡人",pd.Series(dtype=str)).astype(str).str.contains(kw,case=False,na=False)
    )
    view = view[m]

if status_f:    view = view[view["維修狀態"].isin(status_f)]
if model_f != "全部型號":   view = view[view["產品型號"] == model_f]
if repair_f != "全部類型":  view = view[view["維修類型"] == repair_f]
if prio_f != "全部等級":    view = view[view["優先等級"].astype(str).str.startswith(prio_f)]
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    d0, d1 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    view = view[(view["_date"] >= d0) & (view["_date"] <= d1)]

# ── 結果標題列 ───────────────────────────────
ecol, xcol = st.columns([8, 2])
with ecol:
    st.markdown(f"""
    <div class="card" style="margin-top:4px">
      <div class="card-header">
        <div class="card-title">
          <span class="card-dot" style="background:var(--accent)"></span>
          查詢結果
        </div>
        <span style="font-size:11px;color:var(--muted)">共 {len(view)} 筆 / 全部 {len(df)} 筆</span>
      </div>
    </div>""", unsafe_allow_html=True)

with xcol:
    if not view.empty:
        export_cols = [c for c in [
            "RMA編號","馬達序號","產品型號","故障類別","是否曾撞擊/墜機",
            "飛行總時數(估計)","故障詳細描述","客戶公司","聯絡人","聯絡電話",
            "客戶Email","馬達數量","維修類型","維修狀態","優先等級","收件日期","備註"
        ] if c in view.columns]
        exp = view[export_cols].copy()
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            exp.to_excel(writer, index=False, sheet_name="維修歷史")
        buf.seek(0)
        st.download_button(
            label="⬇️ 匯出 Excel",
            data=buf,
            file_name=f"維修歷史_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

if view.empty:
    st.warning("沒有符合條件的案件。")
    st.stop()

id_col = "子件編號" if "子件編號" in view.columns else "RMA編號"
show_cols = [id_col,"主單編號","馬達序號","產品型號","故障類別","客戶公司",
             "收件日期","維修狀態","優先等級","維修類型"]
show_cols = [c for c in show_cols if c in view.columns]
disp = view[show_cols].copy()

disp["維修狀態"] = disp["維修狀態"].apply(
    lambda s: f"{STATUS_EMOJI.get(s,'')} {s}" if pd.notna(s) else s
)

st.dataframe(
    disp,
    use_container_width=True,
    height=min(460, 56 + len(disp) * 38),
    column_config={
        id_col:     st.column_config.TextColumn("子件編號",   width=160),
        "主單編號": st.column_config.TextColumn("主單",       width=150),
        "馬達序號": st.column_config.TextColumn("S/N",        width=100),
        "產品型號": st.column_config.TextColumn("型號",        width=150),
        "故障類別": st.column_config.TextColumn("故障",        width=100),
        "客戶公司": st.column_config.TextColumn("客戶",        width=130),
        "收件日期": st.column_config.TextColumn("收件日期",    width=140),
        "維修狀態": st.column_config.TextColumn("狀態",        width=130),
        "優先等級": st.column_config.TextColumn("優先",        width=70),
        "維修類型": st.column_config.TextColumn("維修類型",    width=130),
    },
    hide_index=True,
)

# ── 案件詳情 ──────────────────────────────────
st.markdown("""
<div class="card" style="margin-top:8px">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--blue2)"></span>
      案件詳細資訊
    </div>
  </div>
</div>""", unsafe_allow_html=True)

_id_col  = "子件編號" if "子件編號" in view.columns else "RMA編號"
rma_list = view[_id_col].dropna().tolist()
sel_rma  = st.selectbox("選擇子件查看詳情", rma_list, label_visibility="collapsed")

if sel_rma:
    r = view[view[_id_col] == sel_rma].iloc[0]
    d1, d2, d3 = st.columns(3)

    with d1:
        st.markdown("""<div class="card">
          <div class="card-header"><div class="card-title">
            <span class="card-dot" style="background:var(--accent)"></span>客戶資訊
          </div></div><div class="card-body">""", unsafe_allow_html=True)
        for label, key in [("客戶公司","客戶公司"),("聯絡人","聯絡人"),("電話","聯絡電話"),("Email","客戶Email")]:
            val = r.get(key,"—") or "—"
            st.markdown(
                f'<div style="font-size:11px;color:var(--muted);margin-top:8px">{label}</div>'
                f'<div style="font-size:13px;font-weight:600">{val}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

    with d2:
        st.markdown("""<div class="card">
          <div class="card-header"><div class="card-title">
            <span class="card-dot" style="background:var(--orange)"></span>馬達資訊
          </div></div><div class="card-body">""", unsafe_allow_html=True)
        for label, key in [("產品型號","產品型號"),("馬達序號 S/N","馬達序號"),
                            ("送修數量","馬達數量"),("飛行時數","飛行總時數(估計)"),
                            ("曾撞擊/墜機","是否曾撞擊/墜機")]:
            val = r.get(key,"—") or "—"
            st.markdown(
                f'<div style="font-size:11px;color:var(--muted);margin-top:8px">{label}</div>'
                f'<div style="font-size:13px;font-weight:600">{val}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

    with d3:
        st.markdown("""<div class="card">
          <div class="card-header"><div class="card-title">
            <span class="card-dot" style="background:var(--pass)"></span>維修資訊
          </div></div><div class="card-body">""", unsafe_allow_html=True)

        status_val = r.get("維修狀態","—") or "—"
        pri_val    = r.get("優先等級","—") or "—"
        pri_clr    = {"P1":"var(--cr)","P2":"var(--warn)","P3":"var(--accent)","P4":"var(--muted)"}.get(str(pri_val)[:2],"var(--muted)")

        st.markdown(
            f'<div style="font-size:11px;color:var(--muted);margin-top:8px">維修狀態</div>'
            f'<div style="font-size:13px;font-weight:600">'
            f'{STATUS_EMOJI.get(status_val,"")} {status_val}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:11px;color:var(--muted);margin-top:8px">優先等級</div>'
            f'<div style="font-size:13px;font-weight:700;color:{pri_clr}">{pri_val}</div>',
            unsafe_allow_html=True,
        )
        for label, key in [("維修類型","維修類型"),("收件日期","收件日期"),("故障類別","故障類別")]:
            val = r.get(key,"—") or "—"
            st.markdown(
                f'<div style="font-size:11px;color:var(--muted);margin-top:8px">{label}</div>'
                f'<div style="font-size:13px;font-weight:600">{val}</div>',
                unsafe_allow_html=True,
            )
        tat = calc_tat(r)
        st.markdown(
            f'<div style="font-size:11px;color:var(--muted);margin-top:8px">已處理天數</div>'
            f'<div style="font-size:13px;font-weight:700;color:var(--accent)">{tat}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div></div>", unsafe_allow_html=True)

    fd_val   = r.get("故障詳細描述","") or ""
    tech_val = r.get("內部-技術檢測","") or ""
    note_val = r.get("備註","") or ""

    if fd_val or tech_val or note_val:
        st.markdown("""<div class="card" style="margin-top:8px">
          <div class="card-header"><div class="card-title">
            <span class="card-dot" style="background:var(--muted)"></span>備註 / 技術記錄
          </div></div><div class="card-body">""", unsafe_allow_html=True)
        if fd_val:
            st.markdown(
                f'<div style="font-size:11px;color:var(--muted);margin-bottom:4px">故障詳細描述</div>'
                f'<div style="font-size:13px;padding:8px;background:#f7f9fc;'
                f'border-radius:5px;border-left:3px solid var(--accent)">{fd_val}</div>',
                unsafe_allow_html=True,
            )
        if tech_val:
            st.markdown(
                f'<div style="font-size:11px;color:var(--muted);margin-top:10px;margin-bottom:4px">技術檢測備註</div>'
                f'<div style="font-size:13px;padding:8px;background:#f7f9fc;'
                f'border-radius:5px;border-left:3px solid var(--orange)">{tech_val}</div>',
                unsafe_allow_html=True,
            )
        if note_val:
            st.markdown(
                f'<div style="font-size:11px;color:var(--muted);margin-top:10px;margin-bottom:4px">備註</div>'
                f'<div style="font-size:13px;padding:8px;background:#f7f9fc;'
                f'border-radius:5px;border-left:3px solid var(--muted)">{note_val}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)
