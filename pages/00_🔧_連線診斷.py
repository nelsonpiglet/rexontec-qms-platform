"""
REXONTEC — Google 連線診斷頁面
用於排查 Streamlit Cloud 上的 gcp_service_account 問題
"""
import streamlit as st
import traceback
from datetime import datetime, timezone

st.set_page_config(page_title="連線診斷", page_icon="🔧", layout="wide")

st.title("🔧 Google Sheets 連線診斷")
st.caption("此頁面用於排查 Streamlit Cloud 連線問題，確認無誤後可移除")
st.divider()

# ── 步驟 1：Secrets 載入 ──────────────────────────────
st.subheader("步驟 1：Secrets 載入")
try:
    sa = st.secrets["gcp_service_account"]
    kid    = sa.get("private_key_id", "")
    email  = sa.get("client_email",   "")
    pk     = sa.get("private_key",    "")
    proj   = sa.get("project_id",     "")

    col1, col2 = st.columns(2)
    with col1:
        st.success("✅ `[gcp_service_account]` 載入成功")
        st.code(f"""
project_id      = {proj}
client_email    = {email}
private_key_id  = {kid}
        """)
    with col2:
        st.markdown("**private_key 格式檢查**")
        has_begin  = "-----BEGIN PRIVATE KEY-----" in pk
        has_end    = "-----END PRIVATE KEY-----"   in pk
        real_nl    = pk.count("\n")
        esc_n      = pk.count("\\n")

        st.write(f"✅ BEGIN 標記" if has_begin else "❌ 缺少 BEGIN")
        st.write(f"✅ END 標記"   if has_end   else "❌ 缺少 END")
        st.write(f"長度：{len(pk)} 字元（應 > 1600）")
        st.write(f"真實換行：{real_nl}（正常 = 換行後 google-auth 重組，0 也可）")
        st.write(f"長度是否合理：{'✅' if len(pk) > 1600 else '❌ 太短，可能被截斷'}")

except KeyError:
    st.error("❌ st.secrets 中找不到 `[gcp_service_account]`")
    st.info("請至 Streamlit Cloud → Manage app → Settings → Secrets 貼入正確的 TOML")
    st.stop()
except Exception as e:
    st.error(f"❌ Secrets 載入失敗：{e}")
    st.stop()

st.divider()

# ── 步驟 2：google-auth 憑證建立 ──────────────────────
st.subheader("步驟 2：google-auth 憑證建立")
creds = None
try:
    from google.oauth2.service_account import Credentials
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    st.success(f"✅ Credentials 物件建立成功")
    st.write(f"Service Account Email：`{creds.service_account_email}`")
    st.write(f"Token 有效：{creds.valid}")
except Exception as e:
    st.error(f"❌ 憑證建立失敗：{type(e).__name__}")
    st.code(traceback.format_exc())
    st.stop()

st.divider()

# ── 步驟 3：Token 刷新測試 ─────────────────────────────
st.subheader("步驟 3：Token 刷新測試（實際連線 Google）")
try:
    import google.auth.transport.requests
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    st.success("✅ Token 刷新成功！金鑰有效，Google 認證通過")
    st.write(f"Token 到期：{creds.expiry}")
except Exception as e:
    err_msg = str(e)
    st.error(f"❌ Token 刷新失敗：{type(e).__name__}")
    st.code(err_msg)

    if "invalid_grant" in err_msg:
        if "Invalid JWT Signature" in err_msg:
            st.warning("""
**可能原因：金鑰 `private_key` 內容有問題**

請確認：
1. 此金鑰是否已在 Google Cloud Console 被「刪除/停用」
2. 若已刪除 → 需建立全新金鑰，重新設定 Secrets
3. 若未刪除 → private_key 格式可能仍有問題
            """)
        elif "account not found" in err_msg.lower():
            st.warning("Service Account 不存在或已被刪除")
        else:
            st.warning("JWT 無效，可能是時鐘偏差或金鑰問題")
    st.stop()

st.divider()

# ── 步驟 4：gspread 連線測試 ──────────────────────────
st.subheader("步驟 4：gspread 連線測試")
try:
    import gspread
    client = gspread.authorize(creds)
    st.success("✅ gspread client 建立成功")

    SPREADSHEET_ID = "1OksPtvaabwXIMdO8gPA7A6s6oHpLy_Liewcc_pyOmA8"
    ss = client.open_by_key(SPREADSHEET_ID)
    sheets = [ws.title for ws in ss.worksheets()]
    st.success(f"✅ Google Sheet 開啟成功！工作表：{sheets}")
except Exception as e:
    st.error(f"❌ gspread 連線失敗：{type(e).__name__}: {e}")
    st.stop()

st.divider()
st.success("🎉 所有步驟通過！Google Sheets 連線正常。")
st.balloons()
