"""
REXONTEC 力科 — 追蹤查詢
OQC 出廠檢驗 & IQC 進料品質 — 批號 / 序號 / 品號 / 採購單 / 日期
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime, date, timedelta

from utils.style  import QMS_CSS, topbar, page_header
from utils.auth   import require_login, user_info_bar
from utils.gsheet import load_oqc_records, load_iqc_records

st.set_page_config(
    page_title="REXONTEC 力科 | 追蹤查詢",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()
user_info_bar()

# ── 導覽列 ──────────────────────────────────────────────
c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 1, 1, 1, 1, 1, 3])
with c1:
    if st.button("🏠 指揮平台", use_container_width=True): st.switch_page("app.py")
with c2:
    if st.button("📋 檢驗輸入", use_container_width=True): st.switch_page("pages/01_出廠檢驗輸入.py")
with c3:
    if st.button("🔬 IQC 進料", use_container_width=True): st.switch_page("pages/06_IQC進料檢驗.py")
with c4:
    if st.button("📋 IPQC 巡檢", use_container_width=True): st.switch_page("pages/20_📋_IPQC巡檢.py")
with c5:
    if st.button("📊 儀表板",   use_container_width=True): st.switch_page("pages/02_儀表板.py")
with c6:
    if st.button("🤖 AI 分析",  use_container_width=True): st.switch_page("pages/07_AI異常分析.py")

st.markdown(page_header(
    "追蹤查詢",
    "OQC 出廠檢驗 & IQC 進料品質 — 批號 / 序號 / 品號 / 採購單 / 日期",
    "TRK",
), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# 資料載入（快取 5 分鐘）
# ════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner="載入 OQC 資料中…")
def _load_oqc() -> pd.DataFrame:
    try:
        df_e = load_oqc_records("esc")
        df_m = load_oqc_records("motor")
        df   = pd.concat([df_e, df_m], ignore_index=True)
        if not df.empty:
            df["建立時間"] = pd.to_datetime(df["建立時間"], errors="coerce")
            df = df.sort_values("建立時間", ascending=False).reset_index(drop=True)
        return df
    except Exception as ex:
        st.warning(f"⚠️ 無法載入 OQC 資料：{ex}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner="載入 IQC 資料中…")
def _load_iqc() -> pd.DataFrame:
    try:
        df = load_iqc_records()
        if not df.empty:
            df["建立時間"] = pd.to_datetime(df["建立時間"], errors="coerce")
            df = df.sort_values("建立時間", ascending=False).reset_index(drop=True)
        return df
    except Exception as ex:
        st.warning(f"⚠️ 無法載入 IQC 資料：{ex}")
        return pd.DataFrame()


# ════════════════════════════════════════════════════════
# 共用輔助
# ════════════════════════════════════════════════════════
def _parse_detail(s) -> dict:
    try:
        if not s or str(s).strip() in ("", "nan"):
            return {}
        return json.loads(str(s))
    except Exception:
        return {}


def _verdict_chip(v: str) -> str:
    v = str(v)
    if v == "PASS":
        return ('<span style="background:#eafaf1;color:#27ae60;padding:2px 10px;'
                'border-radius:99px;font-size:11px;font-weight:700;'
                'border:1px solid #a9dfbf">✓ PASS</span>')
    elif "FAIL" in v:
        return (f'<span style="background:#fdedec;color:#e74c3c;padding:2px 10px;'
                f'border-radius:99px;font-size:11px;font-weight:700;'
                f'border:1px solid #f5b7b1">✗ {v}</span>')
    return (f'<span style="background:#fef9e7;color:#f39c12;padding:2px 10px;'
            f'border-radius:99px;font-size:11px;font-weight:700;'
            f'border:1px solid #fad7a0">{v}</span>')


def _stat_cards(total, n_pass, n_fail, cr, ma, mi, label_id=""):
    yield_rt = f"{n_pass/total*100:.1f}%" if total else "─"
    st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:12px 0">
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1e88e5;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">查詢結果</div>
    <div style="font-size:16px;font-weight:900;color:#0d1b2a;font-family:monospace">{label_id}</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1e88e5;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">筆數</div>
    <div style="font-size:22px;font-weight:700;color:#0d1b2a">{total}</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #27ae60;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">合格率</div>
    <div style="font-size:22px;font-weight:700;color:#27ae60">{yield_rt}</div>
    <div style="font-size:10px;color:#aaa">{n_pass} 合格 / {n_fail} 不合格</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #c0392b;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">CR 不良</div>
    <div style="font-size:22px;font-weight:700;color:#c0392b">{cr}</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #d68910;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">MA 不良</div>
    <div style="font-size:22px;font-weight:700;color:#d68910">{ma}</div>
  </div>
  <div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1e8449;
              border-radius:8px;padding:12px 14px">
    <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px">MI 不良</div>
    <div style="font-size:22px;font-weight:700;color:#1e8449">{mi}</div>
  </div>
</div>
""", unsafe_allow_html=True)


def _date_filter_row(df: pd.DataFrame, date_col: str, key_prefix: str):
    """回傳日期篩選後的 DataFrame；若未選擇則回傳原始。"""
    if date_col not in df.columns:
        return df
    d1, d2 = st.columns(2)
    today = date.today()
    with d1:
        date_from = st.date_input("日期（起）", value=None,
                                  key=f"{key_prefix}_df",
                                  format="YYYY/MM/DD")
    with d2:
        date_to = st.date_input("日期（迄）", value=None,
                                key=f"{key_prefix}_dt",
                                format="YYYY/MM/DD")
    if date_from:
        df = df[df[date_col].dt.date >= date_from]
    if date_to:
        df = df[df[date_col].dt.date <= date_to]
    return df


# ════════════════════════════════════════════════════════
# OQC 明細展開
# ════════════════════════════════════════════════════════
def _render_oqc_record(row, expanded=False):
    date_str = row["建立時間"].strftime("%Y/%m/%d %H:%M") if pd.notna(row["建立時間"]) else "─"
    with st.expander(
        f"📄 {row['記錄編號']}　{date_str}　{row.get('機種','─')}　{row.get('批號','─')}　{row.get('總判定','─')}",
        expanded=expanded,
    ):
        ic1, ic2, ic3, ic4, ic5 = st.columns(5)
        ic1.metric("機種",   str(row.get("機種","─")))
        ic2.metric("料號",   str(row.get("料號","─")))
        ic3.metric("抽驗數", str(row.get("抽驗數量","─")))
        ic4.metric("檢驗員", str(row.get("檢驗員","─")))
        ic5.metric("總判定", str(row.get("總判定","─")))

        ng_txt = str(row.get("NG_項目摘要",""))
        if ng_txt and ng_txt not in ("", "nan"):
            st.markdown(f"""
<div style="background:#fff8f7;border:1px solid #f5b7b1;border-radius:6px;
            padding:10px 14px;font-size:12px;margin-top:8px">
  <b style="color:#c0392b">NG 摘要：</b>{ng_txt}
</div>""", unsafe_allow_html=True)

        detail = _parse_detail(row.get("明細JSON",""))
        if detail:
            first_item = next(iter(detail.values()), {})
            sn_list = list(first_item.keys()) if isinstance(first_item, dict) else []
            if sn_list:
                st.markdown(f"**序號清單（{len(sn_list)} 台）：** " + " ｜ ".join(sn_list))
                sn_rows = []
                for sn in sn_list:
                    pass_cnt = sum(1 for iid, ud in detail.items()
                                   if isinstance(ud, dict) and ud.get(sn, {}).get("result") == "PASS")
                    fail_cnt = sum(1 for iid, ud in detail.items()
                                   if isinstance(ud, dict) and ud.get(sn, {}).get("result") == "FAIL")
                    sn_rows.append({"序號": sn,
                                    "OK 項目": pass_cnt,
                                    "NG 項目": fail_cnt,
                                    "判定": "NG" if fail_cnt > 0 else ("OK" if pass_cnt > 0 else "─")})
                sdf = pd.DataFrame(sn_rows)
                st.dataframe(sdf, use_container_width=True, hide_index=True,
                             height=min(200, 56 + len(sdf) * 38))


# ════════════════════════════════════════════════════════
# IQC 明細展開
# ════════════════════════════════════════════════════════
def _render_iqc_record(row, expanded=False):
    date_str = row["建立時間"].strftime("%Y/%m/%d %H:%M") if pd.notna(row["建立時間"]) else "─"
    with st.expander(
        f"📄 {row['記錄編號']}　{date_str}　{row.get('零件名稱','─')}　"
        f"料號 {row.get('料號','─')}　{row.get('總判定','─')}",
        expanded=expanded,
    ):
        ic1, ic2, ic3, ic4, ic5 = st.columns(5)
        ic1.metric("零件名稱", str(row.get("零件名稱","─")))
        ic2.metric("料號",     str(row.get("料號","─")))
        ic3.metric("供應商",   str(row.get("供應商","─")))
        ic4.metric("採購單號", str(row.get("採購單號","─")))
        ic5.metric("總判定",   str(row.get("總判定","─")))

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("批號",    str(row.get("批號","─")))
        rc2.metric("進料數量", str(row.get("進料數量","─")))
        rc3.metric("抽樣數量", str(row.get("抽樣數量","─")))
        rc4.metric("IQC 檢驗員", str(row.get("IQC檢驗員","─")))

        ng_txt = str(row.get("NG_項目摘要",""))
        if ng_txt and ng_txt not in ("", "nan"):
            st.markdown(f"""
<div style="background:#fff8f7;border:1px solid #f5b7b1;border-radius:6px;
            padding:10px 14px;font-size:12px;margin-top:8px">
  <b style="color:#c0392b">NG 摘要：</b>{ng_txt}
</div>""", unsafe_allow_html=True)

        detail = _parse_detail(row.get("明細JSON",""))
        if detail:
            item_rows = []
            for iid, r_data in detail.items():
                if not isinstance(r_data, dict):
                    continue
                res    = r_data.get("result", None)
                inputs = r_data.get("inputs", {})
                remark = r_data.get("remark", "")
                # 量測值摘要
                meas_str = "、".join(
                    f"{k}={v}" for k, v in inputs.items() if v not in (None, "", [])
                ) if inputs else "─"
                res_label = ("OK" if res == "pass" else ("NG" if res == "fail" else "─"))
                item_rows.append({
                    "項目 ID": str(iid),
                    "量測記錄": meas_str[:60],
                    "備註": str(remark)[:30],
                    "判定": res_label,
                })
            if item_rows:
                idf = pd.DataFrame(item_rows)
                def _color(v):
                    if v == "NG":   return "background-color:#fdedec;color:#e74c3c;font-weight:bold"
                    if v == "OK":   return "background-color:#eafaf1;color:#27ae60"
                    return ""
                try:
                    styled = idf.style.map(_color, subset=["判定"])
                except AttributeError:
                    styled = idf.style.applymap(_color, subset=["判定"])
                st.dataframe(styled, use_container_width=True, hide_index=True,
                             height=min(300, 56 + len(idf) * 38))


# ════════════════════════════════════════════════════════
# 主頁面：兩大分類 Tab
# ════════════════════════════════════════════════════════
tab_oqc, tab_iqc = st.tabs(["📦 出廠檢驗追蹤 (OQC)", "🔬 IQC 進料追蹤"])

# ─────────────────────────────────────────────────────────
# ██  OQC TAB
# ─────────────────────────────────────────────────────────
with tab_oqc:
    df_oqc = _load_oqc()

    if df_oqc.empty:
        st.info("ℹ️ 尚無 OQC 資料，請先完成至少一筆出廠檢驗並提交。")
    else:
        oqc_t1, oqc_t2, oqc_t3 = st.tabs(["📦 批號追蹤", "🔎 SN 序號追蹤", "📋 全部記錄"])

        # ── OQC Tab1：批號追蹤 ────────────────────────────
        with oqc_t1:
            st.markdown("#### 🔍 依批號查詢")
            lot_list = sorted(
                [str(x) for x in df_oqc["批號"].dropna().unique()
                 if str(x).strip() not in ("", "nan")],
                reverse=True,
            )
            col_sel, col_pick = st.columns([3, 1])
            with col_sel:
                lot_input = st.text_input("輸入批號（或從下方選擇）",
                                          placeholder="例：2026-05-A001",
                                          key="oqc_lot_input")
            with col_pick:
                st.markdown("<br>", unsafe_allow_html=True)
                if lot_list:
                    picked = st.selectbox("現有批號", [""] + lot_list,
                                          key="oqc_lot_pick",
                                          label_visibility="collapsed")
                    if picked:
                        lot_input = picked

            query_lot = lot_input.strip()

            if not query_lot:
                st.markdown("##### 最近批號一覽")
                recent = (
                    df_oqc.groupby("批號", dropna=False)
                    .agg(
                        筆數    =("記錄編號", "count"),
                        最近日期=("建立時間", "max"),
                        機種    =("機種", lambda x: " / ".join(x.dropna().unique()[:3])),
                        合格率  =("總判定", lambda x: f"{(x == 'PASS').mean()*100:.0f}%"),
                    )
                    .sort_values("最近日期", ascending=False)
                    .head(10)
                    .reset_index()
                )
                recent["最近日期"] = recent["最近日期"].dt.strftime("%Y/%m/%d")
                st.dataframe(recent, use_container_width=True, hide_index=True)
                st.caption("💡 輸入批號後按 Enter 可查看詳細記錄")
            else:
                lot_df = df_oqc[df_oqc["批號"].astype(str) == query_lot].copy()
                if lot_df.empty:
                    st.warning(f"⚠️ 找不到批號「{query_lot}」的記錄")
                else:
                    total  = len(lot_df)
                    n_pass = (lot_df["總判定"] == "PASS").sum()
                    n_fail = total - n_pass
                    cr_s   = lot_df["CR_不良數"].astype(int).sum() if "CR_不良數" in lot_df else 0
                    ma_s   = lot_df["MA_不良數"].astype(int).sum() if "MA_不良數" in lot_df else 0
                    mi_s   = lot_df["MI_不良數"].astype(int).sum() if "MI_不良數" in lot_df else 0
                    _stat_cards(total, n_pass, n_fail, cr_s, ma_s, mi_s, query_lot)
                    st.markdown("##### 檢驗記錄明細")
                    for _, row in lot_df.iterrows():
                        _render_oqc_record(row)

        # ── OQC Tab2：SN 序號追蹤 ──────────────────────────
        with oqc_t2:
            st.markdown("#### 🔎 依序號（SN）查詢")
            sn_col, btn_col = st.columns([3, 1])
            with sn_col:
                sn_query = st.text_input("輸入序號",
                                         placeholder="例：SN-001",
                                         key="oqc_sn_q").strip()
            with btn_col:
                st.markdown("<br>", unsafe_allow_html=True)
                st.button("🔍 查詢", key="oqc_sn_btn", use_container_width=True)

            if not sn_query:
                st.info("💡 輸入序號後按 Enter 或點「查詢」")
            else:
                with st.spinner("搜尋中…"):
                    matched = []
                    for _, row in df_oqc.iterrows():
                        detail = _parse_detail(row.get("明細JSON",""))
                        for iid, ud in detail.items():
                            if isinstance(ud, dict) and sn_query in ud:
                                matched.append((row, detail))
                                break

                if not matched:
                    st.warning(f"⚠️ 找不到序號「{sn_query}」的記錄")
                    st.caption("提示：序號需完全吻合（區分大小寫）")
                else:
                    st.success(f"✅ 找到 **{len(matched)}** 筆含「{sn_query}」的記錄")
                    for row, detail in matched:
                        date_str = row["建立時間"].strftime("%Y/%m/%d %H:%M") if pd.notna(row["建立時間"]) else "─"
                        sn_item_results = {
                            iid: ud[sn_query]
                            for iid, ud in detail.items()
                            if isinstance(ud, dict) and sn_query in ud
                        }
                        pass_cnt = sum(1 for v in sn_item_results.values() if v.get("result") == "PASS")
                        fail_cnt = sum(1 for v in sn_item_results.values() if v.get("result") == "FAIL")
                        vcol = "#e74c3c" if fail_cnt > 0 else "#27ae60"
                        vtxt = f"NG（{fail_cnt} 項）" if fail_cnt > 0 else "OK"

                        with st.expander(
                            f"📄 {row['記錄編號']}　{date_str}　{row.get('機種','─')}　{row.get('批號','─')}",
                            expanded=True,
                        ):
                            st.markdown(f"""
<div style="display:flex;gap:16px;align-items:center;
            background:#f7f9fc;border-radius:8px;padding:12px 16px;margin-bottom:10px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a">序號：
    <span style="font-family:monospace;color:#1e88e5">{sn_query}</span></div>
  <div style="font-size:13px;font-weight:700;color:{vcol}">判定：{vtxt}</div>
  <div style="font-size:11px;color:#6b7c93">
    OK {pass_cnt} 項 &nbsp;/&nbsp; NG {fail_cnt} 項
    &nbsp;/&nbsp; 批號：{row.get('批號','─')}
    &nbsp;/&nbsp; 機種：{row.get('機種','─')}
    &nbsp;/&nbsp; 料號：{row.get('料號','─')}
  </div>
</div>""", unsafe_allow_html=True)

                            show_all = st.checkbox("顯示全部項目（含 OK）",
                                                   key=f"oqc_sa_{row['記錄編號']}_{sn_query}")
                            item_rows = []
                            for iid, r_data in sn_item_results.items():
                                res = r_data.get("result","─")
                                val = r_data.get("value")
                                if not show_all and res != "FAIL":
                                    continue
                                val_str = f"{val:.2f}" if isinstance(val, (int, float)) else "─"
                                item_rows.append({"項目 ID": iid, "結果": res, "數值": val_str})
                            if item_rows:
                                idf = pd.DataFrame(item_rows)
                                def _cr(v):
                                    if v == "FAIL": return "background-color:#fdedec;color:#e74c3c;font-weight:bold"
                                    if v == "PASS": return "background-color:#eafaf1;color:#27ae60"
                                    return ""
                                try:
                                    _styled = idf.style.map(_cr, subset=["結果"])
                                except AttributeError:
                                    _styled = idf.style.applymap(_cr, subset=["結果"])
                                st.dataframe(_styled, use_container_width=True, hide_index=True,
                                             height=min(300, 56 + len(idf)*38))
                            elif not show_all and fail_cnt == 0:
                                st.success("🎉 此序號所有項目皆 OK")

        # ── OQC Tab3：全部記錄（進階查詢）────────────────────
        with oqc_t3:
            st.markdown("#### 📋 OQC 全部記錄查詢")

            # 篩選列 1：機種 / 品號 / 序號範圍 / 批號
            fa, fb, fc, fd = st.columns(4)
            with fa:
                model_opts = ["全部"] + sorted(df_oqc["機種"].dropna().unique().tolist())
                model_f = st.selectbox("機種", model_opts, key="oqc_all_model")
            with fb:
                pn_kw = st.text_input("品號 / 料號", key="oqc_all_pn", placeholder="搜尋料號…")
            with fc:
                sn_kw = st.text_input("序號範圍", key="oqc_all_sn", placeholder="搜尋序號…")
            with fd:
                lot_kw = st.text_input("批號", key="oqc_all_lot", placeholder="搜尋批號…")

            # 篩選列 2：日期 / 判定 / 檢驗員
            fe, ff, fg, fh = st.columns(4)
            with fe:
                date_from = st.date_input("日期（起）", value=None,
                                          key="oqc_all_df", format="YYYY/MM/DD")
            with ff:
                date_to = st.date_input("日期（迄）", value=None,
                                        key="oqc_all_dt", format="YYYY/MM/DD")
            with fg:
                v_opts = ["全部"] + sorted(df_oqc["總判定"].dropna().unique().tolist())
                v_f = st.selectbox("判定結果", v_opts, key="oqc_all_v")
            with fh:
                i_opts = ["全部"] + sorted(df_oqc["檢驗員"].dropna().unique().tolist())
                i_f = st.selectbox("檢驗員", i_opts, key="oqc_all_i")

            filtered = df_oqc.copy()
            if model_f != "全部":
                filtered = filtered[filtered["機種"] == model_f]
            if pn_kw.strip():
                filtered = filtered[filtered["料號"].astype(str).str.contains(pn_kw.strip(), case=False, na=False)]
            if sn_kw.strip():
                filtered = filtered[filtered["序號範圍"].astype(str).str.contains(sn_kw.strip(), case=False, na=False)]
            if lot_kw.strip():
                filtered = filtered[filtered["批號"].astype(str).str.contains(lot_kw.strip(), case=False, na=False)]
            if date_from:
                filtered = filtered[filtered["建立時間"].dt.date >= date_from]
            if date_to:
                filtered = filtered[filtered["建立時間"].dt.date <= date_to]
            if v_f != "全部":
                filtered = filtered[filtered["總判定"] == v_f]
            if i_f != "全部":
                filtered = filtered[filtered["檢驗員"] == i_f]

            st.caption(f"共 {len(filtered)} 筆")

            show_cols = [c for c in [
                "記錄編號","建立時間","產品類型","機種","料號","批號",
                "序號範圍","抽驗數量","總判定",
                "CR_不良數","MA_不良數","MI_不良數","檢驗員","主管(品保)",
            ] if c in filtered.columns]

            disp = filtered[show_cols].copy()
            if "建立時間" in disp.columns:
                disp["建立時間"] = disp["建立時間"].dt.strftime("%Y/%m/%d %H:%M")
            st.dataframe(disp, use_container_width=True, hide_index=True,
                         height=min(600, 56 + len(disp)*38))

            csv = disp.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ 匯出 CSV",
                data=csv.encode("utf-8-sig"),
                file_name=f"OQC_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

            # 展開各筆明細
            if len(filtered) > 0 and len(filtered) <= 50:
                st.markdown("---")
                st.markdown("##### 點擊展開各筆明細")
                for _, row in filtered.iterrows():
                    _render_oqc_record(row)
            elif len(filtered) > 50:
                st.caption("🔍 篩選結果超過 50 筆，請縮小查詢範圍以展開明細。")


# ─────────────────────────────────────────────────────────
# ██  IQC TAB  — 依機種 / 料號 / 進貨單號 / 日期區間查詢
# ─────────────────────────────────────────────────────────
with tab_iqc:
    df_iqc = _load_iqc()

    if df_iqc.empty:
        st.info("ℹ️ 尚無 IQC 資料，請先完成至少一筆進料檢驗並提交。")
    else:
        # ── 篩選條件 ────────────────────────────────────────
        st.markdown("#### 🔍 IQC 進料品質查詢")
        st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1565c0;
            border-radius:8px;padding:14px 18px;margin-bottom:14px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:12px;font-weight:700;color:#0d1b2a;margin-bottom:10px">🔎 查詢條件</div>
""", unsafe_allow_html=True)

        f1, f2, f3 = st.columns(3)
        with f1:
            part_opts = ["全部"] + sorted(
                [str(x) for x in df_iqc["零件名稱"].dropna().unique()
                 if str(x).strip() not in ("", "nan")]
            )
            iqc_part_f = st.selectbox("機種 / 零件名稱", part_opts, key="iqc_f_part")
        with f2:
            iqc_pn_kw = st.text_input("料號", key="iqc_f_pn", placeholder="輸入料號搜尋…")
        with f3:
            iqc_po_kw = st.text_input("進貨單號", key="iqc_f_po", placeholder="輸入進貨單號搜尋…")

        f4, f5, f6 = st.columns(3)
        with f4:
            iqc_date_from = st.date_input("日期（起）", value=None,
                                           key="iqc_f_df", format="YYYY/MM/DD")
        with f5:
            iqc_date_to = st.date_input("日期（迄）", value=None,
                                         key="iqc_f_dt", format="YYYY/MM/DD")
        with f6:
            v_opts_iqc = ["全部"] + sorted(
                [str(x) for x in df_iqc["總判定"].dropna().unique()
                 if str(x).strip() not in ("", "nan")]
            )
            iqc_v_f = st.selectbox("判定結果", v_opts_iqc, key="iqc_f_v")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── 套用篩選 ────────────────────────────────────────
        filtered_iqc = df_iqc.copy()
        if iqc_part_f != "全部":
            filtered_iqc = filtered_iqc[filtered_iqc["零件名稱"] == iqc_part_f]
        if iqc_pn_kw.strip():
            filtered_iqc = filtered_iqc[
                filtered_iqc["料號"].astype(str).str.contains(iqc_pn_kw.strip(), case=False, na=False)]
        if iqc_po_kw.strip():
            filtered_iqc = filtered_iqc[
                filtered_iqc["採購單號"].astype(str).str.contains(iqc_po_kw.strip(), case=False, na=False)]
        if iqc_date_from:
            filtered_iqc = filtered_iqc[filtered_iqc["建立時間"].dt.date >= iqc_date_from]
        if iqc_date_to:
            filtered_iqc = filtered_iqc[filtered_iqc["建立時間"].dt.date <= iqc_date_to]
        if iqc_v_f != "全部":
            filtered_iqc = filtered_iqc[filtered_iqc["總判定"] == iqc_v_f]

        # ── 統計摘要（有篩選時顯示） ─────────────────────────
        total_iqc  = len(filtered_iqc)
        np_iqc     = (filtered_iqc["總判定"] == "PASS").sum()
        nf_iqc     = total_iqc - np_iqc
        cr_iqc     = filtered_iqc["CR_不良數"].astype(int).sum() if "CR_不良數" in filtered_iqc else 0
        ma_iqc     = filtered_iqc["MA_不良數"].astype(int).sum() if "MA_不良數" in filtered_iqc else 0
        mi_iqc     = filtered_iqc["MI_不良數"].astype(int).sum() if "MI_不良數" in filtered_iqc else 0
        _stat_cards(total_iqc, np_iqc, nf_iqc, cr_iqc, ma_iqc, mi_iqc, f"{total_iqc} 筆")

        # ── 清單一覽 ────────────────────────────────────────
        iqc_show_cols = [c for c in [
            "記錄編號", "建立時間", "零件名稱", "料號", "供應商",
            "採購單號", "進料數量", "抽樣數量",
            "總判定", "CR_不良數", "MA_不良數", "MI_不良數", "IQC檢驗員",
        ] if c in filtered_iqc.columns]

        disp_iqc = filtered_iqc[iqc_show_cols].copy()
        if "建立時間" in disp_iqc.columns:
            disp_iqc["建立時間"] = disp_iqc["建立時間"].dt.strftime("%Y/%m/%d %H:%M")

        # 欄位重命名：採購單號 → 進貨單號（顯示用）
        disp_iqc = disp_iqc.rename(columns={"採購單號": "進貨單號"})

        st.caption(f"共 {total_iqc} 筆")
        st.dataframe(disp_iqc, use_container_width=True, hide_index=True,
                     height=min(500, 56 + len(disp_iqc) * 38))

        csv_iqc = disp_iqc.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ 匯出 CSV",
            data=csv_iqc.encode("utf-8-sig"),
            file_name=f"IQC_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

        # ── 個別明細展開 ────────────────────────────────────
        if 0 < total_iqc <= 50:
            st.markdown("---")
            st.markdown("##### 點擊展開各筆明細")
            for _, row in filtered_iqc.iterrows():
                _render_iqc_record(row)
        elif total_iqc > 50:
            st.caption("🔍 篩選結果超過 50 筆，請縮小查詢範圍以展開明細。")
        else:
            st.info("ℹ️ 無符合條件的記錄，請調整查詢條件。")
