"""
REXONTEC — SCAR 供應商異常管理
供應商異常單 / 追蹤 / CAPA / 結案
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

from utils.style  import QMS_CSS, topbar, page_header
from utils.auth   import require_login, user_info_bar
from utils.sqm    import (
    DEFECT_CATEGORIES, RESP_UNITS, SCAR_REPLY_STATUS,
    CAPA_STATUS, CLOSE_STATUS, STATUS_COLOR, status_chip,
)
from utils.gsheet import (
    load_sqm_defects, append_scar, load_scars, update_scar,
    update_sqm_defect,
)

st.set_page_config(
    page_title="REXONTEC 力科 | SCAR 管理",
    page_icon="📝",
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
    "SCAR 供應商異常管理",
    "Supplier Corrective Action Request — 異常追蹤 / CAPA / 結案管控",
    "SCR",
), unsafe_allow_html=True)

# ── 資料載入 ──────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def _load_scars_df() -> pd.DataFrame:
    try:
        df = load_scars()
        if not df.empty and "建立時間" in df.columns:
            df["建立時間"] = pd.to_datetime(df["建立時間"], errors="coerce")
            df = df.sort_values("建立時間", ascending=False).reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()

# 從 SQM 異常頁帶過來的預填資料
prefill = st.session_state.pop("scar_prefill", {})

tab_list, tab_new = st.tabs(["📋 SCAR 追蹤列表", "📝 新增 SCAR"])


# ═══════════════════════════════════════════════════════
# TAB 1：SCAR 追蹤列表
# ═══════════════════════════════════════════════════════
with tab_list:
    df_scar = _load_scars_df()

    if df_scar.empty:
        st.info("ℹ️ 尚無 SCAR 記錄，請點「新增 SCAR」建立第一筆。")
    else:
        # 篩選
        fa, fb, fc, fd = st.columns(4)
        with fa:
            sup_opts = ["全部"] + sorted(df_scar["供應商"].dropna().unique().tolist())
            f_sup = st.selectbox("供應商", sup_opts, key="sl_sup")
        with fb:
            rep_opts = ["全部"] + SCAR_REPLY_STATUS
            f_rep = st.selectbox("供應商回覆狀態", rep_opts, key="sl_rep")
        with fc:
            capa_opts = ["全部"] + CAPA_STATUS
            f_capa = st.selectbox("CAPA 狀態", capa_opts, key="sl_capa")
        with fd:
            close_opts = ["全部", "Open", "Closed"]
            f_close = st.selectbox("結案狀態", close_opts, key="sl_close")

        flt = df_scar.copy()
        if f_sup   != "全部": flt = flt[flt["供應商"]         == f_sup]
        if f_rep   != "全部": flt = flt[flt["供應商回覆狀態"] == f_rep]
        if f_capa  != "全部": flt = flt[flt["CAPA狀態"]       == f_capa]
        if f_close != "全部": flt = flt[flt["結案狀態"]       == f_close]

        # KPI 摘要
        total_s  = len(flt)
        open_s   = (flt["結案狀態"] == "Open").sum()
        wait_rep = (flt["供應商回覆狀態"] == "待回覆").sum()
        overdue  = (flt["供應商回覆狀態"] == "逾期未回覆").sum()

        st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0">
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1e88e5;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700">SCAR 總數</div>
    <div style="font-size:26px;font-weight:900;color:#0d1b2a">{total_s}</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #e67e22;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700">Open 未結案</div>
    <div style="font-size:26px;font-weight:900;color:#e67e22">{open_s}</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #e74c3c;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700">等待回覆</div>
    <div style="font-size:26px;font-weight:900;color:#e74c3c">{wait_rep}</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #c0392b;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700">逾期未回覆</div>
    <div style="font-size:26px;font-weight:900;color:#c0392b">{overdue}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # 清單表格
        show_cols = [c for c in [
            "SCAR編號", "建立時間", "供應商", "料號", "異常類別",
            "要求回覆期限", "供應商回覆狀態", "CAPA狀態", "結案狀態",
        ] if c in flt.columns]

        disp = flt[show_cols].copy()
        if "建立時間" in disp.columns:
            disp["建立時間"] = disp["建立時間"].dt.strftime("%Y/%m/%d")

        st.caption(f"共 {total_s} 筆")
        st.dataframe(disp, use_container_width=True, hide_index=True,
                     height=min(380, 56 + total_s * 38))

        csv = disp.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("⬇️ 匯出 CSV",
                           data=csv.encode("utf-8-sig"),
                           file_name=f"SCAR_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                           mime="text/csv")

        # 明細展開 & 狀態更新
        if 0 < total_s <= 50:
            st.markdown("---")
            st.markdown("##### 📄 明細 & 狀態更新")
            for _, row in flt.iterrows():
                dt_str    = row["建立時間"].strftime("%Y/%m/%d") if pd.notna(row.get("建立時間")) else "─"
                rep_s     = str(row.get("供應商回覆狀態", ""))
                capa_s    = str(row.get("CAPA狀態", ""))
                close_s   = str(row.get("結案狀態", "Open"))

                rep_chip  = status_chip(rep_s)
                capa_chip = status_chip(capa_s)
                close_chip= status_chip(close_s)

                with st.expander(
                    f"📝 {row['SCAR編號']}  ｜  {dt_str}  ｜  "
                    f"{row.get('供應商','─')}  ｜  {row.get('異常類別','─')}  ｜  結案：{close_s}"
                ):
                    # ── 異常資訊 ─────────────────────────
                    ic1, ic2, ic3, ic4 = st.columns(4)
                    ic1.metric("供應商",   str(row.get("供應商","─")))
                    ic2.metric("料號",     str(row.get("料號","─")))
                    ic3.metric("異常類別", str(row.get("異常類別","─")))
                    ic4.metric("異常數量", str(row.get("異常數量","─")))

                    desc = str(row.get("異常描述",""))
                    if desc and desc != "nan":
                        st.markdown(f"""
<div style="background:#fff8f7;border:1px solid #f5b7b1;border-radius:6px;
            padding:10px 14px;font-size:12px;margin:8px 0">
  <b style="color:#c0392b">異常描述：</b>{desc}
</div>""", unsafe_allow_html=True)

                    # ── CAPA 內容 ─────────────────────────
                    st.markdown("**🔧 CAPA 改善記錄**")
                    ce1, ce2 = st.columns(2)
                    with ce1:
                        d3  = str(row.get("臨時對策_D3",""))
                        d45 = str(row.get("根本原因_D4D5",""))
                        st.text_area("D3 臨時對策", value="" if d3=="nan" else d3,
                                     height=60, disabled=True, key=f"d3_{row['SCAR編號']}")
                        st.text_area("D4/D5 根本原因", value="" if d45=="nan" else d45,
                                     height=60, disabled=True, key=f"d45_{row['SCAR編號']}")
                    with ce2:
                        d6 = str(row.get("永久對策_D6",""))
                        d7 = str(row.get("CAPA驗證_D7",""))
                        st.text_area("D6 永久對策", value="" if d6=="nan" else d6,
                                     height=60, disabled=True, key=f"d6_{row['SCAR編號']}")
                        st.text_area("D7 CAPA驗證", value="" if d7=="nan" else d7,
                                     height=60, disabled=True, key=f"d7_{row['SCAR編號']}")

                    # ── 狀態更新 ─────────────────────────
                    st.markdown("---")
                    st.markdown("**✏️ 更新狀態**")
                    u1, u2, u3 = st.columns(3)
                    with u1:
                        new_rep  = st.selectbox("供應商回覆狀態",
                                                SCAR_REPLY_STATUS,
                                                index=SCAR_REPLY_STATUS.index(rep_s)
                                                      if rep_s in SCAR_REPLY_STATUS else 0,
                                                key=f"rep_{row['SCAR編號']}")
                    with u2:
                        new_capa = st.selectbox("CAPA 狀態",
                                                CAPA_STATUS,
                                                index=CAPA_STATUS.index(capa_s)
                                                      if capa_s in CAPA_STATUS else 0,
                                                key=f"capa_{row['SCAR編號']}")
                    with u3:
                        new_close= st.selectbox("結案狀態",
                                                CLOSE_STATUS,
                                                index=CLOSE_STATUS.index(close_s)
                                                      if close_s in CLOSE_STATUS else 0,
                                                key=f"close_{row['SCAR編號']}")

                    # CAPA 填寫
                    st.markdown("**📝 填寫改善對策**")
                    c1e, c2e = st.columns(2)
                    with c1e:
                        new_d3  = st.text_area("D3 臨時對策",   key=f"nd3_{row['SCAR編號']}",  height=60)
                        new_d45 = st.text_area("D4/D5 根本原因",key=f"nd45_{row['SCAR編號']}", height=60)
                    with c2e:
                        new_d6  = st.text_area("D6 永久對策",   key=f"nd6_{row['SCAR編號']}",  height=60)
                        new_d7  = st.text_area("D7 CAPA 驗證",  key=f"nd7_{row['SCAR編號']}",  height=60)

                    new_rep_date = st.date_input("供應商回覆日期",
                                                  value=None,
                                                  key=f"rdate_{row['SCAR編號']}",
                                                  format="YYYY/MM/DD")
                    new_rep_content = st.text_area("供應商回覆內容",
                                                    key=f"rcont_{row['SCAR編號']}",
                                                    height=60)
                    new_mgr = st.text_input("主管審核", key=f"mgr_{row['SCAR編號']}")

                    update_btn = st.button("💾 儲存更新", key=f"upd_{row['SCAR編號']}",
                                           type="primary", use_container_width=False)
                    if update_btn:
                        updates: dict = {
                            "供應商回覆狀態": new_rep,
                            "CAPA狀態":       new_capa,
                            "結案狀態":       new_close,
                        }
                        if new_d3.strip():        updates["臨時對策_D3"]    = new_d3.strip()
                        if new_d45.strip():       updates["根本原因_D4D5"]  = new_d45.strip()
                        if new_d6.strip():        updates["永久對策_D6"]    = new_d6.strip()
                        if new_d7.strip():        updates["CAPA驗證_D7"]    = new_d7.strip()
                        if new_rep_date:          updates["供應商回覆日期"] = str(new_rep_date)
                        if new_rep_content.strip():updates["供應商回覆內容"]= new_rep_content.strip()
                        if new_mgr.strip():       updates["主管審核"]       = new_mgr.strip()

                        try:
                            update_scar(row["SCAR編號"], updates)
                            # 同步更新 SQM 異常記錄的狀態
                            def_id = str(row.get("異常記錄編號","")).strip()
                            if def_id and def_id != "nan":
                                new_def_status = "已結案" if new_close == "Closed" else "等待供應商回覆"
                                update_sqm_defect(def_id, "處理狀態", new_def_status)
                            st.success("✅ 已更新！")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 更新失敗：{e}")

        elif total_s > 50:
            st.caption("🔍 超過 50 筆，請縮小篩選範圍以展開明細。")


# ═══════════════════════════════════════════════════════
# TAB 2：新增 SCAR
# ═══════════════════════════════════════════════════════
with tab_new:
    if prefill:
        st.info(f"📎 已從異常記錄 **{prefill.get('異常記錄編號','')}** 帶入資料，請確認後開立。")

    st.markdown("#### 📋 異常基本資訊")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        s_defect_id = st.text_input("關聯異常記錄編號",
                                     value=prefill.get("異常記錄編號", ""),
                                     key="ns_defect_id")
    with s2:
        s_supplier  = st.text_input("供應商 *",
                                     value=prefill.get("供應商", ""),
                                     key="ns_supplier")
    with s3:
        s_pn        = st.text_input("料號 *",
                                     value=prefill.get("料號", ""),
                                     key="ns_pn")
    with s4:
        s_name      = st.text_input("品名",
                                     value=prefill.get("品名", ""),
                                     key="ns_name")

    s5, s6, s7, s8 = st.columns(4)
    _date_val = date.today()
    if prefill.get("異常日期"):
        try:
            _date_val = datetime.strptime(prefill["異常日期"][:10], "%Y-%m-%d").date()
        except Exception:
            pass
    with s5:
        s_defect_date = st.date_input("異常日期 *", value=_date_val, key="ns_defdate")
    with s6:
        _cat_idx = 0
        if prefill.get("異常類別") in DEFECT_CATEGORIES:
            _cat_idx = DEFECT_CATEGORIES.index(prefill["異常類別"])
        s_cat = st.selectbox("異常類別 *", DEFECT_CATEGORIES, index=_cat_idx, key="ns_cat")
    with s7:
        s_qty = st.number_input("異常數量",
                                 value=int(prefill.get("異常數量", 0)) if prefill else 0,
                                 min_value=0, step=1, key="ns_qty")
    with s8:
        s_deadline = st.date_input("要求回覆期限 *",
                                    value=date.today() + timedelta(days=14),
                                    key="ns_deadline")

    s_desc = st.text_area("異常描述 *",
                           value=prefill.get("異常描述", ""),
                           placeholder="描述異常現象、影響程度…",
                           height=80, key="ns_desc")

    st.markdown("#### 🔧 責任 & 要求")
    t1, t2, t3 = st.columns(3)
    with t1:
        s_resp    = st.selectbox("責任歸屬 *", RESP_UNITS, key="ns_resp")
    with t2:
        s_creator = st.text_input("開立人員 *", key="ns_creator")
    with t3:
        s_remark  = st.text_input("備註",       key="ns_remark")

    st.markdown("---")
    btn_c1, btn_c2, _ = st.columns([2, 2, 6])
    with btn_c1:
        scar_submit = st.button("🚨 開立 SCAR", type="primary", use_container_width=True)

    if scar_submit:
        errs = []
        if not s_supplier.strip(): errs.append("供應商")
        if not s_pn.strip():       errs.append("料號")
        if not s_desc.strip():     errs.append("異常描述")
        if not s_creator.strip():  errs.append("開立人員")

        if errs:
            with btn_c2:
                st.warning(f"⚠️ 請填寫：{'、'.join(errs)}")
        else:
            payload = {
                "異常記錄編號": s_defect_id.strip(),
                "供應商":       s_supplier.strip(),
                "料號":         s_pn.strip(),
                "品名":         s_name.strip(),
                "異常日期":     str(s_defect_date),
                "異常類別":     s_cat,
                "異常描述":     s_desc.strip(),
                "異常數量":     s_qty,
                "要求回覆期限": str(s_deadline),
                "責任歸屬":     s_resp,
                "建立人員":     s_creator.strip(),
                "備註":         s_remark.strip(),
            }
            try:
                scar_no = append_scar(payload)

                # 同步更新 SQM 異常記錄
                def_id = s_defect_id.strip()
                if def_id:
                    try:
                        update_sqm_defect(def_id, "SCAR編號",  scar_no)
                        update_sqm_defect(def_id, "處理狀態", "SCAR開立中")
                    except Exception:
                        pass  # 異常記錄可能不存在（手動開立），不影響 SCAR

                st.success(f"✅ SCAR 已開立！SCAR 編號：**{scar_no}**")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ 開立失敗：{e}")
