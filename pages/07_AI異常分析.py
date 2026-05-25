"""
REXONTEC 力科 QMS — AI 異常分析
NG 模式自動識別 + AI 品質分析報告
"""
import streamlit as st
import pandas as pd
import json
from datetime import date, timedelta

from utils.style  import QMS_CSS, topbar, page_header
from utils.auth   import require_login, user_info_bar
from utils.gsheet import load_oqc_records, load_iqc_records

st.set_page_config(
    page_title="REXONTEC 力科 | AI 異常分析",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()
user_info_bar()

# ── 導覽列 ──────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 4])
with c1:
    if st.button("🏠 指揮平台", use_container_width=True): st.switch_page("app.py")
with c2:
    if st.button("📋 檢驗輸入", use_container_width=True): st.switch_page("pages/01_出廠檢驗輸入.py")
with c3:
    if st.button("📊 儀表板",   use_container_width=True): st.switch_page("pages/02_儀表板.py")
with c4:
    if st.button("🔍 追蹤查詢", use_container_width=True): st.switch_page("pages/05_追蹤查詢.py")
with c5:
    if st.button("📋 IPQC 巡檢", use_container_width=True): st.switch_page("pages/20_📋_IPQC巡檢.py")

st.markdown(page_header("AI 異常分析",
                         "NG 模式自動識別 & AI 品質分析報告生成", "AI"),
            unsafe_allow_html=True)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    _PLOTLY = True
except ImportError:
    _PLOTLY = False

# ════════════════════════════════════════════════════════
# 資料載入
# ════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner="載入資料中…")
def _load_all():
    try:
        oqc = pd.concat([load_oqc_records("esc"), load_oqc_records("motor")],
                        ignore_index=True)
        if not oqc.empty:
            oqc["建立時間"] = pd.to_datetime(oqc["建立時間"], errors="coerce")
    except Exception:
        oqc = pd.DataFrame()
    try:
        iqc = load_iqc_records()
        if not iqc.empty:
            iqc["建立時間"] = pd.to_datetime(iqc["建立時間"], errors="coerce")
    except Exception:
        iqc = pd.DataFrame()
    return oqc, iqc

df_oqc, df_iqc = _load_all()

# ════════════════════════════════════════════════════════
# 共用：解析 NG 摘要
# ════════════════════════════════════════════════════════
def _parse_ng_summary(df: pd.DataFrame) -> pd.DataFrame:
    """從 NG_項目摘要 欄解析出每個 NG 項目的 grade / name / 批號 / 機種"""
    rows = []
    for _, r in df.iterrows():
        ng_txt = str(r.get("NG_項目摘要", ""))
        if ng_txt.strip() in ("", "nan"):
            continue
        for item in ng_txt.split("；"):
            item = item.strip()
            if not item:
                continue
            grade = "CR" if "[CR]" in item else ("MA" if "[MA]" in item else "MI")
            name  = (item.replace("[CR]","").replace("[MA]","").replace("[MI]","")
                         .split("(")[0].strip()[:30])
            rows.append({
                "等級":   grade,
                "NG項目": name,
                "批號":   str(r.get("批號","─")),
                "機種":   str(r.get("機種","─")),
                "檢驗員": str(r.get("檢驗員","─")),
                "日期":   r.get("建立時間"),
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["等級","NG項目","批號","機種","檢驗員","日期"])


# ════════════════════════════════════════════════════════
# Tab
# ════════════════════════════════════════════════════════
tab_ng, tab_ai = st.tabs(["🔍 NG 模式自動識別", "🤖 AI 品質分析報告"])


# ─────────────────────────────────────────────────────────
# Tab 1：NG 模式自動識別
# ─────────────────────────────────────────────────────────
with tab_ng:
    if df_oqc.empty and df_iqc.empty:
        st.info("ℹ️ 尚無任何檢驗資料")
        st.stop()

    # 日期篩選
    today = date.today()
    fa, fb, fc = st.columns([2, 2, 4])
    with fa:
        ng_from = st.date_input("起始日期", value=date(today.year, 1, 1),
                                key="ng_df", format="YYYY/MM/DD")
    with fb:
        ng_to   = st.date_input("結束日期", value=today,
                                key="ng_dt", format="YYYY/MM/DD")
    with fc:
        quick = st.radio("快速選擇", ["本月","近3個月","今年","全部"],
                         horizontal=True, key="ng_quick")
        if quick == "本月":     ng_from = date(today.year, today.month, 1)
        elif quick == "近3個月": ng_from = today - timedelta(days=90)
        elif quick == "今年":    ng_from = date(today.year, 1, 1)

    # 套用日期篩選
    def _filt(df):
        if df.empty or "建立時間" not in df.columns: return df
        return df[(df["建立時間"].dt.date >= ng_from) &
                  (df["建立時間"].dt.date <= ng_to)].copy()

    oqc_f = _filt(df_oqc)
    iqc_f = _filt(df_iqc)

    st.markdown("---")

    # ── OQC NG 分析 ──────────────────────────────────────
    st.markdown("### 📦 OQC 出廠檢驗 NG 模式")

    ng_df = _parse_ng_summary(oqc_f)

    if ng_df.empty:
        st.success("🎉 此期間 OQC 無任何 NG 記錄！")
    else:
        # 統計
        ng_count = (ng_df.groupby(["NG項目","等級"])
                    .size().reset_index(name="出現次數")
                    .sort_values("出現次數", ascending=False))

        # 批號重複 NG（同一項目出現 ≥2 次）
        repeat_ng = ng_count[ng_count["出現次數"] >= 2].copy()

        # KPI
        kc1, kc2, kc3, kc4 = st.columns(4)
        kc1.metric("NG 總項次",   len(ng_df))
        kc2.metric("不重複 NG 項目", ng_count["NG項目"].nunique())
        kc3.metric("重複出現（≥2次）", len(repeat_ng))
        kc4.metric("受影響批號數", ng_df["批號"].nunique())

        st.markdown("<br>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)

        # ── Top NG 項目 ──────────────────────────────────
        with col_a:
            st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #c0392b;
            border-radius:8px;padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🏆 Top NG 項目排行（出現次數）
  </div>""", unsafe_allow_html=True)

            top10 = ng_count.head(10)
            color_map = {"CR":"#c0392b","MA":"#d68910","MI":"#1e8449"}

            if _PLOTLY:
                fig = px.bar(top10, x="出現次數", y="NG項目", orientation="h",
                             color="等級", color_discrete_map=color_map,
                             text="出現次數")
                fig.update_traces(textposition="outside")
                fig.update_layout(
                    height=300, margin=dict(l=10,r=30,t=5,b=5),
                    xaxis_title="", yaxis_title="",
                    plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=-0.15),
                    yaxis=dict(autorange="reversed"),
                    font=dict(size=11),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(top10, use_container_width=True, hide_index=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # ── 機種 × NG 項目熱力圖 ─────────────────────────
        with col_b:
            st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1e88e5;
            border-radius:8px;padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🗺️ 機種 × NG 項目 交叉分析
  </div>""", unsafe_allow_html=True)

            if ng_df["機種"].nunique() > 0 and ng_df["NG項目"].nunique() > 0:
                heat = (ng_df.groupby(["機種","NG項目"])
                        .size().reset_index(name="次數"))
                top_items = ng_count["NG項目"].head(8).tolist()
                heat = heat[heat["NG項目"].isin(top_items)]

                if not heat.empty and _PLOTLY:
                    pivot = heat.pivot_table(index="機種", columns="NG項目",
                                             values="次數", fill_value=0)
                    fig2 = px.imshow(pivot, color_continuous_scale="Reds",
                                     aspect="auto", text_auto=True)
                    fig2.update_layout(
                        height=300, margin=dict(l=10,r=10,t=5,b=5),
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(size=10),
                        coloraxis_showscale=False,
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.dataframe(heat, use_container_width=True, hide_index=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # ── 重複 NG 警示 ──────────────────────────────────
        if not repeat_ng.empty:
            st.markdown("""
<div style="background:#fff8f7;border:1px solid #f5b7b1;border-left:4px solid #c0392b;
            border-radius:8px;padding:14px 18px;margin-top:10px">
  <div style="font-size:13px;font-weight:700;color:#c0392b;margin-bottom:10px">
    ⚠️ 重複出現 NG 警示（同項目出現 ≥ 2 次，需重點關注）
  </div>""", unsafe_allow_html=True)

            for _, rw in repeat_ng.iterrows():
                grade_color = color_map.get(rw["等級"], "#888")
                batches = ng_df[ng_df["NG項目"] == rw["NG項目"]]["批號"].unique()
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;padding:7px 0;
            border-bottom:1px solid #fde8e6">
  <span style="background:{grade_color};color:#fff;padding:1px 8px;
               border-radius:4px;font-size:10px;font-weight:800">{rw['等級']}</span>
  <span style="font-size:12.5px;font-weight:700;flex:1">{rw['NG項目']}</span>
  <span style="background:#fdedec;color:#c0392b;padding:2px 10px;border-radius:99px;
               font-size:11px;font-weight:700">{rw['出現次數']} 次</span>
  <span style="font-size:11px;color:#6b7c93">批號：{' / '.join(batches[:5])}</span>
</div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── NG 明細表 ──────────────────────────────────────
        with st.expander("📋 NG 完整明細", expanded=False):
            disp_ng = ng_df.copy()
            if "日期" in disp_ng.columns:
                disp_ng["日期"] = disp_ng["日期"].dt.strftime("%Y/%m/%d")
            st.dataframe(disp_ng, use_container_width=True, hide_index=True)

    # ── IQC NG 分析 ──────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔬 IQC 進料品質 NG 模式")

    if iqc_f.empty:
        st.info("ℹ️ 此期間無 IQC 資料")
    else:
        iqc_ng_rows = []
        for _, r in iqc_f.iterrows():
            ng_txt = str(r.get("NG_項目摘要",""))
            if ng_txt.strip() in ("","nan"): continue
            for item in ng_txt.split("；"):
                item = item.strip()
                if item:
                    iqc_ng_rows.append({
                        "NG項目":  item[:30],
                        "零件名稱": str(r.get("零件名稱","─")),
                        "供應商":  str(r.get("供應商","─")),
                        "批號":    str(r.get("批號","─")),
                    })

        if not iqc_ng_rows:
            st.success("🎉 此期間 IQC 無任何 NG 記錄！")
        else:
            iqc_ng_df = pd.DataFrame(iqc_ng_rows)
            ic1, ic2 = st.columns(2)

            with ic1:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1565c0;
            border-radius:8px;padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📦 零件 NG 頻率排行
  </div>""", unsafe_allow_html=True)

                part_ng = (iqc_ng_df.groupby("零件名稱")
                           .size().reset_index(name="NG次數")
                           .sort_values("NG次數", ascending=False))

                if _PLOTLY:
                    fig3 = px.bar(part_ng, x="NG次數", y="零件名稱",
                                  orientation="h", text="NG次數",
                                  color_discrete_sequence=["#1565c0"])
                    fig3.update_traces(textposition="outside")
                    fig3.update_layout(
                        height=250, margin=dict(l=10,r=30,t=5,b=5),
                        plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                        xaxis_title="", yaxis_title="",
                        yaxis=dict(autorange="reversed"), font=dict(size=11),
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.dataframe(part_ng, use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with ic2:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #d68910;
            border-radius:8px;padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🏭 供應商 NG 頻率排行
  </div>""", unsafe_allow_html=True)

                vendor_ng = (iqc_ng_df.groupby("供應商")
                             .size().reset_index(name="NG次數")
                             .sort_values("NG次數", ascending=False))

                if _PLOTLY:
                    fig4 = px.bar(vendor_ng, x="NG次數", y="供應商",
                                  orientation="h", text="NG次數",
                                  color_discrete_sequence=["#d68910"])
                    fig4.update_traces(textposition="outside")
                    fig4.update_layout(
                        height=250, margin=dict(l=10,r=30,t=5,b=5),
                        plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                        xaxis_title="", yaxis_title="",
                        yaxis=dict(autorange="reversed"), font=dict(size=11),
                    )
                    st.plotly_chart(fig4, use_container_width=True)
                else:
                    st.dataframe(vendor_ng, use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Tab 2：AI 品質分析報告
# ─────────────────────────────────────────────────────────
with tab_ai:
    st.markdown("""
<div style="background:#e8f4fd;border:1px solid #aed6f1;border-left:4px solid #1e88e5;
            border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:12.5px">
  🤖 使用 Claude AI 自動分析品質資料，生成中文品質分析報告，包含：本期品質摘要、主要異常、改善建議。
</div>""", unsafe_allow_html=True)

    # ── API Key 設定 ──────────────────────────────────────
    st.markdown("#### 🔑 Claude API 設定")

    # 優先從 secrets 讀取
    saved_key = ""
    try:
        saved_key = st.secrets.get("claude_api_key", "")
    except Exception:
        pass

    with st.expander("⚙️ API Key 設定（展開填入）", expanded=not bool(saved_key)):
        st.markdown("""
<div style="font-size:12px;color:#6b7c93;margin-bottom:8px">
  請至 <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a>
  申請免費 API Key，貼入下方即可使用。<br>
  （API Key 僅存在本次工作階段，不會上傳）
</div>""", unsafe_allow_html=True)

        api_key_input = st.text_input(
            "Claude API Key",
            value=saved_key,
            type="password",
            placeholder="sk-ant-api03-...",
            key="claude_api_key_input",
        )

        if api_key_input:
            st.success("✅ API Key 已填入")

    api_key = api_key_input if api_key_input else saved_key

    st.markdown("---")

    # ── 分析設定 ──────────────────────────────────────────
    st.markdown("#### 📅 分析設定")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        ai_from = st.date_input("分析起始日期",
                                value=date(today.year, today.month, 1),
                                key="ai_df", format="YYYY/MM/DD")
    with ac2:
        ai_to = st.date_input("分析結束日期", value=today,
                              key="ai_dt", format="YYYY/MM/DD")
    with ac3:
        report_lang = st.selectbox("報告語言", ["繁體中文", "English"], key="ai_lang")

    include_oqc = st.checkbox("包含 OQC 出廠檢驗分析", value=True, key="ai_oqc")
    include_iqc = st.checkbox("包含 IQC 進料品質分析", value=True, key="ai_iqc")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 生成報告 ──────────────────────────────────────────
    gen_btn = st.button("🤖 生成 AI 品質分析報告",
                        type="primary", use_container_width=True,
                        disabled=not bool(api_key))

    if not api_key:
        st.warning("⚠️ 請先填入 Claude API Key 才能生成報告")

    if gen_btn and api_key:
        with st.spinner("AI 正在分析品質資料，生成報告中…"):
            try:
                # ── 整理分析資料 ──────────────────────────
                def _filt_date(df):
                    if df.empty or "建立時間" not in df.columns: return df
                    return df[(df["建立時間"].dt.date >= ai_from) &
                              (df["建立時間"].dt.date <= ai_to)].copy()

                oqc_a = _filt_date(df_oqc) if include_oqc else pd.DataFrame()
                iqc_a = _filt_date(df_iqc) if include_iqc else pd.DataFrame()

                summary_parts = []

                # OQC 摘要
                if not oqc_a.empty:
                    total_o  = len(oqc_a)
                    pass_o   = (oqc_a["總判定"]=="PASS").sum()
                    yield_o  = f"{pass_o/total_o*100:.1f}%" if total_o else "─"
                    ng_o_df  = _parse_ng_summary(oqc_a)
                    top_ng_o = []
                    if not ng_o_df.empty:
                        top_ng_o = (ng_o_df.groupby(["NG項目","等級"])
                                    .size().reset_index(name="次數")
                                    .sort_values("次數", ascending=False)
                                    .head(5))
                        top_ng_o = [f"{r['等級']}-{r['NG項目']}({r['次數']}次)"
                                    for _, r in top_ng_o.iterrows()]

                    model_stat_o = ""
                    if "機種" in oqc_a.columns:
                        ms = (oqc_a.groupby("機種")
                              .agg(筆數=("記錄編號","count"),
                                   合格=("總判定",lambda x:(x=="PASS").sum()))
                              .reset_index())
                        ms["良率"] = (ms["合格"]/ms["筆數"]*100).round(1)
                        model_stat_o = "；".join(
                            f"{r['機種']}良率{r['良率']}%({r['筆數']}筆)"
                            for _, r in ms.iterrows())

                    summary_parts.append(f"""
【OQC 出廠檢驗】分析期間：{ai_from} ~ {ai_to}
- 總檢驗筆數：{total_o} 筆
- 合格率：{yield_o}（合格 {pass_o} 筆，不合格 {total_o-pass_o} 筆）
- 機種良率：{model_stat_o or '無'}
- Top NG 項目：{', '.join(top_ng_o) if top_ng_o else '無 NG 記錄'}
""")

                # IQC 摘要
                if not iqc_a.empty:
                    total_i = len(iqc_a)
                    pass_i  = (iqc_a["總判定"]=="PASS").sum()
                    yield_i = f"{pass_i/total_i*100:.1f}%" if total_i else "─"

                    ng_i_rows = []
                    for _, r in iqc_a.iterrows():
                        ng_txt = str(r.get("NG_項目摘要",""))
                        if ng_txt.strip() not in ("","nan"):
                            for item in ng_txt.split("；"):
                                item = item.strip()
                                if item:
                                    ng_i_rows.append({
                                        "NG項目": item,
                                        "零件":   str(r.get("零件名稱","─")),
                                        "供應商": str(r.get("供應商","─")),
                                    })

                    top_ng_i = []
                    if ng_i_rows:
                        ngi_df = pd.DataFrame(ng_i_rows)
                        top_ng_i = (ngi_df.groupby("NG項目").size()
                                    .reset_index(name="次數")
                                    .sort_values("次數",ascending=False)
                                    .head(5))
                        top_ng_i = [f"{r['NG項目']}({r['次數']}次)"
                                    for _, r in top_ng_i.iterrows()]

                    part_stat = ""
                    if "零件名稱" in iqc_a.columns:
                        ps = (iqc_a.groupby("零件名稱")
                              .agg(筆數=("記錄編號","count"),
                                   合格=("總判定",lambda x:(x=="PASS").sum()))
                              .reset_index())
                        ps["良率"] = (ps["合格"]/ps["筆數"]*100).round(1)
                        part_stat = "；".join(
                            f"{r['零件名稱']}良率{r['良率']}%"
                            for _, r in ps.iterrows())

                    summary_parts.append(f"""
【IQC 進料品質】分析期間：{ai_from} ~ {ai_to}
- 總進料檢驗：{total_i} 筆
- 合格率：{yield_i}（合格 {pass_i} 筆，不合格 {total_i-pass_i} 筆）
- 各零件良率：{part_stat or '無'}
- Top NG 項目：{', '.join(top_ng_i) if top_ng_i else '無 NG 記錄'}
""")

                if not summary_parts:
                    st.warning("此期間無可分析的資料，請調整日期範圍")
                    st.stop()

                data_summary = "\n".join(summary_parts)
                lang_note = "請用繁體中文撰寫。" if report_lang == "繁體中文" else "Please write in English."

                prompt = f"""你是一位專業的品質管理顧問（QA/QC），請根據以下 REXONTEC 力科的品質檢驗數據，撰寫一份完整的品質分析報告。

{data_summary}

{lang_note}

報告格式請包含以下章節：
1. **本期品質摘要** — 整體良率、重要數字
2. **主要異常項目** — 列出最需要關注的 NG 問題，分析可能原因
3. **趨勢判斷** — 根據現有數據判斷品質趨勢
4. **具體改善建議** — 針對主要問題提出 3~5 項可行的改善行動
5. **結論** — 一段總結

語氣專業，言簡意賅，適合在品質會議中使用。"""

                # ── 呼叫 Claude API ────────────────────────
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
                report_text = message.content[0].text

                # ── 顯示報告 ──────────────────────────────
                st.markdown("---")
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid #1e88e5;
            border-radius:8px;padding:20px 24px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:14px;font-weight:700;color:#0d1b2a;margin-bottom:16px">
    🤖 AI 品質分析報告 &nbsp;
    <span style="font-size:11px;color:#6b7c93;font-weight:400">
      分析期間：{} ~ {} ｜ 由 Claude AI 生成
    </span>
  </div>""".format(ai_from, ai_to), unsafe_allow_html=True)

                st.markdown(report_text)
                st.markdown("</div>", unsafe_allow_html=True)

                # 匯出報告
                st.markdown("<br>", unsafe_allow_html=True)
                report_export = f"REXONTEC QMS 品質分析報告\n分析期間：{ai_from} ~ {ai_to}\n\n{report_text}"
                st.download_button(
                    "⬇️ 下載報告（TXT）",
                    data=report_export.encode("utf-8"),
                    file_name=f"QMS品質報告_{ai_from}_{ai_to}.txt",
                    mime="text/plain",
                )

            except Exception as e:
                err = str(e)
                if "invalid_api_key" in err or "authentication" in err.lower():
                    st.error("❌ API Key 無效，請確認後重新填入")
                elif "insufficient_quota" in err:
                    st.error("❌ API 額度不足，請至 console.anthropic.com 確認")
                else:
                    st.error(f"❌ 生成失敗：{e}")
