"""
REXONTEC 力科品質指揮平台 — 維修保養系統
維修狀態追蹤
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.rma_gsheet       import load_all_cases, update_status, get_photos, delete_case
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
