"""
REXONTEC 力科 — 客訴與8D管理系統
8D 改善報告 PDF 產生器（含 REXON Logo 抬頭）
"""
from fpdf import FPDF
from datetime import datetime
import textwrap, os

FONT_REG   = "C:/Windows/Fonts/msjh.ttc"
FONT_BOLD  = "C:/Windows/Fonts/msjhbd.ttc"
LOGO_PATH  = os.path.join(os.path.dirname(__file__), "..", "assets", "rexon_logo_white.png")

D8_STEPS = [
    ("D1", "問題處理小組", "PROBLEM SOLVING TEAM",           "D1_團隊成員",  (21,  101, 192)),
    ("D2", "問題敘述",     "PROBLEM DESCRIPTION",            "D2_問題描述",  (40,   53, 147)),
    ("D3", "緊急對策",     "CONTAINMENT ACTION",             "D3_臨時對策",  (106,  27, 154)),
    ("D4", "問題真因",     "ROOT CAUSE",                     "D4_根因分析",  (173,  20,  87)),
    ("D5", "矯正措施",     "CORRECTIVE ACTION",              "D5_永久改善",  (183,  28,  28)),
    ("D6", "改善驗證",     "CORRECTIVE ACTION VERIFICATION", "D6_改善驗證",  (230, 101,   0)),
    ("D7", "永久預防",     "PERMANENT PREVENTIVE ACTION",    "D7_預防措施",  (46,  125,  50)),
    ("D8", "小組評論",     "TEAM MEMBER COMMENTS",           "D8_結案表揚",  (0,   105,  92)),
]

NAVY  = (13,  27,  42)
GREEN = (0,  154,  68)   # REXON green
WHITE = (255, 255, 255)
LIGHT = (248, 249, 250)
GREY  = (200, 200, 200)
LGREY = (230, 232, 235)
DIM   = (120, 130, 145)
TEXT  = (30,  40,  55)
GOLD  = (240, 165,   0)


class D8PDF(FPDF):
    def __init__(self, report_data: dict):
        super().__init__()
        self.data = report_data
        self.add_font("R",  "", FONT_REG,  uni=True)
        self.add_font("B",  "", FONT_BOLD, uni=True)
        self.set_auto_page_break(auto=True, margin=18)
        self._first_page = True

    # ── 每頁頁首（頁2起精簡版）────────────────────────
    def header(self):
        if self._first_page:
            self._first_page = False
            return
        # 頁2+ 細帶
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 10, "F")
        self.set_xy(0, 1)
        self.set_font("B", size=8)
        self.set_text_color(*GOLD)
        self.cell(0, 8, "  REXONTEC 力科   客戶抱怨受理 / 追查處理書 (8D)", ln=0)
        d8_id = self.data.get("8D編號", "")
        cs_id = self.data.get("客訴編號", "")
        self.set_font("R", size=7.5)
        self.set_text_color(*LGREY)
        self.cell(0, 8, f"{d8_id}  /  {cs_id}  ", align="R", ln=1)
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("R", size=8)
        self.set_text_color(*DIM)
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        self.cell(0, 8,
                  f"力山科技股份有限公司  |  產生時間：{now}  |  第 {self.page_no()} 頁",
                  align="C")

    # ── 工具 ──────────────────────────────────────────
    def _text(self): self.set_text_color(*TEXT)
    def _dim(self):  self.set_text_color(*DIM)

    def section_band(self, code, zh, en, rgb):
        """彩色 D1–D8 標題帶"""
        y = self.get_y()
        self.set_fill_color(*rgb)
        self.rect(14, y, 182, 9, "F")
        # 圓形編號
        self.set_fill_color(*WHITE)
        self.ellipse(15.5, y + 0.8, 7.5, 7.5, "F")
        self.set_xy(15.5, y + 0.8)
        self.set_font("B", size=7)
        self.set_text_color(*rgb)
        self.cell(7.5, 7.5, code, align="C")
        # 中文
        self.set_xy(25, y + 0.5)
        self.set_font("B", size=10)
        self.set_text_color(*WHITE)
        self.cell(80, 8, zh)
        # 英文
        self.set_xy(105, y + 1.8)
        self.set_font("R", size=7.5)
        self.set_text_color(255, 255, 200)
        self.cell(88, 6, en)
        self.ln(11)

    def content_block(self, text):
        """灰底文字框"""
        text = str(text or "").strip()
        if not text:
            return
        self.set_font("R", size=9.5)
        lines = []
        for raw in text.split("\n"):
            raw = raw.strip()
            if raw:
                wrapped = textwrap.wrap(raw, width=72)
                lines.extend(wrapped if wrapped else [raw])
            else:
                lines.append("")
        h = max(len(lines) * 5.5 + 8, 14)
        y = self.get_y()
        self.set_fill_color(*LIGHT)
        self.set_draw_color(*GREY)
        self.rect(14, y, 182, h, "FD")
        self.set_xy(18, y + 4)
        self._text()
        for li in lines:
            self.set_x(18)
            self.cell(178, 5.5, li)
            self.ln(5.5)
        self.ln(4)

    def divider(self):
        y = self.get_y()
        self.set_draw_color(*GREY)
        self.line(14, y, 196, y)
        self.ln(3)


def _draw_letterhead(pdf: D8PDF, cs_data: dict):
    """
    第一頁抬頭：REXON Logo + 公司名 + 標題 + 基本資訊表
    比照 Excel 客戶抱怨受理書格式
    """
    pdf.set_margins(0, 0, 0)
    pdf.set_xy(0, 0)

    # ── 頂部裝飾細線（REXON green）──────────────────
    pdf.set_fill_color(*GREEN)
    pdf.rect(0, 0, 210, 2, "F")

    # ── Logo 區（左 logo + 右公司名）────────────────
    logo_y = 5
    logo_h = 18   # mm

    # Logo 圖片
    logo_abs = os.path.abspath(LOGO_PATH)
    if os.path.exists(logo_abs):
        pdf.image(logo_abs, x=12, y=logo_y, h=logo_h)
    else:
        # fallback 文字 logo
        pdf.set_xy(12, logo_y + 2)
        pdf.set_font("B", size=18)
        pdf.set_text_color(*GREEN)
        pdf.cell(60, 12, "REXON")

    # 右側公司名
    pdf.set_xy(90, logo_y + 2)
    pdf.set_font("B", size=14)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, "力山科技股份有限公司", ln=1)

    pdf.set_xy(90, logo_y + 10)
    pdf.set_font("R", size=8)
    pdf.set_text_color(*DIM)
    pdf.cell(0, 5, "What An Excellent Radio!", ln=1)

    pdf.set_y(logo_y + logo_h + 3)

    # 分隔線（綠色）
    pdf.set_draw_color(*GREEN)
    pdf.set_line_width(0.6)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(4)

    # ── 主標題（灰底置中）────────────────────────────
    title_y = pdf.get_y()
    pdf.set_fill_color(235, 237, 240)
    pdf.set_draw_color(*GREY)
    pdf.rect(12, title_y, 186, 10, "FD")
    pdf.set_xy(12, title_y + 1)
    pdf.set_font("B", size=12)
    pdf.set_text_color(*NAVY)
    pdf.cell(186, 8, "客戶抱怨受理  /  追查處理書  (8D)", align="C", ln=1)
    pdf.ln(3)

    # ── 資訊表（6欄，比照 Excel 格式）─────────────────
    table_y   = pdf.get_y()
    col_defs  = [("客戶編號", 25), ("客戶名稱", 30), ("機種 / 型號", 55),
                 ("M/O 編號", 30), ("批量", 18), ("出貨日期", 28)]
    total_w   = sum(w for _, w in col_defs)
    left_x    = 12

    # 表頭列（深藍底 白字）
    pdf.set_fill_color(*NAVY)
    pdf.set_draw_color(*GREY)
    pdf.set_text_color(*WHITE)
    pdf.set_font("B", size=8.5)
    pdf.set_xy(left_x, table_y)
    for label, w in col_defs:
        pdf.cell(w, 7, label, border=1, align="C", fill=True)
    pdf.ln(7)

    # 資料列（白底）
    row_y = pdf.get_y()
    row_vals = [
        cs_data.get("客戶編號", ""),
        cs_data.get("客戶名稱", ""),
        cs_data.get("機型", ""),
        cs_data.get("mo_number", cs_data.get("SN/Lot", "")),
        str(cs_data.get("批量", "1")),
        cs_data.get("出貨日期", ""),
    ]

    # 機型可能多行 → 計算最高行數
    model_text = str(row_vals[2]).strip()
    model_lines = [l.strip() for l in model_text.replace(" / ", "\n").replace("/", "\n").split("\n") if l.strip()]
    row_h = max(len(model_lines) * 5.5 + 4, 14)

    pdf.set_fill_color(*WHITE)
    pdf.set_text_color(*TEXT)
    pdf.set_font("R", size=9)

    x_cursor = left_x
    for i, (label, w) in enumerate(col_defs):
        val = row_vals[i]
        pdf.set_xy(x_cursor, row_y)
        if i == 2:  # 機型欄多行
            pdf.rect(x_cursor, row_y, w, row_h, "FD")
            pdf.set_font("R", size=8)
            pdf.set_xy(x_cursor + 1, row_y + 2)
            for ln_txt in model_lines:
                pdf.set_x(x_cursor + 1)
                pdf.cell(w - 2, 5.5, ln_txt)
                pdf.ln(5.5)
            pdf.set_font("R", size=9)
        else:
            pdf.cell(w, row_h, str(val), border=1, align="C")
        x_cursor += w

    pdf.set_y(row_y + row_h + 4)
    pdf.set_draw_color(200, 200, 200)
    pdf.ln(2)

    # ── 附加資訊列（抱怨方式 / 首發再發 / 發文日期）─────
    extra_y = pdf.get_y()
    extras = [
        ("抱怨方式", cs_data.get("抱怨方式", "E-mail"),          45),
        ("首發/再發", cs_data.get("首發再發", "首發"),             45),
        ("客訴等級",  cs_data.get("客訴等級", ""),                 45),
        ("發文日期",  cs_data.get("客訴日期", ""),                 51),
    ]
    pdf.set_fill_color(243, 246, 251)
    pdf.rect(12, extra_y, 186, 8, "FD")
    x_cur = 12
    for lbl, val, w in extras:
        pdf.set_xy(x_cur + 1, extra_y + 1)
        pdf.set_font("B", size=8); pdf.set_text_color(*DIM)
        pdf.cell(20, 6, lbl + "：")
        pdf.set_font("R", size=8.5); pdf.set_text_color(*TEXT)
        pdf.cell(w - 22, 6, str(val))
        x_cur += w
    pdf.ln(10)


def generate_8d_pdf(cs_data: dict, d8_data: dict) -> bytes:
    """
    cs_data: 客訴清單欄位 dict（包含 mo_number / 批量 / 出貨日期 等擴充欄位）
    d8_data: 8D記錄欄位 dict
    回傳 PDF bytes
    """
    merged = {**cs_data, **d8_data}
    pdf = D8PDF(merged)
    pdf.add_page()

    # ── ① 抬頭（Logo + 資訊表）─────────────────────
    _draw_letterhead(pdf, cs_data)

    pdf.set_margins(14, 0, 14)
    pdf.divider()

    # ── ② D1–D8 步驟內容 ────────────────────────────
    for code, zh, en, col_name, rgb in D8_STEPS:
        content = d8_data.get(col_name, "") or merged.get(col_name, "")
        pdf.section_band(code, zh, en, rgb)
        pdf.content_block(content)

    # ── ③ 簽核欄 ────────────────────────────────────
    pdf.divider()
    pdf.ln(1)
    pdf.set_font("B", size=9)
    pdf.set_text_color(*NAVY)
    pdf.set_x(14)
    pdf.cell(0, 6, "核准 / 簽核", ln=1)

    y_sign = pdf.get_y()
    pdf.set_fill_color(*LIGHT)
    pdf.set_draw_color(*GREY)
    pdf.rect(14, y_sign, 182, 14, "FD")

    sign_roles = [
        ("核准", cs_data.get("核准", "蔡承叡")),
        ("審核", cs_data.get("審核", "尤俊河")),
        ("經辦", cs_data.get("經辦", "尤俊河")),
        ("客戶確認", ""),
    ]
    for i, (role, name) in enumerate(sign_roles):
        x = 14 + i * 45.5
        pdf.set_xy(x + 3, y_sign + 2)
        pdf.set_font("B", size=8); pdf.set_text_color(*DIM)
        pdf.cell(42, 5, role)
        pdf.set_xy(x + 3, y_sign + 7)
        pdf.set_font("R", size=9); pdf.set_text_color(*TEXT)
        pdf.cell(42, 5, name)

    pdf.ln(16)

    # SOP / 文件編號
    sop = cs_data.get("SOP參考", "") or d8_data.get("SOP參考", "")
    if sop:
        pdf.set_font("R", size=8); pdf.set_text_color(*DIM)
        pdf.set_x(14)
        pdf.cell(0, 5, f"參考文件：{sop}", ln=1)

    pdf.ln(1)
    pdf.set_font("R", size=7.5); pdf.set_text_color(*DIM)
    pdf.set_x(14)
    d8_id = d8_data.get("8D編號", "")
    pdf.cell(0, 5, f"本報告由 REXONTEC 力科品質指揮平台自動產生　Document No. {d8_id}")

    return bytes(pdf.output())
