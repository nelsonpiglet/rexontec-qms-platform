"""
REXONTEC 力科品質指揮平台 — 維修保養系統
維修報告產生（單件 / 批次 PDF）
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.rma_master_gsheet  import load_all_masters
from utils.rma_detail_gsheet  import load_all_details, load_details_by_master
from utils.style               import QMS_CSS, topbar, page_header, STATUS_EMOJI, gsheet_error_banner
from utils.rma_pdf_report      import generate_repair_pdf, generate_batch_repair_pdf

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
    if st.button("🏠 指揮平台", use_container_width=True): st.switch_page("app.py")
with c1:
    if st.button("📝 維修輸入", use_container_width=True): st.switch_page("pages/09_維修輸入.py")
with c2:
    if st.button("📋 狀態追蹤", use_container_width=True): st.switch_page("pages/10_維修狀態追蹤.py")
with c3:
    if st.button("📊 KPI", use_container_width=True): st.switch_page("pages/11_維修KPI儀表板.py")
with c4:
    if st.button("🔍 歷史", use_container_width=True): st.switch_page("pages/12_維修歷史查詢.py")
with c5:
    if st.button("⚙️ 設定", use_container_width=True): st.switch_page("pages/13_維修系統設定.py")
with c6:
    if st.button("📄 報告", use_container_width=True): st.switch_page("pages/14_維修報告.py")

st.markdown(
    page_header("維修報告產生", "REXONTEC 力科 | Repair Report Generator", "RPT"),
    unsafe_allow_html=True)

st.markdown("""
<style>
.preview-row { display:flex; align-items:center; gap:8px; padding:7px 0;
               border-bottom:1px solid var(--border); font-size:12.5px; }
.preview-label { width:110px; font-weight:700; color:var(--muted); font-size:11px; flex-shrink:0; }
.preview-val   { color:var(--text); font-weight:600; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=30, show_spinner="載入案件資料...")
def get_masters():
    return load_all_masters()

@st.cache_data(ttl=30, show_spinner="載入子件資料...")
def get_details():
    return load_all_details()


_, btn_col = st.columns([10, 1])
with btn_col:
    if st.button("🔄", use_container_width=True, help="重新整理"):
        st.cache_data.clear(); st.rerun()

try:
    masters_df = get_masters()
    details_df = get_details()
except Exception as _e:
    gsheet_error_banner(_e)
    st.stop()

if masters_df.empty:
    st.info("目前沒有任何維修主單。")
    st.stop()


# ── 報告類型 ─────────────────────────────────
st.markdown("""
<div class="card"><div class="card-header"><div class="card-title">
  <span class="card-dot" style="background:var(--accent)"></span>報告類型
</div></div></div>""", unsafe_allow_html=True)

report_mode = st.radio(
    "報告類型",
    ["📄 單顆報告（選擇特定 SN）", "📋 合併報告（可選多張主單合併輸出）"],
    horizontal=True, label_visibility="collapsed",
)
is_batch_report = report_mode.startswith("📋")


# ── 篩選 ─────────────────────────────────────
st.markdown("""
<div class="card" style="margin-top:8px"><div class="card-header"><div class="card-title">
  <span class="card-dot" style="background:var(--orange)"></span>
  選擇要產生報告的案件
</div></div></div>""", unsafe_allow_html=True)

sc1, sc2 = st.columns([3, 3])
with sc1:
    kw = st.text_input("🔍 搜尋", placeholder="主單編號 / 子件編號 / 客戶名 / S/N",
                        label_visibility="collapsed")
with sc2:
    cust_opts  = ["全部客戶"] + sorted(masters_df["客戶公司"].dropna().unique().tolist())
    cust_f     = st.selectbox("客戶篩選", cust_opts, label_visibility="collapsed")

if is_batch_report:
    # ── 選多張主單 ───────────────────────────────────────────────────────────
    view_m = masters_df.copy()
    if kw:
        msk = (view_m["主單編號"].astype(str).str.contains(kw, case=False, na=False) |
               view_m["客戶公司"].astype(str).str.contains(kw, case=False, na=False))
        view_m = view_m[msk]
    if cust_f != "全部客戶":
        view_m = view_m[view_m["客戶公司"] == cust_f]

    if view_m.empty:
        st.warning("沒有符合條件的主單。")
        st.stop()

    def _master_label(m):
        row = masters_df[masters_df["主單編號"] == m]
        cust = row["客戶公司"].values[0] if not row.empty else ""
        qty  = row["退修數量"].values[0]  if not row.empty else "?"
        return f"{m}  ―  {cust}  |  {qty} 顆"

    sel_masters = st.multiselect(
        "選擇主單（可多選，合併成同一張報告）",
        view_m["主單編號"].tolist(),
        format_func=_master_label,
        placeholder="點選選擇一張或多張主單…",
        label_visibility="collapsed",
    )

    if not sel_masters:
        st.info("請至少選擇一張主單以產生報告。")
        st.stop()

    def pf(label, value, color="var(--text)"):
        return (f'<div class="preview-row"><span class="preview-label">{label}</span>'
                f'<span class="preview-val" style="color:{color}">{value or "—"}</span></div>')

    # 預覽所選主單
    st.markdown("""
    <div class="card" style="margin-top:8px"><div class="card-header"><div class="card-title">
      <span class="card-dot" style="background:var(--orange)"></span>已選主單預覽
    </div></div></div>""", unsafe_allow_html=True)

    all_subs = []
    total_motors = 0
    for mid_sel in sel_masters:
        mr_row = masters_df[masters_df["主單編號"] == mid_sel]
        if mr_row.empty:
            continue
        mr_info = mr_row.iloc[0].to_dict()
        sub_df  = (details_df[details_df["主單編號"] == mid_sel]
                   if not details_df.empty else pd.DataFrame())
        all_subs.append({"master": mr_info, "details": sub_df})
        total_motors += len(sub_df)

        with st.expander(f"📦 {mid_sel}  ({len(sub_df)} 顆馬達)", expanded=len(sel_masters) == 1):
            p1, p2 = st.columns(2)
            with p1:
                st.markdown(
                    pf("客戶公司", mr_info.get("客戶公司","")) +
                    pf("聯絡人",   mr_info.get("聯絡人","")) +
                    pf("收件日期", str(mr_info.get("收件日期",""))[:16]),
                    unsafe_allow_html=True)
            with p2:
                st.markdown(
                    pf("退修數量", f"{mr_info.get('退修數量','')} 顆") +
                    pf("維修類型", mr_info.get("維修類型","")) +
                    pf("優先等級", mr_info.get("優先等級","")),
                    unsafe_allow_html=True)
            if not sub_df.empty:
                sub_show = sub_df[[c for c in ["子件編號","馬達序號","產品型號","故障類別","技術判定","是否報廢"]
                                   if c in sub_df.columns]].copy()
                st.dataframe(sub_show, use_container_width=True, hide_index=True,
                             height=min(300, 56 + len(sub_show)*38))

    # ── 產生合併 PDF 按鈕 ──
    st.markdown("<br>", unsafe_allow_html=True)
    _, mid_col, _ = st.columns([1, 2, 1])
    with mid_col:
        gen_batch = st.button(
            f"📋　產生檢測維修報告（共 {total_motors} 顆馬達）",
            use_container_width=True, type="primary",
            disabled=(total_motors == 0),
        )

    if gen_batch:
        if total_motors == 0:
            st.error("選取的主單沒有子件資料，無法產生報告。")
        else:
            with st.spinner(f"產生 {total_motors} 顆馬達報告中，請稍候..."):
                try:
                    masters_data = [
                        {"master": md["master"], "details": md["details"].to_dict("records")}
                        for md in all_subs
                    ]
                    pdf_bytes = generate_batch_repair_pdf(masters_data)
                    ids_str = "_".join(sel_masters[:3]) + ("_more" if len(sel_masters) > 3 else "")
                    fname = f"檢測報告_{ids_str}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    st.success(f"✅ 檢測維修報告已產生！共 {total_motors} 顆馬達、{len(sel_masters)} 張主單")
                    _, dl_col, _ = st.columns([1, 2, 1])
                    with dl_col:
                        st.download_button(
                            label=f"⬇️　下載 {fname}",
                            data=pdf_bytes, file_name=fname,
                            mime="application/pdf", use_container_width=True)
                    size_kb = len(pdf_bytes) / 1024
                    st.markdown(
                        f'<p style="font-size:11px;color:var(--muted);text-align:center">'
                        f'檔案大小：{size_kb:.1f} KB &nbsp;|&nbsp; '
                        f'主單：{len(sel_masters)} 張 &nbsp;|&nbsp; '
                        f'馬達：{total_motors} 顆</p>', unsafe_allow_html=True)
                except Exception as ex:
                    st.error(f"❌ PDF 產生失敗：{ex}")
                    st.exception(ex)

else:
    # ── 單顆報告 ──
    view_d = details_df.copy() if not details_df.empty else pd.DataFrame()
    if kw and not view_d.empty:
        msk = (
            view_d.get("子件編號",pd.Series(dtype=str)).astype(str).str.contains(kw,case=False,na=False) |
            view_d.get("主單編號",pd.Series(dtype=str)).astype(str).str.contains(kw,case=False,na=False) |
            view_d.get("馬達序號",pd.Series(dtype=str)).astype(str).str.contains(kw,case=False,na=False)
        )
        view_d = view_d[msk]
    if cust_f != "全部客戶" and not view_d.empty and not masters_df.empty:
        cust_masters = masters_df[masters_df["客戶公司"] == cust_f]["主單編號"].tolist()
        if "主單編號" in view_d.columns:
            view_d = view_d[view_d["主單編號"].isin(cust_masters)]

    if view_d.empty:
        st.warning("沒有符合條件的子件。")
        st.stop()

    sel_detail = st.selectbox(
        "選擇子件",
        view_d["子件編號"].tolist() if "子件編號" in view_d.columns else [],
        format_func=lambda d: (
            f"{d}  ―  S/N "
            + str(view_d[view_d["子件編號"]==d]["馬達序號"].values[0]
                   if not view_d[view_d["子件編號"]==d].empty else "")
            + "  "
            + str(view_d[view_d["子件編號"]==d]["產品型號"].values[0]
                   if not view_d[view_d["子件編號"]==d].empty else "")
        ),
        label_visibility="collapsed",
    )

    if not sel_detail:
        st.stop()

    dr_row = view_d[view_d["子件編號"] == sel_detail]
    if dr_row.empty:
        st.warning("找不到該子件。")
        st.stop()
    dr = dr_row.iloc[0].to_dict()

    # 取主單資訊
    mid = dr.get("主單編號","")
    mr_row2 = masters_df[masters_df["主單編號"] == mid] if mid else pd.DataFrame()
    mr2 = mr_row2.iloc[0].to_dict() if not mr_row2.empty else {}

    # 合併顯示
    st.markdown("""
    <div class="card" style="margin-top:8px"><div class="card-header"><div class="card-title">
      <span class="card-dot" style="background:var(--orange)"></span>案件資料預覽
    </div></div></div>""", unsafe_allow_html=True)

    def pf(label, value, color="var(--text)"):
        return (f'<div class="preview-row"><span class="preview-label">{label}</span>'
                f'<span class="preview-val" style="color:{color}">{value or "—"}</span></div>')

    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown(
            pf("子件編號",   dr.get("子件編號",""),  "var(--accent)") +
            pf("主單編號",   mid) +
            pf("客戶公司",   mr2.get("客戶公司","")) +
            pf("聯絡人",     mr2.get("聯絡人","")),
            unsafe_allow_html=True)
    with p2:
        st.markdown(
            pf("產品型號", dr.get("產品型號","")) +
            pf("馬達序號", dr.get("馬達序號","")) +
            pf("故障類別", dr.get("故障類別","")) +
            pf("維修類型", mr2.get("維修類型","")),
            unsafe_allow_html=True)
    with p3:
        sv = dr.get("維修狀態","")
        st.markdown(
            pf("維修狀態", f"{STATUS_EMOJI.get(sv,'')} {sv}",
               {"已出廠":"var(--pass)","已完成":"var(--pass)","已取消":"var(--cr)"}.get(sv,"var(--text)")) +
            pf("優先等級", mr2.get("優先等級","")) +
            pf("收件日期", str(mr2.get("收件日期",""))[:16]) +
            pf("技術判定", dr.get("技術判定","")),
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, mid_col2, _ = st.columns([1, 2, 1])
    with mid_col2:
        gen_btn = st.button("📄　產生 PDF 維修報告", use_container_width=True, type="primary")

    if gen_btn:
        merged = {**mr2, **dr,
                  "RMA編號": sel_detail,
                  "客戶公司":   mr2.get("客戶公司",""),
                  "聯絡人":     mr2.get("聯絡人",""),
                  "聯絡電話":   mr2.get("聯絡電話",""),
                  "客戶Email":  mr2.get("客戶Email",""),
                  "收件日期":   mr2.get("收件日期",""),
                  "維修類型":   mr2.get("維修類型",""),
                  "優先等級":   mr2.get("優先等級",""),
                  }
        with st.spinner("正在產生 PDF，請稍候..."):
            try:
                pdf_bytes = generate_repair_pdf(merged)
                fname = f"維修報告_{sel_detail}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.success("✅ PDF 報告已產生！")
                _, dl_col2, _ = st.columns([1, 2, 1])
                with dl_col2:
                    st.download_button(
                        label=f"⬇️　下載 {fname}", data=pdf_bytes,
                        file_name=fname, mime="application/pdf",
                        use_container_width=True)
                size_kb = len(pdf_bytes) / 1024
                st.markdown(
                    f'<p style="font-size:11px;color:var(--muted);text-align:center">'
                    f'檔案大小：{size_kb:.1f} KB &nbsp;|&nbsp; '
                    f'子件：{sel_detail} &nbsp;|&nbsp; '
                    f'客戶：{mr2.get("客戶公司","")}</p>', unsafe_allow_html=True)
            except Exception as ex:
                st.error(f"❌ PDF 產生失敗：{ex}")
                st.exception(ex)
