"""
REXONTEC 力科品質指揮平台 — 維修保養系統
維修狀態追蹤
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.rma_gsheet       import load_all_cases, update_status, get_photos, delete_case, update_detection
from utils.style             import QMS_CSS, topbar, page_header, stat_cards, status_badge, STATUS_EMOJI, gsheet_error_banner
from utils.rma_email_notify  import notify_case_closed

st.set_page_config(
    page_title="REXONTEC 力科 | 狀態追蹤",
    page_icon="📋",
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

st.markdown(page_header("維修狀態追蹤", "Repair Status Tracking", "TRK"), unsafe_allow_html=True)

STATUS_LIST   = ["待收件","已收件","初診中","等待零件","維修中","待QC","已出廠","報廢通知","已取消"]
DONE_STATUS   = {"已出廠","報廢通知","已取消"}
PRIORITY_DAYS = {"P1":2,"P2":5,"P3":7,"P4":14}


def calc_overdue(row) -> int:
    if row.get("維修狀態") in DONE_STATUS: return 0
    recv = row.get("收件日期","")
    pri  = str(row.get("優先等級","P3"))[:2]
    days = PRIORITY_DAYS.get(pri, 7)
    try:
        dt  = datetime.strptime(str(recv)[:16], "%Y/%m/%d %H:%M")
        due = dt + timedelta(days=days)
        return (datetime.now() - due).days
    except Exception:
        return 0


@st.cache_data(ttl=30, show_spinner="載入案件資料...")
def get_data():
    return load_all_cases()


col_r1, col_r2 = st.columns([8, 1])
with col_r2:
    if st.button("🔄 重新整理", use_container_width=True):
        st.cache_data.clear(); st.rerun()

try:
    df = get_data()
except Exception as _e:
    gsheet_error_banner(_e)
if df.empty:
    st.info("目前沒有任何維修案件，請先到「維修案件輸入」頁面新增案件。")
    st.stop()

df["逾期天數"] = df.apply(calc_overdue, axis=1)

# ── KPI 統計卡 ────────────────────────────────
total      = len(df)
active     = df[~df["維修狀態"].isin(DONE_STATUS)]
done       = df[df["維修狀態"] == "已出廠"]
pending_qc = df[df["維修狀態"] == "待QC"]
overdue    = active[active["逾期天數"] > 0]

st.markdown(stat_cards([
    {"label":"總案件數",  "value": total,           "sub":"全部工單"},
    {"label":"進行中",    "value": len(active),      "sub":"尚未出廠",  "cls":"sc-orange","vcls":"v-orange"},
    {"label":"已完成",    "value": len(done),        "sub":"已出廠",    "cls":"sc-green", "vcls":"v-green"},
    {"label":"待 QC",     "value": len(pending_qc),  "sub":"等待檢驗",  "cls":"sc-purple","vcls":"v-purple"},
    {"label":"⚠️ 逾期",  "value": len(overdue),     "sub":"需立即處理","cls":"sc-red",   "vcls":"v-red"},
]), unsafe_allow_html=True)

# ── 篩選列 ────────────────────────────────────
st.markdown("""
<div class="card">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--blue2)"></span>
      篩選條件
    </div>
  </div>
</div>""", unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns([2.5, 2, 2, 1])
with f1: kw            = st.text_input("🔍 搜尋", placeholder="RMA編號 / 序號 / 客戶公司", label_visibility="collapsed")
with f2: status_filter = st.multiselect("狀態", STATUS_LIST, placeholder="全部狀態")
with f3:
    model_opts   = ["全部型號"] + sorted(df["產品型號"].dropna().unique().tolist())
    model_filter = st.selectbox("型號", model_opts, label_visibility="collapsed")
with f4: overdue_only  = st.checkbox("僅顯示逾期", value=False)

view = df.copy()
if kw:
    mask = (
        view["RMA編號"].astype(str).str.contains(kw, case=False, na=False) |
        view["馬達序號"].astype(str).str.contains(kw, case=False, na=False) |
        view["客戶公司"].astype(str).str.contains(kw, case=False, na=False)
    )
    view = view[mask]
if status_filter:                  view = view[view["維修狀態"].isin(status_filter)]
if model_filter != "全部型號":     view = view[view["產品型號"] == model_filter]
if overdue_only:                   view = view[view["逾期天數"] > 0]

# ── 案件清單 ──────────────────────────────────
st.markdown(f"""
<div class="card" style="margin-top:4px">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--accent)"></span>
      案件清單
    </div>
    <span style="font-size:11px;color:var(--muted)">共 {len(view)} 筆</span>
  </div>
</div>""", unsafe_allow_html=True)

if view.empty:
    st.warning("沒有符合條件的案件。")
else:
    show_cols = ["RMA編號","馬達序號","產品型號","故障類別","客戶公司","收件日期","維修狀態","優先等級","逾期天數"]
    show_cols = [c for c in show_cols if c in view.columns]
    disp = view[show_cols].copy()

    disp["逾期天數"] = disp["逾期天數"].apply(
        lambda v: f"🔴 {v}天" if v > 0 else ("—" if v == 0 else f"⏰ 剩{abs(v)}天")
    )
    disp["維修狀態"] = disp["維修狀態"].apply(
        lambda s: f"{STATUS_EMOJI.get(s,'')} {s}" if pd.notna(s) else s
    )

    st.dataframe(
        disp,
        use_container_width=True,
        height=min(420, 56 + len(disp) * 38),
        column_config={
            "RMA編號":  st.column_config.TextColumn("RMA 編號",  width=150),
            "馬達序號": st.column_config.TextColumn("S/N",       width=100),
            "產品型號": st.column_config.TextColumn("型號",       width=160),
            "故障類別": st.column_config.TextColumn("故障",       width=100),
            "客戶公司": st.column_config.TextColumn("客戶",       width=130),
            "收件日期": st.column_config.TextColumn("收件日期",   width=140),
            "維修狀態": st.column_config.TextColumn("狀態",       width=130),
            "優先等級": st.column_config.TextColumn("優先",       width=70),
            "逾期天數": st.column_config.TextColumn("逾期",       width=110),
        },
        hide_index=True,
    )

# ── 狀態更新 ──────────────────────────────────
st.markdown("""
<div class="card" style="margin-top:8px">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--orange)"></span>
      更新維修狀態
    </div>
  </div>
</div>""", unsafe_allow_html=True)

rma_list = df["RMA編號"].dropna().tolist()

with st.form("update_form"):
    ua, ub = st.columns(2)
    with ua:
        sel_rma = st.selectbox("選擇 RMA 案件", rma_list)
    with ub:
        cur_row    = df[df["RMA編號"] == sel_rma]
        cur_status = cur_row["維修狀態"].values[0] if not cur_row.empty else "待收件"
        cur_idx    = STATUS_LIST.index(cur_status) if cur_status in STATUS_LIST else 0
        new_status = st.selectbox(
            f"新狀態　（目前：{STATUS_EMOJI.get(cur_status,'')} {cur_status}）",
            STATUS_LIST, index=cur_idx
        )

    tech_note = st.text_area(
        "技術備註（選填）", placeholder="例：更換定子線圈，空載電流恢復正常…", height=76
    )

    if not cur_row.empty:
        r = cur_row.iloc[0]
        st.markdown(
            f'<div style="font-size:11.5px;color:var(--muted);padding:4px 0">'
            f'型號：{r.get("產品型號","")} &nbsp;|&nbsp; S/N：{r.get("馬達序號","")} &nbsp;|&nbsp; '
            f'故障：{r.get("故障類別","")} &nbsp;|&nbsp; 客戶：{r.get("客戶公司","")} &nbsp;|&nbsp; '
            f'收件：{str(r.get("收件日期",""))[:16]}</div>',
            unsafe_allow_html=True
        )

    submitted_u = st.form_submit_button("💾　儲存狀態", type="primary")

if submitted_u:
    if new_status == cur_status and not tech_note:
        st.warning("狀態未變更，也沒有填入備註。")
    else:
        with st.spinner("更新中..."):
            ok = update_status(sel_rma, new_status, tech_note)
        if ok:
            st.success(f"✅ {sel_rma} 已更新為：{STATUS_EMOJI.get(new_status,'')} **{new_status}**")
            if new_status in {"已出廠", "報廢通知"} and not cur_row.empty:
                info = cur_row.iloc[0].to_dict()
                sent = notify_case_closed(sel_rma, new_status, info)
                if sent:
                    st.toast("📧 業務通知已寄出", icon="✅")
            st.cache_data.clear(); st.rerun()
        else:
            st.error(f"❌ 找不到 {sel_rma}，請重新整理後再試。")

# ── 🔧 五步技術檢測區塊 ──────────────────────────────
st.markdown("""
<div class="card" style="margin-top:8px">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--teal)"></span>
      🔧 技術檢測（五步檢測法）
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ── 輔助函式 ──
def _coil_abnormal(ab, bc, ca):
    vals = [v for v in [ab, bc, ca] if v > 0]
    if len(vals) < 2:
        return False, 0.0
    avg = sum(vals) / len(vals)
    if avg == 0:
        return False, 0.0
    max_dev = max(abs(v - avg) / avg for v in vals) * 100
    return max_dev > 10.0, max_dev

WARRANTY_OPTIONS = [
    "", "保固內", "保固外 / 人為撞擊", "保固外 / 人為損壞",
    "保固外 / 超時", "可能製程問題（保固內）", "待定",
]

det_rma = st.selectbox(
    "選擇 RMA 案件（技術檢測）", rma_list,
    key="det_rma_sel", label_visibility="collapsed",
)
det_df = df[df["RMA編號"] == det_rma]

if not det_df.empty:
    dr = det_df.iloc[0].to_dict()

    def _b(k):   return str(dr.get(k, "否")).strip() == "是"
    def _f(k):
        try:     return float(dr.get(k, 0) or 0)
        except:  return 0.0
    def _s(k):   return str(dr.get(k, "") or "")

    # 案件資訊列
    st.markdown(
        f'<div style="font-size:11.5px;color:var(--muted);padding:4px 0 8px">'
        f'型號：<b>{dr.get("產品型號","")}</b> &nbsp;|&nbsp; '
        f'S/N：<b>{dr.get("馬達序號","")}</b> &nbsp;|&nbsp; '
        f'客戶：{dr.get("客戶公司","")} &nbsp;|&nbsp; '
        f'狀態：{STATUS_EMOJI.get(str(dr.get("維修狀態","")),"")} {dr.get("維修狀態","")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 維修病歷 ──
    motor_sn = str(dr.get("馬達序號", "")).strip()
    if motor_sn:
        hist = df[df["馬達序號"].astype(str).str.strip() == motor_sn].sort_values(
            "收件日期", ascending=False
        )
        if len(hist) > 1:
            with st.expander(
                f"⚠️ 維修病歷：S/N [{motor_sn}] 共 {len(hist)} 次送修（含本次）",
                expanded=True,
            ):
                h_cols = ["RMA編號", "收件日期", "故障類別", "保固判定", "維修方式", "最終判定", "維修狀態"]
                h_cols = [c for c in h_cols if c in hist.columns]
                st.dataframe(
                    hist[h_cols].reset_index(drop=True),
                    use_container_width=True, hide_index=True,
                )

    # ───────────── Step 1 外觀檢測 ─────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid #1a9b7a;padding-left:10px;margin:12px 0 6px">'
        'Step 1 🔬 外觀檢測</div>',
        unsafe_allow_html=True,
    )
    c1a, c1b, c1c, c1d = st.columns(4)
    with c1a: s1_shell = st.checkbox("外殼撞傷", value=_b("S1-外殼撞傷"), key=f"s1sh_{det_rma}")
    with c1b: s1_axis  = st.checkbox("軸心歪斜", value=_b("S1-軸心歪斜"), key=f"s1ax_{det_rma}")
    with c1c: s1_sand  = st.checkbox("沙土侵入", value=_b("S1-沙土侵入"), key=f"s1sd_{det_rma}")
    with c1d: s1_screw = st.checkbox("螺絲裂痕", value=_b("S1-螺絲裂痕"), key=f"s1sc_{det_rma}")

    # ───────────── Step 2 手感測試 ─────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid #1a9b7a;padding-left:10px;margin:12px 0 6px">'
        'Step 2 🤚 手感測試</div>',
        unsafe_allow_html=True,
    )
    c2a, c2b, c2c, _ = st.columns(4)
    with c2a: s2_noise   = st.checkbox("異音",     value=_b("S2-異音"),     key=f"s2no_{det_rma}")
    with c2b: s2_stuck   = st.checkbox("卡頓",     value=_b("S2-卡頓"),     key=f"s2st_{det_rma}")
    with c2c: s2_bearing = st.checkbox("軸承鬆動", value=_b("S2-軸承鬆動"), key=f"s2be_{det_rma}")

    # ───────────── Step 3 電氣測試 ─────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid #1a9b7a;padding-left:10px;margin:12px 0 6px">'
        'Step 3 ⚡ 電氣測試（三用電表）</div>',
        unsafe_allow_html=True,
    )
    c3a, c3b, c3c = st.columns(3)
    with c3a: s3_ab = st.number_input("AB 阻值 (Ω)", value=_f("S3-AB阻值"), min_value=0.0, step=0.1, format="%.2f", key=f"s3ab_{det_rma}")
    with c3b: s3_bc = st.number_input("BC 阻值 (Ω)", value=_f("S3-BC阻值"), min_value=0.0, step=0.1, format="%.2f", key=f"s3bc_{det_rma}")
    with c3c: s3_ca = st.number_input("CA 阻值 (Ω)", value=_f("S3-CA阻值"), min_value=0.0, step=0.1, format="%.2f", key=f"s3ca_{det_rma}")

    coil_bad, coil_dev = _coil_abnormal(s3_ab, s3_bc, s3_ca)
    if s3_ab > 0 or s3_bc > 0 or s3_ca > 0:
        if coil_bad:
            st.error(f"⚠️ 線圈異常：三組阻值最大差異 **{coil_dev:.1f}%**（超過 10% 閾值），請確認線圈狀態")
        else:
            st.success(f"✅ 阻值均衡：差異 {coil_dev:.1f}%（< 10%），正常")

    # ───────────── Step 4 通電測試 ─────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid #1a9b7a;padding-left:10px;margin:12px 0 6px">'
        'Step 4 🔌 通電測試</div>',
        unsafe_allow_html=True,
    )
    c4a, c4b, c4c, _ = st.columns(4)
    with c4a: s4_vib   = st.checkbox("高震動",   value=_b("S4-高震動"),   key=f"s4vb_{det_rma}")
    with c4b: s4_heat  = st.checkbox("高溫",     value=_b("S4-高溫"),     key=f"s4ht_{det_rma}")
    with c4c: s4_start = st.checkbox("無法啟動", value=_b("S4-無法啟動"), key=f"s4st_{det_rma}")

    # ───────────── Step 5 拆解分析 ─────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid #1a9b7a;padding-left:10px;margin:12px 0 6px">'
        'Step 5 🔩 拆解分析</div>',
        unsafe_allow_html=True,
    )
    c5a, c5b, c5c, _ = st.columns(4)
    with c5a: s5_coil   = st.checkbox("線圈燒毀", value=_b("S5-線圈燒毀"), key=f"s5co_{det_rma}")
    with c5b: s5_magnet = st.checkbox("磁鐵脫落", value=_b("S5-磁鐵脫落"), key=f"s5mg_{det_rma}")
    with c5c: s5_rust   = st.checkbox("生鏽",     value=_b("S5-生鏽"),     key=f"s5rs_{det_rma}")

    # ── 自動判定橫幅 ──
    auto_msgs = []
    if s1_shell and s1_axis:
        auto_msgs.append(("保固外 / 人為撞擊", "#fff3f3", "#ffd0d0", "var(--cr)"))
    if s5_magnet:
        auto_msgs.append(("可能製程問題（建議保固內）", "#e8f8f5", "#a9dfbf", "var(--teal)"))
    if coil_bad:
        auto_msgs.append(("線圈異常 — 建議確認過載/堵轉紀錄", "#fef9e7", "#f9e79f", "var(--warn)"))

    if auto_msgs:
        st.markdown('<div style="margin:8px 0">', unsafe_allow_html=True)
        for msg, bg, bd, tc in auto_msgs:
            st.markdown(
                f'<div style="background:{bg};border:1px solid {bd};border-radius:6px;'
                f'padding:9px 14px;font-size:12.5px;color:{tc};font-weight:700;margin-bottom:6px">'
                f'🤖 系統自動判定：{msg}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 最終結果 ──
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:var(--navy);'
        'border-left:4px solid var(--accent);padding-left:10px;margin:12px 0 6px">'
        '📋 最終結果</div>',
        unsafe_allow_html=True,
    )
    fr1, fr2 = st.columns(2)
    with fr1:
        final_verdict = st.text_input(
            "最終判定", value=_s("最終判定"),
            placeholder="例：軸承磨損、線圈燒毀…", key=f"fv_{det_rma}",
        )
        saved_w = _s("保固判定")
        w_idx   = WARRANTY_OPTIONS.index(saved_w) if saved_w in WARRANTY_OPTIONS else 0
        warranty_judg = st.selectbox(
            "保固判定", WARRANTY_OPTIONS, index=w_idx, key=f"wj_{det_rma}",
        )
    with fr2:
        repair_method = st.text_area(
            "維修方式", value=_s("維修方式"),
            placeholder="例：更換軸承、重繞線圈…", height=80, key=f"rm_{det_rma}",
        )
        is_scrap = st.checkbox("是否報廢", value=_b("是否報廢"), key=f"scrap_{det_rma}")

    # ── 儲存 & PDF ──
    sv_col, pdf_col, _ = st.columns([2, 2, 3])
    with sv_col:
        save_det = st.button("💾 儲存檢測結果", type="primary",
                             use_container_width=True, key="save_det_btn")
    with pdf_col:
        gen_pdf  = st.button("📄 產生維修報告", use_container_width=True, key="gen_pdf_btn")

    if save_det:
        now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
        det_data = {
            "S1-外殼撞傷": "是" if s1_shell else "否",
            "S1-軸心歪斜": "是" if s1_axis  else "否",
            "S1-沙土侵入": "是" if s1_sand  else "否",
            "S1-螺絲裂痕": "是" if s1_screw else "否",
            "S2-異音":     "是" if s2_noise   else "否",
            "S2-卡頓":     "是" if s2_stuck   else "否",
            "S2-軸承鬆動": "是" if s2_bearing else "否",
            "S3-AB阻值":   round(s3_ab, 3),
            "S3-BC阻值":   round(s3_bc, 3),
            "S3-CA阻值":   round(s3_ca, 3),
            "S3-線圈異常": "是" if coil_bad else "否",
            "S4-高震動":   "是" if s4_vib   else "否",
            "S4-高溫":     "是" if s4_heat  else "否",
            "S4-無法啟動": "是" if s4_start else "否",
            "S5-線圈燒毀": "是" if s5_coil   else "否",
            "S5-磁鐵脫落": "是" if s5_magnet else "否",
            "S5-生鏽":     "是" if s5_rust   else "否",
            "最終判定": final_verdict,
            "保固判定": warranty_judg,
            "維修方式": repair_method,
            "是否報廢": "是" if is_scrap else "否",
            "五步檢測時間": now_str,
        }
        with st.spinner("儲存中..."):
            ok = update_detection(det_rma, det_data)
        if ok:
            st.success(f"✅ {det_rma} 五步檢測結果已儲存")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("❌ 儲存失敗，請重新整理後再試")

    if gen_pdf:
        try:
            from utils.rma_pdf_report import generate_repair_pdf
            latest = load_all_cases()
            r_pdf  = latest[latest["RMA編號"] == det_rma]
            if r_pdf.empty:
                st.error("找不到案件資料，請先儲存後再產生報告")
            else:
                with st.spinner("產生 PDF 中，請稍候..."):
                    pdf_bytes = generate_repair_pdf(r_pdf.iloc[0].to_dict())
                fname = f"維修報告_{det_rma}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.success("✅ PDF 已產生！")
                st.download_button(
                    label=f"⬇️ 下載 {fname}",
                    data=pdf_bytes, file_name=fname,
                    mime="application/pdf", use_container_width=True,
                    key="dl_pdf_btn",
                )
        except Exception as _ex:
            st.error(f"❌ PDF 產生失敗：{_ex}")

# ── 故障照片查看 ──────────────────────────────
st.markdown("""
<div class="card" style="margin-top:8px">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--blue2)"></span>
      故障照片查看
    </div>
  </div>
</div>""", unsafe_allow_html=True)

photo_rma = st.selectbox("選擇 RMA 查看照片", ["— 選擇案件 —"] + rma_list,
                          label_visibility="collapsed", key="photo_sel")
if photo_rma and photo_rma != "— 選擇案件 —":
    with st.spinner("載入照片..."):
        urls = get_photos(photo_rma)
    if urls:
        st.markdown(f'<div style="font-size:12px;color:var(--muted);margin-bottom:8px">共 {len(urls)} 張照片</div>',
                    unsafe_allow_html=True)
        img_cols = st.columns(min(len(urls), 4))
        for col, url in zip(img_cols, urls):
            with col:
                try:
                    st.image(url, use_container_width=True)
                except Exception:
                    st.markdown(f'<a href="{url}" target="_blank">📷 查看照片</a>',
                                unsafe_allow_html=True)
        if len(urls) > 4:
            for url in urls[4:]:
                st.markdown(f'<a href="{url}" target="_blank" style="font-size:12px">📷 {url}</a>',
                            unsafe_allow_html=True)
    else:
        st.info("此案件尚未上傳故障照片。")

# ── 刪除維修單 ────────────────────────────────
st.markdown("""
<div class="card" style="margin-top:8px;border-left:4px solid var(--cr)">
  <div class="card-header" style="background:#fff8f7">
    <div class="card-title" style="color:var(--cr)">
      <span class="card-dot" style="background:var(--cr)"></span>
      刪除 / 取消維修單
    </div>
  </div>
</div>""", unsafe_allow_html=True)

with st.expander("⚠️ 展開刪除功能（請謹慎操作）", expanded=False):
    del_col1, del_col2 = st.columns([3, 2])
    with del_col1:
        active_rma  = df[df["維修狀態"] != "已取消"]["RMA編號"].dropna().tolist()
        sel_del_rma = st.selectbox("選擇要刪除的 RMA 案件",
                                    ["— 請選擇 —"] + active_rma, key="del_rma_sel")
    with del_col2:
        del_mode = st.radio("刪除模式",
                            ["✅ 軟刪除（標記已取消，保留紀錄）", "🗑️ 硬刪除（永久移除，無法還原）"],
                            key="del_mode")

    if sel_del_rma and sel_del_rma != "— 請選擇 —":
        target_row = df[df["RMA編號"] == sel_del_rma]
        if not target_row.empty:
            r = target_row.iloc[0]
            st.markdown(
                f'<div style="background:#fff3f3;border:1px solid #ffd0d0;border-radius:6px;'
                f'padding:10px 14px;font-size:12px;color:#555;margin:6px 0">'
                f'<b>{sel_del_rma}</b> &nbsp;|&nbsp; 型號：{r.get("產品型號","")} '
                f'&nbsp;|&nbsp; S/N：{r.get("馬達序號","")} '
                f'&nbsp;|&nbsp; 客戶：{r.get("客戶公司","")} '
                f'&nbsp;|&nbsp; 目前狀態：{r.get("維修狀態","")}</div>',
                unsafe_allow_html=True
            )

        is_hard   = "硬刪除" in del_mode
        warn_text = "永久從 Google Sheet 移除，**無法還原**！" if is_hard else "狀態將標記為「已取消」，資料保留不刪除。"
        confirm_del = st.checkbox(
            f"我確認要{'硬刪除（永久移除）' if is_hard else '取消'} **{sel_del_rma}**，{warn_text}",
            key="del_confirm"
        )

        if is_hard:
            confirm_text = st.text_input(
                f"請輸入 RMA 編號「{sel_del_rma}」以確認硬刪除",
                key="del_hard_confirm", placeholder="輸入 RMA 編號以解鎖"
            )
            hard_ok = (confirm_text.strip() == sel_del_rma)
        else:
            hard_ok = True

        del_btn = st.button(
            f"{'🗑️ 永久刪除' if is_hard else '✅ 標記取消'} {sel_del_rma}",
            type="primary", disabled=not (confirm_del and hard_ok), key="del_btn"
        )

        if del_btn:
            with st.spinner("執行刪除中..."):
                ok = delete_case(sel_del_rma, hard=is_hard)
            if ok:
                action_label = "已永久刪除" if is_hard else "已標記為「已取消」"
                st.success(f"✅ {sel_del_rma} {action_label}")
                st.cache_data.clear(); st.rerun()
            else:
                st.error(f"❌ 找不到 {sel_del_rma}，請重新整理後再試。")

# ── 逾期警示 ──────────────────────────────────
overdue_df = df[~df["維修狀態"].isin(DONE_STATUS) & (df["逾期天數"] > 0)]
if not overdue_df.empty:
    st.markdown(f"""
    <div class="card" style="margin-top:8px;border-left:4px solid var(--cr)">
      <div class="card-header" style="background:#fff8f7">
        <div class="card-title" style="color:var(--cr)">
          <span class="card-dot" style="background:var(--cr)"></span>
          ⚠️ 逾期案件警示（{len(overdue_df)} 件）
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    warn_cols = ["RMA編號","馬達序號","產品型號","客戶公司","維修狀態","優先等級","逾期天數"]
    warn_cols = [c for c in warn_cols if c in overdue_df.columns]
    w = overdue_df[warn_cols].copy()
    w["逾期天數"] = w["逾期天數"].apply(lambda v: f"🔴 {v} 天")
    st.dataframe(w, use_container_width=True, hide_index=True)
