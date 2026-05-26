"""
REXONTEC — SQM 進料異常登錄
欄位比照 IQC問題點病歷 Excel：
  發生日期 / 來源 / 機種 / 零件名稱 / 零件編號（單據號碼）/ 廠商 / 不良數
  P問題點 / 原因分析 / D改善對策 / C效果確認 / A標準化
  責任歸屬 / 完成日期 / 負責人 / 狀態 / 照片 / 廠商稽核
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime

from utils.style  import QMS_CSS, topbar, page_header
from utils.auth   import require_login, user_info_bar
from utils.sqm    import (
    SOURCE_OPTIONS, IQC_STATUS_OPTIONS, RESP_OPTIONS,
    DEFECT_CATEGORY_OPTIONS,
    DEFECT_STATUS, STATUS_COLOR, status_chip,
)
from utils.gsheet import (
    append_sqm_defect, load_sqm_defects,
    update_sqm_defect, delete_sqm_defect, append_scar,
    upload_photo_to_drive,
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
n1,n2,n3,n4,n5,n6,n7,n8 = st.columns([1,1,1,1,1,1,1,2])
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
    if st.button("📥 文件匯入",  use_container_width=True): st.switch_page("pages/50_📥_文件匯入中心.py")
with n7:
    if st.button("⚙️ 系統設定",  use_container_width=True): st.switch_page("pages/03_系統設定.py")

st.markdown(page_header(
    "SQM 進料異常登錄",
    "Supplier Quality Management — IQC 進料不良登錄 / PDCA 追蹤 / SCAR 開立",
    "SQM",
), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# 資料載入
# ─────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _load():
    return load_sqm_defects()


tab_new, tab_query = st.tabs(["📝 新增異常登錄", "📋 異常記錄查詢"])


# ═══════════════════════════════════════════════════════
# Tab 1：新增異常登錄
# ═══════════════════════════════════════════════════════
with tab_new:
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid var(--accent);padding-left:10px;margin:0 0 16px">'
        '填寫進料異常資料</div>',
        unsafe_allow_html=True,
    )

    # ── 照片上傳（在 form 外，避免 Streamlit file_uploader 限制）──
    st.markdown("**📷 上傳不良品照片**")
    ph1, ph2 = st.columns([2, 3])
    with ph1:
        uploaded_photo = st.file_uploader(
            "選擇照片（JPG / PNG / WEBP，最大 10 MB）",
            type=["jpg", "jpeg", "png", "webp", "bmp"],
            key="sqm_photo_file",
            label_visibility="collapsed",
        )
    with ph2:
        if uploaded_photo:
            st.image(uploaded_photo, caption="預覽", width=220)
        else:
            st.caption("或貼入 Google Drive 照片連結（表單內）")

    with st.form("sqm_form", clear_on_submit=True):
        # ── 基本資訊 ──────────────────────────────────
        st.markdown("**📌 基本資訊**")
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        with r1c1:
            f_date   = st.date_input("發生日期 ⭐", value=date.today())
        with r1c2:
            f_source = st.selectbox(
                "來源", [""] + SOURCE_OPTIONS,
                help="問題發現來源",
            )
        with r1c3:
            f_defcat = st.selectbox(
                "異常類別 ⭐", [""] + DEFECT_CATEGORY_OPTIONS,
                help="不良品異常分類",
            )
        with r1c4:
            f_model  = st.text_input("機種", placeholder="e.g. GPS / PJ2+GPS")

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            f_pname  = st.text_input("零件名稱", placeholder="零件/材料名稱")
        with r2c2:
            f_pno    = st.text_input("零件編號（單據號碼）⭐", placeholder="料號 / 批號")
        with r2c3:
            f_vendor = st.text_input("廠商 ⭐", placeholder="供應商名稱")

        r3c1, r3c2, r3c3 = st.columns(3)
        with r3c1:
            f_qty    = st.number_input("不良數 ⭐", min_value=0, step=1, value=0)
        with r3c2:
            f_resp   = st.selectbox("責任歸屬", [""] + RESP_OPTIONS)
        with r3c3:
            f_status = st.selectbox("狀態", IQC_STATUS_OPTIONS, index=0)

        st.divider()

        # ── PDCA 分析 ────────────────────────────────
        st.markdown("**📊 PDCA 問題分析**")
        f_problem = st.text_area(
            "P 問題點 ⭐",
            placeholder="描述具體不良現象，例如：按鍵毛邊、旋鈕孔有毛邊，抽驗200PCS/12個不良",
            height=90,
        )

        pa1, pa2 = st.columns(2)
        with pa1:
            f_cause  = st.text_area("原因分析", placeholder="根本原因分析", height=80)
        with pa2:
            f_action = st.text_area("D 改善對策", placeholder="矯正/改善措施", height=80)

        pb1, pb2 = st.columns(2)
        with pb1:
            f_confirm = st.text_area("C 效果確認", placeholder="改善效果確認/驗證結果", height=80)
        with pb2:
            f_std    = st.text_area("A 標準化", placeholder="標準化措施/文件更新", height=80)

        st.divider()

        # ── 其他欄位 ─────────────────────────────────
        st.markdown("**📋 其他資訊**")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            f_owner  = st.text_input("負責人", placeholder="負責處理人員")
        with rc2:
            f_due    = st.date_input("完成日期", value=None)
        with rc3:
            f_audit  = st.text_input("廠商稽核", placeholder="稽核紀錄或結果")

        f_photo_url = st.text_input(
            "照片連結（選填，若已在上方上傳則不需填寫）",
            placeholder="或直接貼入 Google Drive 分享連結",
        )

        submitted = st.form_submit_button(
            "💾 新增異常登錄", type="primary", use_container_width=True
        )

    if submitted:
        err = []
        if not f_pno.strip():    err.append("零件編號（單據號碼）")
        if not f_vendor.strip(): err.append("廠商")
        if not f_problem.strip():err.append("P問題點")
        if f_qty <= 0:           err.append("不良數（須 > 0）")

        if err:
            st.error(f"❌ 以下必填欄位尚未填寫：**{'、'.join(err)}**")
        else:
            # ── 處理照片 ──────────────────────────────
            photo_url = f_photo_url.strip()
            if uploaded_photo and not photo_url:
                with st.spinner("📤 上傳照片至 Google Drive…"):
                    try:
                        photo_url = upload_photo_to_drive(
                            file_bytes=uploaded_photo.read(),
                            filename=uploaded_photo.name,
                            mime_type=uploaded_photo.type or "image/jpeg",
                        )
                        st.toast(f"📷 照片已上傳：{uploaded_photo.name}", icon="✅")
                    except Exception as e:
                        st.warning(f"⚠️ 照片上傳失敗（{e}），記錄仍正常儲存。")

            try:
                rec_id = append_sqm_defect({
                    "發生日期":             f_date.strftime("%Y/%m/%d"),
                    "來源":                 f_source,
                    "機種":                 f_model.strip(),
                    "零件名稱":             f_pname.strip(),
                    "零件編號（單據號碼）": f_pno.strip(),
                    "廠商":                 f_vendor.strip(),
                    "不良數":               str(f_qty),
                    "P問題點":              f_problem.strip(),
                    "原因分析":             f_cause.strip(),
                    "D改善對策":            f_action.strip(),
                    "C效果確認":            f_confirm.strip(),
                    "A標準化":              f_std.strip(),
                    "責任歸屬":             f_resp,
                    "完成日期":             f_due.strftime("%Y/%m/%d") if f_due else "",
                    "負責人":               f_owner.strip(),
                    "狀態":                 f_status,
                    "照片":                 photo_url,
                    "廠商稽核":             f_audit.strip(),
                    "處理狀態":             "待處理",
                    "異常類別":             f_defcat,
                })
                st.success(f"✅ 新增成功！記錄編號：**{rec_id}**")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ 寫入失敗：{e}")


# ═══════════════════════════════════════════════════════
# Tab 2：異常記錄查詢
# ═══════════════════════════════════════════════════════
with tab_query:
    # 重新整理按鈕（清除快取，確保顯示最新資料）
    _rf_col, _info_col = st.columns([1, 5])
    with _rf_col:
        if st.button("🔄 重新整理", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with _info_col:
        st.caption("資料每 60 秒自動更新，或點擊「重新整理」即時載入最新資料。")

    df = _load()

    # ── 篩選列 ────────────────────────────────────────
    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
    with fc1:
        vendors = ["全部"] + sorted(df["廠商"].dropna().unique().tolist()) if not df.empty else ["全部"]
        fv = st.selectbox("廠商", vendors, key="fq_vendor")
    with fc2:
        models  = ["全部"] + sorted(df["機種"].dropna().unique().tolist()) if not df.empty else ["全部"]
        fm = st.selectbox("機種", models, key="fq_model")
    with fc3:
        stats   = ["全部"] + IQC_STATUS_OPTIONS
        fs = st.selectbox("狀態", stats, key="fq_status")
    with fc4:
        sources = ["全部"] + SOURCE_OPTIONS
        fsr = st.selectbox("來源", sources, key="fq_source")
    with fc5:
        defcats = ["全部"] + DEFECT_CATEGORY_OPTIONS
        fdc = st.selectbox("異常類別", defcats, key="fq_defcat")
    with fc6:
        kw = st.text_input("🔍 關鍵字", placeholder="廠商/零件/問題點")

    fd1, fd2 = st.columns(2)
    with fd1:
        date_from = st.date_input("發生日期 從", value=None, key="fq_from")
    with fd2:
        date_to   = st.date_input("發生日期 至", value=None, key="fq_to")

    if df.empty:
        st.info("📭 尚無資料，請先新增異常登錄。")
    else:
        dff = df.copy()

        if fv  != "全部": dff = dff[dff["廠商"] == fv]
        if fm  != "全部": dff = dff[dff["機種"] == fm]
        if fs  != "全部": dff = dff[dff["狀態"] == fs]
        if fsr != "全部": dff = dff[dff["來源"] == fsr]
        if fdc != "全部" and "異常類別" in dff.columns:
            dff = dff[dff["異常類別"] == fdc]
        if kw:
            mask = dff.apply(lambda r: kw in " ".join(r.astype(str)), axis=1)
            dff  = dff[mask]

        # 日期篩選
        if "發生日期" in dff.columns:
            dff["_d"] = pd.to_datetime(dff["發生日期"], errors="coerce")
            if date_from:
                dff = dff[dff["_d"] >= pd.Timestamp(date_from)]
            if date_to:
                dff = dff[dff["_d"] <= pd.Timestamp(date_to)]
            dff = dff.drop(columns=["_d"], errors="ignore")

        # ── KPI 卡片 ──────────────────────────────────
        n_total    = len(dff)
        n_open     = len(dff[dff.get("狀態", pd.Series(dtype=str)).eq("處理中")]) if "狀態" in dff.columns else 0
        n_closed   = len(dff[dff.get("狀態", pd.Series(dtype=str)).eq("結案")]) if "狀態" in dff.columns else 0
        n_recur    = len(dff[dff.get("狀態", pd.Series(dtype=str)).eq("再發")]) if "狀態" in dff.columns else 0

        kc1, kc2, kc3, kc4 = st.columns(4)
        kc1.metric("查詢結果", n_total)
        kc2.metric("🔄 處理中", n_open)
        kc3.metric("✅ 已結案", n_closed)
        kc4.metric("⚠️ 再發", n_recur, delta=f"+{n_recur}" if n_recur else None, delta_color="inverse")

        # ── 資料表 ────────────────────────────────────
        show_cols = [c for c in [
            "記錄編號", "發生日期", "來源", "異常類別", "機種", "零件名稱",
            "零件編號（單據號碼）", "廠商", "不良數",
            "P問題點", "負責人", "狀態", "SCAR編號",
        ] if c in dff.columns]

        st.dataframe(
            dff[show_cols].reset_index(drop=True),
            use_container_width=True,
            height=min(450, 35 * (len(dff) + 1) + 10),
        )

        # CSV 匯出
        st.download_button(
            "⬇️ 匯出 CSV",
            data=dff.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"SQM異常_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

        # ── 展開詳情 ──────────────────────────────────
        if not dff.empty:
            st.markdown("---")
            st.markdown(
                '<div style="font-size:12px;font-weight:700;color:var(--muted);margin-bottom:8px">'
                '點擊展開查看詳情 / 開立 SCAR</div>',
                unsafe_allow_html=True,
            )
            for _, row in dff.iterrows():
                rid  = row.get("記錄編號", "")
                vendor = row.get("廠商", "")
                pno  = row.get("零件編號（單據號碼）", "")
                prob = str(row.get("P問題點", ""))[:50]
                stat = row.get("狀態", "")
                with st.expander(f"📋 {rid} ｜ {vendor} ｜ {pno} ｜ {prob}…"):
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        st.markdown(f"**發生日期：** {row.get('發生日期','')}")
                        st.markdown(f"**來源：** {row.get('來源','')}")
                        st.markdown(f"**異常類別：** {row.get('異常類別','─') or '─'}")
                        st.markdown(f"**機種：** {row.get('機種','')}")
                        st.markdown(f"**零件名稱：** {row.get('零件名稱','')}")
                        st.markdown(f"**零件編號：** {row.get('零件編號（單據號碼）','')}")
                        st.markdown(f"**廠商：** {row.get('廠商','')}")
                        st.markdown(f"**不良數：** {row.get('不良數','')}")
                        st.markdown(f"**負責人：** {row.get('負責人','')}")
                        st.markdown(f"**完成日期：** {row.get('完成日期','')}")
                    with dc2:
                        st.markdown(f"**責任歸屬：** {row.get('責任歸屬','')}")
                        st.markdown(f"**狀態：** {stat}")
                        st.markdown(f"**SCAR 編號：** {row.get('SCAR編號','─') or '─'}")
                        if row.get("廠商稽核"):
                            st.markdown(f"**廠商稽核：** {row.get('廠商稽核')}")
                        # 照片預覽
                        photo_val = row.get("照片", "")
                        if photo_val:
                            st.markdown(f"[📷 查看照片]({photo_val})")
                            # 嘗試直接顯示（Google Drive 直連格式）
                            if "drive.google.com/file/d/" in photo_val:
                                fid = photo_val.split("/file/d/")[1].split("/")[0]
                                thumb = f"https://drive.google.com/thumbnail?id={fid}&sz=w400"
                                st.image(thumb, width=280, caption="不良品照片")

                    st.markdown("---")
                    for label, key in [
                        ("P 問題點", "P問題點"),
                        ("原因分析", "原因分析"),
                        ("D 改善對策", "D改善對策"),
                        ("C 效果確認", "C效果確認"),
                        ("A 標準化",   "A標準化"),
                    ]:
                        val = row.get(key, "")
                        if val:
                            st.markdown(f"**{label}：** {val}")

                    # 開立 SCAR 按鈕
                    scar_no = row.get("SCAR編號", "")
                    if not scar_no:
                        if st.button(f"🚨 開立 SCAR", key=f"scar_{rid}"):
                            st.session_state["scar_prefill"] = {
                                "異常記錄編號": rid,
                                "供應商":       vendor,
                                "料號":         pno,
                                "品名":         row.get("零件名稱", ""),
                                "異常日期":     row.get("發生日期", ""),
                                "異常描述":     row.get("P問題點", ""),
                                "異常數量":     str(row.get("不良數", "")),
                                "異常類別":     "",
                            }
                            st.switch_page("pages/41_📝_SCAR管理.py")
                    else:
                        st.info(f"✅ 已開立 SCAR：**{scar_no}**")

                    # 狀態快速更新
                    st.markdown("**快速更新狀態**")
                    uc1, uc2 = st.columns([2, 1])
                    with uc1:
                        new_stat = st.selectbox(
                            "新狀態",
                            IQC_STATUS_OPTIONS,
                            index=IQC_STATUS_OPTIONS.index(stat) if stat in IQC_STATUS_OPTIONS else 0,
                            key=f"stat_{rid}",
                        )
                    with uc2:
                        st.write("")
                        st.write("")
                        if st.button("更新", key=f"upd_{rid}"):
                            try:
                                update_sqm_defect(rid, "狀態", new_stat)
                                st.success("✅ 狀態已更新")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ {e}")

                    # 刪除記錄
                    st.markdown("---")
                    del_col1, del_col2 = st.columns([3, 1])
                    with del_col2:
                        if st.button(
                            "🗑️ 刪除此記錄",
                            key=f"del_{rid}",
                            type="secondary",
                            use_container_width=True,
                            help="永久刪除此筆異常記錄，無法復原",
                        ):
                            st.session_state[f"confirm_del_{rid}"] = True
                    if st.session_state.get(f"confirm_del_{rid}"):
                        with del_col1:
                            st.warning(f"⚠️ 確定要永久刪除 **{rid}** 嗎？此動作無法復原！")
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            if st.button("✅ 確認刪除", key=f"del_yes_{rid}", type="primary"):
                                try:
                                    delete_sqm_defect(rid)
                                    st.success(f"✅ 已刪除 {rid}")
                                    st.session_state.pop(f"confirm_del_{rid}", None)
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ {e}")
                        with dc2:
                            if st.button("❌ 取消", key=f"del_no_{rid}"):
                                st.session_state.pop(f"confirm_del_{rid}", None)
                                st.rerun()
