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
from utils.gsheet import load_oqc_records, load_iqc_records, load_ipqc_records, update_oqc_record, delete_oqc_records

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
    "OQC 出廠檢驗 & IQC 進料品質 & IPQC 製程巡檢 — 批號 / 序號 / 日期 / 巡查員",
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


@st.cache_data(ttl=300, show_spinner="載入 IPQC 資料中…")
def _load_ipqc() -> pd.DataFrame:
    try:
        df = load_ipqc_records()
        if not df.empty:
            df["建立時間"] = pd.to_datetime(df["建立時間"], errors="coerce")
            df = df.sort_values("建立時間", ascending=False).reset_index(drop=True)
        return df
    except Exception as ex:
        st.warning(f"⚠️ 無法載入 IPQC 資料：{ex}")
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
tab_oqc, tab_iqc, tab_ipqc = st.tabs(["📦 出廠檢驗追蹤 (OQC)", "🔬 IQC 進料追蹤", "📋 IPQC 製程巡檢追蹤"])

# ─────────────────────────────────────────────────────────
# ██  OQC TAB
# ─────────────────────────────────────────────────────────
with tab_oqc:
    df_oqc = _load_oqc()

    if df_oqc.empty:
        st.info("ℹ️ 尚無 OQC 資料，請先完成至少一筆出廠檢驗並提交。")
    else:
        oqc_t1, oqc_t2, oqc_t3, oqc_t4 = st.tabs(
            ["📦 批號追蹤", "🔎 SN 序號追蹤", "📋 全部記錄", "✏️ 修改檢驗單"]
        )

        # ── OQC Tab1：批號 + 品號 + 出貨日期 + 機種 查詢 ───────
        with oqc_t1:
            st.markdown("#### 🔍 出廠檢驗查詢")
            st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1565c0;
            border-radius:8px;padding:14px 18px;margin-bottom:14px;
            box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:12px;font-weight:700;color:#0d1b2a;margin-bottom:10px">🔎 查詢條件（可組合使用）</div>
""", unsafe_allow_html=True)

            q1, q2, q3 = st.columns(3)
            with q1:
                model_opts_t1 = ["全部機種"] + sorted(
                    [str(x) for x in df_oqc["機種"].dropna().unique()
                     if str(x).strip() not in ("", "nan")]
                )
                t1_model = st.selectbox("機種", model_opts_t1, key="oqc_t1_model")
            with q2:
                t1_pn = st.text_input("品號 / 料號", placeholder="輸入料號搜尋…",
                                      key="oqc_t1_pn")
            with q3:
                lot_list = sorted(
                    [str(x) for x in df_oqc["批號"].dropna().unique()
                     if str(x).strip() not in ("", "nan")],
                    reverse=True,
                )
                lot_input = st.text_input("批號（留空則不限）",
                                          placeholder="例：2026-05-A001",
                                          key="oqc_lot_input")

            q4, q5, q6 = st.columns(3)
            with q4:
                t1_date_from = st.date_input("出貨日期（起）", value=None,
                                             key="oqc_t1_df", format="YYYY/MM/DD")
            with q5:
                t1_date_to = st.date_input("出貨日期（迄）", value=None,
                                           key="oqc_t1_dt", format="YYYY/MM/DD")
            with q6:
                v_opts_t1 = ["全部"] + sorted(df_oqc["總判定"].dropna().unique().tolist())
                t1_verdict = st.selectbox("判定結果", v_opts_t1, key="oqc_t1_v")

            st.markdown("</div>", unsafe_allow_html=True)

            # 套用篩選
            t1_view = df_oqc.copy()
            if t1_model != "全部機種":
                t1_view = t1_view[t1_view["機種"] == t1_model]
            if t1_pn.strip():
                t1_view = t1_view[t1_view["料號"].astype(str).str.contains(
                    t1_pn.strip(), case=False, na=False)]
            if lot_input.strip():
                t1_view = t1_view[t1_view["批號"].astype(str).str.contains(
                    lot_input.strip(), case=False, na=False)]
            if t1_date_from:
                t1_view = t1_view[t1_view["建立時間"].dt.date >= t1_date_from]
            if t1_date_to:
                t1_view = t1_view[t1_view["建立時間"].dt.date <= t1_date_to]
            if t1_verdict != "全部":
                t1_view = t1_view[t1_view["總判定"] == t1_verdict]

            any_filter = (
                t1_model != "全部機種" or t1_pn.strip() or lot_input.strip()
                or t1_date_from or t1_date_to or t1_verdict != "全部"
            )

            if not any_filter:
                # 未輸入任何條件時顯示最近批號摘要
                st.markdown("##### 最近批號一覽（輸入條件後自動篩選）")
                recent = (
                    df_oqc.groupby("批號", dropna=False)
                    .agg(
                        筆數    =("記錄編號", "count"),
                        最近日期=("建立時間", "max"),
                        機種    =("機種", lambda x: " / ".join(x.dropna().unique()[:3])),
                        料號    =("料號", lambda x: " / ".join(x.dropna().unique()[:2])),
                        合格率  =("總判定", lambda x: f"{(x=='PASS').mean()*100:.0f}%"),
                    )
                    .sort_values("最近日期", ascending=False)
                    .head(15)
                    .reset_index()
                )
                recent["最近日期"] = recent["最近日期"].dt.strftime("%Y/%m/%d")
                st.dataframe(recent, use_container_width=True, hide_index=True)
                st.caption("💡 設定上方條件（品號 / 出貨日期 / 機種 / 批號）可篩選明細")
            else:
                total  = len(t1_view)
                n_pass = (t1_view["總判定"] == "PASS").sum()
                n_fail = total - n_pass
                cr_s   = t1_view["CR_不良數"].astype(int).sum() if "CR_不良數" in t1_view else 0
                ma_s   = t1_view["MA_不良數"].astype(int).sum() if "MA_不良數" in t1_view else 0
                mi_s   = t1_view["MI_不良數"].astype(int).sum() if "MI_不良數" in t1_view else 0
                label  = lot_input.strip() or t1_pn.strip() or t1_model or f"{total} 筆"
                _stat_cards(total, n_pass, n_fail, cr_s, ma_s, mi_s, label)

                if t1_view.empty:
                    st.warning("⚠️ 沒有符合條件的記錄")
                else:
                    # 摘要清單
                    sum_cols = [c for c in [
                        "記錄編號","建立時間","機種","料號","批號",
                        "序號範圍","抽驗數量","總判定","CR_不良數","MA_不良數","MI_不良數","檢驗員",
                    ] if c in t1_view.columns]
                    sum_disp = t1_view[sum_cols].copy()
                    if "建立時間" in sum_disp.columns:
                        sum_disp["建立時間"] = sum_disp["建立時間"].dt.strftime("%Y/%m/%d %H:%M")
                    st.caption(f"共 {total} 筆")
                    st.dataframe(sum_disp, use_container_width=True, hide_index=True,
                                 height=min(420, 56 + len(sum_disp) * 38))

                    # 明細展開（≤30 筆才展開）
                    if total <= 30:
                        st.markdown("---")
                        st.markdown("##### 點擊展開各筆明細")
                        for _, row in t1_view.iterrows():
                            _render_oqc_record(row)
                    else:
                        st.caption("🔍 結果超過 30 筆，請縮小查詢範圍以展開明細。")

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

        # ── OQC Tab4：修改檢驗單 ──────────────────────────
        with oqc_t4:
            st.markdown("#### ✏️ 修改已提交的檢驗單")
            st.markdown("""
<div style="background:#fffbea;border:1px solid #f5c518;border-left:4px solid #f5c518;
            border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:12px;color:#555">
  ⚠️ 修改將直接更新 Google Sheet 原始記錄。僅限修改表頭欄位（機種/料號/批號/數量/檢驗員/備註/判定），
  序號明細（明細JSON）請至原始工作表修改。
</div>""", unsafe_allow_html=True)

            # 選擇要修改的記錄
            rec_opts = df_oqc["記錄編號"].dropna().tolist()
            if not rec_opts:
                st.info("尚無 OQC 記錄可供修改。")
            else:
                e1, e2 = st.columns([3, 1])
                with e1:
                    edit_kw = st.text_input("搜尋記錄（輸入記錄編號 / 機種 / 料號 / 批號）",
                                            placeholder="例：OQC-MD-2026-0001 或 機種名稱",
                                            key="oqc_edit_kw")
                with e2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    edit_show_all = st.checkbox("顯示全部", key="oqc_edit_show_all")

                # 篩選可選記錄
                edit_pool = df_oqc.copy()
                if edit_kw.strip() and not edit_show_all:
                    kw = edit_kw.strip()
                    edit_pool = edit_pool[
                        edit_pool["記錄編號"].astype(str).str.contains(kw, case=False, na=False) |
                        edit_pool["機種"].astype(str).str.contains(kw, case=False, na=False) |
                        edit_pool["料號"].astype(str).str.contains(kw, case=False, na=False) |
                        edit_pool["批號"].astype(str).str.contains(kw, case=False, na=False)
                    ]

                if edit_pool.empty:
                    st.warning("找不到符合條件的記錄，請調整搜尋關鍵字。")
                else:
                    # 下拉選單格式：記錄編號 | 日期 | 機種 | 批號
                    def _rec_label(r):
                        dt = r["建立時間"].strftime("%Y/%m/%d") if pd.notna(r["建立時間"]) else "─"
                        return f"{r['記錄編號']}　{dt}　{r.get('機種','─')}　{r.get('批號','─')}"

                    edit_labels = edit_pool.apply(_rec_label, axis=1).tolist()
                    edit_rec_ids = edit_pool["記錄編號"].tolist()
                    label_map = dict(zip(edit_labels, edit_rec_ids))

                    sel_label = st.selectbox(
                        f"選擇要修改的記錄（共 {len(edit_pool)} 筆）",
                        edit_labels,
                        key="oqc_edit_sel"
                    )
                    sel_rec_id = label_map.get(sel_label, "")

                    if sel_rec_id:
                        cur_row = df_oqc[df_oqc["記錄編號"] == sel_rec_id].iloc[0]

                        st.markdown("---")
                        st.markdown(f"**修改：`{sel_rec_id}`**")

                        with st.form("oqc_edit_form"):
                            ef1, ef2, ef3 = st.columns(3)
                            with ef1:
                                e_model = st.text_input(
                                    "機種",
                                    value=str(cur_row.get("機種", "")),
                                    key="ef_model"
                                )
                            with ef2:
                                e_pn = st.text_input(
                                    "料號（品號）",
                                    value=str(cur_row.get("料號", "")),
                                    key="ef_pn"
                                )
                            with ef3:
                                e_customer = st.text_input(
                                    "客戶名稱",
                                    value=str(cur_row.get("客戶名稱", "")),
                                    key="ef_cust"
                                )

                            ef4, ef5, ef6 = st.columns(3)
                            with ef4:
                                e_batch = st.text_input(
                                    "批號",
                                    value=str(cur_row.get("批號", "")),
                                    key="ef_batch"
                                )
                            with ef5:
                                e_serial = st.text_input(
                                    "序號範圍",
                                    value=str(cur_row.get("序號範圍", "")),
                                    key="ef_serial"
                                )
                            with ef6:
                                e_qty = st.text_input(
                                    "本批數量",
                                    value=str(cur_row.get("本批數量", "")),
                                    key="ef_qty"
                                )

                            ef7, ef8, ef9 = st.columns(3)
                            with ef7:
                                e_sample = st.text_input(
                                    "抽驗數量",
                                    value=str(cur_row.get("抽驗數量", "")),
                                    key="ef_sample"
                                )
                            with ef8:
                                e_inspector = st.text_input(
                                    "檢驗員",
                                    value=str(cur_row.get("檢驗員", "")),
                                    key="ef_insp"
                                )
                            with ef9:
                                e_supervisor = st.text_input(
                                    "主管(品保)",
                                    value=str(cur_row.get("主管(品保)", "")),
                                    key="ef_sup"
                                )

                            ef10, ef11 = st.columns([1, 2])
                            with ef10:
                                verdict_opts = ["PASS", "FAIL", "FAIL(MI)", "待審"]
                                cur_v = str(cur_row.get("總判定", "PASS"))
                                v_idx = verdict_opts.index(cur_v) if cur_v in verdict_opts else 0
                                e_verdict = st.selectbox(
                                    "總判定",
                                    verdict_opts,
                                    index=v_idx,
                                    key="ef_verdict"
                                )
                            with ef11:
                                e_note = st.text_area(
                                    "備註",
                                    value=str(cur_row.get("備註", "")),
                                    height=68,
                                    key="ef_note"
                                )

                            e_ng_summary = st.text_area(
                                "NG 項目摘要（若有修改請更新）",
                                value=str(cur_row.get("NG_項目摘要", "")) if str(cur_row.get("NG_項目摘要", "")) != "nan" else "",
                                height=60,
                                key="ef_ng"
                            )

                            save_btn = st.form_submit_button("💾 儲存修改", type="primary")

                        if save_btn:
                            updates = {
                                "機種":       e_model,
                                "料號":       e_pn,
                                "客戶名稱":   e_customer,
                                "批號":       e_batch,
                                "序號範圍":   e_serial,
                                "本批數量":   e_qty,
                                "抽驗數量":   e_sample,
                                "檢驗員":     e_inspector,
                                "主管(品保)": e_supervisor,
                                "總判定":     e_verdict,
                                "備註":       e_note,
                                "NG_項目摘要": e_ng_summary,
                            }
                            with st.spinner("更新中…"):
                                ok = update_oqc_record(sel_rec_id, updates)
                            if ok:
                                st.success(f"✅ {sel_rec_id} 已成功更新！")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ 找不到記錄 {sel_rec_id}，請重新整理後再試。")

            # ── 刪除區塊 ──────────────────────────────────
            st.markdown("---")
            st.markdown("""
<div style="background:#fff0f0;border:1px solid #f5b7b1;border-left:4px solid #c0392b;
            border-radius:8px;padding:10px 14px;margin-bottom:10px">
  <span style="font-size:13px;font-weight:700;color:#c0392b">🗑️ 刪除 OQC 檢驗單</span>
  <span style="font-size:11px;color:#888;margin-left:8px">刪除後無法還原，請謹慎操作</span>
</div>""", unsafe_allow_html=True)

            if not rec_opts:
                st.info("尚無 OQC 記錄。")
            else:
                # ── 篩選列（讓使用者先縮小範圍再勾選）──────
                d1, d2, d3 = st.columns(3)
                with d1:
                    del_model_opts = ["全部機種"] + sorted(
                        [str(x) for x in df_oqc["機種"].dropna().unique()
                         if str(x).strip() not in ("", "nan")]
                    )
                    del_model = st.selectbox("機種篩選", del_model_opts, key="del_model")
                with d2:
                    del_pn = st.text_input("品號 / 料號篩選", placeholder="輸入料號…",
                                           key="del_pn")
                with d3:
                    del_kw = st.text_input("批號 / 記錄編號篩選", placeholder="輸入批號或記錄編號…",
                                           key="del_kw")

                del_pool = df_oqc.copy()
                if del_model != "全部機種":
                    del_pool = del_pool[del_pool["機種"] == del_model]
                if del_pn.strip():
                    del_pool = del_pool[del_pool["料號"].astype(str).str.contains(
                        del_pn.strip(), case=False, na=False)]
                if del_kw.strip():
                    del_pool = del_pool[
                        del_pool["批號"].astype(str).str.contains(del_kw.strip(), case=False, na=False) |
                        del_pool["記錄編號"].astype(str).str.contains(del_kw.strip(), case=False, na=False)
                    ]

                if del_pool.empty:
                    st.warning("找不到符合條件的記錄。")
                else:
                    # 勾選表格
                    del_show = del_pool[[c for c in [
                        "記錄編號","建立時間","機種","料號","批號",
                        "序號範圍","抽驗數量","總判定","檢驗員",
                    ] if c in del_pool.columns]].copy()
                    if "建立時間" in del_show.columns:
                        del_show["建立時間"] = del_show["建立時間"].dt.strftime("%Y/%m/%d %H:%M")

                    del_show.insert(0, "勾選刪除", False)

                    edited = st.data_editor(
                        del_show,
                        use_container_width=True,
                        hide_index=True,
                        height=min(480, 56 + len(del_show) * 38),
                        column_config={
                            "勾選刪除": st.column_config.CheckboxColumn(
                                "☑ 刪除", width=70, default=False
                            ),
                            "記錄編號": st.column_config.TextColumn("記錄編號", width=180),
                            "建立時間": st.column_config.TextColumn("建立時間", width=140),
                            "機種":     st.column_config.TextColumn("機種",     width=130),
                            "料號":     st.column_config.TextColumn("料號",     width=120),
                            "批號":     st.column_config.TextColumn("批號",     width=140),
                            "序號範圍": st.column_config.TextColumn("序號範圍", width=120),
                            "抽驗數量": st.column_config.TextColumn("抽驗",     width=60),
                            "總判定":   st.column_config.TextColumn("判定",     width=80),
                            "檢驗員":   st.column_config.TextColumn("檢驗員",   width=80),
                        },
                        disabled=[c for c in del_show.columns if c != "勾選刪除"],
                        key="del_editor",
                    )

                    to_delete = edited[edited["勾選刪除"] == True]["記錄編號"].tolist()

                    if to_delete:
                        st.markdown(
                            f'<div style="background:#fdedec;border:1px solid #f5b7b1;'
                            f'border-radius:6px;padding:8px 14px;font-size:12px;margin:6px 0">'
                            f'已勾選 <b style="color:#c0392b">{len(to_delete)}</b> 筆：'
                            f'{" ｜ ".join(to_delete)}</div>',
                            unsafe_allow_html=True
                        )
                        confirm_del = st.checkbox(
                            f"⚠️ 我確認永久刪除以上 {len(to_delete)} 筆記錄（無法還原）",
                            key="del_confirm"
                        )
                        del_exec_btn = st.button(
                            f"🗑️ 確認刪除 {len(to_delete)} 筆",
                            type="primary",
                            disabled=not confirm_del,
                            key="del_exec"
                        )
                        if del_exec_btn:
                            with st.spinner(f"刪除 {len(to_delete)} 筆記錄中…"):
                                result = delete_oqc_records(to_delete)
                            n_ok  = len(result["deleted"])
                            n_bad = len(result["not_found"])
                            if n_ok:
                                st.success(f"✅ 已成功刪除 {n_ok} 筆：{', '.join(result['deleted'])}")
                            if n_bad:
                                st.warning(f"⚠️ {n_bad} 筆找不到（可能已被刪除）：{', '.join(result['not_found'])}")
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        st.caption("💡 勾選左側核取方塊以選取要刪除的記錄")


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


# ─────────────────────────────────────────────────────────
# ██  IPQC TAB  — 依機種 / 日期 / 巡查員 / 類型查詢
# ─────────────────────────────────────────────────────────
with tab_ipqc:
    df_ipqc = _load_ipqc()

    if df_ipqc.empty:
        st.info("ℹ️ 尚無 IPQC 記錄，請先完成至少一筆巡檢並點「💾 提交記錄至雲端」。")
    else:
        st.markdown("#### 🔍 IPQC 製程巡檢查詢")
        st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #e67e22;
            border-radius:8px;padding:14px 18px;margin-bottom:14px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:12px;font-weight:700;color:#0d1b2a;margin-bottom:10px">🔎 查詢條件</div>
""", unsafe_allow_html=True)

        ip1, ip2, ip3, ip4 = st.columns(4)
        with ip1:
            model_opts_ip = ["全部"] + sorted(
                [str(x) for x in df_ipqc["機種名稱"].dropna().unique()
                 if str(x).strip() not in ("", "nan")]
            )
            ip_model_f = st.selectbox("機種", model_opts_ip, key="ip_f_model")
        with ip2:
            type_opts = ["全部", "巡檢", "首台FAI"]
            ip_type_f = st.selectbox("巡檢類型", type_opts, key="ip_f_type")
        with ip3:
            ip_insp_kw = st.text_input("巡查員", key="ip_f_insp", placeholder="輸入巡查員姓名…")
        with ip4:
            ip_mfg_kw = st.text_input("製造編號", key="ip_f_mfg", placeholder="輸入製造編號…")

        ip5, ip6, ip7 = st.columns(3)
        with ip5:
            ip_date_from = st.date_input("日期（起）", value=None,
                                          key="ip_f_df", format="YYYY/MM/DD")
        with ip6:
            ip_date_to = st.date_input("日期（迄）", value=None,
                                        key="ip_f_dt", format="YYYY/MM/DD")
        with ip7:
            v_opts_ip = ["全部", "OK", "NG"]
            ip_v_f = st.selectbox("判定結果", v_opts_ip, key="ip_f_v")

        st.markdown("</div>", unsafe_allow_html=True)

        # 套用篩選
        filtered_ip = df_ipqc.copy()
        if ip_model_f != "全部":
            filtered_ip = filtered_ip[filtered_ip["機種名稱"] == ip_model_f]
        if ip_type_f != "全部":
            filtered_ip = filtered_ip[filtered_ip["巡檢類型"] == ip_type_f]
        if ip_insp_kw.strip():
            filtered_ip = filtered_ip[
                filtered_ip["巡查員"].astype(str).str.contains(ip_insp_kw.strip(), case=False, na=False)]
        if ip_mfg_kw.strip():
            filtered_ip = filtered_ip[
                filtered_ip["製造編號"].astype(str).str.contains(ip_mfg_kw.strip(), case=False, na=False)]
        if ip_date_from:
            filtered_ip = filtered_ip[filtered_ip["建立時間"].dt.date >= ip_date_from]
        if ip_date_to:
            filtered_ip = filtered_ip[filtered_ip["建立時間"].dt.date <= ip_date_to]
        if ip_v_f != "全部":
            filtered_ip = filtered_ip[filtered_ip["總判定"] == ip_v_f]

        # 統計摘要
        total_ip  = len(filtered_ip)
        ng_ip     = (filtered_ip["總判定"] == "NG").sum()
        ok_ip     = total_ip - ng_ip
        cr_ip     = pd.to_numeric(filtered_ip.get("CR_NG數", 0), errors="coerce").fillna(0).astype(int).sum()
        ma_ip     = pd.to_numeric(filtered_ip.get("MA_NG數", 0), errors="coerce").fillna(0).astype(int).sum()
        mi_ip     = pd.to_numeric(filtered_ip.get("MI_NG數", 0), errors="coerce").fillna(0).astype(int).sum()
        _stat_cards(total_ip, ok_ip, ng_ip, cr_ip, ma_ip, mi_ip, f"{total_ip} 筆")

        # 清單
        ip_show_cols = [c for c in [
            "記錄編號", "建立時間", "機種名稱", "製造編號", "日期",
            "本批數量", "不良件數", "不良率", "巡查員",
            "巡檢類型", "總判定", "NG工序數", "CR_NG數", "MA_NG數", "MI_NG數",
            "NG_工序摘要",
        ] if c in filtered_ip.columns]

        disp_ip = filtered_ip[ip_show_cols].copy()
        if "建立時間" in disp_ip.columns:
            disp_ip["建立時間"] = disp_ip["建立時間"].dt.strftime("%Y/%m/%d %H:%M")

        st.caption(f"共 {total_ip} 筆")
        st.dataframe(disp_ip, use_container_width=True, hide_index=True,
                     height=min(500, 56 + len(disp_ip) * 38))

        csv_ip = disp_ip.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ 匯出 CSV",
            data=csv_ip.encode("utf-8-sig"),
            file_name=f"IPQC_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

        # 明細展開
        if 0 < total_ip <= 50:
            st.markdown("---")
            st.markdown("##### 點擊展開各筆明細")
            for _, row in filtered_ip.iterrows():
                date_str = row["建立時間"].strftime("%Y/%m/%d %H:%M") if pd.notna(row["建立時間"]) else "─"
                vcolor   = "#e74c3c" if str(row.get("總判定")) == "NG" else "#27ae60"
                with st.expander(
                    f"📋 {row['記錄編號']}　{date_str}　{row.get('機種名稱','─')}　"
                    f"{row.get('巡檢類型','─')}　判定：{row.get('總判定','─')}",
                ):
                    r1, r2, r3, r4, r5 = st.columns(5)
                    r1.metric("機種",   str(row.get("機種名稱", "─")))
                    r2.metric("製造編號", str(row.get("製造編號", "─")))
                    r3.metric("巡查員", str(row.get("巡查員", "─")))
                    r4.metric("巡檢類型", str(row.get("巡檢類型", "─")))
                    r5.metric("不良率",  str(row.get("不良率", "─")))

                    ng_txt = str(row.get("NG_工序摘要", ""))
                    if ng_txt and ng_txt not in ("", "nan"):
                        st.markdown(f"""
<div style="background:#fff8f7;border:1px solid #f5b7b1;border-radius:6px;
            padding:10px 14px;font-size:12px;margin-top:8px">
  <b style="color:#c0392b">NG 工序摘要：</b>{ng_txt}
</div>""", unsafe_allow_html=True)

                    r6, r7, r8 = st.columns(3)
                    r6.metric("CR NG", str(row.get("CR_NG數", 0)))
                    r7.metric("MA NG", str(row.get("MA_NG數", 0)))
                    r8.metric("MI NG", str(row.get("MI_NG數", 0)))

        elif total_ip > 50:
            st.caption("🔍 篩選結果超過 50 筆，請縮小查詢範圍以展開明細。")
        else:
            st.info("ℹ️ 無符合條件的記錄，請調整查詢條件。")
