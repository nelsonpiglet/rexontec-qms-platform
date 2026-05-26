"""
REXONTEC 力科 IQC — PDF 進料品質管制檢驗報告生成
依賴：reportlab >= 4.1  (pip install reportlab)
中文字型：共用 pdf_report.py 的字型與顏色常數
"""
import io
from datetime import datetime

# ── 共用顏色 / 字型（reuse pdf_report 已登錄的字型，避免重複 register） ─────
_IMPORT_OK = False
_reg_fonts = None
_F = _FB = "Helvetica"   # placeholder until real import

try:
    from utils.pdf_report import (
        _reg_fonts, _F, _FB,
        C_NAVY, C_BLUE, C_ORANGE, C_PASS, C_FAIL,
        C_GRAY, C_LGRAY, C_CR, C_MA, C_MI, C_WHITE,
        GRADE_COLORS,
    )
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer,
    )
    _IMPORT_OK = True
except ImportError:
    pass   # _IMPORT_OK stays False; generate_iqc_pdf will raise ImportError


# ══════════════════════════════════════════════════════
# 公開 API
# ══════════════════════════════════════════════════════
def generate_iqc_pdf(part: dict, header: dict, results: dict) -> bytes:
    """
    生成 IQC 進料品質管制檢驗報告 PDF，回傳 bytes。

    part    : utils/iqc_data.py 的零件字典
    header  : {
        "part", "vendor", "lot", "po",
        "qty", "sample", "date", "inspector",
        "is_sample", "docNo", "samplingStd", "aql"
      }
    results : {
        item_id: {
          "result":  "pass" | "fail" | None,
          "inputs":  {key: str_val},
          "remark":  str
        }
      }
    """
    if not _IMPORT_OK:
        raise ImportError("請先安裝 reportlab：pip install reportlab")

    _reg_fonts()

    # _reg_fonts() 可能已將 pdf_report._F/_FB 更新為 CID 字型名稱（備援路徑）
    # 必須重新讀取，確保 closure S()/SB() 使用正確的字型名
    import utils.pdf_report as _pr
    _F  = _pr._F
    _FB = _pr._FB

    # ── 頁面尺寸（A4 縱向）────────────────────────────
    W, H = A4
    LM = RM = 14 * mm
    TM = BM = 14 * mm
    avail_w = W - LM - RM

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM, bottomMargin=BM,
    )

    # ── Style helpers ────────────────────────────────
    def S(name, **kw):
        return ParagraphStyle(name, fontName=_F, **kw)

    def SB(name, **kw):
        return ParagraphStyle(name, fontName=_FB, **kw)

    def P(text, style=None):
        return Paragraph(
            str(text) if text is not None else "─",
            style or s_body,
        )

    def PB(text, style=None):
        return Paragraph(
            str(text) if text is not None else "─",
            style or s_bold,
        )

    def PC(text, style=None):
        return Paragraph(
            str(text) if text is not None else "─",
            style or s_center,
        )

    s_body    = S("iq_body",   fontSize=8.5, textColor=C_NAVY,  leading=12)
    s_bold    = SB("iq_bold",  fontSize=8.5, textColor=C_NAVY,  leading=12)
    s_center  = SB("iq_ctr",   fontSize=8.5, textColor=C_NAVY,  leading=12, alignment=1)
    s_wcenter = SB("iq_wctr",  fontSize=8,   textColor=C_WHITE, leading=11, alignment=1)

    story    = []
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ══════════════════════════════════════════════════
    # 1. 標題帶（左橙色條 + 公司名 | 右對齊報告類型）
    # ══════════════════════════════════════════════════
    is_sample = header.get("is_sample", False)
    rec_id    = (
        f"IQC-{part.get('id','PART')}-"
        f"{datetime.now().strftime('%Y%m%d-%H%M')}"
    )

    s_co_name  = SB("iq_coname",  fontSize=16, textColor=C_ORANGE, leading=20)
    s_co_sub   = S ("iq_cosub",   fontSize=8.5, textColor=colors.HexColor("#b0bec5"), leading=12)
    s_rpt_type = SB("iq_rpttype", fontSize=14, textColor=C_WHITE,  leading=18, alignment=2)
    s_rpt_id   = S ("iq_rptid",   fontSize=8,  textColor=colors.HexColor("#9aafc4"),
                    leading=11, alignment=2)

    ACCENT_W = 5 * mm
    LEFT_W   = (avail_w - ACCENT_W) * 0.62
    RIGHT_W  = (avail_w - ACCENT_W) * 0.38

    # 公司別（力科 REXONTEC / 力山 REXON）
    _company     = header.get("company", "rexontec")
    _co_name_txt = "REXON 力山" if _company == "rexon" else "REXONTEC 力科"

    # 若送樣勾選，在報告類型前加 [送樣] 字樣（橙色高亮）
    if is_sample:
        title_txt = (
            '<font color="#f0a500"><b>[送樣]</b></font>  '
            'IQC 進料品質管制檢驗表'
        )
    else:
        title_txt = "IQC 進料品質管制檢驗表"

    header_tbl = Table(
        [
            [
                "",
                P(_co_name_txt, s_co_name),
                P(title_txt, s_rpt_type),
            ],
            [
                "",
                P("IQC 進料品質管制系統  Incoming Quality Control", s_co_sub),
                P(rec_id, s_rpt_id),
            ],
        ],
        colWidths=[ACCENT_W, LEFT_W, RIGHT_W],
    )
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
        ("BACKGROUND",    (0, 0), (0, -1),  C_ORANGE),
        ("LEFTPADDING",   (0, 0), (0, -1),  0),
        ("RIGHTPADDING",  (0, 0), (0, -1),  0),
        ("TOPPADDING",    (0, 0), (0, -1),  0),
        ("BOTTOMPADDING", (0, 0), (0, -1),  0),
        ("LEFTPADDING",   (1, 0), (1, -1),  12),
        ("RIGHTPADDING",  (1, 0), (1, -1),  6),
        ("LEFTPADDING",   (2, 0), (2, -1),  6),
        ("RIGHTPADDING",  (2, 0), (2, -1),  12),
        ("TOPPADDING",    (1, 0), (2, 0),   10),
        ("BOTTOMPADDING", (1, 0), (2, 0),   3),
        ("TOPPADDING",    (1, 1), (2, 1),   3),
        ("BOTTOMPADDING", (1, 1), (2, 1),   10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════
    # 2. 表頭資訊（雙欄 key-value）
    # ══════════════════════════════════════════════════
    aql     = header.get("aql", {})
    aql_str = (
        f"CR:{aql.get('cr', 0)}  "
        f"MA:{aql.get('ma', 0.65)}  "
        f"MI:{aql.get('mi', 1.5)}"
    )

    def hrow(l1, v1, l2="", v2=""):
        return [PB(l1), P(v1), PB(l2), P(v2)]

    info_rows = [
        hrow("零件名稱",
             header.get("part") or part.get("name", "─"),
             "供應商",
             header.get("vendor") or part.get("vendor", "─")),
        hrow("批號 / 料號",
             header.get("lot", "─"),
             "採購單號",
             header.get("po", "─")),
        hrow("進料數量",
             f"{header.get('qty', 0)} PCS",
             "抽樣數量",
             f"{header.get('sample', 0)} PCS"),
        hrow("檢驗日期",
             str(header.get("date", "─")),
             "IQC 檢驗員",
             header.get("inspector", "─")),
        hrow("文件編號",
             header.get("docNo") or part.get("docNo", "─"),
             "抽樣標準",
             header.get("samplingStd") or part.get("samplingStd", "─")),
        hrow("AQL 標準",
             aql_str,
             "機種 / 機型",
             part.get("machine", "─")),
    ]

    cw      = avail_w / 4
    info_tbl = Table(
        info_rows,
        colWidths=[cw * 0.55, cw * 0.95, cw * 0.55, cw * 0.95],
    )
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), C_LGRAY),
        ("BACKGROUND",    (2, 0), (2, -1), C_LGRAY),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#dce3ec")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════
    # 3. 檢驗結果表格（依 section）
    # ══════════════════════════════════════════════════
    # 欄寬：No. | 等級 | 檢驗項目 | 規格標準 | 設備 | 量測記錄 | 判定
    W_NO     = 9  * mm
    W_GRADE  = 11 * mm
    W_TOOL   = 22 * mm
    W_RESULT = 16 * mm
    _remain  = avail_w - W_NO - W_GRADE - W_TOOL - W_RESULT
    W_NAME   = _remain * 0.42
    W_SPEC   = _remain * 0.35
    W_MEAS   = _remain - W_NAME - W_SPEC

    col_w = [W_NO, W_GRADE, W_NAME, W_SPEC, W_TOOL, W_MEAS, W_RESULT]

    tbl_header_row = [
        PC("No.",     s_wcenter),
        PC("等級",    s_wcenter),
        PC("檢驗項目", s_wcenter),
        PC("規格標準", s_wcenter),
        PC("設備",    s_wcenter),
        PC("量測記錄", s_wcenter),
        PC("判定",    s_wcenter),
    ]

    seq_no         = 0
    ng_items_flat  = []   # for NG summary section

    for sec in part.get("sections", []):
        sec_label = sec.get("label", "")
        sec_sub   = sec.get("sublabel", "")
        items     = sec.get("items", [])
        if not items:
            continue

        # Section 標題列（全寬，深藍底）
        sec_span = Table(
            [[Paragraph(
                f'<b>{sec_label}</b>'
                f'{" - " + sec_sub if sec_sub else ""}',
                SB("iq_sh", fontSize=8.5, textColor=C_WHITE, leading=12),
            )]],
            colWidths=[avail_w],
        )
        sec_span.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story.append(sec_span)

        tbl_rows   = [tbl_header_row]
        style_cmds = [
            ("BACKGROUND",    (0, 0), (-1, 0), C_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), _FB),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#c5cfe0")),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
            ("ALIGN",         (0, 0), (1, -1),  "CENTER"),
            ("ALIGN",         (6, 0), (6, -1),  "CENTER"),
        ]

        for row_i, item in enumerate(items, start=1):
            seq_no += 1
            iid    = item["id"]
            grade  = item["grade"]
            gcol   = GRADE_COLORS.get(grade, C_BLUE)

            state  = results.get(iid, {})
            res    = state.get("result")      # "pass" / "fail" / None (lowercase)
            inputs = state.get("inputs", {})
            remark = state.get("remark", "")

            row_bg = C_WHITE if row_i % 2 == 0 else C_LGRAY

            # ── 量測記錄欄位 ────────────────────────
            inp_defs = item.get("inputs", [])
            if inp_defs:
                lines = []
                for inp in inp_defs:
                    val = inputs.get(inp["key"], "")
                    label_txt = inp["label"]
                    unit_txt  = inp["unit"]
                    disp_val  = str(val) if (val != "" and val is not None) else "─"
                    # Out-of-range highlight
                    mn = inp.get("min")
                    mx = inp.get("max")
                    oor = False
                    try:
                        n = float(disp_val)
                        if mn is not None and n < mn: oor = True
                        if mx is not None and n > mx: oor = True
                    except (ValueError, TypeError):
                        pass
                    val_fmt = (
                        f'<font color="#e74c3c"><b>{disp_val}</b></font>'
                        if oor else disp_val
                    )
                    lines.append(
                        f'{label_txt}: {val_fmt} {unit_txt}'
                    )
                meas_cell = Paragraph(
                    "<br/>".join(lines),
                    S("iq_meas", fontSize=7.5, textColor=C_NAVY, leading=10),
                )
            else:
                meas_cell = PC("─")

            # ── 判定欄位 ────────────────────────────
            if res == "pass":
                res_txt = "OK"
                res_col = C_PASS
                res_bg  = colors.HexColor("#eafaf1")
            elif res == "fail":
                res_txt = "NG"
                res_col = C_FAIL
                res_bg  = colors.HexColor("#fdedec")
                ng_items_flat.append(item)
            else:
                res_txt = "─"
                res_col = colors.HexColor("#9aafc4")
                res_bg  = row_bg

            # ── 項目名稱欄位（含 alert + remark sub-line） ──
            name_lines = [f'<b>{item["name"]}</b>']
            if item.get("alert"):
                name_lines.append(
                    f'<font color="#e74c3c" size="7">[!] {item["alert"]}</font>'
                )
            if remark:
                name_lines.append(
                    f'<font color="#6b7c93" size="7">備: {remark}</font>'
                )
            name_cell = Paragraph(
                "<br/>".join(name_lines),
                S("iq_nc", fontSize=8.5, textColor=C_NAVY, leading=11),
            )

            # ── 規格標準欄位（spec + specDetail sub-line） ──
            spec_lines = [item.get("spec", "─")]
            if item.get("specDetail"):
                spec_lines.append(
                    f'<font color="#6b7c93" size="7">{item["specDetail"]}</font>'
                )
            spec_cell = Paragraph(
                "<br/>".join(spec_lines),
                S("iq_sc", fontSize=8.5, textColor=C_NAVY, leading=11),
            )

            tbl_rows.append([
                PC(f"{seq_no}"),
                PC(grade),
                name_cell,
                spec_cell,
                P(item.get("tool", "─")),
                meas_cell,
                Paragraph(
                    res_txt,
                    SB(f"iq_rc{seq_no}", fontSize=9,
                       textColor=res_col, leading=12, alignment=1),
                ),
            ])

            r = row_i  # actual row index in tbl_rows (0 = header)

            # 行底色
            if res == "fail":
                style_cmds.append(("BACKGROUND", (0, r), (5, r), colors.HexColor("#fff8f7")))
                style_cmds.append(("LINEABOVE",  (0, r), (-1, r), 0.5, C_FAIL))
            else:
                style_cmds.append(("BACKGROUND", (0, r), (5, r), row_bg))

            # 判定欄單獨底色
            style_cmds.append(("BACKGROUND", (6, r), (6, r), res_bg))
            style_cmds.append(("TEXTCOLOR",  (6, r), (6, r), res_col))
            style_cmds.append(("FONTNAME",   (6, r), (6, r), _FB))

            # 等級欄顏色
            style_cmds.append(("TEXTCOLOR",  (1, r), (1, r), gcol))
            style_cmds.append(("FONTNAME",   (1, r), (1, r), _FB))

        tbl = Table(tbl_rows, colWidths=col_w, repeatRows=1)
        tbl.setStyle(TableStyle(style_cmds))
        story.append(tbl)
        story.append(Spacer(1, 3 * mm))

    # ══════════════════════════════════════════════════
    # 4. NG 項目警示摘要
    # ══════════════════════════════════════════════════
    if ng_items_flat:
        story.append(Spacer(1, 2 * mm))
        ng_hdr = Table(
            [[P("NG 項目警示摘要",
                SB("iq_nh", fontSize=9, textColor=C_WHITE, leading=13))]],
            colWidths=[avail_w],
        )
        ng_hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_CR),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story.append(ng_hdr)

        ng_header_row = [
            PC("等級",    s_wcenter),
            PC("檢驗項目", s_wcenter),
            PC("規格標準", s_wcenter),
            PC("量測記錄", s_wcenter),
            PC("備註",    s_wcenter),
        ]
        ng_rows = [ng_header_row]

        ng_cw = [
            11 * mm,
            50 * mm,
            avail_w - 11 * mm - 50 * mm - 40 * mm - 25 * mm,
            40 * mm,
            25 * mm,
        ]

        for item in ng_items_flat:
            iid      = item["id"]
            state    = results.get(iid, {})
            inputs   = state.get("inputs", {})
            remark   = state.get("remark", "")
            inp_defs = item.get("inputs", [])

            if inp_defs:
                meas_str = "  ".join(
                    f'{inp["label"]}='
                    f'{inputs.get(inp["key"], "─")}'
                    f'{inp["unit"]}'
                    for inp in inp_defs
                )
            else:
                meas_str = "─"

            ng_rows.append([
                PC(item["grade"]),
                P(item["name"]),
                P(item.get("spec", "─")),
                P(meas_str),
                P(remark or "─"),
            ])

        ng_tbl = Table(ng_rows, colWidths=ng_cw, repeatRows=1)
        ng_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_CR),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), _FB),
            ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#fff8f7")),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#f5b7b1")),
            ("TEXTCOLOR",     (0, 1), (0, -1), C_CR),
            ("FONTNAME",      (0, 1), (0, -1), _FB),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("ALIGN",         (0, 0), (0, -1), "CENTER"),
        ]))
        story.append(ng_tbl)
        story.append(Spacer(1, 3 * mm))

    # ══════════════════════════════════════════════════
    # 5. 總判定
    # ══════════════════════════════════════════════════
    all_items_flat = [
        item
        for sec in part.get("sections", [])
        for item in sec.get("items", [])
    ]
    cr_ng = sum(
        1 for it in all_items_flat
        if it["grade"] == "CR"
        and results.get(it["id"], {}).get("result") == "fail"
    )
    ma_ng = sum(
        1 for it in all_items_flat
        if it["grade"] == "MA"
        and results.get(it["id"], {}).get("result") == "fail"
    )
    mi_ng = sum(
        1 for it in all_items_flat
        if it["grade"] == "MI"
        and results.get(it["id"], {}).get("result") == "fail"
    )

    is_pass  = (cr_ng == 0 and ma_ng == 0)
    vrd_text = "合格  PASS" if is_pass else "不合格  FAIL"
    vrd_col  = C_PASS if is_pass else C_FAIL
    vrd_bg   = (
        colors.HexColor("#eafaf1") if is_pass
        else colors.HexColor("#fdedec")
    )

    vrd_tbl = Table(
        [[
            Paragraph(
                vrd_text,
                SB("iq_vrd", fontSize=14, textColor=vrd_col, leading=18, alignment=1),
            ),
            P(
                f"CR：{cr_ng} 項  MA：{ma_ng} 項  MI：{mi_ng} 項",
                S("iq_vs", fontSize=8,
                  textColor=colors.HexColor("#6b7c93"), leading=12, alignment=1),
            ),
        ]],
        colWidths=[avail_w * 0.5, avail_w * 0.5],
    )
    vrd_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), vrd_bg),
        ("BOX",           (0, 0), (-1, -1), 1.2, vrd_col),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(vrd_tbl)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════
    # 6. 簽核確認 Approval — 3 等寬方框格式
    # ══════════════════════════════════════════════════
    story.append(Spacer(1, 2 * mm))
    approval_hdr = Table(
        [[Paragraph("簽核確認  Approval",
                    SB("iq_ah", fontSize=9, textColor=C_WHITE, leading=13))]],
        colWidths=[avail_w],
    )
    approval_hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    story.append(approval_hdr)

    box_w  = avail_w / 3
    s_role = SB("iq_role",  fontSize=9,   textColor=C_NAVY, leading=14, alignment=1)
    s_date = S ("iq_sdate", fontSize=7.5,
                textColor=colors.HexColor("#6b7c93"), leading=11, alignment=1)

    sig_tbl = Table(
        [
            [Paragraph(r, s_role) for r in ["IQC 檢驗員", "品保主管", "核准"]],
            [Spacer(1, 1)] * 3,
            [Paragraph("日期：___/___/___", s_date)] * 3,
        ],
        colWidths=[box_w] * 3,
        rowHeights=[None, 18 * mm, None],
    )
    sig_tbl.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 0.6, colors.HexColor("#c5cfe0")),
        ("LINEAFTER",     (0, 0), (1, -1),  0.6, colors.HexColor("#c5cfe0")),
        ("LINEBELOW",     (0, 1), (-1, 1),  0.8, C_NAVY),
        ("TOPPADDING",    (0, 0), (-1, 0),  10),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  6),
        ("TOPPADDING",    (0, 1), (-1, 1),  4),
        ("BOTTOMPADDING", (0, 1), (-1, 1),  4),
        ("TOPPADDING",    (0, 2), (-1, 2),  6),
        ("BOTTOMPADDING", (0, 2), (-1, 2),  10),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_tbl)

    # ── Footer ──────────────────────────────────────
    story.append(Spacer(1, 3 * mm))
    story.append(Table(
        [[P(
            f"REXONTEC 力科  IQC 進料品質管制系統  ·  {gen_time}  ·  CONFIDENTIAL",
            S("iq_ft", fontSize=7,
              textColor=colors.HexColor("#9aafc4"), alignment=1),
        )]],
        colWidths=[avail_w],
    ))

    doc.build(story)
    return buf.getvalue()
