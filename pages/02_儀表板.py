"""
REXONTEC 力科 QMS — Dashboard 儀表板
OQC 出廠 + IQC 進料 品質統計
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

from utils.style  import QMS_CSS, topbar, page_header
from utils.auth   import require_login, user_info_bar
from utils.gsheet import load_oqc_records, load_iqc_records, load_ipqc_records

st.set_page_config(
    page_title="REXONTEC 力科 | QMS Dashboard",
    page_icon="📊",
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
    if st.button("🔍 追蹤查詢", use_container_width=True): st.switch_page("pages/05_追蹤查詢.py")
with c6:
    if st.button("🤖 AI 分析",  use_container_width=True): st.switch_page("pages/07_AI異常分析.py")

st.markdown(page_header("Dashboard 儀表板",
                         "OQC 出廠 & IQC 進料 — 品質統計分析", "DB"),
            unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# 資料載入
# ════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner="載入資料中…")
def _load_oqc():
    try:
        df = pd.concat([load_oqc_records("esc"), load_oqc_records("motor")],
                       ignore_index=True)
        if not df.empty:
            df["建立時間"] = pd.to_datetime(df["建立時間"], errors="coerce")
            df = df.sort_values("建立時間", ascending=False).reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner="載入 IQC 資料中…")
def _load_iqc():
    try:
        df = load_iqc_records()
        if not df.empty:
            df["建立時間"] = pd.to_datetime(df["建立時間"], errors="coerce")
            df = df.sort_values("建立時間", ascending=False).reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner="載入 IPQC 資料中…")
def _load_ipqc():
    try:
        df = load_ipqc_records()
        if not df.empty:
            df["建立時間"] = pd.to_datetime(df["建立時間"], errors="coerce")
            df = df.sort_values("建立時間", ascending=False).reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()

# ── Chart 工具（優先 plotly，回退 st.bar_chart）─────────
try:
    import plotly.express as px
    import plotly.graph_objects as go
    _PLOTLY = True
except ImportError:
    _PLOTLY = False

# ════════════════════════════════════════════════════════
# 共用：統計卡片
# ════════════════════════════════════════════════════════
def _kpi_cards(total, n_pass, n_fail, cr, ma, mi, yield_label="合格率"):
    yld = f"{n_pass/total*100:.1f}%" if total else "─"
    cols = st.columns(6)
    data = [
        ("📋 總筆數",   str(total),  "#1e88e5"),
        (f"✅ {yield_label}", yld,  "#27ae60"),
        ("✓ 合格",     str(n_pass), "#27ae60"),
        ("✗ 不合格",   str(n_fail), "#e74c3c"),
        ("🔴 CR 不良",  str(cr),    "#c0392b"),
        ("🟡 MA 不良",  str(ma),    "#d68910"),
    ]
    for col, (label, val, color) in zip(cols, data):
        col.markdown(f"""
<div style="background:#fff;border:1px solid #dce3ec;border-left:4px solid {color};
            border-radius:8px;padding:14px 16px;box-shadow:0 2px 8px rgba(13,27,42,.08);
            text-align:center">
  <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1px;margin-bottom:4px">
    {label}
  </div>
  <div style="font-size:26px;font-weight:900;color:{color};font-family:'DM Mono',monospace;line-height:1">
    {val}
  </div>
</div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# 共用：日期篩選
# ════════════════════════════════════════════════════════
def _date_filter(df, prefix):
    today = date.today()
    fa, fb, fc = st.columns([2, 2, 4])
    with fa:
        d_from = st.date_input("起始日期", value=date(today.year, today.month, 1),
                               key=f"{prefix}_df", format="YYYY/MM/DD")
    with fb:
        d_to = st.date_input("結束日期", value=today,
                             key=f"{prefix}_dt", format="YYYY/MM/DD")
    with fc:
        quick = st.radio("快速選擇", ["本月", "近3個月", "今年", "全部"],
                         horizontal=True, key=f"{prefix}_quick")
        if quick == "本月":
            d_from = date(today.year, today.month, 1);  d_to = today
        elif quick == "近3個月":
            d_from = today - timedelta(days=90);         d_to = today
        elif quick == "今年":
            d_from = date(today.year, 1, 1);             d_to = today
        # 全部：維持 d_from/d_to

    if "建立時間" in df.columns and not df.empty:
        mask = (df["建立時間"].dt.date >= d_from) & (df["建立時間"].dt.date <= d_to)
        return df[mask].copy(), d_from, d_to
    return df, d_from, d_to


# ════════════════════════════════════════════════════════
# 主體
# ════════════════════════════════════════════════════════
tab_oqc, tab_iqc, tab_ipqc = st.tabs(["📦 OQC 出廠檢驗", "🔬 IQC 進料品質", "📋 IPQC 製程巡檢"])

# ─────────────────────────────────────────────────────────
# OQC Tab
# ─────────────────────────────────────────────────────────
with tab_oqc:
    df_oqc_all = _load_oqc()

    if df_oqc_all.empty:
        st.info("ℹ️ 尚無 OQC 資料，請先完成至少一筆出廠檢驗並提交。")
    else:
        # 日期篩選
        st.markdown("#### 📅 日期範圍")
        df_oqc, oqc_from, oqc_to = _date_filter(df_oqc_all, "oqc")
        st.markdown("<br>", unsafe_allow_html=True)

        if df_oqc.empty:
            st.warning("此期間無資料")
        else:
            total   = len(df_oqc)
            n_pass  = (df_oqc["總判定"] == "PASS").sum()
            n_fail  = total - n_pass
            cr_sum  = pd.to_numeric(df_oqc.get("CR_不良數", 0), errors="coerce").fillna(0).astype(int).sum()
            ma_sum  = pd.to_numeric(df_oqc.get("MA_不良數", 0), errors="coerce").fillna(0).astype(int).sum()
            mi_sum  = pd.to_numeric(df_oqc.get("MI_不良數", 0), errors="coerce").fillna(0).astype(int).sum()

            _kpi_cards(total, n_pass, n_fail, cr_sum, ma_sum, mi_sum)
            st.markdown("<br>", unsafe_allow_html=True)

            # ── 圖表區 ────────────────────────────────────
            ch1, ch2 = st.columns(2)

            # ── 月度良率趨勢 ──────────────────────────────
            with ch1:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📈 月度良率趨勢
  </div>""", unsafe_allow_html=True)

                df_oqc["月份"] = df_oqc["建立時間"].dt.to_period("M").astype(str)
                monthly = (df_oqc.groupby("月份")
                           .agg(筆數=("記錄編號","count"),
                                合格=("總判定", lambda x:(x=="PASS").sum()))
                           .reset_index())
                monthly["良率%"] = (monthly["合格"] / monthly["筆數"] * 100).round(1)

                if _PLOTLY:
                    fig = px.line(monthly, x="月份", y="良率%",
                                  markers=True, text="良率%",
                                  color_discrete_sequence=["#1e88e5"])
                    fig.update_traces(textposition="top center",
                                      texttemplate="%{text}%",
                                      line_width=2.5, marker_size=8)
                    fig.add_hline(y=100, line_dash="dot",
                                  line_color="#27ae60", opacity=0.5)
                    fig.update_layout(
                        height=260, margin=dict(l=10,r=10,t=10,b=10),
                        yaxis=dict(range=[0,105], ticksuffix="%"),
                        xaxis_title="", yaxis_title="",
                        plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(size=11),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.line_chart(monthly.set_index("月份")["良率%"])

                st.markdown("</div>", unsafe_allow_html=True)

            # ── NG Pareto ─────────────────────────────────
            with ch2:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📊 NG 項目 Pareto
  </div>""", unsafe_allow_html=True)

                ng_rows = []
                for ng_txt in df_oqc["NG_項目摘要"].dropna():
                    if str(ng_txt).strip() in ("", "nan"):
                        continue
                    for item in str(ng_txt).split("；"):
                        item = item.strip()
                        if not item:
                            continue
                        # 取出等級與名稱
                        grade = "CR" if "[CR]" in item else ("MA" if "[MA]" in item else "MI")
                        name  = item.replace("[CR]","").replace("[MA]","").replace("[MI]","").split("(")[0].strip()
                        if name:
                            ng_rows.append({"項目": name[:20], "等級": grade})

                if ng_rows:
                    ng_df = (pd.DataFrame(ng_rows)
                               .groupby(["項目","等級"])
                               .size().reset_index(name="次數")
                               .sort_values("次數", ascending=False)
                               .head(10))
                    color_map = {"CR":"#c0392b","MA":"#d68910","MI":"#1e8449"}
                    if _PLOTLY:
                        fig2 = px.bar(ng_df, x="次數", y="項目",
                                      orientation="h", color="等級",
                                      color_discrete_map=color_map,
                                      text="次數")
                        fig2.update_traces(textposition="outside")
                        fig2.update_layout(
                            height=260, margin=dict(l=10,r=30,t=10,b=10),
                            xaxis_title="", yaxis_title="",
                            plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                            legend=dict(orientation="h", y=-0.15),
                            font=dict(size=11),
                            yaxis=dict(autorange="reversed"),
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.bar_chart(ng_df.set_index("項目")["次數"])
                else:
                    st.success("🎉 此期間無 NG 記錄！")

                st.markdown("</div>", unsafe_allow_html=True)

            # ── 產品類型 & 機種分布 ───────────────────────
            ch3, ch4 = st.columns(2)

            with ch3:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🥧 電調 / 馬達 比例
  </div>""", unsafe_allow_html=True)

                if "產品類型" in df_oqc.columns:
                    pt_cnt = df_oqc["產品類型"].value_counts().reset_index()
                    pt_cnt.columns = ["類型", "筆數"]
                    if _PLOTLY:
                        fig3 = px.pie(pt_cnt, names="類型", values="筆數",
                                      color_discrete_sequence=["#1e88e5","#27ae60"],
                                      hole=0.45)
                        fig3.update_traces(textinfo="label+percent",
                                           textfont_size=12)
                        fig3.update_layout(
                            height=220, margin=dict(l=10,r=10,t=10,b=10),
                            paper_bgcolor="rgba(0,0,0,0)",
                            showlegend=False,
                        )
                        st.plotly_chart(fig3, use_container_width=True)
                    else:
                        st.bar_chart(pt_cnt.set_index("類型"))
                st.markdown("</div>", unsafe_allow_html=True)

            with ch4:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🏷️ 機種良率排行
  </div>""", unsafe_allow_html=True)

                if "機種" in df_oqc.columns:
                    model_stat = (df_oqc.groupby("機種")
                                  .agg(筆數=("記錄編號","count"),
                                       合格=("總判定", lambda x:(x=="PASS").sum()))
                                  .reset_index())
                    model_stat["良率%"] = (model_stat["合格"]/model_stat["筆數"]*100).round(1)
                    model_stat = model_stat.sort_values("良率%")

                    if _PLOTLY:
                        colors = ["#27ae60" if v==100 else ("#f39c12" if v>=80 else "#e74c3c")
                                  for v in model_stat["良率%"]]
                        fig4 = go.Figure(go.Bar(
                            x=model_stat["良率%"],
                            y=model_stat["機種"],
                            orientation="h",
                            marker_color=colors,
                            text=[f"{v}%" for v in model_stat["良率%"]],
                            textposition="outside",
                        ))
                        fig4.update_layout(
                            height=220, margin=dict(l=10,r=40,t=10,b=10),
                            xaxis=dict(range=[0,110], ticksuffix="%"),
                            xaxis_title="", yaxis_title="",
                            plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(size=11),
                        )
                        st.plotly_chart(fig4, use_container_width=True)
                    else:
                        st.bar_chart(model_stat.set_index("機種")["良率%"])
                st.markdown("</div>", unsafe_allow_html=True)

            # ── 最近記錄 ──────────────────────────────────
            st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📋 最近 20 筆 OQC 記錄
  </div>""", unsafe_allow_html=True)

            show_cols = [c for c in ["記錄編號","建立時間","產品類型","機種","批號",
                                      "抽驗數量","總判定","CR_不良數","MA_不良數","MI_不良數",
                                      "檢驗員"] if c in df_oqc.columns]
            disp = df_oqc[show_cols].head(20).copy()
            if "建立時間" in disp.columns:
                disp["建立時間"] = disp["建立時間"].dt.strftime("%Y/%m/%d %H:%M")

            st.dataframe(disp, use_container_width=True, hide_index=True,
                         height=min(500, 56 + len(disp)*38))
            st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# IQC Tab
# ─────────────────────────────────────────────────────────
with tab_iqc:
    df_iqc_all = _load_iqc()

    if df_iqc_all.empty:
        st.info("ℹ️ 尚無 IQC 資料，請先完成至少一筆進料檢驗並提交。")
    else:
        # 日期篩選
        st.markdown("#### 📅 日期範圍")
        df_iqc, iqc_from, iqc_to = _date_filter(df_iqc_all, "iqc")
        st.markdown("<br>", unsafe_allow_html=True)

        if df_iqc.empty:
            st.warning("此期間無資料")
        else:
            total_i  = len(df_iqc)
            np_i     = (df_iqc["總判定"] == "PASS").sum()
            nf_i     = total_i - np_i
            cr_i     = pd.to_numeric(df_iqc.get("CR_不良數",0), errors="coerce").fillna(0).astype(int).sum()
            ma_i     = pd.to_numeric(df_iqc.get("MA_不良數",0), errors="coerce").fillna(0).astype(int).sum()
            mi_i     = pd.to_numeric(df_iqc.get("MI_不良數",0), errors="coerce").fillna(0).astype(int).sum()

            _kpi_cards(total_i, np_i, nf_i, cr_i, ma_i, mi_i)
            st.markdown("<br>", unsafe_allow_html=True)

            ci1, ci2 = st.columns(2)

            # ── IQC 月度趨勢 ───────────────────────────────
            with ci1:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📈 月度合格率趨勢
  </div>""", unsafe_allow_html=True)

                df_iqc["月份"] = df_iqc["建立時間"].dt.to_period("M").astype(str)
                monthly_i = (df_iqc.groupby("月份")
                             .agg(筆數=("記錄編號","count"),
                                  合格=("總判定", lambda x:(x=="PASS").sum()))
                             .reset_index())
                monthly_i["良率%"] = (monthly_i["合格"]/monthly_i["筆數"]*100).round(1)

                if _PLOTLY:
                    fig5 = px.line(monthly_i, x="月份", y="良率%",
                                   markers=True, text="良率%",
                                   color_discrete_sequence=["#1565c0"])
                    fig5.update_traces(textposition="top center",
                                       texttemplate="%{text}%",
                                       line_width=2.5, marker_size=8)
                    fig5.add_hline(y=100, line_dash="dot",
                                   line_color="#27ae60", opacity=0.5)
                    fig5.update_layout(
                        height=260, margin=dict(l=10,r=10,t=10,b=10),
                        yaxis=dict(range=[0,105], ticksuffix="%"),
                        xaxis_title="", yaxis_title="",
                        plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(size=11),
                    )
                    st.plotly_chart(fig5, use_container_width=True)
                else:
                    st.line_chart(monthly_i.set_index("月份")["良率%"])
                st.markdown("</div>", unsafe_allow_html=True)

            # ── 零件合格率排行 ────────────────────────────
            with ci2:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🏷️ 零件合格率排行
  </div>""", unsafe_allow_html=True)

                if "零件名稱" in df_iqc.columns:
                    part_stat = (df_iqc.groupby("零件名稱")
                                 .agg(筆數=("記錄編號","count"),
                                      合格=("總判定", lambda x:(x=="PASS").sum()))
                                 .reset_index())
                    part_stat["良率%"] = (part_stat["合格"]/part_stat["筆數"]*100).round(1)
                    part_stat = part_stat.sort_values("良率%")

                    if _PLOTLY:
                        pcolors = ["#27ae60" if v==100 else ("#f39c12" if v>=80 else "#e74c3c")
                                   for v in part_stat["良率%"]]
                        fig6 = go.Figure(go.Bar(
                            x=part_stat["良率%"],
                            y=part_stat["零件名稱"],
                            orientation="h",
                            marker_color=pcolors,
                            text=[f"{v}%" for v in part_stat["良率%"]],
                            textposition="outside",
                        ))
                        fig6.update_layout(
                            height=260, margin=dict(l=10,r=40,t=10,b=10),
                            xaxis=dict(range=[0,110], ticksuffix="%"),
                            xaxis_title="", yaxis_title="",
                            plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(size=11),
                        )
                        st.plotly_chart(fig6, use_container_width=True)
                    else:
                        st.bar_chart(part_stat.set_index("零件名稱")["良率%"])
                st.markdown("</div>", unsafe_allow_html=True)

            # ── IQC 最近記錄 ──────────────────────────────
            st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📋 最近 20 筆 IQC 記錄
  </div>""", unsafe_allow_html=True)

            iqc_cols = [c for c in ["記錄編號","建立時間","零件名稱","料號","供應商",
                                     "採購單號","進料數量","抽樣數量",
                                     "總判定","CR_不良數","MA_不良數","MI_不良數",
                                     "IQC檢驗員"] if c in df_iqc.columns]
            disp_i = df_iqc[iqc_cols].head(20).copy()
            if "建立時間" in disp_i.columns:
                disp_i["建立時間"] = disp_i["建立時間"].dt.strftime("%Y/%m/%d %H:%M")
            disp_i = disp_i.rename(columns={"採購單號": "進貨單號"})

            st.dataframe(disp_i, use_container_width=True, hide_index=True,
                         height=min(500, 56 + len(disp_i)*38))
            st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# IPQC Tab
# ─────────────────────────────────────────────────────────
with tab_ipqc:
    df_ipqc_all = _load_ipqc()

    if df_ipqc_all.empty:
        st.info("ℹ️ 尚無 IPQC 記錄，請先完成至少一筆巡檢並點「💾 提交記錄至雲端」。")
    else:
        st.markdown("#### 📅 日期範圍")
        df_ipqc, ipqc_from, ipqc_to = _date_filter(df_ipqc_all, "ipqc")
        st.markdown("<br>", unsafe_allow_html=True)

        if df_ipqc.empty:
            st.warning("此期間無資料")
        else:
            total_ip = len(df_ipqc)
            cr_ip    = pd.to_numeric(df_ipqc.get("CR_NG數", 0), errors="coerce").fillna(0).astype(int).sum()
            ma_ip    = pd.to_numeric(df_ipqc.get("MA_NG數", 0), errors="coerce").fillna(0).astype(int).sum()
            mi_ip    = pd.to_numeric(df_ipqc.get("MI_NG數", 0), errors="coerce").fillna(0).astype(int).sum()
            ng_recs  = (df_ipqc["總判定"] == "NG").sum()
            ng_rate  = f"{ng_recs / total_ip * 100:.1f}%" if total_ip else "─"

            # KPI
            _kpi_cards(total_ip, total_ip - ng_recs, ng_recs, cr_ip, ma_ip, mi_ip, "巡檢OK率")
            st.markdown("<br>", unsafe_allow_html=True)

            ci1, ci2 = st.columns(2)

            # 月度巡檢趨勢
            with ci1:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📈 月度巡檢筆數趨勢
  </div>""", unsafe_allow_html=True)

                df_ipqc["月份"] = df_ipqc["建立時間"].dt.to_period("M").astype(str)
                monthly_ip = (df_ipqc.groupby("月份")
                              .agg(筆數=("記錄編號", "count"),
                                   NG筆=("總判定", lambda x: (x == "NG").sum()))
                              .reset_index())
                monthly_ip["OK率%"] = ((monthly_ip["筆數"] - monthly_ip["NG筆"])
                                        / monthly_ip["筆數"] * 100).round(1)

                if _PLOTLY:
                    import plotly.graph_objects as go2
                    fig_ip = go2.Figure()
                    fig_ip.add_bar(x=monthly_ip["月份"], y=monthly_ip["筆數"],
                                   name="總筆數", marker_color="#90caf9")
                    fig_ip.add_bar(x=monthly_ip["月份"], y=monthly_ip["NG筆"],
                                   name="NG筆數", marker_color="#ef9a9a")
                    fig_ip.update_layout(
                        height=260, barmode="overlay",
                        margin=dict(l=10,r=10,t=10,b=10),
                        xaxis_title="", yaxis_title="",
                        plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                        legend=dict(orientation="h", y=-0.2),
                        font=dict(size=11),
                    )
                    st.plotly_chart(fig_ip, use_container_width=True)
                else:
                    st.bar_chart(monthly_ip.set_index("月份")[["筆數", "NG筆"]])

                st.markdown("</div>", unsafe_allow_html=True)

            # NG 工序 Pareto
            with ci2:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📊 NG 工序 Pareto
  </div>""", unsafe_allow_html=True)

                ng_rows_ip = []
                for ng_txt in df_ipqc["NG_工序摘要"].dropna():
                    if str(ng_txt).strip() in ("", "nan"):
                        continue
                    for seg in str(ng_txt).split(" | "):
                        seg = seg.strip()
                        if "：" in seg:
                            station_part = seg.split("：")[0].strip()
                            st_name = station_part.split("/")[-1] if "/" in station_part else station_part
                            ng_rows_ip.append(st_name[:16])

                if ng_rows_ip:
                    import pandas as _pd2
                    ng_sdf = (_pd2.Series(ng_rows_ip).value_counts()
                                                     .reset_index()
                                                     .rename(columns={"index": "工序", 0: "次數",
                                                                       "count": "次數"})
                                                     .head(10))
                    if _PLOTLY:
                        import plotly.express as _px2
                        fig_par = _px2.bar(ng_sdf, x="次數", y=ng_sdf.columns[0],
                                           orientation="h",
                                           color_discrete_sequence=["#e67e22"])
                        fig_par.update_traces(texttemplate="%{x}", textposition="outside")
                        fig_par.update_layout(
                            height=260, margin=dict(l=10,r=40,t=10,b=10),
                            xaxis_title="", yaxis_title="",
                            plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                            yaxis=dict(autorange="reversed"),
                            font=dict(size=11),
                        )
                        st.plotly_chart(fig_par, use_container_width=True)
                    else:
                        st.bar_chart(ng_sdf.set_index(ng_sdf.columns[0])["次數"])
                else:
                    st.success("🎉 此期間無 NG 工序！")

                st.markdown("</div>", unsafe_allow_html=True)

            # 機種 & 巡檢類型分布
            ci3, ci4 = st.columns(2)

            with ci3:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🥧 巡檢 / FAI 比例
  </div>""", unsafe_allow_html=True)

                if "巡檢類型" in df_ipqc.columns:
                    tp_cnt = df_ipqc["巡檢類型"].value_counts().reset_index()
                    tp_cnt.columns = ["類型", "筆數"]
                    if _PLOTLY:
                        import plotly.express as _px3
                        fig_tp = _px3.pie(tp_cnt, names="類型", values="筆數",
                                          color_discrete_sequence=["#e67e22", "#1565c0"],
                                          hole=0.45)
                        fig_tp.update_traces(textinfo="label+percent", textfont_size=12)
                        fig_tp.update_layout(
                            height=220, margin=dict(l=10,r=10,t=10,b=10),
                            paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                        )
                        st.plotly_chart(fig_tp, use_container_width=True)
                    else:
                        st.bar_chart(tp_cnt.set_index("類型"))
                st.markdown("</div>", unsafe_allow_html=True)

            with ci4:
                st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08);margin-bottom:14px">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    🏷️ 機種 NG率排行
  </div>""", unsafe_allow_html=True)

                if "機種名稱" in df_ipqc.columns:
                    m_stat = (df_ipqc.groupby("機種名稱")
                              .agg(筆數=("記錄編號", "count"),
                                   NG=("總判定", lambda x: (x == "NG").sum()))
                              .reset_index())
                    m_stat["OK率%"] = ((m_stat["筆數"] - m_stat["NG"]) / m_stat["筆數"] * 100).round(1)
                    m_stat = m_stat.sort_values("OK率%")

                    if _PLOTLY:
                        import plotly.graph_objects as _go4
                        mcolors = ["#27ae60" if v == 100 else ("#f39c12" if v >= 80 else "#e74c3c")
                                   for v in m_stat["OK率%"]]
                        fig_m = _go4.Figure(_go4.Bar(
                            x=m_stat["OK率%"], y=m_stat["機種名稱"],
                            orientation="h", marker_color=mcolors,
                            text=[f"{v}%" for v in m_stat["OK率%"]],
                            textposition="outside",
                        ))
                        fig_m.update_layout(
                            height=220, margin=dict(l=10,r=40,t=10,b=10),
                            xaxis=dict(range=[0, 110], ticksuffix="%"),
                            xaxis_title="", yaxis_title="",
                            plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(size=11),
                        )
                        st.plotly_chart(fig_m, use_container_width=True)
                    else:
                        st.bar_chart(m_stat.set_index("機種名稱")["OK率%"])
                st.markdown("</div>", unsafe_allow_html=True)

            # 最近記錄表
            st.markdown("""
<div style="background:#fff;border:1px solid #dce3ec;border-radius:8px;
            padding:14px 18px;box-shadow:0 2px 8px rgba(13,27,42,.08)">
  <div style="font-size:13px;font-weight:700;color:#0d1b2a;margin-bottom:10px">
    📋 最近 20 筆 IPQC 記錄
  </div>""", unsafe_allow_html=True)

            ipqc_show = [c for c in [
                "記錄編號", "建立時間", "機種名稱", "製造編號", "日期",
                "本批數量", "不良件數", "不良率", "巡查員",
                "巡檢類型", "總判定", "NG工序數", "CR_NG數", "MA_NG數", "MI_NG數",
            ] if c in df_ipqc.columns]

            disp_ip = df_ipqc[ipqc_show].head(20).copy()
            if "建立時間" in disp_ip.columns:
                disp_ip["建立時間"] = disp_ip["建立時間"].dt.strftime("%Y/%m/%d %H:%M")
            st.dataframe(disp_ip, use_container_width=True, hide_index=True,
                         height=min(500, 56 + len(disp_ip) * 38))
            st.markdown("</div>", unsafe_allow_html=True)


# ── 重新整理按鈕 ──────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 重新載入資料", use_container_width=False):
    st.cache_data.clear()
    st.rerun()
