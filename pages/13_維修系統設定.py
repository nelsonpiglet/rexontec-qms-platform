"""
REXONTEC 力科品質指揮平台 — 維修保養系統
系統設定（Email 通知）
"""
import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from utils.style      import QMS_CSS, topbar, page_header
from utils.rma_config import load_config, save_config

st.set_page_config(
    page_title="REXONTEC 力科 | 維修系統設定",
    page_icon="⚙️",
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

st.markdown(
    page_header("系統設定", "REXONTEC 力科 | System Configuration", "CFG"),
    unsafe_allow_html=True,
)

cfg       = load_config()
email_cfg = cfg.get("email", {})

# ── Email 設定卡 ──────────────────────────────
st.markdown("""
<div class="card">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--accent)"></span>
      📧 Email 通知設定
    </div>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown("""
<div style="background:#e8f4fd;border:1px solid #90caf9;border-radius:8px;
            padding:14px 18px;margin-bottom:16px;font-size:13px;color:#1a2332">
  <b>📌 Gmail App Password 取得步驟：</b><br>
  1. 登入 Gmail → 點右上角頭像 → <b>管理 Google 帳戶</b><br>
  2. 點選 <b>安全性</b> → 確認已開啟 <b>兩步驟驗證</b><br>
  3. 搜尋「應用程式密碼」→ 選擇「郵件」→ 點 <b>產生</b><br>
  4. 複製產生的 <b>16 碼密碼</b>（格式：xxxx xxxx xxxx xxxx）填入下方
</div>
""", unsafe_allow_html=True)

with st.form("email_settings_form"):
    st.markdown("#### 發信帳號設定")
    c1, c2 = st.columns(2)
    with c1:
        sender_email = st.text_input(
            "發信 Gmail 帳號 *",
            value=email_cfg.get("sender_email",""),
            placeholder="yourname@gmail.com",
        )
    with c2:
        sender_password = st.text_input(
            "Gmail App Password * （16碼）",
            value=email_cfg.get("sender_password",""),
            placeholder="xxxx xxxx xxxx xxxx",
            type="password",
        )

    st.markdown("#### 收件設定")
    c3, c4 = st.columns(2)
    with c3:
        sales_email = st.text_input(
            "業務收件信箱 * （主要通知對象）",
            value=email_cfg.get("sales_email",""),
            placeholder="sales@rexontec.com",
        )
    with c4:
        cc_email = st.text_input(
            "副本信箱（選填）",
            value=email_cfg.get("cc_email",""),
            placeholder="manager@rexontec.com，可留空",
        )

    st.markdown("#### 通知時機")
    col_a, col_b = st.columns(2)
    with col_a:
        notify_new = st.checkbox("📦 新維修案件建立時通知", value=cfg.get("notify_on_new", True))
    with col_b:
        notify_close = st.checkbox("✅ 案件結案 / 報廢時通知", value=cfg.get("notify_on_close", True))

    st.markdown("<br>", unsafe_allow_html=True)
    sa, sb, sc = st.columns([1, 1, 1])
    with sa:
        save_btn = st.form_submit_button("💾　儲存設定", type="primary", use_container_width=True)
    with sb:
        test_btn = st.form_submit_button("📨　發送測試信", use_container_width=True)

# ── 儲存 ─────────────────────────────────────
if save_btn:
    errors = []
    if not sender_email.strip():    errors.append("請填入發信 Gmail 帳號")
    if not sender_password.strip(): errors.append("請填入 App Password")
    if not sales_email.strip():     errors.append("請填入業務收件信箱")
    for e in errors:
        st.error(f"⚠️  {e}")

    if not errors:
        new_cfg = {
            **cfg,
            "notify_on_new":   notify_new,
            "notify_on_close": notify_close,
            "email": {
                "smtp_server":    "smtp.gmail.com",
                "smtp_port":      587,
                "sender_email":   sender_email.strip(),
                "sender_password":sender_password.strip(),
                "sales_email":    sales_email.strip(),
                "cc_email":       cc_email.strip(),
            },
        }
        if save_config(new_cfg):
            st.success("✅ 設定已儲存！")
            st.rerun()
        else:
            st.error("❌ 儲存失敗，請檢查資料夾權限。")

# ── 測試信 ────────────────────────────────────
if test_btn:
    if not sender_email.strip() or not sender_password.strip() or not sales_email.strip():
        st.error("⚠️  請先填入發信帳號、App Password 及業務信箱，再測試。")
    else:
        with st.spinner("連線中，請稍候..."):
            try:
                now        = datetime.now().strftime("%Y/%m/%d %H:%M")
                recipients = [sales_email.strip()]
                if cc_email.strip():
                    recipients.append(cc_email.strip())

                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[REXONTEC 力科] Email 通知測試 — {now}"
                msg["From"]    = sender_email.strip()
                msg["To"]      = sales_email.strip()
                if cc_email.strip():
                    msg["Cc"] = cc_email.strip()

                html = f"""
                <div style="font-family:Arial,sans-serif;max-width:500px">
                  <div style="background:#0d1b2a;padding:14px 24px;border-radius:8px 8px 0 0">
                    <span style="color:#f0a500;font-weight:900;font-size:17px;
                                 letter-spacing:3px">REXONTEC 力科</span>
                  </div>
                  <div style="background:#fff;border:1px solid #dce3ec;
                              padding:24px;border-radius:0 0 8px 8px">
                    <h2 style="color:#0d1b2a;font-size:15px;margin:0 0 14px">
                      ✅ Email 通知測試成功
                    </h2>
                    <p style="font-size:13px;color:#555">
                      您已完成 REXONTEC 力科維修系統的 Email 通知設定。<br>
                      系統將在以下時機自動發送通知：
                    </p>
                    <ul style="font-size:13px;color:#555">
                      {"<li>📦 新維修案件建立時</li>" if notify_new else ""}
                      {"<li>✅ 案件結案 / ⚠️ 報廢通知時</li>" if notify_close else ""}
                    </ul>
                    <p style="font-size:11px;color:#9aafc4;margin-top:16px">
                      測試時間：{now}
                    </p>
                  </div>
                </div>"""
                msg.attach(MIMEText(html, "html", "utf-8"))

                with smtplib.SMTP("smtp.gmail.com", 587) as srv:
                    srv.ehlo(); srv.starttls()
                    srv.login(sender_email.strip(), sender_password.strip())
                    srv.sendmail(sender_email.strip(), recipients, msg.as_string())

                st.success(f"✅ 測試信已成功寄出至 **{sales_email.strip()}**！請確認收件匣。")

            except smtplib.SMTPAuthenticationError:
                st.error(
                    "❌ 驗證失敗！請確認：\n"
                    "1. Gmail 帳號正確\n"
                    "2. 填入的是 **App Password**（非 Gmail 登入密碼）\n"
                    "3. Gmail 已開啟兩步驟驗證"
                )
            except Exception as ex:
                st.error(f"❌ 發送失敗：{ex}")

# ── 目前設定狀態 ──────────────────────────────
st.markdown("""
<div class="card" style="margin-top:8px">
  <div class="card-header">
    <div class="card-title">
      <span class="card-dot" style="background:var(--pass)"></span>
      目前設定狀態
    </div>
  </div>
</div>""", unsafe_allow_html=True)

current = load_config()
ec = current.get("email", {})

def status_row(label, value, ok_check=True):
    if ok_check and value:
        badge = '<span style="background:#eafaf1;color:#27ae60;border:1px solid #a9dfbf;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700">✓ 已設定</span>'
    else:
        badge = '<span style="background:#fdedec;color:#c0392b;border:1px solid #f5b7b1;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700">✗ 未設定</span>'
    display = value if (value and label != "App Password") else ("●●●●●●●●" if value else "—")
    return f"""
    <div style="display:flex;align-items:center;padding:9px 0;
                border-bottom:1px solid var(--border);gap:12px">
      <div style="width:160px;font-size:12px;font-weight:700;color:var(--muted)">{label}</div>
      <div style="flex:1;font-size:13px;color:var(--text)">{display}</div>
      <div>{badge}</div>
    </div>"""

rows_html = (
    status_row("發信 Gmail",   ec.get("sender_email",""))     +
    status_row("App Password", ec.get("sender_password",""))  +
    status_row("業務收件信箱", ec.get("sales_email",""))      +
    status_row("副本信箱",     ec.get("cc_email",""), ok_check=False)
)

notify_new_s   = current.get("notify_on_new",   True)
notify_close_s = current.get("notify_on_close", True)
rows_html += (
    status_row("新案件通知", "開啟" if notify_new_s   else "", ok_check=notify_new_s)   +
    status_row("結案通知",   "開啟" if notify_close_s else "", ok_check=notify_close_s)
)

st.markdown(f'<div style="padding:4px 0">{rows_html}</div>', unsafe_allow_html=True)

all_set = bool(ec.get("sender_email") and ec.get("sender_password") and ec.get("sales_email"))
if all_set:
    st.success("🎉 Email 通知已就緒，系統將自動發送通知給業務。")
else:
    st.warning("⚠️  Email 通知尚未完整設定，請填入必填欄位並儲存。")
