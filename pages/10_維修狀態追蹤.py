"""
REXONTEC 力科品質指揮平台 — 維修保養系統
維修狀態追蹤（主單 + 子件架構）
"""
import streamlit as st
import pandas as pd
import re
import urllib.request
from datetime import datetime, timedelta
from utils.rma_master_gsheet  import (load_all_masters, update_master_status,
                                       sync_master_status, delete_master,
                                       MASTER_DONE_STATUS)
from utils.rma_detail_gsheet  import (load_all_details, load_details_by_master,
                                       update_detail_status, update_detail_detection,
                                       update_detail_photos, get_detail_photos,
                                       delete_detail, batch_update_details,
                                       multi_update_details)
from utils.rma_detection_db   import get_step_custom_items
from utils.style               import (QMS_CSS, topbar, page_header, stat_cards,
                                        status_badge, STATUS_EMOJI, gsheet_error_banner)
from utils.rma_email_notify    import notify_case_closed

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

st.markdown(page_header("維修狀態追蹤", "Repair Status Tracking", "TRK"), unsafe_allow_html=True)


# ── 常數 ─────────────────────────────────────
FAULT_TYPES = [
    "運轉異音", "過熱", "轉速不穩", "完全不轉",
    "震動異常", "電流異常", "外殼損傷", "線材問題",
    "重落地損傷", "摔落檢測", "試轉卡頓", "上電燒毀", "異物",
    "其他",
]
REPAIR_TYPES = [
    "摔落損傷", "飛機迫降", "試飛摔落", "試轉卡頓",
    "無載運轉異常", "飛測摔落", "飛測墜毀",
    "上電燒毀", "試轉異常", "重落地損傷",
]
STATUS_LIST = ["待收件","已收件","初診中","待檢測","待零件","維修中","待QC","已完成","已出廠","已取消"]
DONE_STATUS = {"已完成","已出廠","已取消"}
TECH_JUDGMENT_LIST = [
    "", "檢測正常", "可維修", "保固內", "保固外", "人為撞擊",
    "軸承損壞", "線圈燒毀", "磁鐵脫落", "待拆解分析",
    "無法維修", "建議報廢", "已報廢",
]
WARRANTY_OPTIONS = [
    "", "保固內", "保固外 / 人為撞擊", "保固外 / 人為損壞",
    "保固外 / 超時", "可能製程問題（保固內）", "待定",
]
PRIORITY_DAYS = {"P1": 2, "P2": 5, "P3": 7, "P4": 14}
PRIORITY_COLOR = {"P1": "var(--cr)", "P2": "var(--warn)", "P3": "var(--accent)", "P4": "var(--muted)"}


def _gdrive_bytes(url: str):
    try:
        m = re.search(r'[?&]id=([A-Za-z0-9_\-]+)', url)
        if not m:
            m = re.search(r'/d/([A-Za-z0-9_\-]+)', url)
        if not m:
            return None
        fid = m.group(1)
        req = urllib.request.Request(
            f"https://drive.google.com/thumbnail?id={fid}&sz=w1200",
            headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=10).read()
        return data if len(data) > 512 else None
    except Exception:
        return None


def calc_overdue(recv: str, pri: str) -> int:
    days = PRIORITY_DAYS.get(str(pri)[:2], 7)
    try:
        dt = datetime.strptime(str(recv)[:16], "%Y/%m/%d %H:%M")
        return (datetime.now() - dt - timedelta(days=days)).days
    except Exception:
        return 0


# ── 資料載入 ─────────────────────────────────
@st.cache_data(ttl=30, show_spinner="載入主單資料...")
def get_masters():
    return load_all_masters()

@st.cache_data(ttl=30, show_spinner="載入子件資料...")
def get_details():
    return load_all_details()


col_r1, col_r2 = st.columns([8, 1])
with col_r2:
    if st.button("🔄 重新整理", use_container_width=True):
        st.cache_data.clear(); st.rerun()

try:
    masters_df = get_masters()
    details_df = get_details()
except Exception as _e:
    # 429 Rate Limit → 等 3 秒後自動重試一次
    import time
    _code = getattr(getattr(_e, "response", None), "status_code", None)
    if _code == 429:
        time.sleep(3)
        try:
            st.cache_data.clear()
            masters_df = get_masters()
            details_df = get_details()
        except Exception as _e2:
            gsheet_error_banner(_e2)
    else:
        gsheet_error_banner(_e)

if masters_df.empty:
    st.info("目前沒有任何維修主單，請先到「維修輸入」頁面建立主單。")
    st.stop()


# ── KPI 卡 ───────────────────────────────────
total_m  = len(masters_df)
active_m = masters_df[~masters_df["整體狀態"].isin(DONE_STATUS)]
done_m   = masters_df[masters_df["整體狀態"].isin({"已完成","已出廠"})]
total_d  = len(details_df) if not details_df.empty else 0
done_d   = len(details_df[details_df["維修狀態"].isin({"已完成","已出廠"})]) if not details_df.empty else 0

st.markdown(stat_cards([
    {"label":"維修主單",   "value": total_m,       "sub":"全部批次"},
    {"label":"進行中",     "value": len(active_m), "sub":"未完成主單", "cls":"sc-orange","vcls":"v-orange"},
    {"label":"已出廠",     "value": len(done_m),   "sub":"完成主單",   "cls":"sc-green","vcls":"v-green"},
    {"label":"馬達總件數", "value": total_d,        "sub":"所有子件"},
    {"label":"子件完成",   "value": done_d,         "sub":"已完成/出廠","cls":"sc-purple","vcls":"v-purple"},
]), unsafe_allow_html=True)


# ── 主單篩選 ─────────────────────────────────
st.markdown("""
<div class="card"><div class="card-header"><div class="card-title">
  <span class="card-dot" style="background:var(--blue2)"></span>篩選主單
</div></div></div>""", unsafe_allow_html=True)

fa, fb, fc, fd = st.columns([3, 2, 2, 1])
with fa: kw_m = st.text_input("🔍 搜尋", placeholder="主單編號 / 客戶公司 / 聯絡人",
                               label_visibility="collapsed")
with fb: sta_f = st.multiselect("狀態", STATUS_LIST, placeholder="全部狀態")
with fc:
    cust_opts = ["全部客戶"] + sorted(masters_df["客戶公司"].dropna().unique().tolist())
    cust_f = st.selectbox("客戶", cust_opts, label_visibility="collapsed")
with fd: active_only = st.checkbox("僅進行中", value=False)

view_m = masters_df.copy()
if kw_m:
    msk = (
        view_m["主單編號"].astype(str).str.contains(kw_m, case=False, na=False) |
        view_m["客戶公司"].astype(str).str.contains(kw_m, case=False, na=False) |
        view_m["聯絡人"].astype(str).str.contains(kw_m, case=False, na=False)
    )
    view_m = view_m[msk]
if sta_f:              view_m = view_m[view_m["整體狀態"].isin(sta_f)]
if cust_f != "全部客戶": view_m = view_m[view_m["客戶公司"] == cust_f]
if active_only:        view_m = view_m[~view_m["整體狀態"].isin(DONE_STATUS)]


# ── 主單列表 ─────────────────────────────────
st.markdown(f"""
<div class="card" style="margin-top:4px"><div class="card-header">
  <div class="card-title">
    <span class="card-dot" style="background:var(--accent)"></span>維修主單列表
  </div>
  <span style="font-size:11px;color:var(--muted)">共 {len(view_m)} 筆</span>
</div></div>""", unsafe_allow_html=True)

if view_m.empty:
    st.warning("沒有符合條件的主單。")
else:
    # 組裝顯示用 DataFrame（加入進度欄）
    disp_rows = []
    for _, mr in view_m.iterrows():
        mid   = mr.get("主單編號","")
        sub   = details_df[details_df["主單編號"] == mid] if not details_df.empty and "主單編號" in details_df.columns else pd.DataFrame()
        total = len(sub)
        done  = len(sub[sub["維修狀態"].isin({"已完成","已出廠"})]) if total > 0 else 0
        prog  = f"{done}/{total}" if total > 0 else "0/0"
        disp_rows.append({
            "主單編號": mid,
            "客戶公司": mr.get("客戶公司",""),
            "退修數量": f"{mr.get('退修數量',0)} 顆",
            "進度":     prog,
            "整體狀態": f"{STATUS_EMOJI.get(str(mr.get('整體狀態','')),'')} {mr.get('整體狀態','')}",
            "優先等級": mr.get("優先等級",""),
            "收件日期": str(mr.get("收件日期",""))[:16],
        })
    disp_df = pd.DataFrame(disp_rows)
    st.dataframe(
        disp_df,
        use_container_width=True,
        height=min(400, 56 + len(disp_df)*38),
        column_config={
            "主單編號": st.column_config.TextColumn("主單編號",  width=170),
            "客戶公司": st.column_config.TextColumn("客戶",      width=140),
            "退修數量": st.column_config.TextColumn("數量",      width=70),
            "進度":     st.column_config.TextColumn("完成進度",  width=80),
            "整體狀態": st.column_config.TextColumn("狀態",      width=130),
            "優先等級": st.column_config.TextColumn("優先",      width=70),
            "收件日期": st.column_config.TextColumn("收件日期",  width=140),
        },
        hide_index=True,
    )


# ── 選擇主單 ─────────────────────────────────
master_list = masters_df["主單編號"].dropna().tolist()

st.markdown("""
<div class="card" style="margin-top:8px"><div class="card-header">
  <div class="card-title">
    <span class="card-dot" style="background:var(--orange)"></span>選擇主單操作
  </div>
</div></div>""", unsafe_allow_html=True)

sel_master = st.selectbox(
    "選擇主單", master_list,
    format_func=lambda m: (
        f"{m}  ―  "
        + str(masters_df[masters_df["主單編號"]==m]["客戶公司"].values[0]
               if not masters_df[masters_df["主單編號"]==m].empty else "")
        + f"  |  {masters_df[masters_df['主單編號']==m]['退修數量'].values[0] if not masters_df[masters_df['主單編號']==m].empty else '?'} 顆"
    ),
    key="sel_master", label_visibility="collapsed",
)

mr = masters_df[masters_df["主單編號"] == sel_master]
if mr.empty:
    st.stop()
mr = mr.iloc[0].to_dict()

# 子件資料（該主單）
sub_df = details_df[details_df["主單編號"] == sel_master].reset_index(drop=True) \
         if not details_df.empty and "主單編號" in details_df.columns \
         else pd.DataFrame()

total_sub = len(sub_df)
done_sub  = len(sub_df[sub_df["維修狀態"].isin({"已完成","已出廠"})]) if total_sub > 0 else 0
pct       = int(done_sub / total_sub * 100) if total_sub > 0 else 0

# ── 主單資訊卡 ──
st.markdown(f"""
<div style="background:#f0f4f8;border:2px solid var(--navy);border-radius:10px;padding:14px 18px;margin:8px 0">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
    <div>
      <div style="font-size:18px;font-weight:900;color:var(--navy)">{sel_master}</div>
      <div style="font-size:12px;color:var(--muted);margin-top:2px">
        客戶：<b>{mr.get('客戶公司','')}</b> &nbsp;|&nbsp;
        聯絡人：{mr.get('聯絡人','')} &nbsp;|&nbsp;
        電話：{mr.get('聯絡電話','')} &nbsp;|&nbsp;
        收件：{str(mr.get('收件日期',''))[:16]}
      </div>
      <div style="font-size:12px;color:var(--muted);margin-top:4px">
        維修類型：{mr.get('維修類型','')} &nbsp;|&nbsp;
        優先等級：<b style="color:{PRIORITY_COLOR.get(str(mr.get('優先等級','P3'))[:2],'var(--muted)')}">{mr.get('優先等級','')}</b>
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-size:26px;font-weight:900;color:var(--accent)">{done_sub}/{total_sub}</div>
      <div style="font-size:11px;color:var(--muted)">子件完成進度</div>
      <div style="width:140px;background:#dce3ec;border-radius:4px;height:8px;margin-top:4px;overflow:hidden">
        <div style="width:{pct}%;background:{'var(--pass)' if pct==100 else 'var(--accent)'};height:100%;border-radius:4px"></div>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 子件清單 + 批次操作
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="card" style="margin-top:8px"><div class="card-header">
  <div class="card-title">
    <span class="card-dot" style="background:var(--teal)"></span>子件清單（馬達列表）
  </div>
</div></div>""", unsafe_allow_html=True)

if sub_df.empty:
    st.warning("此主單目前沒有子件記錄。")
else:
    sub_show = sub_df[[c for c in
        ["子件編號","馬達序號","產品型號","故障類別","維修狀態","技術判定","維修成本評估","最終判定"]
        if c in sub_df.columns]].copy()
    if "維修狀態" in sub_show.columns:
        sub_show["維修狀態"] = sub_show["維修狀態"].apply(
            lambda s: f"{STATUS_EMOJI.get(s,'')} {s}" if pd.notna(s) else s
        )

    # 可選擇列（用 data_editor + 勾選欄位）
    sub_edit = sub_df[[c for c in
        ["子件編號","馬達序號","產品型號","故障類別","維修類型","維修狀態","技術判定","維修方式","維修成本評估","是否報廢","備註"]
        if c in sub_df.columns]].copy()
    sub_edit.insert(0, "✅選取", False)

    # 動態加入既有值（包含舊資料），確保 SelectboxColumn 能正確顯示
    _existing_ft = [v for v in sub_df.get("故障類別", pd.Series(dtype=str)).dropna().unique()
                    if v and v not in FAULT_TYPES]
    _existing_rt = [v for v in sub_df.get("維修類型",  pd.Series(dtype=str)).dropna().unique()
                    if v and v not in REPAIR_TYPES]
    _fault_opts  = FAULT_TYPES  + _existing_ft
    _repair_opts = REPAIR_TYPES + _existing_rt

    edited_sub = st.data_editor(
        sub_edit,
        use_container_width=True,
        height=min(450, 56 + len(sub_edit)*38),
        column_config={
            "✅選取":      st.column_config.CheckboxColumn("選取",       width=55),
            "子件編號":    st.column_config.TextColumn("子件編號",       width=170, disabled=True),
            "馬達序號":    st.column_config.TextColumn("S/N",           width=100, disabled=True),
            "產品型號":    st.column_config.TextColumn("型號",           width=140, disabled=True),
            "故障類別":    st.column_config.SelectboxColumn("故障類別",    width=120, options=_fault_opts),
            "維修類型":    st.column_config.SelectboxColumn("維修需求",   width=130, options=_repair_opts),
            "維修狀態":    st.column_config.SelectboxColumn("狀態",       width=120, options=STATUS_LIST),
            "技術判定":    st.column_config.SelectboxColumn("技術判定",   width=120, options=TECH_JUDGMENT_LIST),
            "維修方式":    st.column_config.TextColumn("維修方式",       width=130),
            "維修成本評估": st.column_config.TextColumn("維修成本",     width=110),
            "是否報廢":    st.column_config.SelectboxColumn("報廢",      width=80, options=["","是","否"]),
        },
        hide_index=True,
        key=f"sub_editor_{sel_master}",
    )

    # ── 儲存單列修改 ──
    sv_col, _ = st.columns([2, 5])
    with sv_col:
        if st.button("💾 儲存子件修改", type="primary", use_container_width=True,
                     key="save_sub_rows"):
            with st.spinner("批次寫入中..."):
                # ① 先收集所有變更，不在迴圈內做 IO
                all_changes   = {}
                notify_closed = []
                for _, row in edited_sub.iterrows():
                    did = row.get("子件編號","")
                    if not did: continue
                    orig = sub_df[sub_df["子件編號"] == did]
                    if orig.empty: continue
                    orig = orig.iloc[0]
                    changes = {
                        col: str(row[col])
                        for col in ["故障類別","維修類型","維修狀態","技術判定","維修方式","維修成本評估","是否報廢","備註"]
                        if col in row.index and str(row[col]) != str(orig.get(col,""))
                    }
                    if changes:
                        all_changes[did] = changes
                        if changes.get("維修狀態","") in {"已出廠","已完成"}:
                            notify_closed.append((did, changes["維修狀態"], orig.to_dict()))
                # ② 單次批次寫入（2 reads + 1 batch write）
                updated = multi_update_details(all_changes) if all_changes else 0
            if updated:
                for did, ns, orig in notify_closed:
                    notify_case_closed(did, ns, {**orig, **all_changes.get(did,{})})
                fresh_sub = load_all_details()
                fresh_sub = fresh_sub[fresh_sub["主單編號"] == sel_master]
                sync_master_status(sel_master, fresh_sub)
                st.success(f"✅ 已更新 {updated} 筆子件")
                st.cache_data.clear(); st.rerun()
            else:
                st.info("沒有偵測到變更。")

    # ── 批次套用（對勾選列） ──
    checked_ids = edited_sub[edited_sub["✅選取"] == True]["子件編號"].tolist()

    if checked_ids:
        st.markdown(f"""
        <div style="background:#e8f4fd;border:1px solid #90caf9;border-radius:6px;
                    padding:10px 14px;margin:8px 0;font-size:12.5px;color:#1a2332">
          📦 已選取 <b>{len(checked_ids)}</b> 顆馬達，可套用批次操作：
        </div>""", unsafe_allow_html=True)

        with st.form("batch_apply_form"):
            ba1, ba2, ba3 = st.columns(3)
            with ba1:
                b_fault_type  = st.selectbox("批次故障類別（留空=不改）",
                                              ["（不更改）"] + FAULT_TYPES,  key="bs_ft")
                b_repair_type = st.selectbox("批次維修需求（留空=不改）",
                                              ["（不更改）"] + REPAIR_TYPES, key="bs_rt")
                b_status = st.selectbox("批次更新狀態（留空=不改）",
                                        ["（不更改）"] + STATUS_LIST, key="bs_s")
                b_verdict = st.selectbox("批次技術判定（留空=不改）",
                                         ["（不更改）"] + [t for t in TECH_JUDGMENT_LIST if t], key="bs_v")
            with ba2:
                b_warranty = st.selectbox("批次保固判定（留空=不改）",
                                          ["（不更改）"] + WARRANTY_OPTIONS[1:], key="bs_w")
                b_repair   = st.text_input("批次維修方式（留空=不改）", key="bs_r")
            with ba3:
                b_cost     = st.text_input("批次維修成本評估（留空=不改）", key="bs_c")
                b_scrap    = st.selectbox("批次是否報廢（留空=不改）",
                                          ["（不更改）", "是", "否"], key="bs_sc")
                b_repairable = st.selectbox("批次是否可維修（留空=不改）",
                                             ["（不更改）","可維修","不可維修","待評估"], key="bs_ri")
            apply_batch = st.form_submit_button("🚀 批次套用到選取馬達", type="primary",
                                                use_container_width=True)

        if apply_batch:
            batch_data = {}
            if b_fault_type  != "（不更改）": batch_data["故障類別"]    = b_fault_type
            if b_repair_type != "（不更改）": batch_data["維修類型"]    = b_repair_type
            if b_status != "（不更改）":    batch_data["維修狀態"]    = b_status
            if b_verdict != "（不更改）":   batch_data["技術判定"]    = b_verdict
            if b_warranty != "（不更改）":  batch_data["保固判定"]    = b_warranty
            if b_repair.strip():            batch_data["維修方式"]    = b_repair.strip()
            if b_cost.strip():              batch_data["維修成本評估"] = b_cost.strip()
            if b_scrap != "（不更改）":     batch_data["是否報廢"]    = b_scrap
            if b_repairable != "（不更改）": batch_data["是否可維修"] = b_repairable

            if not batch_data:
                st.warning("請至少填入一個要套用的欄位。")
            else:
                with st.spinner(f"批次更新 {len(checked_ids)} 顆馬達中..."):
                    cnt = batch_update_details(checked_ids, batch_data)
                    # 同步主單狀態
                    fresh_sub = load_all_details()
                    fresh_sub = fresh_sub[fresh_sub["主單編號"] == sel_master]
                    sync_master_status(sel_master, fresh_sub)
                st.success(f"✅ 已批次更新 {cnt} 顆馬達：{', '.join(batch_data.keys())}")
                st.cache_data.clear(); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# 技術檢測區塊（per SN）
# ══════════════════════════════════════════════════════════════════════════════
if sub_df.empty:
    st.stop()

st.markdown("""
<div class="card" style="margin-top:8px"><div class="card-header">
  <div class="card-title">
    <span class="card-dot" style="background:var(--teal)"></span>🔧 技術檢測
  </div>
</div></div>""", unsafe_allow_html=True)

# 選擇子件（只顯示當前主單的 SN）
det_options = sub_df["子件編號"].dropna().tolist()
det_rma = st.selectbox(
    "選擇馬達子件（技術檢測）",
    det_options,
    format_func=lambda d: (
        f"{d}  ―  S/N "
        + str(sub_df[sub_df["子件編號"]==d]["馬達序號"].values[0]
               if not sub_df[sub_df["子件編號"]==d].empty else "")
        + "  "
        + str(sub_df[sub_df["子件編號"]==d]["產品型號"].values[0]
               if not sub_df[sub_df["子件編號"]==d].empty else "")
    ),
    key=f"det_rma_sel_{sel_master}", label_visibility="collapsed",
)

det_df = sub_df[sub_df["子件編號"] == det_rma]
if det_df.empty:
    st.stop()

dr = det_df.iloc[0].to_dict()

def _b(k):
    return str(dr.get(k, "否")).strip() == "是"
def _f(k):
    try: return float(dr.get(k, 0) or 0)
    except: return 0.0
def _s(k):
    return str(dr.get(k, "") or "")

st.markdown(
    f'<div style="font-size:11.5px;color:var(--muted);padding:4px 0 8px">'
    f'子件：<b>{det_rma}</b> &nbsp;|&nbsp; '
    f'S/N：<b>{dr.get("馬達序號","")}</b> &nbsp;|&nbsp; '
    f'型號：{dr.get("產品型號","")} &nbsp;|&nbsp; '
    f'故障：{dr.get("故障類別","")} &nbsp;|&nbsp; '
    f'狀態：{STATUS_EMOJI.get(str(dr.get("維修狀態","")),"")} {dr.get("維修狀態","")}'
    f'</div>',
    unsafe_allow_html=True,
)

# ── 維修病歷 ──
motor_sn_det = str(dr.get("馬達序號","")).strip()
if motor_sn_det and not details_df.empty and "馬達序號" in details_df.columns:
    hist = details_df[details_df["馬達序號"].astype(str).str.strip() == motor_sn_det]
    if len(hist) > 1:
        with st.expander(f"⚠️ 維修病歷：S/N [{motor_sn_det}] 共 {len(hist)} 次送修（含本次）",
                         expanded=True):
            h_cols = [c for c in ["子件編號","主單編號","故障類別","保固判定","維修方式","最終判定","維修狀態"]
                      if c in hist.columns]
            st.dataframe(hist[h_cols].reset_index(drop=True),
                         use_container_width=True, hide_index=True)

# ── 提前終止 session_state ──
_et_stop_key  = f"et_stop_{det_rma}"
_et_scrap_key = f"et_scrap_{det_rma}"

# ── 預載自定義項目 ──
_s1_custom = get_step_custom_items("S1")
_s2_custom = get_step_custom_items("S2")
_s4_custom = get_step_custom_items("S4")
_s5_custom = get_step_custom_items("S5")

def _coil_abnormal(ab, bc, ca):
    vals = [v for v in [ab, bc, ca] if v > 0]
    if len(vals) < 2: return False, 0.0
    avg = sum(vals) / len(vals)
    if avg == 0: return False, 0.0
    max_dev = max(abs(v - avg) / avg for v in vals) * 100
    return max_dev > 10.0, max_dev

def _render_custom(step_id, custom_items, suffix):
    vals = {}
    if not custom_items: return vals
    for bi in range(0, len(custom_items), 4):
        batch = custom_items[bi:bi+4]
        cols  = st.columns(4)
        for j, item in enumerate(batch):
            col_key = f"{step_id}-{item['id']}"
            with cols[j]:
                vals[col_key] = st.checkbox(
                    item.get("label", item["id"]),
                    value=_b(col_key),
                    key=f"{step_id.lower()}c{bi+j}_{suffix}",
                )
    return vals

STEP_STYLE = ('<div style="font-size:13px;font-weight:700;color:var(--navy);'
              'border-left:4px solid #1a9b7a;padding-left:10px;margin:12px 0 6px">'
              '{label}</div>')

# ───────── Step 1 外觀檢測 ─────────
st.markdown(STEP_STYLE.format(label="Step 1 🔬 外觀檢測"), unsafe_allow_html=True)
c1a, c1b, c1c, c1d = st.columns(4)
with c1a: s1_shell = st.checkbox("外殼撞傷", value=_b("S1-外殼撞傷"), key=f"s1sh_{det_rma}")
with c1b: s1_axis  = st.checkbox("軸心歪斜", value=_b("S1-軸心歪斜"), key=f"s1ax_{det_rma}")
with c1c: s1_sand  = st.checkbox("沙土侵入", value=_b("S1-沙土侵入"), key=f"s1sd_{det_rma}")
with c1d: s1_screw = st.checkbox("螺絲裂痕", value=_b("S1-螺絲裂痕"), key=f"s1sc_{det_rma}")
_c1e1, _c1e2, _c1e3, _c1e4 = st.columns(4)
with _c1e1: s1_ok = st.checkbox("正常", value=_b("S1-正常"), key=f"s1ok_{det_rma}")
_s1_cust_vals = _render_custom("S1", _s1_custom, det_rma)

# 人為撞擊提前終止
if s1_axis and s1_shell:
    st.markdown(
        '<div style="background:#fff3f3;border:2px solid #e74c3c;border-radius:8px;'
        'padding:12px 18px;margin:8px 0 4px;font-size:13px;font-weight:700;color:#c0392b">'
        '⚠️ 已符合人為撞擊判定，建議停止後續檢測</div>',
        unsafe_allow_html=True)
    et_c1, et_c2, et_c3 = st.columns([2, 2, 4])
    with et_c1:
        if st.button("🛑 結束檢測", key=f"et_stop_btn_{det_rma}", type="primary"):
            st.session_state[_et_stop_key]  = True
            st.session_state[_et_scrap_key] = False
            st.rerun()
    with et_c2:
        if st.button("♻️ 轉報廢流程", key=f"et_scrap_btn_{det_rma}"):
            st.session_state[_et_scrap_key] = True
            st.session_state[_et_stop_key]  = False
            st.rerun()
    if st.session_state.get(_et_stop_key, False):
        st.info("⏹ 已選擇結束檢測，步驟 2–5 已跳過。")
    elif st.session_state.get(_et_scrap_key, False):
        st.info("♻️ 已選擇轉報廢流程，請填寫下方最終結果。")
else:
    st.session_state.pop(_et_stop_key, None)
    st.session_state.pop(_et_scrap_key, None)

_is_early_stop  = st.session_state.get(_et_stop_key, False)
_is_early_scrap = st.session_state.get(_et_scrap_key, False)

s2_noise = s2_stuck = s2_bearing = s2_ok = False
s3_ab = s3_bc = s3_ca = 0.0
coil_bad, coil_dev = False, 0.0
s4_vib = s4_heat = s4_start = s4_ok = False
s5_coil = s5_magnet = s5_rust = s5_ok = False
_s2_cust_vals = {}; _s4_cust_vals = {}; _s5_cust_vals = {}

if not _is_early_stop:
    # ───────── Step 2 手感測試 ─────────
    st.markdown(STEP_STYLE.format(label="Step 2 🤚 手感測試"), unsafe_allow_html=True)
    c2a, c2b, c2c, c2d = st.columns(4)
    with c2a: s2_noise   = st.checkbox("異音",     value=_b("S2-異音"),     key=f"s2no_{det_rma}")
    with c2b: s2_stuck   = st.checkbox("卡頓",     value=_b("S2-卡頓"),     key=f"s2st_{det_rma}")
    with c2c: s2_bearing = st.checkbox("軸承鬆動", value=_b("S2-軸承鬆動"), key=f"s2be_{det_rma}")
    with c2d: s2_ok      = st.checkbox("正常",     value=_b("S2-正常"),     key=f"s2ok_{det_rma}")
    _s2_cust_vals = _render_custom("S2", _s2_custom, det_rma)

    # ───────── Step 3 電氣測試 ─────────
    st.markdown(STEP_STYLE.format(label="Step 3 ⚡ 電氣測試（三用電表）"), unsafe_allow_html=True)
    c3a, c3b, c3c = st.columns(3)
    with c3a: s3_ab = st.number_input("AB 阻值 (Ω)", value=_f("S3-AB阻值"), min_value=0.0, step=0.1, format="%.2f", key=f"s3ab_{det_rma}")
    with c3b: s3_bc = st.number_input("BC 阻值 (Ω)", value=_f("S3-BC阻值"), min_value=0.0, step=0.1, format="%.2f", key=f"s3bc_{det_rma}")
    with c3c: s3_ca = st.number_input("CA 阻值 (Ω)", value=_f("S3-CA阻值"), min_value=0.0, step=0.1, format="%.2f", key=f"s3ca_{det_rma}")
    coil_bad, coil_dev = _coil_abnormal(s3_ab, s3_bc, s3_ca)
    if s3_ab > 0 or s3_bc > 0 or s3_ca > 0:
        if coil_bad:
            st.error(f"⚠️ 線圈異常：三組阻值最大差異 **{coil_dev:.1f}%**（超過 10% 閾值）")
        else:
            st.success(f"✅ 阻值均衡：差異 {coil_dev:.1f}%（< 10%），正常")

    # ───────── Step 4 通電測試 ─────────
    st.markdown(STEP_STYLE.format(label="Step 4 🔌 通電測試"), unsafe_allow_html=True)
    c4a, c4b, c4c, c4d = st.columns(4)
    with c4a: s4_vib   = st.checkbox("高震動",   value=_b("S4-高震動"),   key=f"s4vb_{det_rma}")
    with c4b: s4_heat  = st.checkbox("高溫",     value=_b("S4-高溫"),     key=f"s4ht_{det_rma}")
    with c4c: s4_start = st.checkbox("無法啟動", value=_b("S4-無法啟動"), key=f"s4st_{det_rma}")
    with c4d: s4_ok    = st.checkbox("正常",     value=_b("S4-正常"),     key=f"s4ok_{det_rma}")
    _s4_cust_vals = _render_custom("S4", _s4_custom, det_rma)

    # ───────── Step 5 拆解分析 ─────────
    st.markdown(STEP_STYLE.format(label="Step 5 🔩 拆解分析"), unsafe_allow_html=True)
    c5a, c5b, c5c, c5d = st.columns(4)
    with c5a: s5_coil   = st.checkbox("線圈燒毀", value=_b("S5-線圈燒毀"), key=f"s5co_{det_rma}")
    with c5b: s5_magnet = st.checkbox("磁鐵脫落", value=_b("S5-磁鐵脫落"), key=f"s5mg_{det_rma}")
    with c5c: s5_rust   = st.checkbox("生鏽",     value=_b("S5-生鏽"),     key=f"s5rs_{det_rma}")
    with c5d: s5_ok     = st.checkbox("正常",     value=_b("S5-正常"),     key=f"s5ok_{det_rma}")
    _s5_cust_vals = _render_custom("S5", _s5_custom, det_rma)

    if coil_bad and s5_coil:
        st.markdown(
            '<div style="background:#e8f8f5;border:1px solid #a9dfbf;border-radius:6px;'
            'padding:9px 14px;font-size:12.5px;color:var(--teal);font-weight:700;margin:6px 0">'
            '✅ 已確認線圈燒毀</div>', unsafe_allow_html=True)

# 自動判定橫幅
auto_msgs = []
if _is_early_scrap:
    auto_msgs.append(("保固外 / 人為撞擊 — 已轉報廢流程","#fff3f3","#ffd0d0","var(--cr)"))
if s5_magnet:
    auto_msgs.append(("可能製程問題（建議保固內）","#e8f8f5","#a9dfbf","var(--teal)"))
if coil_bad and not s5_coil:
    auto_msgs.append(("線圈異常 — 建議確認過載/堵轉紀錄","#fef9e7","#f9e79f","var(--warn)"))
if auto_msgs:
    for msg, bg, bd, tc in auto_msgs:
        st.markdown(
            f'<div style="background:{bg};border:1px solid {bd};border-radius:6px;'
            f'padding:9px 14px;font-size:12.5px;color:{tc};font-weight:700;margin:4px 0">'
            f'🤖 系統自動判定：{msg}</div>', unsafe_allow_html=True)

# ── 最終結果 ──
st.markdown(STEP_STYLE.format(label="📋 最終結果"), unsafe_allow_html=True)
fr1, fr2, fr3 = st.columns(3)
with fr1:
    saved_tj = _s("技術判定")
    tj_idx = TECH_JUDGMENT_LIST.index(saved_tj) if saved_tj in TECH_JUDGMENT_LIST else 0
    if _is_early_scrap and not saved_tj:
        tj_idx = TECH_JUDGMENT_LIST.index("建議報廢") if "建議報廢" in TECH_JUDGMENT_LIST else 0
    tech_judg_det = st.selectbox("技術判定", TECH_JUDGMENT_LIST, index=tj_idx, key=f"tjd_{det_rma}")
    saved_w = _s("保固判定")
    w_idx   = WARRANTY_OPTIONS.index(saved_w) if saved_w in WARRANTY_OPTIONS else 0
    warranty_judg = st.selectbox("保固判定", WARRANTY_OPTIONS, index=w_idx, key=f"wj_{det_rma}")
with fr2:
    repair_method = st.text_area("維修方式", value=_s("維修方式"),
                                  placeholder="例：更換軸承、重繞線圈…", height=80, key=f"rm_{det_rma}")
with fr3:
    _scrap_default = _b("是否報廢") or _is_early_scrap
    is_scrap = st.checkbox("是否報廢", value=_scrap_default, key=f"scrap_{det_rma}")
    saved_ir  = _s("是否可維修")
    ir_opts   = ["", "可維修", "不可維修", "待評估"]
    ir_idx    = ir_opts.index(saved_ir) if saved_ir in ir_opts else 0
    is_repairable = st.selectbox("是否可維修", ir_opts, index=ir_idx, key=f"ir_{det_rma}")
    cost_eval = st.text_input("維修成本評估", value=_s("維修成本評估"),
                               placeholder="例：軸承更換約 NT$300…", key=f"ce_{det_rma}")
final_verdict = ""  # 已移除最終判定輸入欄

# ── 儲存 & PDF ──
sv_col, pdf_col, _ = st.columns([2, 2, 3])
with sv_col:
    save_det = st.button("💾 儲存檢測結果", type="primary", use_container_width=True, key="save_det_btn")
with pdf_col:
    gen_pdf  = st.button("📄 產生維修報告", use_container_width=True, key="gen_pdf_btn")

if save_det:
    now_str  = datetime.now().strftime("%Y/%m/%d %H:%M")
    det_data = {
        "S1-外殼撞傷": "是" if s1_shell else "否",
        "S1-軸心歪斜": "是" if s1_axis  else "否",
        "S1-沙土侵入": "是" if s1_sand  else "否",
        "S1-螺絲裂痕": "是" if s1_screw else "否",
        "S1-正常":     "是" if s1_ok    else "否",
        "S2-異音":     "是" if s2_noise   else "否",
        "S2-卡頓":     "是" if s2_stuck   else "否",
        "S2-軸承鬆動": "是" if s2_bearing else "否",
        "S2-正常":     "是" if s2_ok      else "否",
        "S3-AB阻值":   round(s3_ab, 3),
        "S3-BC阻值":   round(s3_bc, 3),
        "S3-CA阻值":   round(s3_ca, 3),
        "S3-線圈異常": "是" if coil_bad else "否",
        "S4-高震動":   "是" if s4_vib   else "否",
        "S4-高溫":     "是" if s4_heat  else "否",
        "S4-無法啟動": "是" if s4_start else "否",
        "S4-正常":     "是" if s4_ok    else "否",
        "S5-線圈燒毀": "是" if s5_coil   else "否",
        "S5-磁鐵脫落": "是" if s5_magnet else "否",
        "S5-生鏽":     "是" if s5_rust   else "否",
        "S5-正常":     "是" if s5_ok     else "否",
        "最終判定":    final_verdict,
        "保固判定":    warranty_judg,
        "技術判定":    tech_judg_det,
        "維修方式":    repair_method,
        "是否報廢":    "是" if is_scrap else "否",
        "是否可維修":  is_repairable,
        "維修成本評估": cost_eval,
        "五步檢測時間": now_str,
        **{k: "是" if v else "否" for k, v in _s1_cust_vals.items()},
        **{k: "是" if v else "否" for k, v in _s2_cust_vals.items()},
        **{k: "是" if v else "否" for k, v in _s4_cust_vals.items()},
        **{k: "是" if v else "否" for k, v in _s5_cust_vals.items()},
    }
    with st.spinner("儲存中..."):
        ok = update_detail_detection(det_rma, det_data)
    if ok:
        st.success(f"✅ {det_rma} 技術檢測結果已儲存")
        st.session_state.pop(_et_stop_key, None)
        st.session_state.pop(_et_scrap_key, None)
        st.cache_data.clear(); st.rerun()
    else:
        st.error("❌ 儲存失敗，請重新整理後再試")

if gen_pdf:
    try:
        from utils.rma_pdf_report import generate_repair_pdf
        # 合併主單資訊到子件資料
        merged = {**mr, **dr, "RMA編號": det_rma, "客戶公司": mr.get("客戶公司",""),
                  "聯絡人": mr.get("聯絡人",""), "聯絡電話": mr.get("聯絡電話",""),
                  "客戶Email": mr.get("客戶Email",""),
                  "收件日期": mr.get("收件日期",""), "維修類型": mr.get("維修類型","")}
        with st.spinner("產生 PDF 中，請稍候..."):
            pdf_bytes = generate_repair_pdf(merged)
        fname = f"維修報告_{det_rma}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        st.success("✅ PDF 已產生！")
        st.download_button(label=f"⬇️ 下載 {fname}", data=pdf_bytes,
                           file_name=fname, mime="application/pdf",
                           use_container_width=True, key="dl_pdf_btn")
    except Exception as _ex:
        st.error(f"❌ PDF 產生失敗：{_ex}")


# ══════════════════════════════════════════════════════════════════════════════
# 故障照片查看
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="card" style="margin-top:8px"><div class="card-header">
  <div class="card-title">
    <span class="card-dot" style="background:var(--blue2)"></span>故障照片查看
  </div>
</div></div>""", unsafe_allow_html=True)

photo_did = st.selectbox("選擇子件查看照片",
                          ["— 選擇 —"] + det_options,
                          label_visibility="collapsed", key="photo_sel")
if photo_did and photo_did != "— 選擇 —":
    with st.spinner("載入照片..."):
        urls = get_detail_photos(photo_did)
    if urls:
        st.markdown(f'<div style="font-size:12px;color:var(--muted);margin-bottom:8px">共 {len(urls)} 張照片</div>',
                    unsafe_allow_html=True)
        show_urls = urls[:8]
        img_cols  = st.columns(min(len(show_urls), 4))
        for col, url in zip(img_cols * 2, show_urls):
            with col:
                img_data = _gdrive_bytes(url)
                if img_data:
                    st.image(img_data, use_container_width=True)
                else:
                    m = re.search(r'[?&]id=([A-Za-z0-9_\-]+)', url)
                    fid  = m.group(1) if m else ""
                    view = f"https://drive.google.com/file/d/{fid}/view" if fid else url
                    st.markdown(f'<a href="{view}" target="_blank" style="font-size:12px">📷 在 Drive 查看</a>',
                                unsafe_allow_html=True)
    else:
        st.info("此子件尚未上傳故障照片。")


# ══════════════════════════════════════════════════════════════════════════════
# 刪除 / 取消
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="card" style="margin-top:8px;border-left:4px solid var(--cr)">
  <div class="card-header" style="background:#fff8f7">
    <div class="card-title" style="color:var(--cr)">
      <span class="card-dot" style="background:var(--cr)"></span>刪除 / 取消
    </div>
  </div>
</div>""", unsafe_allow_html=True)

with st.expander("⚠️ 展開刪除功能（請謹慎操作）", expanded=False):
    del_scope = st.radio("刪除範圍",
                         ["🔩 單一子件", "📋 整份主單（含全部子件）"],
                         horizontal=True, key="del_scope")

    del_mode = st.radio("刪除模式",
                        ["✅ 軟刪除（標記已取消，資料保留）",
                         "🗑️ 硬刪除（永久移除，無法還原）"],
                        horizontal=True, key="del_mode_det")
    is_hard = "硬刪除" in del_mode

    # ── 刪除單一子件 ──
    if del_scope.startswith("🔩"):
        sel_del = st.selectbox("選擇要刪除的子件",
                               ["— 請選擇 —"] + det_options, key="del_det_sel")

        if sel_del and sel_del != "— 請選擇 —":
            confirm_del = st.checkbox(
                f"我確認要{'永久刪除' if is_hard else '取消'} **{sel_del}**",
                key="del_det_confirm")
            hard_ok = True
            if is_hard:
                ct = st.text_input(f"輸入子件編號「{sel_del}」以確認",
                                   key="del_det_hard_txt", placeholder="輸入子件編號以解鎖")
                hard_ok = ct.strip() == sel_del

            if st.button(f"{'🗑️ 永久刪除' if is_hard else '✅ 標記取消'} {sel_del}",
                         type="primary", disabled=not (confirm_del and hard_ok),
                         key="del_det_btn"):
                with st.spinner("執行刪除中..."):
                    ok = delete_detail(sel_del, hard=is_hard)
                if ok:
                    fresh_sub = load_all_details()
                    fresh_sub = fresh_sub[fresh_sub["主單編號"] == sel_master] \
                                if not fresh_sub.empty else pd.DataFrame()
                    sync_master_status(sel_master, fresh_sub)
                    st.success(f"✅ {sel_del} 已{'永久刪除' if is_hard else '標記為已取消'}")
                    st.cache_data.clear(); st.rerun()
                else:
                    st.error(f"❌ 找不到 {sel_del}，請重新整理後再試。")

    # ── 刪除整份主單 ──
    else:
        sub_count = len(sub_df) if not sub_df.empty else 0
        st.markdown(
            f'<div style="background:#fff3f3;border:1px solid #ffd0d0;border-radius:6px;'
            f'padding:10px 14px;font-size:12.5px;color:#555;margin:6px 0">'
            f'<b>{sel_master}</b> &nbsp;｜&nbsp; '
            f'客戶：{mr.get("客戶公司","")} &nbsp;｜&nbsp; '
            f'子件數量：<b>{sub_count}</b> 顆</div>',
            unsafe_allow_html=True)

        if is_hard:
            st.warning("⚠️ 硬刪除整份主單：主單列將永久移除。子件請以「子件硬刪除」另行處理，或先軟刪除後再手動清理 Google Sheet。")

        confirm_master = st.checkbox(
            f"我確認要{'永久刪除' if is_hard else '取消'} 整份主單 **{sel_master}**（含所有子件）",
            key="del_master_confirm")
        hard_ok_m = True
        if is_hard:
            ctm = st.text_input(f"輸入主單編號「{sel_master}」以確認硬刪除",
                                key="del_master_hard_txt", placeholder="輸入主單編號以解鎖")
            hard_ok_m = ctm.strip() == sel_master

        if st.button(f"{'🗑️ 永久刪除' if is_hard else '✅ 整份取消'} {sel_master}",
                     type="primary", disabled=not (confirm_master and hard_ok_m),
                     key="del_master_btn"):
            with st.spinner("刪除整份主單中..."):
                # 先取消/刪除所有子件
                if not sub_df.empty:
                    for did in sub_df["子件編號"].dropna().tolist():
                        delete_detail(did, hard=is_hard)
                # 再刪除主單
                ok_m = delete_master(sel_master, hard=is_hard)
            if ok_m:
                action = "永久刪除" if is_hard else "整份標記為已取消"
                st.success(f"✅ 主單 {sel_master}（含 {sub_count} 顆子件）已{action}")
                st.cache_data.clear(); st.rerun()
            else:
                st.error(f"❌ 操作失敗，請重新整理後再試。")
