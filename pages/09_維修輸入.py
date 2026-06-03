"""
REXONTEC 力科品質指揮平台 — 維修保養系統
維修案件輸入（主單 + 子件架構）
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.rma_master_gsheet import append_master
from utils.rma_detail_gsheet import append_detail, append_batch_details, update_detail_photos
from utils.style             import QMS_CSS, topbar, page_header
from utils.rma_email_notify  import notify_new_rma
from utils.rma_drive_upload  import upload_photos

st.set_page_config(
    page_title="REXONTEC 力科 | 維修輸入",
    page_icon="📝",
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

st.markdown(page_header("維修案件輸入", "RMA Master + Detail / New Repair Order", "NEW"),
            unsafe_allow_html=True)

MOTOR_MODELS = [
    "MD1001RX_18馬達", "MD1001RX_24馬達",
    "MD2004RX_18馬達", "MD2004RX_24馬達",
    "其他（請於備註說明）",
]
FAULT_TYPES  = ["運轉異音","過熱","轉速不穩","完全不轉",
                "震動異常","電流異常","外殼損傷","線材問題","其他"]
REPAIR_TYPES = [
    "摔落損傷", "飛機迫降", "試飛摔落", "試轉卡頓",
    "無載運轉異常", "飛測摔落", "飛測墜毀",
    "上電燒毀", "試轉異常", "重落地損傷",
]
PRIORITIES   = ["P3 一般（7個工作天）","P2 高（5個工作天）",
                "P1 緊急（2個工作天）","P4 低（14個工作天）"]


def section(num, title, sub=""):
    st.markdown(f"""
    <div class="sec-title">
      <div class="sec-num">{num}</div>
      <div>
        <div class="sec-text">{title}</div>
        {'<div class="sec-sub">'+sub+'</div>' if sub else ''}
      </div>
    </div>""", unsafe_allow_html=True)

HR = "<hr style='border:none;border-top:1px solid var(--border);margin:6px 0 2px'>"


# ── 成功畫面 ──────────────────────────────────
if "submitted_rma" in st.session_state:
    master_id   = st.session_state.submitted_rma
    detail_ids  = st.session_state.submitted_detail_ids
    info        = st.session_state.submitted_info
    motors      = info.get("motors", [])

    st.markdown(f"""
    <div style="max-width:700px;margin:0 auto;padding:16px 0">
      <div class="rma-card">
        <div style="font-size:44px;margin-bottom:8px">✅</div>
        <div style="font-size:20px;font-weight:900;color:var(--navy);margin-bottom:6px">
          維修主單建立成功
        </div>
        <div class="rma-badge" style="font-size:20px;letter-spacing:2px">{master_id}</div>
        <div style="margin-top:12px;font-size:13px;color:var(--muted)">
          客戶：{info['company']} &nbsp;|&nbsp;
          共 {len(detail_ids)} 顆馬達 &nbsp;|&nbsp;
          優先等級：{info['priority']}
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    if motors:
        detail_df = pd.DataFrame({
            "子件編號":   detail_ids,
            "馬達序號 S/N": [m.get("motor_sn","")   for m in motors],
            "型號":       [m.get("model","")        for m in motors],
            "故障類別":   [m.get("fault_type","")   for m in motors],
        })
        st.dataframe(detail_df, use_container_width=True, hide_index=True,
                     height=min(400, 56 + len(detail_df)*38))

    st.markdown("<br>", unsafe_allow_html=True)
    c1c, c2c, c3c = st.columns([1, 1, 1])
    with c2c:
        if st.button("＋ 新增下一筆", use_container_width=True, type="primary"):
            for k in ["submitted_rma","submitted_detail_ids","submitted_info"]:
                st.session_state.pop(k, None)
            st.rerun()
    with c3c:
        if st.button("📋 前往狀態追蹤", use_container_width=True):
            for k in ["submitted_rma","submitted_detail_ids","submitted_info"]:
                st.session_state.pop(k, None)
            st.switch_page("pages/10_維修狀態追蹤.py")
    st.stop()


# ── 送修模式 ──────────────────────────────────
st.markdown("""
<div class="card">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--orange)"></span>
      送修模式
    </div>
  </div>
</div>""", unsafe_allow_html=True)

mode = st.radio(
    "送修模式",
    ["🔧 單顆馬達", "📦 批次多顆（2顆以上）"],
    horizontal=True,
    label_visibility="collapsed",
)
is_batch_mode = mode.startswith("📦")

# ── 表單主體 ──────────────────────────────────
with st.form("repair_form", clear_on_submit=False):

    # ① 客戶資訊
    section("1", "客戶資訊", "Customer Information")
    c1, c2, c3 = st.columns(3)
    with c1: company = st.text_input("客戶公司名稱 *", placeholder="例：台灣無人機科技股份有限公司")
    with c2: contact = st.text_input("聯絡人 *",       placeholder="姓名")
    with c3: phone   = st.text_input("聯絡電話",        placeholder="02-XXXX-XXXX")
    email = st.text_input("電子郵件（選填）", placeholder="example@company.com")
    st.markdown(HR, unsafe_allow_html=True)

    # ② 馬達資訊
    if not is_batch_mode:
        section("2", "馬達資訊", "Motor Information")
        c4, c5, c6 = st.columns(3)
        with c4: motor_sn = st.text_input("馬達序號 S/N *", placeholder="例：246503")
        with c5: model    = st.selectbox("產品型號 *", MOTOR_MODELS)
        with c6: qty      = st.number_input("送修數量（顆）", min_value=1, max_value=50, value=1)
        c7, c8 = st.columns([2, 1])
        with c7: flight_hours = st.number_input("飛行總時數（估計）", min_value=0, max_value=9999, value=0)
        with c8: crash        = st.radio("曾撞擊/墜機？", ["否", "是"], horizontal=True)
    else:
        section("2", "批次馬達資訊", "Batch Motor Information — 每顆一列")
        st.markdown("""
        <div style="background:#e8f4fd;border:1px solid #90caf9;border-radius:6px;
                    padding:10px 14px;margin-bottom:10px;font-size:12.5px;color:#1a2332">
          💡 <b>操作說明：</b>直接在下方表格填入每顆馬達的序號、型號及故障類別。
          按最後一列右側 <b>＋</b> 或拖曳最下角可新增列。
        </div>""", unsafe_allow_html=True)

        bd1, bd2, bd3 = st.columns(3)
        with bd1: default_model = st.selectbox("預設型號（批次套用）", MOTOR_MODELS, key="dm")
        with bd2: default_fault = st.selectbox("預設故障類別（批次套用）", FAULT_TYPES,  key="df")
        with bd3: crash         = st.radio("曾撞擊/墜機？", ["否", "是"], horizontal=True, key="bc")

        if "batch_motors" not in st.session_state:
            st.session_state.batch_motors = pd.DataFrame({
                "馬達序號 S/N *": [""] * 3,
                "產品型號":       [default_model] * 3,
                "故障類別":       [default_fault] * 3,
            })

        batch_df = st.data_editor(
            st.session_state.batch_motors,
            num_rows="dynamic",
            use_container_width=True,
            height=min(480, 56 + len(st.session_state.batch_motors) * 38 + 60),
            column_config={
                "馬達序號 S/N *": st.column_config.TextColumn("馬達序號 S/N *", width=160),
                "產品型號":       st.column_config.SelectboxColumn("產品型號", options=MOTOR_MODELS, width=200),
                "故障類別":       st.column_config.SelectboxColumn("故障類別", options=FAULT_TYPES, width=130),
            },
            hide_index=True,
            key="batch_editor",
        )
        flight_hours = 0
        motor_sn     = ""
        model        = default_model
        qty          = len(batch_df)

    st.markdown(HR, unsafe_allow_html=True)

    # ③ 故障資訊
    if not is_batch_mode:
        section("3", "故障資訊", "Fault Description")
        c9, c10 = st.columns(2)
        with c9:  fault_type  = st.selectbox("故障類別 *", FAULT_TYPES)
        with c10: repair_type = st.selectbox("維修需求 *", REPAIR_TYPES)
    else:
        section("3", "故障資訊（批次共用）", "Fault Description — Shared")
        c9, c10 = st.columns(2)
        with c9:  fault_type  = st.selectbox("主要故障類別", FAULT_TYPES)
        with c10: repair_type = st.selectbox("維修需求 *", REPAIR_TYPES)

    fault_desc = st.text_area(
        "故障詳細描述（選填）",
        placeholder="請描述故障情境、頻率、是否伴隨其他異狀…",
        height=76,
    )
    st.markdown(HR, unsafe_allow_html=True)

    # ④ 服務設定
    section("4", "服務設定", "Service Configuration")
    c11, c12 = st.columns(2)
    with c11: priority = st.selectbox("優先等級", PRIORITIES)
    with c12: note     = st.text_input("備註", placeholder="其他說明事項")
    st.markdown(HR, unsafe_allow_html=True)

    # ⑤ 故障照片
    section("5", "故障照片（選填）", "Fault Photos — max 8 files, 15 MB each")
    st.markdown("""
    <div style="font-size:12px;color:var(--muted);margin-bottom:6px">
      支援格式：JPG、PNG、WEBP &nbsp;·&nbsp; 最多 8 張 &nbsp;·&nbsp;
      照片將上傳至 Google Drive 並連結至此維修單
    </div>""", unsafe_allow_html=True)
    uploaded_photos = st.file_uploader(
        "上傳故障照片",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploaded_photos:
        prev_cols = st.columns(min(len(uploaded_photos), 4))
        for col, f in zip(prev_cols, uploaded_photos[:4]):
            with col:
                st.image(f, caption=f.name[:20], use_container_width=True)
        if len(uploaded_photos) > 4:
            st.caption(f"... 共 {len(uploaded_photos)} 張")

    st.markdown("<br>", unsafe_allow_html=True)
    cl, cm, cr = st.columns([1, 2, 1])
    with cm:
        label = "🚀　建立維修主單" if not is_batch_mode else "🚀　批次建立維修主單"
        submitted = st.form_submit_button(label, use_container_width=True, type="primary")


# ── 驗證 & 送出 ──────────────────────────────
if submitted:
    errors = []
    if not company.strip(): errors.append("請填入「客戶公司名稱」")
    if not contact.strip(): errors.append("請填入「聯絡人」")

    pri_code = priority.split(" ")[0]
    shared = dict(
        company=company.strip(), contact=contact.strip(),
        phone=phone.strip(), email=email.strip(),
        fault_type=fault_type, repair_type=repair_type,
        fault_desc=fault_desc.strip(), crash=crash,
        flight_hours=flight_hours, priority=pri_code,
        note=note.strip(),
    )

    if not is_batch_mode:
        if not motor_sn.strip(): errors.append("請填入「馬達序號 S/N」")
        for e in errors: st.error(f"⚠️  {e}")
        if errors: st.stop()

        motors_list = [{"motor_sn": motor_sn.strip(), "model": model,
                        "fault_type": fault_type}]
        master_data = {**shared, "qty": 1}

        with st.spinner("寫入 Google Sheet 中..."):
            try:
                master_id  = append_master(master_data)
                detail_ids = [append_detail(master_id, 1, {**shared,
                                "motor_sn": motor_sn.strip(), "model": model})]
                notify_new_rma(master_id, {**shared,
                    "motor_sn": motor_sn.strip(), "model": model})
            except Exception as ex:
                st.error(f"❌ 寫入失敗：{ex}")
                st.stop()

        if uploaded_photos:
            with st.spinner(f"上傳 {len(uploaded_photos)} 張照片到 Google Drive..."):
                photo_urls = upload_photos(uploaded_photos, master_id)
                if photo_urls:
                    update_detail_photos(detail_ids[0], photo_urls)

    else:
        valid_motors = []
        for _, row in batch_df.iterrows():
            sn = str(row.get("馬達序號 S/N *", "") or "").strip()
            if sn:
                valid_motors.append({
                    "motor_sn":   sn,
                    "model":      str(row.get("產品型號", model) or model),
                    "fault_type": str(row.get("故障類別", fault_type) or fault_type),
                })

        if not valid_motors:
            errors.append("批次表格中請至少填入一顆馬達序號 S/N")
        for e in errors: st.error(f"⚠️  {e}")
        if errors: st.stop()

        master_data = {**shared, "qty": len(valid_motors)}

        with st.spinner(f"批次建立主單 + {len(valid_motors)} 筆子件中..."):
            try:
                master_id  = append_master(master_data)
                detail_ids = append_batch_details(master_id, shared, valid_motors)
                notify_new_rma(
                    f"{master_id}（{len(detail_ids)} 顆馬達）",
                    {**shared, "motor_sn": f"批次 {len(detail_ids)} 顆",
                     "model": valid_motors[0]["model"],
                     "fault_type": fault_type},
                )
            except Exception as ex:
                st.error(f"❌ 批次寫入失敗：{ex}")
                st.stop()

        if uploaded_photos:
            with st.spinner("上傳照片到 Google Drive..."):
                photo_urls = upload_photos(uploaded_photos, master_id)
                if photo_urls:
                    for did in detail_ids:
                        update_detail_photos(did, photo_urls)

        motors_list = valid_motors
        if "batch_motors" in st.session_state:
            del st.session_state["batch_motors"]

    st.session_state["submitted_rma"]        = master_id
    st.session_state["submitted_detail_ids"] = detail_ids
    st.session_state["submitted_info"] = {
        **shared, "motors": motors_list,
    }
    st.rerun()
