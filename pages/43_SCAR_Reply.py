"""
REXONTEC — 供應商 SCAR 外部回覆頁
不需登入。供應商透過 Email 連結填寫 CAPA 改善回覆。

存取 URL：
  https://your-app.streamlit.app/43_SCAR_Reply?scar_id=SCAR-2026-0001

安全設計：
  - 不呼叫 require_login()，無需帳號
  - 完全隱藏側邊欄與內部導覽
  - 僅顯示與 scar_id 對應的單一 SCAR 公開資訊
  - 不顯示：KPI、儀表板、其他供應商、內部備註、IQC 資料
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from utils.gsheet import load_scars, update_scar, load_sqm_defects

# ── 頁面設定 ─────────────────────────────────────────────
st.set_page_config(
    page_title="SCAR 供應商改善回覆 — REXONTEC 力科技",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── 完全隱藏內部導覽與系統 UI ────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"],
  [data-testid="stSidebarNav"],
  [data-testid="collapsedControl"],
  #MainMenu, header, footer          { display: none !important; }
  .block-container                   { padding-top: 1.2rem; max-width: 780px; }
  .stTextArea textarea               { font-size: 13px; line-height: 1.7; }
  .stTextArea label                  { font-weight: 700; font-size: 13px; }
</style>
""", unsafe_allow_html=True)


# ── 資料載入（Cache 短 TTL，確保即時性） ────────────────
@st.cache_data(ttl=30, show_spinner="讀取 SCAR 資料中…")
def _load_all_scars() -> pd.DataFrame:
    try:
        return load_scars()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def _load_defect_photo(defect_id: str) -> str:
    """從 SQM 異常登錄取得照片 URL（供顯示異常圖片使用）"""
    if not defect_id or defect_id == "nan":
        return ""
    try:
        df = load_sqm_defects()
        if df.empty or "記錄編號" not in df.columns:
            return ""
        match = df[df["記錄編號"] == defect_id]
        if match.empty:
            return ""
        photo = str(match.iloc[0].get("照片", "")).strip()
        return photo if photo not in ("", "nan") else ""
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════
# Header Banner
# ═══════════════════════════════════════════════════════
st.markdown("""
<div style="background:linear-gradient(135deg,#1e3a5f 0%,#2980b9 100%);
            border-radius:12px;padding:22px 28px;margin-bottom:22px;text-align:center">
  <div style="font-size:20px;font-weight:900;color:#fff;letter-spacing:2px">
    ⚙️ REXONTEC 力科技
  </div>
  <div style="font-size:12px;color:#bde3ff;margin-top:6px;letter-spacing:1px">
    SUPPLIER CORRECTIVE ACTION REQUEST &nbsp;—&nbsp; 供應商 CAPA 改善回覆
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# 讀取 URL 參數
# ═══════════════════════════════════════════════════════
scar_id = st.query_params.get("scar_id", "").strip()

if not scar_id:
    st.error(
        "⚠️ **無效的連結**\n\n"
        "請確認您使用的是 REXONTEC 發出的 SCAR 通知信中所附之回覆連結。"
    )
    st.markdown("""
<div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;
            padding:16px 20px;margin-top:16px;font-size:12px;color:#6b7c93;
            text-align:center">
  如有疑問請聯絡 REXONTEC 力科技品保部門
</div>
""", unsafe_allow_html=True)
    st.stop()


# ═══════════════════════════════════════════════════════
# 取得 SCAR 記錄
# ═══════════════════════════════════════════════════════
df_all = _load_all_scars()
scar_row = None

if not df_all.empty and "SCAR編號" in df_all.columns:
    matched = df_all[df_all["SCAR編號"] == scar_id]
    if not matched.empty:
        scar_row = matched.iloc[0].to_dict()

if scar_row is None:
    st.error(
        f"⚠️ **找不到 SCAR 記錄：{scar_id}**\n\n"
        "請確認連結是否正確，或聯絡 REXONTEC 品保部門。"
    )
    st.stop()


# ═══════════════════════════════════════════════════════
# 輔助函式 — 安全取值
# ═══════════════════════════════════════════════════════
def _val(key: str, default: str = "─") -> str:
    v = str(scar_row.get(key, "")).strip()
    return v if v not in ("", "nan") else default


def _val_or_empty(key: str) -> str:
    v = str(scar_row.get(key, "")).strip()
    return v if v not in ("", "nan") else ""


# ═══════════════════════════════════════════════════════
# 狀態提示
# ═══════════════════════════════════════════════════════
close_status  = _val("結案狀態", "Open")
reply_status  = _val("供應商回覆狀態", "待回覆")

if close_status == "Closed":
    st.info("ℹ️ 此 SCAR 已結案。回覆仍可提交以供存檔參考。")

if reply_status == "已回覆":
    st.success("✅ 此 SCAR 已有回覆記錄。您可更新內容後重新提交。")
elif reply_status == "逾期未回覆":
    st.warning("⚠️ 此 SCAR 已逾期，請儘速完成回覆。")


# ═══════════════════════════════════════════════════════
# SCAR 異常資訊卡（公開欄位，不含內部資料）
# ═══════════════════════════════════════════════════════
defect_date    = _val("異常日期")
supplier_name  = _val("供應商")
part_no        = _val("料號")
part_name      = _val("品名", "")
defect_cat     = _val("異常類別")
defect_qty     = _val("異常數量")
defect_desc    = _val_or_empty("異常描述")
reply_deadline = _val("要求回覆期限")

desc_html = ""
if defect_desc:
    desc_html = f"""
      <div style="margin-top:12px;padding-top:12px;border-top:1px solid #f0f0f0;
                  font-size:13px;color:#2c3e50;line-height:1.7">
        <span style="color:#6b7c93;font-size:11px">異常描述：</span><br>{defect_desc}
      </div>"""

st.markdown(f"""
<div style="background:#fff;border:1px solid #dce3ec;border-left:5px solid #e74c3c;
            border-radius:10px;padding:20px 24px;margin-bottom:18px">
  <div style="font-size:10px;color:#6b7c93;font-weight:700;letter-spacing:1.2px;
              text-transform:uppercase;margin-bottom:6px">📋 異常明細</div>
  <div style="font-size:22px;font-weight:900;color:#1e3a5f;margin-bottom:14px">
    {scar_id}
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 24px;font-size:13px">
    <div>
      <span style="color:#6b7c93;font-size:11px">異常日期</span><br>
      <b>{defect_date}</b>
    </div>
    <div>
      <span style="color:#6b7c93;font-size:11px">供應商</span><br>
      <b>{supplier_name}</b>
    </div>
    <div>
      <span style="color:#6b7c93;font-size:11px">料號</span><br>
      <b>{part_no}</b>
    </div>
    <div>
      <span style="color:#6b7c93;font-size:11px">品名</span><br>
      <b>{part_name if part_name else "─"}</b>
    </div>
    <div>
      <span style="color:#6b7c93;font-size:11px">異常類別</span><br>
      <span style="background:#fde3e3;color:#c0392b;padding:3px 12px;
                   border-radius:99px;font-size:11px;font-weight:700">{defect_cat}</span>
    </div>
    <div>
      <span style="color:#6b7c93;font-size:11px">異常數量</span><br>
      <b style="color:#e74c3c;font-size:16px">{defect_qty}</b>
      <span style="font-size:11px;color:#6b7c93"> pcs</span>
    </div>
  </div>
  {desc_html}
  <div style="margin-top:14px;padding-top:12px;border-top:1px solid #fde3e3;
              font-size:12px;color:#e74c3c;font-weight:700">
    ⏰ 請於 {reply_deadline} 前完成回覆
  </div>
</div>
""", unsafe_allow_html=True)


# ── 異常照片（若有）─────────────────────────────────────
defect_id = _val_or_empty("異常記錄編號")
if defect_id:
    photo_url = _load_defect_photo(defect_id)
    if photo_url:
        st.markdown("**📷 異常照片**")
        if "drive.google.com/file/d/" in photo_url:
            file_id = photo_url.split("/file/d/")[1].split("/")[0]
            thumb   = f"https://drive.google.com/thumbnail?id={file_id}&sz=w640"
            st.image(thumb, use_container_width=True)
        else:
            st.markdown(f'<a href="{photo_url}" target="_blank">🔗 查看異常照片</a>',
                        unsafe_allow_html=True)
        st.markdown("")


# ═══════════════════════════════════════════════════════
# CAPA 回覆表單
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🔧 CAPA 改善回覆")
st.caption(
    "請填寫以下改善對策（D3 / D4·D5 / D6 / D7），"
    "建議每欄詳細說明以利 REXONTEC 品保部門審核。"
)

# 取已有回覆（供更新場景使用）
exist_d3   = _val_or_empty("臨時對策_D3")
exist_d45  = _val_or_empty("根本原因_D4D5")
exist_d6   = _val_or_empty("永久對策_D6")
exist_d7   = _val_or_empty("CAPA驗證_D7")
exist_rep  = _val_or_empty("供應商回覆內容")

with st.form("scar_reply_form", clear_on_submit=False):

    # D3
    st.markdown("""
<div style="background:#fff3e0;border-left:4px solid #f39c12;border-radius:6px;
            padding:10px 14px;margin-bottom:8px;font-size:12px">
  <b style="color:#e67e22">D3 — 臨時對策</b>
  <span style="color:#8d6e0a">（立即圍堵措施：全數篩選、隔離可疑批、通知客戶…）</span>
</div>
""", unsafe_allow_html=True)
    f_d3 = st.text_area(
        "D3 臨時對策",
        value=exist_d3,
        placeholder="說明已採取的緊急圍堵行動，包含實施日期與數量…",
        height=100,
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # D4/D5
    st.markdown("""
<div style="background:#fef9e7;border-left:4px solid #f1c40f;border-radius:6px;
            padding:10px 14px;margin-bottom:8px;font-size:12px">
  <b style="color:#d4ac0d">D4/D5 — 根本原因分析</b>
  <span style="color:#7d6608">（5Why / 魚骨圖 — D4：流出點原因；D5：發生源原因）</span>
</div>
""", unsafe_allow_html=True)
    f_d45 = st.text_area(
        "D4/D5 根本原因",
        value=exist_d45,
        placeholder="利用 5Why 或魚骨圖說明為何異常品流出（D4）與為何發生（D5）…",
        height=130,
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # D6
    st.markdown("""
<div style="background:#e8f5e9;border-left:4px solid #27ae60;border-radius:6px;
            padding:10px 14px;margin-bottom:8px;font-size:12px">
  <b style="color:#1e8449">D6 — 永久改善對策</b>
  <span style="color:#1a5c34">（製程改善、防呆設計、SOP更新、供應商管制計畫）</span>
</div>
""", unsafe_allow_html=True)
    f_d6 = st.text_area(
        "D6 永久對策",
        value=exist_d6,
        placeholder="說明永久性預防措施，目標是讓相同問題不再發生…",
        height=100,
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # D7
    st.markdown("""
<div style="background:#e8eaf6;border-left:4px solid #3f51b5;border-radius:6px;
            padding:10px 14px;margin-bottom:8px;font-size:12px">
  <b style="color:#283593">D7 — CAPA 驗證方式</b>
  <span style="color:#1a237e">（驗收標準、預計完成日期、追蹤責任人）</span>
</div>
""", unsafe_allow_html=True)
    f_d7 = st.text_area(
        "D7 CAPA 驗證",
        value=exist_d7,
        placeholder="說明如何確認改善有效，包含量測方法、追蹤頻率與截止日期…",
        height=100,
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # 補充說明（選填）
    with st.expander("📎 補充說明 / 其他備註（選填）"):
        f_reply_content = st.text_area(
            "補充說明",
            value=exist_rep,
            placeholder="附加說明、附件描述、聯絡窗口資訊…",
            height=80,
            label_visibility="collapsed",
        )

    st.markdown("---")

    # 確認勾選
    agree = st.checkbox(
        "☑ 本人確認以上回覆內容正確無誤，代表貴司正式提交此 SCAR 改善回覆。",
    )

    submitted = st.form_submit_button(
        "📤 確認提交 SCAR 回覆",
        type="primary",
        use_container_width=True,
    )

# ── 表單送出處理 ─────────────────────────────────────────
if submitted:
    errors = []
    if not agree:
        errors.append("請勾選確認欄位後再提交。")
    if not f_d3.strip() and not f_d45.strip() and not f_d6.strip():
        errors.append("請至少填寫 D3、D4/D5、D6 其中一項改善對策。")

    if errors:
        for e in errors:
            st.error(f"⚠️ {e}")
    else:
        today_str = datetime.now().strftime("%Y/%m/%d")

        updates: dict = {
            "供應商回覆狀態": "已回覆",
            "供應商回覆日期": today_str,
        }
        if f_d3.strip():           updates["臨時對策_D3"]    = f_d3.strip()
        if f_d45.strip():          updates["根本原因_D4D5"]  = f_d45.strip()
        if f_d6.strip():           updates["永久對策_D6"]    = f_d6.strip()
        if f_d7.strip():           updates["CAPA驗證_D7"]    = f_d7.strip()
        if f_reply_content.strip(): updates["供應商回覆內容"] = f_reply_content.strip()

        try:
            update_scar(scar_id, updates)
            st.cache_data.clear()

            # ── 成功畫面 ──────────────────────────────
            st.markdown(f"""
<div style="background:linear-gradient(135deg,#e8f5e9,#f1f8e9);
            border:1px solid #a5d6a7;border-left:5px solid #27ae60;
            border-radius:10px;padding:22px 26px;margin:12px 0">
  <div style="font-size:28px;margin-bottom:10px">✅</div>
  <div style="font-size:17px;font-weight:900;color:#1b5e20;margin-bottom:8px">
    回覆已成功提交！
  </div>
  <div style="font-size:13px;color:#2e7d32;line-height:1.9">
    感謝 <b>{supplier_name}</b> 的配合。<br>
    SCAR <b>{scar_id}</b> 的改善回覆已記錄完成。<br>
    REXONTEC 品保部門將審查您的回覆，並於 CAPA 驗證完成後通知結案。<br><br>
    如有補充資料，歡迎透過原通知信連結再次開啟本頁面更新。
  </div>
</div>
""", unsafe_allow_html=True)

        except Exception as exc:
            st.error(
                f"❌ **提交失敗**：{exc}\n\n"
                "請稍後再試，或聯絡 REXONTEC 品保部門提供您的 SCAR 編號。"
            )


# ═══════════════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:44px;padding:16px 24px;text-align:center;
            font-size:11px;color:#95a5a6;border-top:1px solid #e9ecef">
  此頁面由 REXONTEC 力科技 品質管理系統（QMS）提供<br>
  如有疑問請聯絡品保部門 &nbsp;｜&nbsp; © {datetime.now().year} REXONTEC 力科技
</div>
""", unsafe_allow_html=True)
