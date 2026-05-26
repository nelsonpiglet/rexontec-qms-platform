"""
REXONTEC 力科技 — SCAR 供應商通知信工具
SMTP 發信 + HTML 模板 + 回覆連結產生

secrets.toml 需設定：
  [smtp]
  host         = "smtp.gmail.com"
  port         = 587
  user         = "your@gmail.com"
  password     = "your_app_password"        # Gmail 請使用「應用程式密碼」
  from_addr    = "REXONTEC QMS <your@gmail.com>"
  app_base_url = "https://your-app.streamlit.app"  # 部署後請更新此網址
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import streamlit as st


# ═══════════════════════════════════════════════════════
# 設定讀取
# ═══════════════════════════════════════════════════════

def get_smtp_cfg() -> dict:
    """
    從 st.secrets["smtp"] 讀取 SMTP 設定。
    回傳含預設值的設定字典。
    """
    defaults = {
        "host":         "smtp.gmail.com",
        "port":         587,
        "user":         "",
        "password":     "",
        "from_addr":    "REXONTEC QMS",
        "app_base_url": "https://your-app.streamlit.app",
    }
    try:
        cfg = dict(st.secrets.get("smtp", {}))
    except Exception:
        cfg = {}
    return {**defaults, **cfg}


def build_reply_url(scar_no: str) -> str:
    """
    產生供應商 SCAR 外部回覆頁連結。
    頁面路由：pages/43_SCAR_Reply.py → /43_SCAR_Reply
    """
    cfg  = get_smtp_cfg()
    base = str(cfg.get("app_base_url", "")).rstrip("/")
    return f"{base}/43_SCAR_Reply?scar_id={scar_no}"


# ═══════════════════════════════════════════════════════
# HTML Email 模板
# ═══════════════════════════════════════════════════════

def _build_html(
    scar_no: str,
    supplier_name: str,
    part_no: str,
    part_name: str,
    defect_cat: str,
    defect_desc: str,
    defect_qty: str,
    reply_deadline: str,
    reply_url: str,
) -> str:
    now_str = datetime.now().strftime("%Y/%m/%d")
    desc_block = ""
    if defect_desc and defect_desc not in ("", "nan"):
        desc_block = f"""
          <tr>
            <td colspan="2" style="padding:10px 0 2px;font-size:12px;color:#6b7c93;
                                   border-top:1px solid #f0f0f0">異常描述</td>
          </tr>
          <tr>
            <td colspan="2" style="padding:2px 0 10px;font-size:13px;color:#2c3e50;
                                   line-height:1.7;border-bottom:1px solid #f0f0f0">
              {defect_desc}
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>SCAR 供應商異常改善通知 — {scar_no}</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;
             font-family:Arial,'Microsoft JhengHei',sans-serif;color:#2c3e50">

<!-- ▌HEADER -->
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:linear-gradient(135deg,#1e3a5f 0%,#2980b9 100%);padding:28px 0">
  <tr>
    <td align="center">
      <div style="font-size:22px;font-weight:900;color:#fff;letter-spacing:2px">
        ⚙️ REXONTEC 力科技
      </div>
      <div style="font-size:12px;color:#bde3ff;margin-top:6px;letter-spacing:1px">
        SUPPLIER CORRECTIVE ACTION REQUEST
      </div>
    </td>
  </tr>
</table>

<!-- ▌BODY WRAPPER -->
<table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td align="center" style="padding:24px 16px 0">
      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%">

        <!-- SCAR 標題卡 -->
        <tr>
          <td>
            <div style="background:#fff;border-radius:10px;
                        border:1px solid #dce3ec;border-left:5px solid #e74c3c;
                        padding:18px 22px;margin-bottom:16px">
              <div style="font-size:10px;color:#6b7c93;font-weight:700;
                          letter-spacing:1px;text-transform:uppercase">
                供應商異常改善要求通知
              </div>
              <div style="font-size:22px;font-weight:900;color:#1e3a5f;margin-top:6px">
                {scar_no}
              </div>
              <div style="font-size:11px;color:#6b7c93;margin-top:6px">
                發出日期：{now_str}
                &nbsp;｜&nbsp;
                請於 <b style="color:#e74c3c">{reply_deadline}</b> 前完成回覆
              </div>
            </div>
          </td>
        </tr>

        <!-- 問候語 -->
        <tr>
          <td style="padding:0 0 16px">
            <p style="font-size:13px;line-height:1.9;margin:0;color:#2c3e50">
              親愛的 <b style="color:#1e3a5f">{supplier_name}</b> 夥伴，
              <br>
              感謝長期合作。本次針對貴司供應品項發現異常，
              請詳閱以下異常明細，並於回覆期限前填寫改善對策。
            </p>
          </td>
        </tr>

        <!-- 異常明細卡 -->
        <tr>
          <td>
            <div style="background:#fff;border-radius:10px;
                        border:1px solid #dce3ec;padding:18px 22px;margin-bottom:16px">
              <div style="font-size:11px;font-weight:700;color:#6b7c93;
                          letter-spacing:1px;margin-bottom:14px">📋 異常明細</div>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="50%" style="padding:7px 0;border-bottom:1px solid #f0f0f0;
                                         font-size:12px;color:#6b7c93">料號</td>
                  <td width="50%" style="padding:7px 0;border-bottom:1px solid #f0f0f0;
                                         font-size:13px;font-weight:700;color:#1e3a5f">
                    {part_no}
                  </td>
                </tr>
                <tr>
                  <td style="padding:7px 0;border-bottom:1px solid #f0f0f0;
                             font-size:12px;color:#6b7c93">品名</td>
                  <td style="padding:7px 0;border-bottom:1px solid #f0f0f0;
                             font-size:13px;font-weight:700;color:#1e3a5f">{part_name}</td>
                </tr>
                <tr>
                  <td style="padding:7px 0;border-bottom:1px solid #f0f0f0;
                             font-size:12px;color:#6b7c93">異常類別</td>
                  <td style="padding:7px 0;border-bottom:1px solid #f0f0f0">
                    <span style="background:#fde3e3;color:#c0392b;padding:2px 10px;
                                 border-radius:99px;font-size:11px;font-weight:700">
                      {defect_cat}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:7px 0;border-bottom:1px solid #f0f0f0;
                             font-size:12px;color:#6b7c93">異常數量</td>
                  <td style="padding:7px 0;border-bottom:1px solid #f0f0f0;
                             font-size:13px;font-weight:700;color:#e74c3c">
                    {defect_qty} pcs
                  </td>
                </tr>
                {desc_block}
              </table>
            </div>
          </td>
        </tr>

        <!-- CAPA 要求說明 -->
        <tr>
          <td>
            <div style="background:#fffdf3;border:1px solid #f5e89a;
                        border-left:4px solid #f39c12;border-radius:8px;
                        padding:14px 18px;margin-bottom:20px">
              <div style="font-size:12px;font-weight:700;color:#7d5a00;margin-bottom:8px">
                📌 請填寫以下 CAPA 改善報告（8D 格式）
              </div>
              <table cellpadding="0" cellspacing="0"
                     style="font-size:12px;color:#5d4000;line-height:2.1">
                <tr>
                  <td style="padding-right:12px;font-weight:700;color:#b8860b">D3</td>
                  <td>臨時對策：立即圍堵措施、隔離可疑品、通知客戶</td>
                </tr>
                <tr>
                  <td style="font-weight:700;color:#b8860b">D4/D5</td>
                  <td>根本原因分析：5Why / 魚骨圖 — 發生源與流出點</td>
                </tr>
                <tr>
                  <td style="font-weight:700;color:#b8860b">D6</td>
                  <td>永久改善對策：製程改善、防呆設計、管制計畫更新</td>
                </tr>
                <tr>
                  <td style="font-weight:700;color:#b8860b">D7</td>
                  <td>CAPA 驗證：驗收標準、完成日期、追蹤責任人</td>
                </tr>
              </table>
            </div>
          </td>
        </tr>

        <!-- CTA 按鈕 -->
        <tr>
          <td align="center" style="padding-bottom:24px">
            <a href="{reply_url}"
               style="display:inline-block;
                      background:linear-gradient(135deg,#e74c3c 0%,#c0392b 100%);
                      color:#fff;text-decoration:none;padding:15px 44px;
                      border-radius:8px;font-size:15px;font-weight:700;
                      letter-spacing:0.5px">
              🔗 點此填寫 SCAR 回覆表單
            </a>
            <div style="font-size:10px;color:#6b7c93;margin-top:10px">
              若按鈕無法點擊，請複製以下網址至瀏覽器開啟：
            </div>
            <div style="font-size:10px;color:#3498db;margin-top:4px;
                        word-break:break-all;padding:0 20px">
              {reply_url}
            </div>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>

<!-- ▌FOOTER -->
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#2c3e50;padding:18px 0;margin-top:8px">
  <tr>
    <td align="center">
      <div style="font-size:11px;color:#95a5a6;line-height:2">
        此信為 REXONTEC 力科技 品質管理系統（QMS）自動發送，請勿直接回覆此郵件。<br>
        如有疑問請聯絡 REXONTEC 品保部門。<br>
        &copy; {datetime.now().year} REXONTEC 力科技
      </div>
    </td>
  </tr>
</table>

</body>
</html>"""


# ═══════════════════════════════════════════════════════
# 主要發送函式
# ═══════════════════════════════════════════════════════

def send_supplier_scar_email(
    scar_no: str,
    supplier_name: str,
    supplier_email: str,
    part_no: str,
    part_name: str,
    defect_cat: str,
    defect_desc: str,
    defect_qty,
    reply_deadline: str,
):
    """
    發送 SCAR 供應商通知信。

    Parameters
    ----------
    scar_no         : SCAR 編號，例如 "SCAR-2026-0001"
    supplier_name   : 供應商名稱
    supplier_email  : 供應商電子郵件地址
    part_no         : 料號
    part_name       : 品名
    defect_cat      : 異常類別
    defect_desc     : 異常描述
    defect_qty      : 異常數量（int 或 str）
    reply_deadline  : 要求回覆期限字串，如 "2026/06/10"

    Returns
    -------
    (success: bool, message: str)
    """
    cfg = get_smtp_cfg()

    # ── 前置檢查 ─────────────────────────────────────
    if not cfg.get("user") or not cfg.get("password"):
        return (
            False,
            "⚠️ SMTP 設定不完整。請在 .streamlit/secrets.toml 的 [smtp] 區塊填入"
            " host / port / user / password / app_base_url。",
        )

    if not supplier_email or "@" not in supplier_email:
        return False, f"⚠️ 供應商 Email 格式不正確：{supplier_email}"

    # ── 產生回覆連結 ──────────────────────────────────
    reply_url = build_reply_url(scar_no)

    # ── 組合郵件內容 ──────────────────────────────────
    html_body = _build_html(
        scar_no=scar_no,
        supplier_name=supplier_name,
        part_no=part_no,
        part_name=part_name,
        defect_cat=defect_cat,
        defect_desc=defect_desc,
        defect_qty=str(defect_qty),
        reply_deadline=reply_deadline,
        reply_url=reply_url,
    )

    text_body = (
        f"REXONTEC 力科技 — SCAR 供應商異常改善通知\n\n"
        f"SCAR 編號：{scar_no}\n"
        f"供應商：  {supplier_name}\n"
        f"料號：    {part_no}  /  品名：{part_name}\n"
        f"異常類別：{defect_cat}\n"
        f"異常數量：{defect_qty} pcs\n"
        f"異常描述：{defect_desc}\n"
        f"要求回覆期限：{reply_deadline}\n\n"
        f"請點擊以下連結填寫 CAPA 回覆：\n"
        f"{reply_url}\n\n"
        f"此信由系統自動發送，請勿直接回覆。\n"
        f"© {datetime.now().year} REXONTEC 力科技"
    )

    subject = (
        f"【REXONTEC 力科技】SCAR 供應商改善通知 — {scar_no}"
        f"（{part_no} / {supplier_name}）"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg.get("from_addr") or cfg["user"]
    msg["To"]      = supplier_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html",  "utf-8"))

    # ── 發送 ─────────────────────────────────────────
    try:
        port = int(cfg.get("port", 587))
        host = str(cfg.get("host", "smtp.gmail.com"))

        if port == 465:
            # SSL 直連（不常用，備用）
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=ctx) as srv:
                srv.login(cfg["user"], cfg["password"])
                srv.sendmail(cfg["user"], [supplier_email], msg.as_string())
        else:
            # STARTTLS（Gmail/Office365 預設 587）
            with smtplib.SMTP(host, port) as srv:
                srv.ehlo()
                srv.starttls(context=ssl.create_default_context())
                srv.ehlo()
                srv.login(cfg["user"], cfg["password"])
                srv.sendmail(cfg["user"], [supplier_email], msg.as_string())

        return True, f"✅ 通知信已成功發送至 {supplier_email}"

    except smtplib.SMTPAuthenticationError:
        return (
            False,
            "❌ SMTP 認證失敗：帳號或密碼錯誤。\n"
            "Gmail 用戶請確認已開啟兩步驟驗證並使用「應用程式密碼」。",
        )
    except smtplib.SMTPRecipientsRefused:
        return False, f"❌ 收件人地址被拒絕：{supplier_email}"
    except smtplib.SMTPConnectError:
        return (
            False,
            f"❌ 無法連線至 SMTP 伺服器 {host}:{port}，請確認網路與防火牆設定。",
        )
    except smtplib.SMTPException as exc:
        return False, f"❌ SMTP 錯誤：{exc}"
    except Exception as exc:
        return False, f"❌ 發送失敗（未知錯誤）：{exc}"
