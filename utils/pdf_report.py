"""
REXONTEC OQC — PDF 報告生成
依賴：reportlab >= 4.1  (pip install reportlab)
中文字型：Windows 微軟正黑體 (msjh.ttc)，自動回退至標楷體
"""
import io, os, glob
from datetime import datetime

# ── reportlab 匯入 ─────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _RL_OK = True
except ImportError:
    _RL_OK = False

# ── 顏色常數 ───────────────────────────────────────────
C_NAVY   = colors.HexColor("#0d1b2a")
C_BLUE   = colors.HexColor("#1a5276")
C_ACCENT = colors.HexColor("#1e88e5")
C_ORANGE = colors.HexColor("#f0a500")
C_PASS   = colors.HexColor("#27ae60")
C_FAIL   = colors.HexColor("#e74c3c")
C_GRAY   = colors.HexColor("#ecf0f1")
C_LGRAY  = colors.HexColor("#f7f9fc")
C_CR     = colors.HexColor("#c0392b")
C_MA     = colors.HexColor("#d68910")
C_MI     = colors.HexColor("#1e8449")
C_WHITE  = colors.white

GRADE_COLORS = {"CR": C_CR, "MA": C_MA, "MI": C_MI}

# ── 字型管理 ───────────────────────────────────────────
# 字型名稱常數（固定，不隨備援切換；確保 iqc_pdf / pdf_report 一致）
_F  = "NotoSansTC"        # Regular
_FB = "NotoSansTC-Bold"   # Bold（以同字型模擬，reportlab 自動加粗）
_fonts_registered = False

# ── 字型搜尋優先順序 ─────────────────────────────────────────────────────
# 第 1 優先：專案內隨附字型（fonts/ 目錄，跨平台保證可用）
_HERE = os.path.dirname(os.path.abspath(__file__))          # utils/
_PROJ = os.path.dirname(_HERE)                               # 專案根目錄
_BUNDLED_FONT = os.path.join(_PROJ, "fonts", "NotoSansTC-Regular.ttf")

# 第 2 優先：各平台系統字型（(path, ttc_subfont_index_or_None)）
_SYS_CANDIDATES = [
    # Windows — NotoSansTC 變體
    ("C:/Windows/Fonts/NotoSansTC-VF.ttf",      None),
    ("C:/Windows/Fonts/NotoSansTC-Regular.ttf", None),
    # Windows — 傳統備援
    ("C:/Windows/Fonts/msjh.ttc",               0),
    ("C:/Windows/Fonts/kaiu.ttf",               None),
    ("C:/Windows/Fonts/mingliu.ttc",            0),
    # Linux / Streamlit Cloud（fonts-noto-cjk 安裝後）
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",   0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf", None),
    ("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",        0),
    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",   0),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttf",             None),
    ("/usr/share/fonts/truetype/arphic/uming.ttc",               0),
    # macOS
    ("/System/Library/Fonts/PingFang.ttc",       0),
    ("/Library/Fonts/Arial Unicode MS.ttf",      None),
]


def _try_register(path: str, idx):
    """嘗試以 TTFont 登錄字型（Regular & Bold 同檔），成功回傳 True。"""
    try:
        if idx is not None:
            reg = TTFont(_F, path, subfontIndex=idx)
            bol = TTFont(_FB, path, subfontIndex=idx)
        else:
            reg = TTFont(_F, path)
            bol = TTFont(_FB, path)
        pdfmetrics.registerFont(reg)
        pdfmetrics.registerFont(bol)
        return True
    except Exception:
        return False


def _reg_fonts():
    """
    登錄中文 TTFont。優先使用專案內隨附的 NotoSansTC-Regular.ttf，
    其次嘗試各平台系統字型路徑，動態 glob 掃描，
    最後以 glob 掃描 Linux /usr/share/fonts 尋找任何可用的 CJK 字型。
    若完全找不到字型，僅印出警告並使用 Helvetica 替代（不崩潰）。
    """
    global _fonts_registered
    if _fonts_registered or not _RL_OK:
        return

    # ── 第 1 優先：專案隨附字型 ──────────────────────────────────────────
    if os.path.exists(_BUNDLED_FONT) and _try_register(_BUNDLED_FONT, None):
        _fonts_registered = True
        return

    # ── 第 2 優先：系統固定路徑 ──────────────────────────────────────────
    for path, idx in _SYS_CANDIDATES:
        if os.path.exists(path) and _try_register(path, idx):
            _fonts_registered = True
            return

    # ── 第 3 優先：Linux glob 動態掃描 ───────────────────────────────────
    for pattern in [
        "/usr/share/fonts/**/*NotoSans*TC*.ttf",
        "/usr/share/fonts/**/*NotoSans*CJK*Regular*.ttc",
        "/usr/share/fonts/**/*NotoSans*CJK*Regular*.otf",
        "/usr/share/fonts/**/*NotoSans*CJK*.ttc",
        "/usr/share/fonts/**/*wqy*.ttf",
        "/usr/share/fonts/**/*arphic*.ttc",
    ]:
        for found in glob.glob(pattern, recursive=True):
            if _try_register(found, 0):
                _fonts_registered = True
                return
            if _try_register(found, None):
                _fonts_registered = True
                return

    # ── 找不到字型：顯示警告，以 Helvetica 替代（避免崩潰）───────────────
    import warnings
    warnings.warn(
        "[PDF] 中文字型缺失：找不到 NotoSansTC-Regular.ttf 或任何 CJK 字型。\n"
        "      PDF 中文將顯示為方塊或亂碼。\n"
        "      解決方式：\n"
        "      1. 確認 fonts/NotoSansTC-Regular.ttf 存在於專案根目錄\n"
        "      2. Streamlit Cloud：確認 packages.txt 含 fonts-noto-cjk\n"
        "      3. 本機 Windows：確認 C:/Windows/Fonts/ 有 NotoSansTC-VF.ttf",
        stacklevel=3,
    )
    # 以 Helvetica 填充，確保 PDF 仍可生成（ASCII 部分正常）
    try:
        pdfmetrics.registerFont(TTFont(_F,  "C:/Windows/Fonts/arial.ttf"))
        pdfmetrics.registerFont(TTFont(_FB, "C:/Windows/Fonts/arialbd.ttf"))
    except Exception:
        pass   # 完全放棄，reportlab 預設字型處理剩餘問題
    _fonts_registered = True  # 標記完成，避免重複嘗試


# ══════════════════════════════════════════════════════
# 公開 API
# ══════════════════════════════════════════════════════
def generate_pdf(
    product_type: str,
    header: dict,
    sections: list,
    results: dict,
    units: list,
    ng_summary: str = "",
    note: str = "",
) -> bytes:
    """
    生成 OQC 出廠檢驗報告 PDF，回傳 bytes。
    若 reportlab 未安裝或字型缺失，拋出例外。
    """
    if not _RL_OK:
        raise ImportError("請先安裝 reportlab：pip install reportlab")

    _reg_fonts()

    # ── 決定頁面方向 ─────────────────────────────────
    n_units = len(units)
    pagesize = landscape(A4) if n_units > 5 else A4
    W, H = pagesize
    LM = RM = 14 * mm
    TM = BM = 14 * mm
    avail_w = W - LM - RM

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=pagesize,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM, bottomMargin=BM,
    )

    # ── Style helpers ─────────────────────────────────
    def S(name, **kw):
        return ParagraphStyle(name, fontName=_F, **kw)

    def SB(name, **kw):
        return ParagraphStyle(name, fontName=_FB, **kw)

    s_title  = SB("title",  fontSize=16, textColor=C_WHITE,  leading=20)
    s_sub    = S("sub",    fontSize=9,  textColor=colors.HexColor("#b0bec5"), leading=13)
    s_body   = S("body",   fontSize=8.5, textColor=C_NAVY,  leading=12)
    s_bold   = SB("bold",  fontSize=8.5, textColor=C_NAVY,  leading=12)
    s_small  = S("small",  fontSize=7.5, textColor=colors.HexColor("#6b7c93"), leading=10)
    s_center = SB("center",fontSize=8.5, textColor=C_NAVY,  leading=12, alignment=1)
    s_wcenter= SB("wcenter",fontSize=8,  textColor=C_WHITE,  leading=11, alignment=1)

    def P(text, style=None):
        return Paragraph(str(text) if text is not None else "─", style or s_body)

    def PB(text):
        return Paragraph(str(text) if text is not None else "─", s_bold)

    def PC(text, style=None):
        return Paragraph(str(text) if text is not None else "─", style or s_center)

    story = []

    # ══════════════════════════════════════════════════
    # 1. 封面標題帶（仿維修報告格式：左橙色條 + 公司名/副標 | 右對齊報告類型）
    # ══════════════════════════════════════════════════
    pt_label    = "電調 ESC"   if product_type == "esc" else "馬達 Motor"
    pt_label_cn = "電調"       if product_type == "esc" else "馬達"
    rec_id = header.get("rec_id") or (
        f"OQC-{'ESC' if product_type=='esc' else 'MTR'}-"
        f"{datetime.now().strftime('%Y%m%d-%H%M')}"
    )
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 標題帶樣式
    s_co_name  = SB("coname",  fontSize=16, textColor=C_ORANGE, leading=20)
    s_co_sub   = S ("cosub",   fontSize=8.5, textColor=colors.HexColor("#b0bec5"), leading=12)
    s_rpt_type = SB("rpttype", fontSize=15, textColor=C_WHITE,  leading=19, alignment=2)
    s_rpt_id   = S ("rptid",   fontSize=8,  textColor=colors.HexColor("#9aafc4"), leading=11, alignment=2)

    ACCENT_W = 5 * mm
    LEFT_W   = (avail_w - ACCENT_W) * 0.62
    RIGHT_W  = (avail_w - ACCENT_W) * 0.38

    # 公司別（力科 REXONTEC / 力山 REXON）
    _company     = header.get("company", "rexontec")
    _co_name_txt = "REXON 力山" if _company == "rexon" else "REXONTEC 力科"

    # 若勾選送樣，在報告類型前加橙色 [送樣]
    _is_sample   = header.get("is_sample", False)
    _rpt_title   = (
        f'<font color="#f0a500"><b>[送樣]</b></font>  {pt_label_cn}  檢驗報告'
        if _is_sample else
        f"{pt_label_cn}  檢驗報告"
    )

    header_tbl = Table(
        [
            # Row 1: company name (large) | report type (large, right-aligned)
            ["", P(_co_name_txt, s_co_name),
                 P(_rpt_title, s_rpt_type)],
            # Row 2: subtitle | report number
            ["", P("OQC 出廠品質管制系統  Outgoing Quality Control", s_co_sub),
                 P(f"{rec_id}", s_rpt_id)],
        ],
        colWidths=[ACCENT_W, LEFT_W, RIGHT_W],
    )
    header_tbl.setStyle(TableStyle([
        # 整體底色
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
        # 左側橙色裝飾條（第 0 欄，兩行）
        ("BACKGROUND",    (0, 0), (0, -1),  C_ORANGE),
        ("LEFTPADDING",   (0, 0), (0, -1),  0),
        ("RIGHTPADDING",  (0, 0), (0, -1),  0),
        ("TOPPADDING",    (0, 0), (0, -1),  0),
        ("BOTTOMPADDING", (0, 0), (0, -1),  0),
        # 文字欄 padding
        ("LEFTPADDING",   (1, 0), (1, -1),  12),
        ("RIGHTPADDING",  (1, 0), (1, -1),  6),
        ("LEFTPADDING",   (2, 0), (2, -1),  6),
        ("RIGHTPADDING",  (2, 0), (2, -1),  12),
        # Row 1 padding（上方多留空間）
        ("TOPPADDING",    (1, 0), (2, 0),   10),
        ("BOTTOMPADDING", (1, 0), (2, 0),   3),
        # Row 2 padding（下方多留空間）
        ("TOPPADDING",    (1, 1), (2, 1),   3),
        ("BOTTOMPADDING", (1, 1), (2, 1),   10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════
    # 2. 表頭資訊（雙欄 key-value）
    # ══════════════════════════════════════════════════
    def hrow(label1, val1, label2="", val2=""):
        return [PB(label1), P(val1), PB(label2), P(val2)]

    is_esc = product_type == "esc"
    info_rows = [
        hrow("機種", header.get("model", "─"),
             "料號", header.get("part_no", "─")),
        hrow("批號", header.get("batch_no", "─"),
             "客戶", header.get("customer", "─")),
        hrow("本批數量", str(header.get("qty", "─")),
             "抽驗數量", str(header.get("sample_qty", "─"))),
        hrow("檢驗日期", header.get("date", "─"),
             "檢驗員", header.get("inspector", "─")),
        hrow("品保主管", header.get("supervisor", "─"),
             "製造組別", header.get("mfg_group", "─") if is_esc else "─"),
    ]
    if is_esc and header.get("mfg_order_no"):
        info_rows.append(hrow("製造編號/櫃號", header.get("mfg_order_no", "─"), "", ""))
    if not is_esc and header.get("insp_method"):
        info_rows.append(hrow("檢驗方法", header.get("insp_method", "─"),
                              "判定結果", header.get("verdict", "─")))

    cw = avail_w / 4
    info_tbl = Table(info_rows, colWidths=[cw * 0.55, cw * 0.95, cw * 0.55, cw * 0.95])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), C_LGRAY),
        ("BACKGROUND",  (2, 0), (2, -1), C_LGRAY),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#dce3ec")),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0,0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════
    # 3. 檢驗結果表格（依 section）
    # ══════════════════════════════════════════════════
    # 欄寬計算
    #  固定欄：No(12) Grade(12) 項目名稱(50) 規格標準(55) 工具(25) = 154mm + units
    fixed_w = [12*mm, 12*mm, 50*mm, 55*mm, 20*mm]
    fixed_total = sum(fixed_w)
    unit_w_each = max(12*mm, (avail_w - fixed_total) / max(n_units, 1))
    # 若 unit 欄太窄就縮短固定欄
    if unit_w_each < 10*mm:
        # 縮小規格欄
        fixed_w[3] = max(35*mm, avail_w - fixed_total + fixed_w[3] - n_units * 10*mm)
        unit_w_each = max(10*mm, (avail_w - sum(fixed_w)) / n_units)

    col_widths = fixed_w + [unit_w_each] * n_units

    # 表格 header 列
    unit_headers = [PC(u[:10], s_wcenter) for u in units]
    tbl_header = [
        PC("No.", s_wcenter),
        PC("等級", s_wcenter),
        PC("檢驗項目", s_wcenter),
        PC("規格標準", s_wcenter),
        PC("設備", s_wcenter),
    ] + unit_headers

    seq_no = 0   # global item counter across all sections → NO1, NO2 …

    for sec in sections:
        sec_id    = sec["id"]
        sec_label = sec["label"]
        sec_sub   = sec.get("subtitle", "")
        items     = sec.get("items", [])
        if not items:
            continue

        # Section 標題列
        sec_title_row = [
            Table([[
                Paragraph(
                    f'<b>{sec_id}｜{sec_label}</b>'
                    f'{"  (" + sec_sub + ")" if sec_sub else ""}',
                    SB("sh", fontSize=8.5, textColor=C_WHITE, leading=12)
                )
            ]], colWidths=[avail_w])
        ]
        # Span across all columns
        sec_span = Table(
            [[Paragraph(
                f'<b>{sec_id} | {sec_label}</b>'
                f'{" - " + sec_sub if sec_sub else ""}',
                SB("sh2", fontSize=8.5, textColor=C_WHITE, leading=12)
            )]],
            colWidths=[avail_w],
        )
        sec_span.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), C_NAVY),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        story.append(sec_span)

        # 表格
        tbl_rows = [tbl_header]
        style_cmds = [
            # Header row style
            ("BACKGROUND",   (0, 0), (-1, 0), C_BLUE),
            ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), _FB),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#c5cfe0")),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN",        (0, 0), (1, -1), "CENTER"),
        ]

        for row_i, item in enumerate(items, start=1):
            seq_no += 1          # running number across all sections
            iid   = item["id"]
            grade = item["grade"]
            itype = item["type"]
            gcol  = GRADE_COLORS.get(grade, C_ACCENT)

            row_bg = C_WHITE if row_i % 2 == 0 else C_LGRAY

            unit_cells = []
            any_fail   = False
            for u in units:
                r_data = results.get(iid, {}).get(u, {})
                res    = r_data.get("result", "─")
                val    = r_data.get("value")
                if res == "PASS":
                    # pf → "OK"; numeric → just the measured value (no OK prefix)
                    cell_txt = "OK" if itype == "pf" else (f"{val:.2f}" if val is not None else "OK")
                elif res == "FAIL":
                    any_fail = True
                    # pf → "NG"; numeric → just the measured value
                    cell_txt = "NG" if itype == "pf" else (f"{val:.2f}" if val is not None else "NG")
                else:
                    cell_txt = "" if itype == "pf" else (f"{val:.2f}" if val is not None else "")
                unit_cells.append(PC(cell_txt))

            tbl_rows.append([
                PC(f"{seq_no}"),      # plain number: 1, 2 … 15
                PC(grade),
                P(item["name"]),
                P(item["spec"]),
                P(item.get("tool", "")),
            ] + unit_cells)

            # 行樣式
            r = row_i  # actual row index in tbl_rows
            if any_fail:
                style_cmds.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#fff8f7")))
                style_cmds.append(("LINEABOVE",  (0, r), (-1, r), 0.5, C_FAIL))
            else:
                style_cmds.append(("BACKGROUND", (0, r), (-1, r), row_bg))

            # 等級欄顏色
            style_cmds.append(("TEXTCOLOR",  (1, r), (1, r), gcol))
            style_cmds.append(("FONTNAME",   (1, r), (1, r), _FB))

            # Unit 欄顏色
            for u_i, u in enumerate(units):
                col_idx = 5 + u_i
                res = results.get(iid, {}).get(u, {}).get("result", "─")
                if res == "PASS":
                    style_cmds += [
                        ("BACKGROUND", (col_idx, r), (col_idx, r), colors.HexColor("#eafaf1")),
                        ("TEXTCOLOR",  (col_idx, r), (col_idx, r), C_PASS),
                        ("FONTNAME",   (col_idx, r), (col_idx, r), _FB),
                    ]
                elif res == "FAIL":
                    style_cmds += [
                        ("BACKGROUND", (col_idx, r), (col_idx, r), colors.HexColor("#fdedec")),
                        ("TEXTCOLOR",  (col_idx, r), (col_idx, r), C_FAIL),
                        ("FONTNAME",   (col_idx, r), (col_idx, r), _FB),
                    ]

        tbl = Table(tbl_rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle(style_cmds))
        story.append(tbl)
        story.append(Spacer(1, 3 * mm))

    # ══════════════════════════════════════════════════
    # 4. NG 警示摘要
    # ══════════════════════════════════════════════════
    ng_items = []
    for sec in sections:
        for item in sec.get("items", []):
            fail_units = [
                u for u in units
                if results.get(item["id"], {}).get(u, {}).get("result") == "FAIL"
            ]
            if fail_units:
                ng_items.append((item, fail_units))

    if ng_items:
        story.append(Spacer(1, 2 * mm))
        ng_rows = [[
            PC("等級", s_wcenter),
            PC("項目 ID", s_wcenter),
            PC("檢驗項目名稱", s_wcenter),
            PC("NG 機台", s_wcenter),
        ]]
        for item, fail_units in ng_items:
            ng_rows.append([
                PC(item["grade"]),
                PC(item["id"]),
                P(item["name"]),
                P(", ".join(fail_units)),
            ])
        ng_tbl = Table(ng_rows,
                       colWidths=[18*mm, 18*mm, 70*mm, avail_w-106*mm],
                       repeatRows=1)
        ng_style = TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), C_CR),
            ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), _FB),
            ("BACKGROUND",   (0, 1), (-1, -1), colors.HexColor("#fff8f7")),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#f5b7b1")),
            ("TEXTCOLOR",    (0, 1), (1, -1), C_CR),
            ("FONTNAME",     (0, 1), (1, -1), _FB),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 5),
            ("ALIGN",        (0, 0), (1, -1), "CENTER"),
        ])
        ng_tbl.setStyle(ng_style)

        ng_hdr = Table([[P("NG 項目警示摘要",
                           SB("nh", fontSize=9, textColor=C_WHITE, leading=13))]],
                       colWidths=[avail_w])
        ng_hdr.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), C_CR),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        story.append(ng_hdr)
        story.append(ng_tbl)
        story.append(Spacer(1, 3 * mm))

    # ══════════════════════════════════════════════════
    # 5. 備註
    # ══════════════════════════════════════════════════
    if note and note.strip():
        note_tbl = Table(
            [[PB("備 註"), P(note)]],
            colWidths=[20*mm, avail_w-20*mm],
        )
        note_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (0, -1), C_LGRAY),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#dce3ec")),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
        ]))
        story.append(note_tbl)
        story.append(Spacer(1, 3 * mm))

    # ══════════════════════════════════════════════════
    # 6. 總判定
    # ══════════════════════════════════════════════════
    all_items_flat = [item for sec in sections for item in sec.get("items", [])]
    cr_ng = sum(1 for it in all_items_flat if it["grade"] == "CR" and
                any(results.get(it["id"], {}).get(u, {}).get("result") == "FAIL" for u in units))
    ma_ng = sum(1 for it in all_items_flat if it["grade"] == "MA" and
                any(results.get(it["id"], {}).get(u, {}).get("result") == "FAIL" for u in units))
    mi_ng = sum(1 for it in all_items_flat if it["grade"] == "MI" and
                any(results.get(it["id"], {}).get(u, {}).get("result") == "FAIL" for u in units))

    is_pass  = (cr_ng == 0 and ma_ng == 0)
    vrd_text = "合格  PASS" if is_pass else "不合格  FAIL"
    vrd_col  = C_PASS if is_pass else C_FAIL
    vrd_bg   = colors.HexColor("#eafaf1") if is_pass else colors.HexColor("#fdedec")

    verdict_data = [
        [
            Paragraph(vrd_text,
                      SB("vrd", fontSize=14, textColor=vrd_col, leading=18, alignment=1)),
            P(f"CR：{cr_ng} 項  MA：{ma_ng} 項  MI：{mi_ng} 項",
              S("vs", fontSize=8, textColor=colors.HexColor("#6b7c93"), leading=12,
                alignment=1)),
        ]
    ]
    vrd_tbl = Table(verdict_data, colWidths=[avail_w * 0.5, avail_w * 0.5])
    vrd_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), vrd_bg),
        ("BOX",          (0, 0), (-1, -1), 1.2, vrd_col),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [5, 5, 5, 5]),
    ]))
    story.append(vrd_tbl)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════
    # 7. 簽核確認 Approval — 3 等寬方框格式
    # ══════════════════════════════════════════════════

    # Section title bar
    story.append(Spacer(1, 2 * mm))
    approval_hdr = Table(
        [[Paragraph("簽核確認  Approval",
                    SB("ah", fontSize=9, textColor=C_WHITE, leading=13))]],
        colWidths=[avail_w],
    )
    approval_hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    story.append(approval_hdr)

    # 3 boxes: role title | spacer (signature area) | date
    box_w   = avail_w / 3
    s_role  = SB("role",  fontSize=9,   textColor=C_NAVY,  leading=14, alignment=1)
    s_date  = S("sdate",  fontSize=7.5, textColor=colors.HexColor("#6b7c93"),
                leading=11, alignment=1)

    sig_roles = ["檢驗員", "品保主管", "核准"]
    # Row 1: role titles
    row_titles = [Paragraph(r, s_role) for r in sig_roles]
    # Row 2: empty — becomes the signature writing area
    row_space  = [Spacer(1, 1)] * 3
    # Row 3: date prompt
    row_date   = [Paragraph("日期：___/___/___", s_date)] * 3

    sig_tbl = Table(
        [row_titles, row_space, row_date],
        colWidths=[box_w] * 3,
        rowHeights=[None, 18 * mm, None],
    )
    sig_tbl.setStyle(TableStyle([
        # Outer border + inner vertical dividers
        ("BOX",          (0, 0), (-1, -1), 0.6, colors.HexColor("#c5cfe0")),
        ("LINEAFTER",    (0, 0), (1, -1),  0.6, colors.HexColor("#c5cfe0")),
        # Signature line: bottom border of the spacer row
        ("LINEBELOW",    (0, 1), (-1, 1),  0.8, C_NAVY),
        # Padding
        ("TOPPADDING",   (0, 0), (-1, 0),  10),
        ("BOTTOMPADDING",(0, 0), (-1, 0),  6),
        ("TOPPADDING",   (0, 1), (-1, 1),  4),
        ("BOTTOMPADDING",(0, 1), (-1, 1),  4),
        ("TOPPADDING",   (0, 2), (-1, 2),  6),
        ("BOTTOMPADDING",(0, 2), (-1, 2),  10),
        # Alignment
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_tbl)

    # Footer
    story.append(Spacer(1, 3 * mm))
    story.append(Table(
        [[P(f"REXONTEC 力科  OQC 出廠品質管制系統  ·  {gen_time}  ·  CONFIDENTIAL",
            S("ft", fontSize=7, textColor=colors.HexColor("#9aafc4"), alignment=1))]],
        colWidths=[avail_w],
    ))

    doc.build(story)
    return buf.getvalue()
