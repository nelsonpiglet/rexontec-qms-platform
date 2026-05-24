"""
REXONTEC 力科 — 維修保養系統 Email 自動通知工具
使用 Gmail SMTP + App Password
"""
import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from utils.rma_config import get_email_cfg, load_config


def _cfg():
    local = get_email_cfg()
    if local:
        return local
    try:
        return st.secrets["email"]
    except Exception:
        return None


def _send(subject: str, body_html: str) -> bool:
    cfg = _cfg()
    if not cfg:
        return False
    try:
        recipients = [cfg["sales_email"]]
        if cfg.get("cc_email"):
            recipients.append(cfg["cc_email"])

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = cfg["sender_email"]
        msg["To"]      = cfg["sales_email"]
        if cfg.get("cc_email"):
            msg["Cc"] = cfg["cc_email"]
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(cfg.get("smtp_server", "smtp.gmail.com"),
                          int(cfg.get("smtp_port", 587))) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(cfg["sender_email"], cfg["sender_password"])
            srv.sendmail(cfg["sender_email"], recipients, msg.as_string())
        return True
    except Exception as e:
        print(f"[Email] 發送失敗：{e}")
        return False


def _shell(badge_color: str, icon: str, title: str, rows: list[tuple], note: str = "") -> str:
    row_html = ""
    for i, (label, value) in enumerate(rows):
        bg = "background:#f7f9fc;" if i % 2 == 0 else ""
        row_html += f"""
        <tr>
          <td style="{bg}padding:9px 12px;font-weight:700;color:#6b7c93;
                     width:35%;font-size:12px">{label}</td>
          <td style="{bg}padding:9px 12px;font-size:13px;color:#1a2332">{value}</td>
        </tr>"""

    note_block = ""
    if note:
        note_block = f"""
        <p style="margin:16px 0 0;padding:12px 14px;background:#fff8e1;
                  border-left:4px solid #f0a500;font-size:12px;color:#555">
          📝 備註：{note}
        </p>"""

    return f"""
    <div style="font-family:Arial,'Noto Sans TC',sans-serif;max-width:620px;margin:0 auto">
      <div style="background:#0d1b2a;padding:14px 24px;border-radius:8px 8px 0 0;
                  display:flex;align-items:center;gap:12px">
        <span style="color:#f0a500;font-weight:900;font-size:17px;letter-spacing:3px">REXONTEC 力科</span>
        <span style="color:rgba(255,255,255,.4);font-size:10px">馬達返廠維修保養系統</span>
      </div>
      <div style="background:#fff;border:1px solid #dce3ec;
                  border-top:none;padding:24px;border-radius:0 0 8px 8px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px">
          <span style="background:{badge_color};color:#fff;font-size:18px;
                       width:36px;height:36px;border-radius:50%;display:inline-flex;
                       align-items:center;justify-content:center">{icon}</span>
          <h2 style="margin:0;font-size:15px;color:#0d1b2a">{title}</h2>
        </div>
        <table style="width:100%;border-collapse:collapse">
          {row_html}
        </table>
        {note_block}
      </div>
      <p style="font-size:10px;color:#9aafc4;text-align:center;margin:8px 0 0">
        此郵件由 REXONTEC 力科 維修管理系統自動發送，請勿直接回覆。
      </p>
    </div>"""


def notify_new_rma(rma_id: str, data: dict) -> bool:
    if not load_config().get("notify_on_new", True):
        return False
    now  = datetime.now().strftime("%Y/%m/%d %H:%M")
    pri  = data.get("priority", "")
    pri_color = {"P1": "#c0392b", "P2": "#e67e22",
                 "P3": "#1e88e5", "P4": "#7b7b7b"}.get(pri, "#1e88e5")

    subject = (f"[REXONTEC 力科] 📦 新維修案件 {rma_id}"
               f" — {data.get('model','')} / {data.get('fault_type','')}")

    rows = [
        ("RMA 編號",
         f"<b style='font-size:15px;color:#0d1b2a'>{rma_id}</b>"),
        ("產品型號",      data.get("model", "")),
        ("馬達序號 S/N",  data.get("motor_sn", "")),
        ("故障類別",      data.get("fault_type", "")),
        ("維修需求",      data.get("repair_type", "")),
        ("客戶公司",      data.get("company", "")),
        ("聯絡人 / 電話",
         f"{data.get('contact','')}　{data.get('phone','')}"),
        ("優先等級",
         f"<span style='background:{pri_color};color:#fff;"
         f"padding:2px 10px;border-radius:99px;font-size:11px;"
         f"font-weight:700'>{pri}</span>"),
        ("建立時間", now),
    ]

    html = _shell("#1e88e5", "📦", "新維修案件已建立，請確認排程", rows,
                  note=data.get("note", ""))
    return _send(subject, html)


def notify_case_closed(rma_id: str, new_status: str, info: dict) -> bool:
    if not load_config().get("notify_on_close", True):
        return False
    now     = datetime.now().strftime("%Y/%m/%d %H:%M")
    is_done = new_status == "已出廠"
    clr     = "#27ae60" if is_done else "#c0392b"
    icon    = "✅" if is_done else "⚠️"
    subject = (f"[REXONTEC 力科] {icon} 案件 {rma_id} 已{new_status}"
               f" — {info.get('客戶公司', '')}")

    rows = [
        ("RMA 編號",
         f"<b style='font-size:15px;color:#0d1b2a'>{rma_id}</b>"),
        ("最新狀態",
         f"<span style='background:{clr};color:#fff;"
         f"padding:3px 12px;border-radius:99px;font-size:12px;"
         f"font-weight:700'>{new_status}</span>"),
        ("產品型號", info.get("產品型號", "")),
        ("馬達序號", info.get("馬達序號", "")),
        ("故障類別", info.get("故障類別", "")),
        ("維修類型", info.get("維修類型", "")),
        ("客戶公司", info.get("客戶公司", "")),
        ("聯絡人",   info.get("聯絡人", "")),
        ("更新時間", now),
    ]

    html = _shell(clr, icon, f"案件 {rma_id} 狀態已更新為「{new_status}」", rows)
    return _send(subject, html)
