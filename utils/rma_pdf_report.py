"""
REXONTEC 力科 — 維修報告 PDF 產生器
使用 fpdf2 + 微軟正黑體（Windows 系統字型）
"""
import io
import os
from datetime import datetime
from fpdf import FPDF, XPos, YPos

C_NAVY   = (13,  27,  42)
C_BLUE   = (26,  58,  92)
C_ACCENT = (30, 136, 229)
C_ORANGE = (240, 165,   0)
C_BG     = (247, 249, 252)
C_BORDER = (220, 227, 236)
C_TEXT   = (26,  35,  50)
C_MUTED  = (107, 124, 147)
C_GREEN  = (39,  174,  96)
C_RED    = (192,  57,  43)
C_PURPLE = (123,  31, 162)
C_YELLOW = (243, 156,  18)
C_WHITE  = (255, 255, 255)
C_LGRAY  = (240, 244, 248)

STATUS_COLOR = {
    "待收件":   C_ORANGE, "已收件":   C_ACCENT, "初診中":   C_ACCENT,
    "等待零件": C_YELLOW, "維修中":   C_ORANGE,
    "待QC":     C_PURPLE, "已出廠":   C_GREEN,  "報廢通知": C_RED,
}
STATUS_EMOJI_TEXT = {
    "待收件":"[待收件]","已收件":"[已收件]","初診中":"[初診中]",
    "等待零件":"[等待零件]","維修中":"[維修中]",
    "待QC":"[待QC]","已出廠":"[已出廠]","報廢通知":"[報廢通知]",
}

FONT_REG  = "C:/Windows/Fonts/msjh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msjhbd.ttc"
PAGE_W    = 210
PAGE_H    = 297
MARGIN    = 16
CONTENT_W = PAGE_W - MARGIN * 2


class RepairPDF(FPDF):

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.add_font("R",  fname=FONT_REG)
        self.add_font("B",  fname=FONT_BOLD)
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(True, margin=22)
        self._rma_id = ""

    def header(self):
        pass

    def footer(self):
        self.set_y(-14)
        self.set_font("R", size=7.5)
        self.set_text_color(*C_MUTED)
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        self.cell(0, 5,
                  f"REXONTEC 力科 | 馬達返廠維修報告  {self._rma_id}"
                  f"  ·  產生時間：{now}"
                  f"  ·  第 {self.page_no()} 頁",
                  align="C")

    def _rgb(self, color):
        self.set_draw_color(*color)

    def _fill(self, color):
        self.set_fill_color(*color)

    def _text_color(self, color):
        self.set_text_color(*color)

    def hline(self, y=None, lw=0.25, color=C_BORDER):
        if y is None:
            y = self.get_y()
        self.set_line_width(lw)
        self._rgb(color)
        self.line(MARGIN, y, PAGE_W - MARGIN, y)

    def section_title(self, num: str, title_zh: str, title_en: str = ""):
        self.set_fill_color(*C_NAVY)
        self.set_text_color(*C_WHITE)
        y = self.get_y()
        self.rect(MARGIN, y, CONTENT_W, 7.5, style="F")
        self.set_xy(MARGIN + 3, y + 0.8)
        self.set_font("B", size=10)
        en_part = f"  {title_en}" if title_en else ""
        self.cell(CONTENT_W - 6, 6, f"{num}.  {title_zh}{en_part}", ln=True)
        self.set_text_color(*C_TEXT)
        self.ln(1)

    def data_row(self, pairs: list[tuple], row_height=6.5, alt=False):
        bg = C_LGRAY if alt else C_WHITE
        self.set_fill_color(*bg)
        col_w = CONTENT_W / len(pairs)
        lbl_w = col_w * 0.38
        val_w = col_w * 0.62

        y0 = self.get_y()
        self.rect(MARGIN, y0, CONTENT_W, row_height, style="F")
        self.hline(y0, lw=0.15)

        x = MARGIN
        for label, value in pairs:
            self.set_xy(x + 2, y0 + 0.8)
            self.set_font("R", size=8.5)
            self._text_color(C_MUTED)
            self.cell(lbl_w - 2, row_height - 1, str(label), align="L")
            self.set_xy(x + lbl_w, y0 + 0.8)
            self.set_font("B", size=9)
            self._text_color(C_TEXT)
            self.cell(val_w - 2, row_height - 1, str(value or "—"), align="L")
            x += col_w

        self.set_y(y0 + row_height)

    def text_block(self, label: str, content: str, alt=False):
        if not content or content.strip() == "":
            self.data_row([(label, "—")], alt=alt)
            return

        bg = C_LGRAY if alt else C_WHITE
        self.set_fill_color(*bg)
        lines = content.strip().split("\n")

        self.set_font("R", size=9)
        available = CONTENT_W * 0.62 - 4
        text_h = 0
        for line in lines:
            line_count = max(1, int(len(line) * 5 / (available * 1.8)) + 1)
            text_h += line_count * 4.5

        row_height = max(7, text_h + 4)
        lbl_w = CONTENT_W * 0.38

        y0 = self.get_y()
        self.rect(MARGIN, y0, CONTENT_W, row_height, style="F")
        self.hline(y0, lw=0.15)

        self.set_xy(MARGIN + 2, y0 + 0.8)
        self.set_font("R", size=8.5)
        self._text_color(C_MUTED)
        self.cell(lbl_w - 2, 6, label, align="L")

        self.set_xy(MARGIN + lbl_w, y0 + 1)
        self.set_font("R", size=9)
        self._text_color(C_TEXT)
        self.multi_cell(CONTENT_W * 0.62 - 2, 4.8, content.strip())

        self.set_y(max(self.get_y(), y0 + row_height))

    def status_badge(self, status: str, x: float, y: float):
        color = STATUS_COLOR.get(status, C_ACCENT)
        label = STATUS_EMOJI_TEXT.get(status, status)
        self.set_font("B", size=9)
        w = self.get_string_width(label) + 8
        self.set_fill_color(*color)
        self.set_text_color(*C_WHITE)
        self.set_draw_color(*color)
        self.rect(x, y, w, 6.5, style="F")
        self.set_xy(x, y + 0.4)
        self.cell(w, 5.8, label, align="C")
        self.set_text_color(*C_TEXT)
        self.set_draw_color(*C_BORDER)
        return w

    def detect_row(self, step_label: str, items: list, alt: bool = False):
        """Draw one row for five-step detection (checkboxes)."""
        bg = C_LGRAY if alt else C_WHITE
        self.set_fill_color(*bg)
        row_h = 7.5
        step_w = CONTENT_W * 0.24
        y0 = self.get_y()
        self.rect(MARGIN, y0, CONTENT_W, row_h, style="F")
        self.hline(y0, lw=0.15)
        self.set_xy(MARGIN + 2, y0 + 1.2)
        self.set_font("B", size=8.5)
        self._text_color(C_NAVY)
        self.cell(step_w - 2, row_h - 2, step_label)
        item_w = (CONTENT_W - step_w) / max(len(items), 1)
        x = MARGIN + step_w
        for label, value in items:
            is_yes = str(value).strip() == "是"
            self.set_xy(x, y0 + 1.2)
            self.set_font("B", size=8.5)
            self._text_color(C_RED if is_yes else C_MUTED)
            self.cell(5, row_h - 2, "●" if is_yes else "○")
            self.set_xy(x + 5, y0 + 1.2)
            self.set_font("R", size=8.5)
            self._text_color(C_TEXT)
            self.cell(item_w - 6, row_h - 2, label)
            x += item_w
        self.set_y(y0 + row_h)

    def detect_resistance_row(self, ab: float, bc: float, ca: float,
                              abnormal: bool, alt: bool = False):
        """Draw Step 3 resistance values row."""
        bg = C_LGRAY if alt else C_WHITE
        self.set_fill_color(*bg)
        row_h = 7.5
        step_w = CONTENT_W * 0.24
        y0 = self.get_y()
        self.rect(MARGIN, y0, CONTENT_W, row_h, style="F")
        self.hline(y0, lw=0.15)
        self.set_xy(MARGIN + 2, y0 + 1.2)
        self.set_font("B", size=8.5)
        self._text_color(C_NAVY)
        self.cell(step_w - 2, row_h - 2, "Step3 電氣測試")
        resist_w = (CONTENT_W - step_w) * 0.65 / 3
        judge_w  = (CONTENT_W - step_w) * 0.35
        x = MARGIN + step_w
        for label in [f"AB: {ab:.2f} Ω", f"BC: {bc:.2f} Ω", f"CA: {ca:.2f} Ω"]:
            self.set_xy(x, y0 + 1.2)
            self.set_font("R", size=8.5)
            self._text_color(C_TEXT)
            self.cell(resist_w, row_h - 2, label)
            x += resist_w
        self.set_xy(x, y0 + 1.2)
        self.set_font("B", size=8.5)
        self._text_color(C_RED if abnormal else C_GREEN)
        self.cell(judge_w, row_h - 2, "! 線圈異常" if abnormal else "√ 阻值均衡")
        self.set_y(y0 + row_h)

    def sign_row(self, roles: list[str]):
        w_each = CONTENT_W / len(roles)
        y0     = self.get_y() + 2
        line_y = y0 + 14

        for i, role in enumerate(roles):
            x = MARGIN + i * w_each
            self.set_draw_color(*C_BORDER)
            self.set_line_width(0.3)
            self.rect(x + 2, y0, w_each - 4, 20)
            self.set_xy(x + 2, y0 + 1)
            self.set_font("B", size=9)
            self._text_color(C_MUTED)
            self.cell(w_each - 4, 6, role, align="C")
            self.set_draw_color(*C_BORDER)
            self.set_line_width(0.25)
            self.line(x + 8, line_y, x + w_each - 8, line_y)
            self.set_xy(x + 2, line_y + 1)
            self.set_font("R", size=7.5)
            self._text_color(C_MUTED)
            self.cell(w_each - 4, 5, "日期：____/____/____", align="C")

        self.set_y(y0 + 24)


def generate_repair_pdf(row: dict) -> bytes:
    pdf = RepairPDF()
    pdf._rma_id = str(row.get("RMA編號", ""))
    pdf.add_page()

    rma_id  = str(row.get("RMA編號",   ""))
    status  = str(row.get("維修狀態",  ""))
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    recv    = str(row.get("收件日期",  ""))[:16]

    # 1. 報告頁首
    pdf.set_fill_color(*C_NAVY)
    pdf.rect(MARGIN, MARGIN, CONTENT_W, 24, style="F")
    pdf.set_fill_color(*C_ORANGE)
    pdf.rect(MARGIN, MARGIN, 4, 24, style="F")

    pdf.set_xy(MARGIN + 7, MARGIN + 2)
    pdf.set_font("B", size=14)
    pdf.set_text_color(*C_ORANGE)
    pdf.cell(80, 8, "REXONTEC 力科", ln=False)

    pdf.set_xy(MARGIN + 7, MARGIN + 10)
    pdf.set_font("R", size=8.5)
    pdf.set_text_color(180, 200, 220)
    pdf.cell(80, 5, "馬達返廠維修保養系統  Motor Repair System", ln=False)

    pdf.set_xy(MARGIN + CONTENT_W - 68, MARGIN + 2)
    pdf.set_font("B", size=13)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(66, 8, "維修報告", align="R", ln=False)
    pdf.set_xy(MARGIN + CONTENT_W - 68, MARGIN + 10)
    pdf.set_font("R", size=8)
    pdf.set_text_color(180, 200, 220)
    pdf.cell(66, 5, "REPAIR REPORT", align="R", ln=False)

    pdf.set_y(MARGIN + 26)
    pdf.set_text_color(*C_TEXT)

    pdf.set_fill_color(*C_LGRAY)
    pdf.rect(MARGIN, pdf.get_y(), CONTENT_W, 12, style="F")

    pdf.set_xy(MARGIN + 3, pdf.get_y() + 2)
    pdf.set_font("R", size=8.5)
    pdf.set_text_color(*C_MUTED)
    pdf.cell(20, 6, "RMA 編號", ln=False)

    pdf.set_xy(MARGIN + 22, pdf.get_y())
    pdf.set_font("B", size=13)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(70, 7, rma_id, ln=False)

    badge_x = MARGIN + CONTENT_W - 55
    badge_y = pdf.get_y() + 0.5
    pdf.status_badge(status, badge_x, badge_y)

    pdf.set_y(pdf.get_y() + 14)
    pdf.hline(lw=0.5, color=C_NAVY)
    pdf.ln(3)

    pdf.data_row([("收件日期", recv), ("報告產生", now_str)], alt=True)
    pdf.data_row([("優先等級", str(row.get("優先等級",""))), ("維修類型", str(row.get("維修類型","")))])
    pdf.ln(4)

    # 2. 客戶資訊
    pdf.section_title("一", "客戶資訊", "Customer Information")
    pdf.data_row([("客戶公司", row.get("客戶公司","")),  ("聯絡人", row.get("聯絡人",""))],    alt=True)
    pdf.data_row([("聯絡電話", row.get("聯絡電話","")), ("客戶 Email", row.get("客戶Email",""))], alt=False)
    pdf.ln(4)

    # 3. 馬達資訊
    pdf.section_title("二", "馬達資訊", "Motor Information")
    pdf.data_row([("產品型號", row.get("產品型號","")),   ("馬達序號 S/N", row.get("馬達序號",""))],   alt=True)
    pdf.data_row([("送修數量", f"{row.get('馬達數量','')} 顆"), ("飛行總時數", f"{row.get('飛行總時數(估計)','')} 小時")], alt=False)
    pdf.data_row([("曾撞擊/墜機", row.get("是否曾撞擊/墜機","否")), ("", "")], alt=True)
    pdf.ln(4)

    # 4. 故障資訊
    pdf.section_title("三", "故障資訊", "Fault Description")
    pdf.data_row([("故障類別", row.get("故障類別","")), ("維修需求", row.get("維修類型",""))], alt=True)
    pdf.text_block("故障詳細描述", str(row.get("故障詳細描述","") or ""), alt=False)
    pdf.ln(4)

    # 4. 五步技術檢測（有資料才顯示）
    _has_det = any(str(row.get(k, "")).strip() for k in [
        "S1-外殼撞傷","S2-異音","S3-AB阻值","S4-高震動","S5-線圈燒毀","最終判定"
    ])
    if _has_det:
        if pdf.get_y() > PAGE_H - 22 - 70:
            pdf.add_page()
        pdf.section_title("四", "五步技術檢測", "Five-Step Inspection")
        _y = ("是","否")
        pdf.detect_row(
            "Step1 外觀檢測",
            [("外殼撞傷", row.get("S1-外殼撞傷","否")),
             ("軸心歪斜", row.get("S1-軸心歪斜","否")),
             ("沙土侵入", row.get("S1-沙土侵入","否")),
             ("螺絲裂痕", row.get("S1-螺絲裂痕","否"))],
            alt=True,
        )
        pdf.detect_row(
            "Step2 手感測試",
            [("異音",     row.get("S2-異音","否")),
             ("卡頓",     row.get("S2-卡頓","否")),
             ("軸承鬆動", row.get("S2-軸承鬆動","否"))],
            alt=False,
        )
        try:
            _ab = float(row.get("S3-AB阻值",0) or 0)
            _bc = float(row.get("S3-BC阻值",0) or 0)
            _ca = float(row.get("S3-CA阻值",0) or 0)
        except Exception:
            _ab = _bc = _ca = 0.0
        pdf.detect_resistance_row(_ab, _bc, _ca,
                                  str(row.get("S3-線圈異常","否")) == "是",
                                  alt=True)
        pdf.detect_row(
            "Step4 通電測試",
            [("高震動",   row.get("S4-高震動","否")),
             ("高溫",     row.get("S4-高溫","否")),
             ("無法啟動", row.get("S4-無法啟動","否"))],
            alt=False,
        )
        pdf.detect_row(
            "Step5 拆解分析",
            [("線圈燒毀", row.get("S5-線圈燒毀","否")),
             ("磁鐵脫落", row.get("S5-磁鐵脫落","否")),
             ("生鏽",     row.get("S5-生鏽","否"))],
            alt=True,
        )
        pdf.data_row([("最終判定", row.get("最終判定","")),
                      ("保固判定", row.get("保固判定",""))], alt=False)
        pdf.data_row([("維修方式", row.get("維修方式","")),
                      ("是否報廢", row.get("是否報廢",""))], alt=True)
        det_time = str(row.get("五步檢測時間","") or "")
        if det_time:
            pdf.data_row([("檢測時間", det_time), ("", "")], alt=False)
        pdf.ln(4)
        _sec5 = "五"
    else:
        _sec5 = "四"

    # 5. 維修記錄
    pdf.section_title(_sec5, "維修記錄", "Repair Record")
    pdf.data_row([("目前狀態", STATUS_EMOJI_TEXT.get(status, status)), ("", "")], alt=True)
    pdf.text_block("技術檢測備註", str(row.get("內部-技術檢測","") or ""), alt=False)
    pdf.text_block("保固判定",     str(row.get("內部-保固判定", "") or ""), alt=True)
    pdf.text_block("備　　　　註", str(row.get("備註","")            or ""), alt=False)
    pdf.ln(4)

    # 6. 故障照片
    raw_photos = str(row.get("故障照片連結", "") or "")
    photo_urls = [u.strip() for u in raw_photos.split(",") if u.strip()]

    _sec_photo = "六" if _has_det else "五"
    _sec_sign  = "七" if _has_det else "六"

    if photo_urls:
        if pdf.get_y() > PAGE_H - 22 - 80:
            pdf.add_page()
        pdf.section_title(_sec_photo, "故障照片", "Fault Photos")
        pdf.ln(2)

        img_w  = (CONTENT_W - 6) / 2
        img_h  = img_w * 0.65
        shown  = 0
        x_pos  = [MARGIN, MARGIN + img_w + 6]

        import urllib.request, io as _io
        for i, url in enumerate(photo_urls[:6]):
            col_idx = i % 2
            try:
                req  = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=8).read()
                ext  = "jpg" if b"\xff\xd8" in data[:4] else "png"
                pdf.image(_io.BytesIO(data),
                          x=x_pos[col_idx],
                          y=pdf.get_y(),
                          w=img_w, h=img_h,
                          type=ext)
                if col_idx == 1 or i == len(photo_urls[:6]) - 1:
                    pdf.set_y(pdf.get_y() + img_h + 3)
                shown += 1
            except Exception:
                pass

        if shown == 0:
            pdf.set_font("R", size=8.5)
            pdf.set_text_color(*C_MUTED)
            for url in photo_urls:
                pdf.cell(0, 5, url, ln=True)
        elif len(photo_urls) > 6:
            pdf.set_font("R", size=8)
            pdf.set_text_color(*C_MUTED)
            pdf.cell(0, 5, f"（另有 {len(photo_urls)-6} 張照片，請至 Google Drive 查看）", ln=True)

        pdf.set_text_color(*C_TEXT)
        pdf.ln(2)

    # 簽核欄
    if pdf.get_y() > PAGE_H - 22 - 50:
        pdf.add_page()

    pdf.section_title(_sec_sign, "簽核確認", "Approval")
    pdf.ln(2)
    pdf.sign_row(["業務確認", "維修技術員", "工程主管"])

    pdf.ln(3)
    pdf.hline(lw=0.3)
    pdf.ln(2)
    pdf.set_font("R", size=7.5)
    pdf.set_text_color(*C_MUTED)
    pdf.multi_cell(
        CONTENT_W, 4.5,
        "本報告由 REXONTEC 力科馬達返廠維修保養系統自動產生，僅供內部使用。"
        "如有疑問請聯絡相關業務人員。",
        align="C",
    )

    return bytes(pdf.output())
