"""
REXONTEC 力科 IQC — 進料品質管制檢驗表
依照力科IQC檢驗.html 內容建立
支援：PASS/FAIL 判定、數值量測、送樣勾選、PDF 報告
"""
import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
from datetime import date, datetime, timedelta

from utils.style import QMS_CSS, topbar, page_header
from utils.auth import require_login, user_info_bar
from utils.iqc_data import get_parts, get_all_items_flat


# ═══════════════════════════════════════════════════════
# 風險零件看板 — 資料載入與計算
# ═══════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def _load_sqm_for_risk() -> pd.DataFrame:
    """從 SQM 異常登錄讀取資料（快取5分鐘）"""
    try:
        from utils.gsheet import load_sqm_defects
        return load_sqm_defects()
    except Exception:
        return pd.DataFrame()


def _calc_risk(df_sqm: pd.DataFrame, days: int = 90) -> dict:
    """
    按「零件名稱」彙整近 N 天內的異常次數與風險等級。
    回傳 dict: {零件名稱: {count, level, vendors, last_date, suggestions, issues, history}}
    """
    if df_sqm.empty:
        return {}

    cutoff = datetime.now() - timedelta(days=days)
    df = df_sqm.copy()
    df["_dt"] = pd.to_datetime(df.get("發生日期", pd.Series(dtype=str)), errors="coerce")

    result: dict = {}
    part_col = "零件名稱"
    if part_col not in df.columns:
        return {}

    # 全部歷史
    all_hist = df[df[part_col].str.strip().ne("") if df[part_col].dtype == object else df[part_col].notna()]
    hist_by_part = {k: v.to_dict("records") for k, v in all_hist.groupby(part_col)}

    # 近90天
    df_rec = df[df["_dt"] >= cutoff].copy()
    for pname, grp in df_rec.groupby(part_col):
        pname = str(pname).strip()
        if not pname:
            continue
        cnt = len(grp)
        level = "high" if cnt >= 3 else ("warn" if cnt >= 1 else "ok")
        vendors = grp["廠商"].dropna().value_counts().index.tolist()[:3] if "廠商" in grp.columns else []
        last_dt = grp["_dt"].max()
        last_date = last_dt.strftime("%Y/%m/%d") if pd.notna(last_dt) else "─"

        # 建議
        cats = (grp["異常類別"].dropna().unique().tolist()
                if "異常類別" in grp.columns else [])
        suggestions = _risk_suggestions(cats)

        # 最近3筆問題描述
        issues = grp["P問題點"].dropna().tolist()[:3] if "P問題點" in grp.columns else []

        result[pname] = {
            "count":       cnt,
            "level":       level,
            "vendors":     vendors,
            "last_date":   last_date,
            "suggestions": suggestions,
            "issues":      issues,
            "history":     hist_by_part.get(pname, []),
        }
    return result


def _risk_suggestions(cats: list) -> list:
    """根據異常類別清單生成檢驗建議"""
    cat_map = {
        "外觀": "👁️ 加強外觀目視檢查（燈光/角度/白色背板）",
        "尺寸": "📏 注意尺寸量測，確認公差符合圖面",
        "功能": "⚡ 加嚴功能測試抽驗比例",
        "包裝": "📦 確認包裝完整性，防靜電與緩衝",
        "組裝": "🔧 注意組裝精度與配合度",
        "材料": "🔬 確認材質證書、硬度與RoHS",
        "製程": "🏭 提高抽驗比例，查核製程管制能力",
    }
    tips = [cat_map[c] for c in cats if c in cat_map]
    if not tips:
        tips = ["📋 依標準 SIP 進行全項目檢驗"]
    return tips


def _risk_badge(level: str) -> tuple[str, str, str]:
    """回傳 (emoji, 文字, 顏色)"""
    if level == "high":
        return "🔴", "高風險", "#c0392b"
    if level == "warn":
        return "🟡", "注意",   "#d68910"
    return "🟢", "正常", "#1e8449"


def _match_part_risk(part: dict, risk_map: dict) -> dict | None:
    """嘗試將 IQC 零件與 SQM 風險資料比對（名稱 substring 或料號）"""
    if not risk_map:
        return None
    pname = part.get("name", "").strip()
    ppn   = part.get("pn",   "").strip()

    # 1. 完全匹配零件名稱
    if pname in risk_map:
        return risk_map[pname]
    # 2. 料號匹配（SQM 零件編號含料號）
    for k, v in risk_map.items():
        for rec in v.get("history", []):
            pno = str(rec.get("零件編號（單據號碼）", "")).strip()
            if ppn and ppn in pno:
                return v
    # 3. 部分名稱匹配
    for k, v in risk_map.items():
        if pname and (pname in k or k in pname):
            return v
    return None

# ── 頁面設定 ─────────────────────────────────────────
st.set_page_config(
    page_title="REXONTEC 力科 | IQC 進料檢驗",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(QMS_CSS, unsafe_allow_html=True)
st.markdown(topbar(), unsafe_allow_html=True)
require_login()
user_info_bar()

# ── 導覽列 ──────────────────────────────────────────
col_nav1, col_nav2, col_nav3, col_nav4, col_nav5, col_nav6, col_nav7, col_nav8 = st.columns([1, 1, 1, 1, 1, 1, 1, 2])
with col_nav1:
    if st.button("🏠 指揮平台", use_container_width=True):
        st.switch_page("app.py")
with col_nav2:
    if st.button("📋 檢驗輸入", use_container_width=True):
        st.switch_page("pages/01_出廠檢驗輸入.py")
with col_nav3:
    if st.button("📋 IPQC 巡檢", use_container_width=True):
        st.switch_page("pages/20_📋_IPQC巡檢.py")
with col_nav4:
    if st.button("📊 儀表板", use_container_width=True):
        st.switch_page("pages/02_儀表板.py")
with col_nav5:
    if st.button("🔍 追蹤查詢", use_container_width=True):
        st.switch_page("pages/05_追蹤查詢.py")
with col_nav6:
    if st.button("🤖 AI 分析", use_container_width=True):
        st.switch_page("pages/07_AI異常分析.py")
with col_nav7:
    if st.button("⚙️ 系統設定", use_container_width=True):
        st.switch_page("pages/03_系統設定.py")

st.markdown(page_header(
    "IQC 進料品質管制",
    "Incoming Quality Control — 零件進料品質檢驗",
    "IQC",
), unsafe_allow_html=True)

# ── 額外 CSS ─────────────────────────────────────────
st.markdown("""
<style>
/* 等級標籤 */
.iq-grade-CR { background:#c0392b; color:#fff; padding:1px 8px; border-radius:4px;
               font-size:10px; font-weight:800; letter-spacing:.4px; }
.iq-grade-MA { background:#d68910; color:#fff; padding:1px 8px; border-radius:4px;
               font-size:10px; font-weight:800; letter-spacing:.4px; }
.iq-grade-MI { background:#1e8449; color:#fff; padding:1px 8px; border-radius:4px;
               font-size:10px; font-weight:800; letter-spacing:.4px; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# SESSION STATE 初始化
# ════════════════════════════════════════════════════
if "iqc_part_id"      not in st.session_state: st.session_state.iqc_part_id      = None
if "iqc_results"      not in st.session_state: st.session_state.iqc_results      = {}
if "iqc_submitted_id" not in st.session_state: st.session_state.iqc_submitted_id = None
# {item_id: {"result": "pass"|"fail"|None, "inputs": {key: val}, "remark": ""}}

# ════════════════════════════════════════════════════
# 提交成功畫面
# ════════════════════════════════════════════════════
if st.session_state.iqc_submitted_id:
    rec_id = st.session_state.iqc_submitted_id
    st.markdown(f"""
<div style="max-width:580px;margin:0 auto;padding:20px 0;text-align:center">
  <div style="font-size:56px;margin-bottom:8px">✅</div>
  <div style="font-size:22px;font-weight:900;color:var(--navy);margin-bottom:6px">
    IQC 記錄提交成功
  </div>
  <div style="font-size:14px;font-weight:700;color:var(--accent);
              font-family:'DM Mono',monospace;letter-spacing:2px;
              background:#e3f2fd;padding:10px 20px;border-radius:8px;
              margin:12px auto;display:inline-block">
    {rec_id}
  </div>
  <div style="font-size:12.5px;color:var(--muted);margin-top:10px">
    資料已寫入 Google Sheet IQC 分頁
  </div>
</div>
""", unsafe_allow_html=True)

    # PDF 下載
    _s_part    = st.session_state.get("_iqc_last_part", {})
    _s_header  = st.session_state.get("_iqc_last_header", {})
    _s_results = st.session_state.get("_iqc_last_results", {})
    if _s_part and _s_header:
        try:
            from utils.iqc_pdf import generate_iqc_pdf
            _pdf_bytes = generate_iqc_pdf(
                part=_s_part, header=_s_header, results=_s_results
            )
            _fname = f"{rec_id}.pdf"
            st.download_button(
                "📄 下載 PDF 報告",
                data=_pdf_bytes,
                file_name=_fname,
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as _e:
            st.warning(f"PDF 生成失敗：{_e}")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 繼續新增下一筆", type="primary", use_container_width=True):
            st.session_state.iqc_submitted_id = None
            st.session_state.iqc_results = {}
            st.rerun()
    with col_b:
        if st.button("🏠 返回首頁", use_container_width=True):
            st.switch_page("app.py")
    st.stop()


# ── 零件庫 ────────────────────────────────────────
parts = get_parts()
parts_by_id = {p["id"]: p for p in parts}

# ── callback：PASS / FAIL ─────────────────────────
def set_iqc_result(item_id, val):
    if item_id not in st.session_state.iqc_results:
        st.session_state.iqc_results[item_id] = {"result": None, "inputs": {}, "remark": ""}
    st.session_state.iqc_results[item_id]["result"] = val

def set_iqc_remark(item_id, text):
    if item_id not in st.session_state.iqc_results:
        st.session_state.iqc_results[item_id] = {"result": None, "inputs": {}, "remark": ""}
    st.session_state.iqc_results[item_id]["remark"] = text

# ── 預先載入 SQM 風險資料（供左右兩側共用）───────────
df_sqm_risk = _load_sqm_for_risk()
risk_map    = _calc_risk(df_sqm_risk)          # {零件名稱: {...}}

# ════════════════════════════════════════════════════
# 左側：零件選擇
# ════════════════════════════════════════════════════
left_col, right_col = st.columns([1, 3])

with left_col:
    st.markdown("""
    <div style="background:var(--navy);color:rgba(255,255,255,.7);padding:8px 12px;
                font-size:9.5px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
                border-radius:6px 6px 0 0;margin-bottom:0">零件庫 PARTS</div>
    """, unsafe_allow_html=True)

    search = st.text_input("", placeholder="🔍 搜尋料號 / 名稱", label_visibility="collapsed", key="iqc_search")
    fl = search.lower()

    # 按 group 分組顯示
    groups: dict[str, list] = {}
    for p in parts:
        g = p.get("group", "其他")
        if fl and fl not in p["name"].lower() and fl not in p["pn"].lower():
            continue
        groups.setdefault(g, []).append(p)

    if not groups:
        st.caption("無結果")
    else:
        for grp_label, grp_parts in groups.items():
            st.markdown(f'<div style="font-size:9.5px;font-weight:700;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase;padding:6px 2px 2px">{grp_label}</div>', unsafe_allow_html=True)
            for p in grp_parts:
                is_active = st.session_state.iqc_part_id == p["id"]
                has_cr    = any(i["grade"] == "CR" for i in get_all_items_flat(p))
                badge_col = "#c0392b" if has_cr else "#d68910"
                badge_txt = "CR" if has_cr else "MA"
                border    = "2px solid var(--accent)" if is_active else "1px solid var(--border)"
                bg        = "#eef5ff" if is_active else "#fff"

                # 風險指示
                p_risk = _match_part_risk(p, risk_map)
                if p_risk:
                    _em, _lbl, _clr = _risk_badge(p_risk["level"])
                    _risk_hint = (
                        f'<div style="font-size:9px;margin:-4px 0 3px 2px;'
                        f'color:{_clr};font-weight:700">'
                        f'{_em} {_lbl}｜{p_risk["count"]}次/90天</div>'
                    )
                else:
                    _risk_hint = (
                        '<div style="font-size:9px;margin:-4px 0 3px 2px;'
                        'color:#1e8449;font-weight:700">🟢 正常</div>'
                    )

                clicked = st.button(
                    f"{p.get('icon','📦')}  {p['name']}\n{p['pn']}",
                    key=f"part_btn_{p['id']}",
                    use_container_width=True,
                )
                st.markdown(_risk_hint, unsafe_allow_html=True)
                if clicked:
                    if st.session_state.iqc_part_id != p["id"]:
                        st.session_state.iqc_part_id = p["id"]
                        st.session_state.iqc_results = {}
                    st.rerun()

# ════════════════════════════════════════════════════
# 右側：檢驗表單
# ════════════════════════════════════════════════════
with right_col:
    if not st.session_state.iqc_part_id:
        # ══════════════════════════════════════════════
        # 風險零件看板（未選取零件時顯示）
        # ══════════════════════════════════════════════
        n_high = sum(1 for v in risk_map.values() if v["level"] == "high")
        n_warn = sum(1 for v in risk_map.values() if v["level"] == "warn")

        st.markdown(f"""
<div style="background:linear-gradient(135deg,var(--navy) 0%,#1a3a5c 100%);
            border-radius:10px;padding:18px 24px;margin-bottom:16px;
            box-shadow:0 4px 16px rgba(13,27,42,.18)">
  <div style="font-size:10px;color:rgba(255,255,255,.5);letter-spacing:2px;
              text-transform:uppercase;margin-bottom:4px">SQM 異常資料 · 近 90 天</div>
  <div style="font-size:20px;font-weight:900;color:#fff;margin-bottom:12px">
    🚨 IQC 風險零件看板
  </div>
  <div style="display:flex;gap:16px">
    <div style="background:rgba(192,57,43,.25);border:1px solid rgba(192,57,43,.5);
                border-radius:8px;padding:8px 20px;text-align:center">
      <div style="font-size:24px;font-weight:900;color:#e74c3c;
                  font-family:'DM Mono',monospace">{n_high}</div>
      <div style="font-size:10px;color:rgba(255,255,255,.6);letter-spacing:1px">🔴 高風險</div>
    </div>
    <div style="background:rgba(214,137,16,.2);border:1px solid rgba(214,137,16,.45);
                border-radius:8px;padding:8px 20px;text-align:center">
      <div style="font-size:24px;font-weight:900;color:#f39c12;
                  font-family:'DM Mono',monospace">{n_warn}</div>
      <div style="font-size:10px;color:rgba(255,255,255,.6);letter-spacing:1px">🟡 注意</div>
    </div>
    <div style="background:rgba(30,132,73,.2);border:1px solid rgba(30,132,73,.4);
                border-radius:8px;padding:8px 20px;text-align:center">
      <div style="font-size:24px;font-weight:900;color:#2ecc71;
                  font-family:'DM Mono',monospace">{len(risk_map)-n_high-n_warn}</div>
      <div style="font-size:10px;color:rgba(255,255,255,.6);letter-spacing:1px">🟢 正常</div>
    </div>
    <div style="margin-left:auto;display:flex;align-items:center">
      <div style="font-size:10px;color:rgba(255,255,255,.4)">
        資料來源：SQM_異常登錄<br>點選左側零件 → 開始檢驗
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        if not risk_map:
            st.info("📊 SQM 尚無異常資料，或資料讀取中。系統將在 5 分鐘內自動更新。")
        else:
            # ── 依風險等級排序顯示 ────────────────────
            sorted_risks = sorted(
                risk_map.items(),
                key=lambda x: {"high": 0, "warn": 1, "ok": 2}[x[1]["level"]]
            )

            for pname, rdata in sorted_risks:
                em, lbl, clr = _risk_badge(rdata["level"])
                vendors_str  = "、".join(rdata["vendors"]) or "─"
                issues_short = rdata["issues"][0][:40] + "…" if rdata["issues"] else "─"

                # 卡片容器
                with st.expander(
                    f"{em} **{pname}**　｜　{lbl}　｜　近90天 {rdata['count']} 次異常　｜　{vendors_str}",
                    expanded=(rdata["level"] == "high"),
                ):
                    # 上方摘要欄
                    ca, cb, cc, cd = st.columns(4)
                    ca.metric("異常次數（90天）", f"{rdata['count']} 次")
                    cb.metric("最近異常日期", rdata["last_date"])
                    cc.metric("涉及廠商", vendors_str[:18])
                    cd.metric("風險等級", lbl)

                    st.markdown("---")

                    # 最近問題描述
                    if rdata["issues"]:
                        st.markdown(
                            '<div style="font-size:11px;font-weight:700;color:var(--navy);'
                            'margin-bottom:6px">📋 最近異常描述</div>',
                            unsafe_allow_html=True,
                        )
                        for i, iss in enumerate(rdata["issues"], 1):
                            st.markdown(
                                f'<div style="background:#fff8f7;border-left:3px solid {clr};'
                                f'padding:6px 10px;border-radius:0 4px 4px 0;'
                                f'font-size:12px;margin-bottom:4px">'
                                f'<b>#{i}</b> {iss}</div>',
                                unsafe_allow_html=True,
                            )

                    # 建議檢查重點
                    st.markdown(
                        '<div style="font-size:11px;font-weight:700;color:var(--navy);'
                        'margin:10px 0 6px">🎯 建議檢查重點</div>',
                        unsafe_allow_html=True,
                    )
                    for tip in rdata["suggestions"]:
                        st.markdown(
                            f'<div style="background:#f0f4ff;border-left:3px solid #3498db;'
                            f'padding:5px 10px;border-radius:0 4px 4px 0;'
                            f'font-size:12px;margin-bottom:4px">{tip}</div>',
                            unsafe_allow_html=True,
                        )

                    # 歷史異常紀錄（全部）
                    if rdata["history"]:
                        st.markdown(
                            f'<div style="font-size:11px;font-weight:700;color:var(--navy);'
                            f'margin:10px 0 6px">📂 歷史異常紀錄（共 {len(rdata["history"])} 筆）</div>',
                            unsafe_allow_html=True,
                        )
                        hist_rows = []
                        for rec in rdata["history"]:
                            hist_rows.append({
                                "發生日期": rec.get("發生日期", ""),
                                "廠商":     rec.get("廠商", ""),
                                "異常類別": rec.get("異常類別", ""),
                                "不良數":   rec.get("不良數", ""),
                                "P問題點":  str(rec.get("P問題點", ""))[:50],
                                "狀態":     rec.get("狀態", ""),
                                "記錄編號": rec.get("記錄編號", ""),
                            })
                        import pandas as _pd
                        st.dataframe(
                            _pd.DataFrame(hist_rows),
                            use_container_width=True,
                            hide_index=True,
                            height=min(300, 35 * len(hist_rows) + 40),
                        )

                    # 照片預留
                    st.markdown(
                        '<div style="background:#f8f9fa;border:1px dashed #ccc;'
                        'border-radius:6px;padding:12px;text-align:center;'
                        'font-size:11px;color:#aaa;margin-top:8px">'
                        '📷 異常照片（預留 — 上傳照片後此處自動顯示）</div>',
                        unsafe_allow_html=True,
                    )

        st.stop()

    part = parts_by_id.get(st.session_state.iqc_part_id)
    if not part:
        st.warning("零件資料不存在，請重新選取")
        st.stop()

    # ══════════════════════════════════════════════
    # 零件病歷卡（選取零件後顯示於頂端）
    # ══════════════════════════════════════════════
    p_risk = _match_part_risk(part, risk_map)
    if p_risk:
        em, lbl, clr = _risk_badge(p_risk["level"])
        _card_bg = {"high": "#fff8f7", "warn": "#fffbf0", "ok": "#f0fdf4"}[p_risk["level"]]
        _border  = {"high": "#e74c3c", "warn": "#f39c12", "ok": "#27ae60"}[p_risk["level"]]
        with st.expander(
            f"{em} 零件病歷卡｜{part['name']}  ── {lbl}，近90天 {p_risk['count']} 次異常",
            expanded=(p_risk["level"] in ("high", "warn")),
        ):
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("異常次數（90天）", f"{p_risk['count']} 次",
                       delta=("⚠️ 需加嚴" if p_risk["level"] == "high" else None),
                       delta_color="inverse")
            mc2.metric("最近異常日期", p_risk["last_date"])
            mc3.metric("涉及廠商", "、".join(p_risk["vendors"])[:16] or "─")
            mc4.metric("風險等級", lbl)

            st.markdown("---")
            tip_col, iss_col = st.columns(2)

            with tip_col:
                st.markdown(
                    '<div style="font-size:11px;font-weight:700;color:var(--navy);'
                    'margin-bottom:6px">🎯 本次檢驗重點建議</div>',
                    unsafe_allow_html=True,
                )
                for tip in p_risk["suggestions"]:
                    st.markdown(
                        f'<div style="background:#f0f4ff;border-left:3px solid #3498db;'
                        f'padding:5px 10px;border-radius:0 4px 4px 0;'
                        f'font-size:12px;margin-bottom:4px">{tip}</div>',
                        unsafe_allow_html=True,
                    )

            with iss_col:
                st.markdown(
                    '<div style="font-size:11px;font-weight:700;color:var(--navy);'
                    'margin-bottom:6px">📋 最近異常描述</div>',
                    unsafe_allow_html=True,
                )
                if p_risk["issues"]:
                    for i, iss in enumerate(p_risk["issues"], 1):
                        st.markdown(
                            f'<div style="background:{_card_bg};border-left:3px solid {_border};'
                            f'padding:5px 10px;border-radius:0 4px 4px 0;'
                            f'font-size:12px;margin-bottom:4px">'
                            f'<b>#{i}</b> {iss}</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("無最近異常描述")

            # 歷史異常紀錄
            if p_risk["history"]:
                st.markdown(
                    f'<div style="font-size:11px;font-weight:700;color:var(--navy);'
                    f'margin:8px 0 4px">📂 歷史異常紀錄（共 {len(p_risk["history"])} 筆）</div>',
                    unsafe_allow_html=True,
                )
                hist_rows = [{
                    "發生日期": r.get("發生日期", ""),
                    "廠商":     r.get("廠商", ""),
                    "異常類別": r.get("異常類別", ""),
                    "不良數":   r.get("不良數", ""),
                    "問題點":   str(r.get("P問題點", ""))[:45],
                    "狀態":     r.get("狀態", ""),
                } for r in p_risk["history"]]
                st.dataframe(
                    pd.DataFrame(hist_rows),
                    use_container_width=True,
                    hide_index=True,
                    height=min(240, 35 * len(hist_rows) + 40),
                )

            # 照片預留
            st.markdown(
                '<div style="background:#f8f9fa;border:1px dashed #ccc;border-radius:6px;'
                'padding:10px;text-align:center;font-size:11px;color:#aaa;margin-top:6px">'
                '📷 異常照片（預留）</div>',
                unsafe_allow_html=True,
            )
    else:
        # 無 SQM 異常資料 → 顯示綠色正常卡
        st.markdown(
            f'<div style="background:#f0fdf4;border:1px solid #a8e6c0;border-radius:8px;'
            f'padding:10px 16px;margin-bottom:8px;font-size:12px;color:#1e8449;">'
            f'🟢 <b>{part["name"]}</b> — 近90天 SQM 無異常記錄，依標準 SIP 進行檢驗。</div>',
            unsafe_allow_html=True,
        )

    all_items = get_all_items_flat(part)

    # ── 初始化本零件的 results ──────────────────────
    for item in all_items:
        iid = item["id"]
        if iid not in st.session_state.iqc_results:
            st.session_state.iqc_results[iid] = {"result": None, "inputs": {}, "remark": ""}

    # ════════════════════════════════════════════
    # 表頭資訊
    # ════════════════════════════════════════════
    st.markdown(f"""
<div style="background:linear-gradient(135deg,var(--navy) 0%,var(--blue) 100%);
            border-radius:10px;padding:18px 22px;margin-bottom:14px;
            box-shadow:var(--sh-md)">
  <div style="font-size:10.5px;color:rgba(255,255,255,.45);margin-bottom:3px">
    {part.get('docNo','')} ｜ {part['name']} ｜ {part.get('samplingStd','')}
  </div>
  <div style="font-size:19px;font-weight:900;color:#fff">IQC 進料品質管制檢驗表</div>
</div>
""", unsafe_allow_html=True)

    with st.expander("📋 基本資料 / 表頭", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            hdr_part   = st.text_input("零件名稱", value=part["name"], key="iqc_hdr_part")
            hdr_vendor = st.text_input("供應商",   value=part.get("vendor",""), key="iqc_hdr_vendor")
        with c2:
            hdr_lot    = st.text_input("批號 / 料號", placeholder="批號", key="iqc_hdr_lot")
            hdr_po     = st.text_input("採購單號",    placeholder="PO No.", key="iqc_hdr_po")
        with c3:
            hdr_qty    = st.number_input("進料數量 (PCS)", min_value=0, value=0, key="iqc_hdr_qty")
            hdr_sample = st.number_input("抽樣數量 (PCS)", min_value=0, value=0, key="iqc_hdr_sample")
        with c4:
            hdr_date   = st.date_input("檢驗日期", value=date.today(), key="iqc_hdr_date")
            hdr_insp   = st.text_input("IQC 檢驗員", placeholder="姓名", key="iqc_hdr_insp")

        # 公司別選擇
        st.markdown("<hr style='border:none;border-top:1px dashed var(--border);margin:8px 0'>",
                    unsafe_allow_html=True)
        _iqc_co_choice = st.radio(
            "公司別",
            ["力科 REXONTEC", "力山 REXON"],
            horizontal=True,
            key="iqc_company",
        )
        iqc_company = "rexon" if "力山" in _iqc_co_choice else "rexontec"
        if iqc_company == "rexon":
            st.markdown(
                '<span style="background:#1a5276;color:#fff;padding:3px 12px;'
                'border-radius:5px;font-size:11px;font-weight:900;letter-spacing:1px">'
                'REXON 力山</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span style="background:#0d1b2a;color:#f0a500;padding:3px 12px;'
                'border-radius:5px;font-size:11px;font-weight:900;letter-spacing:1px">'
                'REXONTEC 力科</span>',
                unsafe_allow_html=True,
            )

    # ════════════════════════════════════════
    # 零件圖面上傳
    # ════════════════════════════════════════
    with st.expander("📐 零件圖面 / 工程圖", expanded=False):
        drw_key = f"iqc_drawing_{part['id']}"
        uploaded_drawings = st.file_uploader(
            "上傳圖面（PNG / JPG / PDF，可多張）",
            type=["png", "jpg", "jpeg", "pdf"],
            accept_multiple_files=True,
            key=drw_key,
            label_visibility="collapsed",
        )
        if uploaded_drawings:
            img_files = [f for f in uploaded_drawings
                         if not f.name.lower().endswith(".pdf")]
            pdf_files = [f for f in uploaded_drawings
                         if f.name.lower().endswith(".pdf")]
            if img_files:
                _drw_cols = st.columns(min(len(img_files), 2))
                for _di, _df in enumerate(img_files):
                    with _drw_cols[_di % 2]:
                        st.image(_df, caption=_df.name, use_container_width=True)
            for _pf in pdf_files:
                st.download_button(
                    f"📄 {_pf.name}（點此下載 PDF 圖面）",
                    data=_pf.getvalue(),
                    file_name=_pf.name,
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.markdown(
                '<div style="text-align:center;color:var(--muted);'
                'font-size:12px;padding:16px 0;opacity:.6">'
                '📐 尚未上傳圖面 — 點選或拖曳圖面到此處</div>',
                unsafe_allow_html=True,
            )

    # ════════════════════════════════════════
    # 進度條
    # ════════════════════════════════════════
    pass_n  = sum(1 for i in all_items if st.session_state.iqc_results.get(i["id"], {}).get("result") == "pass")
    fail_n  = sum(1 for i in all_items if st.session_state.iqc_results.get(i["id"], {}).get("result") == "fail")
    pend_n  = len(all_items) - pass_n - fail_n
    pct     = round((pass_n + fail_n) / len(all_items) * 100) if all_items else 0
    bar_col = "#e74c3c" if fail_n else "#27ae60"

    if pend_n == 0:
        vrd_label = "不 合 格  NG" if fail_n else "合 格  PASS"
        vrd_color = "#e74c3c" if fail_n else "#27ae60"
        vrd_bg    = "#fff8f7" if fail_n else "#eafaf1"
    else:
        vrd_label = f"待 檢 驗 ({pend_n})"
        vrd_color = "var(--muted)"
        vrd_bg    = "var(--bg)"

    st.markdown(f"""
<div style="background:#fff;border:1px solid var(--border);border-radius:8px;
            padding:12px 18px;margin-bottom:14px;display:flex;align-items:center;gap:18px;
            box-shadow:var(--sh)">
  <div style="display:flex;gap:22px">
    <div style="text-align:center">
      <div style="font-size:22px;font-weight:700;font-family:'DM Mono',monospace;color:#27ae60">{pass_n}</div>
      <div style="font-size:9.5px;color:var(--muted);text-transform:uppercase">通過</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:22px;font-weight:700;font-family:'DM Mono',monospace;color:#e74c3c">{fail_n}</div>
      <div style="font-size:9.5px;color:var(--muted);text-transform:uppercase">不通過</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:22px;font-weight:700;font-family:'DM Mono',monospace;color:var(--muted)">{pend_n}</div>
      <div style="font-size:9.5px;color:var(--muted);text-transform:uppercase">待檢</div>
    </div>
  </div>
  <div style="flex:1">
    <div style="height:6px;background:var(--bg);border-radius:99px;overflow:hidden;margin-bottom:4px">
      <div style="height:100%;width:{pct}%;background:{bar_col};border-radius:99px;transition:width .4s"></div>
    </div>
    <div style="font-size:10px;color:var(--muted);text-align:right">完成度 {pct}%</div>
  </div>
  <div style="background:{vrd_bg};border:1.5px solid {vrd_color};border-radius:99px;
              padding:6px 18px;font-size:12px;font-weight:700;color:{vrd_color};
              letter-spacing:1px;white-space:nowrap">{vrd_label}</div>
</div>
""", unsafe_allow_html=True)

    if part.get("alert"):
        st.warning(f"⚠ {part['alert']}")

    # ════════════════════════════════════════
    # 檢驗項目（依 section 折疊顯示）
    # ════════════════════════════════════════
    grade_colors = {"CR": "#c0392b", "MA": "#d68910", "MI": "#1e8449"}

    for sec_idx, sec in enumerate(part.get("sections", [])):
        sec_items = sec.get("items", [])
        sec_done  = sum(1 for i in sec_items
                       if st.session_state.iqc_results.get(i["id"], {}).get("result") is not None)
        sec_ng    = sum(1 for i in sec_items
                       if st.session_state.iqc_results.get(i["id"], {}).get("result") == "fail")
        badge_col = "#e74c3c" if sec_ng else ("#27ae60" if sec_done == len(sec_items) else "var(--muted)")
        badge_txt = f"NG:{sec_ng}" if sec_ng else f"{sec_done}/{len(sec_items)}"
        sec_letter = chr(65 + sec_idx)

        with st.expander(
            f"{sec_letter}｜{sec['label']}　{sec.get('sublabel','')}　【{badge_txt}】",
            expanded=True
        ):
            for item in sec_items:
                iid      = item["id"]
                grade    = item["grade"]
                itype_is_numeric = bool(item.get("inputs"))
                state    = st.session_state.iqc_results.get(iid, {"result": None, "inputs": {}, "remark": ""})
                res      = state.get("result")
                gcol     = grade_colors.get(grade, "#888")

                item_ng = (res == "fail")
                row_bg  = "background:#fff8f7;border-left:3px solid var(--fail);" if item_ng else ""

                # ── 項目標題列
                st.markdown(f"""
<div style="{row_bg}padding:9px 10px 4px;border-bottom:1px solid #edf0f4;
             display:flex;align-items:flex-start;gap:10px;flex-wrap:wrap">
  <span style="background:{gcol};color:#fff;padding:1px 8px;border-radius:4px;
               font-size:10px;font-weight:800;letter-spacing:.4px;flex-shrink:0">{grade}</span>
  <div style="flex:1;min-width:140px">
    <div style="font-size:12.5px;font-weight:700">{iid}. {item['name']}</div>
    <div style="font-size:11px;color:var(--muted);margin-top:1px">
      📏 {item['spec']}
      {'&nbsp;|&nbsp; ' + item['specDetail'] if item.get('specDetail') else ''}
      &nbsp;｜&nbsp; 🔧 {item.get('tool','').replace(chr(10),' / ')}
    </div>
    {'<div style="font-size:11px;color:var(--fail);margin-top:2px">⚠ ' + item['alert'] + '</div>' if item.get('alert') else ''}
  </div>
</div>
""", unsafe_allow_html=True)

                # ── 判定 + 數值輸入區
                col_pass, col_fail, col_remark = st.columns([1, 1, 3])

                with col_pass:
                    pass_active = (res == "pass")
                    if st.button(
                        "✓  PASS",
                        key=f"iqc_pass_{iid}",
                        use_container_width=True,
                        type="primary" if pass_active else "secondary",
                    ):
                        set_iqc_result(iid, "pass")
                        st.rerun()

                with col_fail:
                    fail_active = (res == "fail")
                    if st.button(
                        "✗  FAIL",
                        key=f"iqc_fail_{iid}",
                        use_container_width=True,
                        type="primary" if fail_active else "secondary",
                    ):
                        set_iqc_result(iid, "fail")
                        st.rerun()

                with col_remark:
                    remark_val = state.get("remark", "")
                    new_remark = st.text_input(
                        "備註", value=remark_val,
                        placeholder="備註 / 異常說明…",
                        key=f"iqc_remark_{iid}",
                        label_visibility="collapsed",
                    )
                    if new_remark != remark_val:
                        set_iqc_remark(iid, new_remark)

                # ── 數值輸入（量測欄位）
                if itype_is_numeric:
                    inp_cols = st.columns(min(len(item["inputs"]), 4))
                    for ci, inp in enumerate(item["inputs"]):
                        with inp_cols[ci % len(inp_cols)]:
                            key_val = f"iqc_inp_{iid}_{inp['key']}"
                            cur_v   = state["inputs"].get(inp["key"], "")
                            new_v   = st.text_input(
                                f"{inp['label']} ({inp['unit']})",
                                value=str(cur_v) if cur_v != "" else "",
                                placeholder="—",
                                key=key_val,
                            )
                            if new_v != str(cur_v):
                                if iid not in st.session_state.iqc_results:
                                    st.session_state.iqc_results[iid] = {"result": None, "inputs": {}, "remark": ""}
                                st.session_state.iqc_results[iid]["inputs"][inp["key"]] = new_v
                                # autoFail 判定
                                if new_v and item.get("autoFail"):
                                    try:
                                        n = float(new_v)
                                        mn = inp.get("min")
                                        mx = inp.get("max")
                                        ok = True
                                        if mn is not None and n < mn: ok = False
                                        if mx is not None and n > mx: ok = False
                                        if not ok:
                                            st.session_state.iqc_results[iid]["result"] = "fail"
                                    except ValueError:
                                        pass

                # JS 著色：PASS=綠, FAIL=紅
                if res == "pass":
                    st.markdown('<span class="pass-marker"></span>', unsafe_allow_html=True)
                elif res == "fail":
                    st.markdown('<span class="fail-marker"></span>', unsafe_allow_html=True)

                st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

        st.markdown(f"""
<div style="background:#f7faff;border:1px solid var(--border);padding:7px 14px;
            font-size:10.5px;color:var(--muted);margin-bottom:12px;border-radius:0 0 6px 6px">
  抽樣標準：{part.get('samplingStd','')}　｜
  AQL CR:{part['aql']['cr']} / MA:{part['aql']['ma']} / MI:{part['aql']['mi']}　｜　Ac/Re：0/1
</div>
""", unsafe_allow_html=True)

    # JS 按鈕著色（沿用 OQC 同樣 MutationObserver 方式）
    components.html("""
<script>
(function(){
  var PASS_BG='#27ae60', FAIL_BG='#e74c3c';
  function applyColor(marker, bg){
    var el=marker.parentElement;
    while(el&&el.tagName!=='BODY'){
      if(el.querySelector('button')!==null){
        var btn=el.querySelector('button');
        btn.style.setProperty('background-color',bg,'important');
        btn.style.setProperty('background',bg,'important');
        btn.style.setProperty('border-color',bg,'important');
        btn.style.setProperty('color','#fff','important');
        return;
      }
      el=el.parentElement;
    }
  }
  function colorButtons(){
    var doc=window.parent.document;
    doc.querySelectorAll('span.pass-marker').forEach(function(m){applyColor(m,PASS_BG)});
    doc.querySelectorAll('span.fail-marker').forEach(function(m){applyColor(m,FAIL_BG)});
  }
  colorButtons();setTimeout(colorButtons,200);setTimeout(colorButtons,600);
  var obs=new MutationObserver(function(){colorButtons()});
  obs.observe(window.parent.document.body,{childList:true,subtree:true});
})();
</script>
""", height=0, scrolling=False)

    # ════════════════════════════════════════
    # 底部操作列：提交 / PDF / 重置
    # ════════════════════════════════════════
    st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:12px 0'>",
                unsafe_allow_html=True)

    # 共用表頭 dict（提交 & PDF 都用）
    _iqc_co_raw = st.session_state.get("iqc_company", "力科 REXONTEC")
    _hdr = {
        "part":      st.session_state.get("iqc_hdr_part",   part["name"]),
        "vendor":    st.session_state.get("iqc_hdr_vendor", part.get("vendor", "")),
        "lot":       st.session_state.get("iqc_hdr_lot",    ""),
        "po":        st.session_state.get("iqc_hdr_po",     ""),
        "qty":       st.session_state.get("iqc_hdr_qty",    0),
        "sample":    st.session_state.get("iqc_hdr_sample", 0),
        "date":      str(st.session_state.get("iqc_hdr_date", date.today())),
        "inspector": st.session_state.get("iqc_hdr_insp",  ""),
        "docNo":     part.get("docNo", ""),
        "samplingStd": part.get("samplingStd", ""),
        "aql":       part.get("aql", {}),
        "company":   "rexon" if "力山" in _iqc_co_raw else "rexontec",
    }

    col_submit, col_pdf, col_reset = st.columns([3, 3, 1])

    with col_reset:
        if st.button("⟳ 重置", use_container_width=True):
            st.session_state.iqc_results = {}
            st.rerun()

    with col_pdf:
        if st.button("📄 匯出 PDF", use_container_width=True):
            try:
                from utils.iqc_pdf import generate_iqc_pdf
                with st.spinner("正在生成 PDF…"):
                    _pdf_bytes = generate_iqc_pdf(
                        part=part, header=_hdr,
                        results=st.session_state.iqc_results,
                    )
                    _fname = f"IQC_{part['id']}_{_hdr['lot'] or 'LOT'}_{_hdr['date']}.pdf"
                    st.download_button(
                        "⬇️ 點此下載 PDF",
                        data=_pdf_bytes, file_name=_fname,
                        mime="application/pdf",
                        use_container_width=True, key="iqc_dl_pdf",
                    )
            except ImportError:
                st.info("請先安裝 reportlab：pip install reportlab")
            except Exception as _e:
                st.error(f"PDF 生成失敗：{_e}")

    with col_submit:
        _pend = sum(1 for i in all_items
                    if st.session_state.iqc_results.get(i["id"], {}).get("result") is None)
        if st.button("✅ 提交 → 寫入 Google Sheet",
                     type="primary", use_container_width=True):
            if _pend > 0:
                st.warning(f"尚有 {_pend} 項未判定，確認要提交請再按一次。", icon="⚠️")
            else:
                with st.spinner("寫入 Google Sheet 中…"):
                    try:
                        from utils.gsheet import append_iqc_record
                        _rec_id = append_iqc_record(
                            part=part,
                            header=_hdr,
                            results=st.session_state.iqc_results,
                        )
                        # 保存供提交成功頁使用
                        st.session_state._iqc_last_part    = part
                        st.session_state._iqc_last_header  = _hdr
                        st.session_state._iqc_last_results = dict(st.session_state.iqc_results)
                        st.session_state.iqc_submitted_id  = _rec_id
                        st.rerun()
                    except Exception as _e:
                        st.error(f"寫入失敗：{_e}")
                        st.info("請確認 service_account.json 與 Google Sheet 設定正確")
