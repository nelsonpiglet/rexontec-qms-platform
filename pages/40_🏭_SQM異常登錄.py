"""
REXONTEC — SQM 進料異常登錄
IQC 進料不良登錄 / 開立 SCAR / 歷史查詢
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime

from utils.style  import QMS_CSS, topbar, page_header
from utils.auth   import require_login, user_info_bar
from utils.sqm    import (
    DEFECT_CATEGORIES, JUDGMENT_OPTIONS, RESP_UNITS,
    DEFECT_STATUS, STATUS_COLOR, JUDGMENT_COLOR, status_chip, verdict_chip,
)
from utils.gsheet import (
    append_sqm_defect, load_sqm_defects,
    update_sqm_defect, append_scar, update_scar,
)

st.set_page_config(
    page_title="REXONTEC 力科 | SQM 異常登錄",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()
user_info_bar()

# ── 導覽列 ────────────────────────────────────────────
n1,n2,n3,n4,n5,n6,n7 = st.columns([1,1,1,1,1,1,2])
with n1:
    if st.button("🏠 指揮平台",  use_container_width=True): st.switch_page("app.py")
with n2:
    if st.button("🔬 IQC 進料",  use_container_width=True): st.switch_page("pages/06_IQC進料檢驗.py")
with n3:
    if st.button("🏭 SQM 異常",  use_container_width=True): st.switch_page("pages/40_🏭_SQM異常登錄.py")
with n4:
    if st.button("📝 SCAR 管理", use_container_width=True): st.switch_page("pages/41_📝_SCAR管理.py")
with n5:
    if st.button("📊 SQM 儀表板",use_container_width=True): st.switch_page("pages/42_📊_SQM儀表板.py")
with n6:
    if st.button("⚙️ 系統設定",  use_container_width=True): st.switch_page("pages/03_系統設定.py")

st.markdown(page_header(
    "SQM 進料異常登錄",
    "Supplier Quality Management — IQC 進料不良 / SCAR 開立 / 異常追蹤",
    "SQM",
), unsafe_allow_html=True)

# ── 載入資料 ──────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def _load() -> pd.DataFrame:
    try:
        df = load_sqm_defects()
        if not df.empty and "建立時間" in df.columns:
            df["建立時間"] = pd.to_datetime(df["建立時間"], errors="coerce")
            df = df.sort_values("建立時間", ascending=False).reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()


tab_new, tab_list = st.tabs(["📝 新增異常登錄", "📋 異常記錄查詢"])


# ═══════════════════════════════════════════════════════
# TAB 1：新增異常登錄
# ═══════════════════════════════════════════════════════
with tab_new:
    st.markdown("#### 🏷️ 進料基本資訊")
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    with r1c1:
        f_date     = st.date_input("日期 *", value=date.today(), key="sqm_date")
    with r1c2:
        f_supplier = st.text_input("供應商 *", placeholder="例：ABC Electronics", key="sqm_supplier")
    with r1c3:
        f_pn       = st.text_input("料號 *",   placeholder="例：PJ2-001-A", key="sqm_pn")
    with r1c4:
        f_name     = st.text_input("品名",      placeholder="例：電阻 10KΩ 0402", key="sqm_name")

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    with r2c1:
        f_lot      = st.text_input("批號",      placeholder="例：260513-001", key="sqm_lot")
    with r2c2:
        f_qty_in   = st.number_input("批量（進貨數量）", min_value=0, value=0, step=1, key="sqm_qty_in")
    with r2c3:
        f_qty_ng   = st.number_input("異常數量",           min_value=0, value=0, step=1, key="sqm_qty_ng")
    with r2c4:
        rej_rate   = f"{f_qty_ng/f_qty_in*100:.1f}%" if f_qty_in > 0 else "─"
        st.markdown(
            f'<div style="margin-top:28px;font-size:13px;font-weight:700;color:var(--navy)">'
            f'Reject Rate：{rej_rate}</div>', unsafe_allow_html=True)

    st.markdown("#### ⚠️ 異常資訊")
    r3c1, r3c2, r3c3 = st.columns(3)
    with r3c1:
        f_cat      = st.selectbox("異常類別 *", DEFECT_CATEGORIES, key="sqm_cat")
    with r3c2:
        f_judgment = st.selectbox("判定 *",     JUDGMENT_OPTIONS,  key="sqm_judgment")
    with r3c3:
        f_resp     = st.selectbox("責任單位 *", RESP_UNITS,        key="sqm_resp")

    f_desc = st.text_area("異常描述 *",
                          placeholder="請詳細描述異常現象、發現方式、影響範圍…",
                          height=100, key="sqm_desc")

    st.markdown("#### 📎 附件與備註")
    r4c1, r4c2 = st.columns([3, 1])
    with r4c1:
        f_photo = st.text_input(
            "照片 URL（選填）",
            placeholder="將照片上傳至 Google Drive 後貼上分享連結",
            key="sqm_photo",
        )
    with r4c2:
        f_creator = st.text_input("建立人員 *", placeholder="姓名", key="sqm_creator")

    f_remark = st.text_area("備註", placeholder="其他補充說明…", height=60, key="sqm_remark")

    st.markdown("---")
    c_btn, c_hint, _ = st.columns([2, 4, 4])
    with c_btn:
        submitted = st.button("💾 儲存異常記錄", type="primary", use_container_width=True)

    if submitted:
        errors = []
        if not f_supplier.strip(): errors.append("供應商")
        if not f_pn.strip():       errors.append("料號")
        if not f_desc.strip():     errors.append("異常描述")
        if not f_creator.strip():  errors.append("建立人員")

        if errors:
            with c_hint:
                st.warning(f"⚠️ 請填寫必填欄位：{'、'.join(errors)}")
        else:
            payload = {
                "日期":     str(f_date),
                "供應商":   f_supplier.strip(),
                "料號":     f_pn.strip(),
                "品名":     f_name.strip(),
                "批號":     f_lot.strip(),
                "異常類別": f_cat,
                "異常描述": f_desc.strip(),
                "異常數量": f_qty_ng,
                "批量":     f_qty_in,
                "判定":     f_judgment,
                "責任單位": f_resp,
                "照片URL":  f_photo.strip(),
                "處理狀態": "待處理",
                "建立人員": f_creator.strip(),
                "備註":     f_remark.strip(),
            }
            try:
                rec_id = append_sqm_defect(payload)
                st.success(f"✅ 異常記錄已儲存！記錄編號：**{rec_id}**")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ 儲存失敗：{e}")

    # 圖例提示
    st.markdown("""
<div style="background:#fef9e7;border:1px solid #f9ca24;border-radius:8px;
            padding:12px 16px;font-size:12px;color:#7f6d2c;margin-top:12px">
  <b>💡 照片上傳建議：</b>
  請先將照片上傳至 Google Drive，設為「知道連結的人可查看」，複製連結後貼入「照片 URL」欄位。
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# TAB 2：異常記錄查詢
# ═══════════════════════════════════════════════════════
with tab_list:
    df = _load()

    if df.empty:
        st.info("ℹ️ 尚無異常記錄。請在「新增異常登錄」頁面新增第一筆記錄。")
    else:
        # ── 篩選 ────────────────────────────────────────
        st.markdown("#### 🔎 篩選條件")
        fa, fb, fc, fd, fe = st.columns(5)
        with fa:
            sup_opts = ["全部"] + sorted(df["供應商"].dropna().unique().tolist())
            f_sup_f  = st.selectbox("供應商", sup_opts, key="ql_sup")
        with fb:
            cat_opts = ["全部"] + DEFECT_CATEGORIES
            f_cat_f  = st.selectbox("異常類別", cat_opts, key="ql_cat")
        with fc:
            jud_opts = ["全部"] + JUDGMENT_OPTIONS
            f_jud_f  = st.selectbox("判定", jud_opts, key="ql_jud")
        with fd:
            sta_opts = ["全部"] + DEFECT_STATUS
            f_sta_f  = st.selectbox("處理狀態", sta_opts, key="ql_sta")
        with fe:
            f_kw = st.text_input("料號 / 品名搜尋", key="ql_kw", placeholder="輸入關鍵字…")

        ff, fg, _ = st.columns([2, 2, 4])
        with ff:
            d_from = st.date_input("日期（起）", value=None, key="ql_df", format="YYYY/MM/DD")
        with fg:
            d_to   = st.date_input("日期（迄）", value=None, key="ql_dt", format="YYYY/MM/DD")

        # ── 套用篩選 ────────────────────────────────────
        flt = df.copy()
        if "建立時間" in flt.columns:
            flt = flt.dropna(subset=["建立時間"])
        if f_sup_f != "全部":
            flt = flt[flt["供應商"] == f_sup_f]
        if f_cat_f != "全部":
            flt = flt[flt["異常類別"] == f_cat_f]
        if f_jud_f != "全部":
            flt = flt[flt["判定"] == f_jud_f]
        if f_sta_f != "全部":
            flt = flt[flt["處理狀態"] == f_sta_f]
        if f_kw.strip():
            kw = f_kw.strip()
            flt = flt[
                flt["料號"].astype(str).str.contains(kw, case=False, na=False) |
                flt["品名"].astype(str).str.contains(kw, case=False, na=False)
            ]
        if d_from and "建立時間" in flt.columns:
            flt = flt[flt["建立時間"].dt.date >= d_from]
        if d_to and "建立時間" in flt.columns:
            flt = flt[flt["建立時間"].dt.date <= d_to]

        # ── KPI 摘要 ────────────────────────────────────
        total   = len(flt)
        no_scar = (flt["SCAR編號"].astype(str).str.strip().isin(["", "nan"])).sum()
        closed  = (flt["處理狀態"] == "已結案").sum()
        rej_cnt = flt[flt["判定"] == "拒收退貨"]["異常數量"].astype(str).str.replace(",","").apply(
            lambda x: int(x) if x.isdigit() else 0).sum()

        st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0">
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1e88e5;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">查詢結果</div>
    <div style="font-size:26px;font-weight:900;color:#0d1b2a">{total}</div>
    <div style="font-size:10px;color:#aaa">筆異常記錄</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #e74c3c;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">待開立SCAR</div>
    <div style="font-size:26px;font-weight:900;color:#e74c3c">{no_scar}</div>
    <div style="font-size:10px;color:#aaa">未開立 SCAR</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #27ae60;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">已結案</div>
    <div style="font-size:26px;font-weight:900;color:#27ae60">{closed}</div>
    <div style="font-size:10px;color:#aaa">結案記錄</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #c0392b;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">拒收總數量</div>
    <div style="font-size:26px;font-weight:900;color:#c0392b">{rej_cnt}</div>
    <div style="font-size:10px;color:#aaa">pcs</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── 表格 ────────────────────────────────────────
        show_cols = [c for c in [
            "記錄編號", "建立時間", "供應商", "料號", "品名", "批號",
            "異常類別", "異常數量", "判定", "責任單位", "處理狀態", "SCAR編號",
        ] if c in flt.columns]

        disp = flt[show_cols].copy()
        if "建立時間" in disp.columns:
            disp["建立時間"] = disp["建立時間"].dt.strftime("%Y/%m/%d %H:%M")

        st.caption(f"共 {total} 筆")
        st.dataframe(disp, use_container_width=True, hide_index=True,
                     height=min(420, 56 + total * 38))

        csv = disp.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("⬇️ 匯出 CSV",
                           data=csv.encode("utf-8-sig"),
                           file_name=f"SQM_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                           mime="text/csv")

        # ── 明細展開 & 開立 SCAR ────────────────────────
        if 0 < total <= 60:
            st.markdown("---")
            st.markdown("##### 📄 明細 & 開立 SCAR")
            for _, row in flt.iterrows():
                dt_str   = row["建立時間"].strftime("%Y/%m/%d") if pd.notna(row.get("建立時間")) else "─"
                scar_str = str(row.get("SCAR編號", "")).strip()
                has_scar = scar_str not in ("", "nan")
                status   = str(row.get("處理狀態", "待處理"))
                sc       = STATUS_COLOR.get(status, "#888")
                jc       = JUDGMENT_COLOR.get(str(row.get("判定", "")), "#888")

                with st.expander(
                    f"📋 {row['記錄編號']}  ｜  {dt_str}  ｜  "
                    f"{row.get('供應商','─')}  ｜  {row.get('料號','─')}  ｜  "
                    f"{row.get('異常類別','─')}  ｜  {status}",
                ):
                    dc1, dc2, dc3, dc4, dc5 = st.columns(5)
                    dc1.metric("供應商",   str(row.get("供應商","─")))
                    dc2.metric("料號",     str(row.get("料號","─")))
                    dc3.metric("異常數量", str(row.get("異常數量","─")))
                    dc4.metric("判定",     str(row.get("判定","─")))
                    dc5.metric("責任單位", str(row.get("責任單位","─")))

                    desc = str(row.get("異常描述", ""))
                    if desc and desc != "nan":
                        st.markdown(f"""
<div style="background:#fff8f7;border:1px solid #f5b7b1;border-radius:6px;
            padding:10px 14px;font-size:12px;margin:8px 0">
  <b style="color:#c0392b">異常描述：</b>{desc}
</div>""", unsafe_allow_html=True)

                    photo = str(row.get("照片URL", "")).strip()
                    if photo and photo not in ("", "nan"):
                        st.markdown(f"🔗 [查看照片]({photo})")

                    # SCAR 狀態 / 開立按鈕
                    st.markdown("---")
                    scar_c1, scar_c2, scar_c3 = st.columns([2, 2, 4])
                    with scar_c1:
                        if has_scar:
                            st.markdown(
                                f'✅ **SCAR 已開立**：`{scar_str}`', unsafe_allow_html=True)
                        else:
                            open_scar = st.button("🚨 開立 SCAR",
                                                  key=f"scar_{row['記錄編號']}",
                                                  use_container_width=True,
                                                  type="primary")
                            if open_scar:
                                st.session_state["scar_prefill"] = {
                                    "異常記錄編號": row["記錄編號"],
                                    "供應商":       row.get("供應商", ""),
                                    "料號":         row.get("料號", ""),
                                    "品名":         row.get("品名", ""),
                                    "異常日期":     str(row.get("日期", "")),
                                    "異常類別":     row.get("異常類別", ""),
                                    "異常描述":     row.get("異常描述", ""),
                                    "異常數量":     row.get("異常數量", 0),
                                }
                                st.switch_page("pages/41_📝_SCAR管理.py")
        elif total > 60:
            st.caption("🔍 超過 60 筆，請縮小篩選範圍以展開明細。")
