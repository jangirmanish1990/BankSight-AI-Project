"""
BankSight AI — Standalone Churn Analysis PDF
Filename: churn_analysis_14-May-2026.pdf
Generated: 14-May-2026
Data: Pre-compiled analysis data (provided by upstream SQL + Analysis + Anomaly agents)
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT

# ---------------------------------------------------------------------------
# File path
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)
PDF_PATH    = os.path.join(REPORTS_DIR, "churn_analysis_14-May-2026.pdf")

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
NAVY        = colors.HexColor("#003366")
NAVY_MID    = colors.HexColor("#1F3864")
LIGHT_BLUE  = colors.HexColor("#D6E4F7")
BANNER_BG   = colors.HexColor("#002244")
RED         = colors.HexColor("#CC0000")
RED_LIGHT   = colors.HexColor("#FFB3B3")
RED_DARK    = colors.HexColor("#8B0000")
ORANGE      = colors.HexColor("#E65C00")
ORANGE_LIGHT= colors.HexColor("#FFD5B0")
YELLOW_LIGHT= colors.HexColor("#FFF2CC")
GREEN_LIGHT = colors.HexColor("#E2EFDA")
GREEN_DARK  = colors.HexColor("#375623")
ALT_ROW     = colors.HexColor("#EBF3FB")
WHITE       = colors.white
GREY_LIGHT  = colors.HexColor("#F5F5F5")
GREY_MID    = colors.HexColor("#B8CCE4")
GREY_TEXT   = colors.HexColor("#555555")
FOOTER_BLUE = colors.HexColor("#4472C4")

W, H = A4

# ---------------------------------------------------------------------------
# Report data (pre-compiled from SQL + Analysis + Anomaly agents)
# ---------------------------------------------------------------------------
REPORT_DATE     = "14-May-2026"
DATA_RANGE      = "Jan 2024 – Dec 2024"
DATA_SOURCE     = "banking_mock.db"
TOTAL_CUSTOMERS = 3225
PREPARED_BY     = "BankSight AI Analytics System"
RUN_ID          = "BSA-20260514"

# Section 1
OVERALL = {
    "total":    3225,
    "churned":  681,
    "retained": 2544,
    "churn_pct":  21.12,
    "retain_pct": 78.88,
    "baseline":   21.0,
}

# Section 2
SEGMENT_DATA = [
    ("Premium",  1659, 420, 25.32, "ALERT"),
    ("Standard",  431,  89, 20.65, "NORMAL"),
    ("Basic",    1135, 172, 15.15, "NORMAL"),
]

# Section 3
CITY_DATA = [
    ("Mumbai",    530, 119, 22.45),
    ("Hyderabad", 547, 117, 21.39),
    ("Pune",      530, 113, 21.32),
    ("Bengaluru", 548, 116, 21.17),
    ("Gurugram",  524, 108, 20.61),
    ("Delhi",     546, 108, 19.78),
]

# Section 4
AGE_DATA = [
    ("46 – 60",  536,  268, 50.00, "CRITICAL"),
    ("Over 60",       137,   37, 27.01, "WARNING"),
    ("30 – 45", 2010,  336, 16.72, "NORMAL"),
    ("Under 30",      542,   40,  7.38, "NORMAL"),
]

# Section 5
NPS_DATA = [
    ("Detractor (0 – 3)",  642,  384, 59.81, "CRITICAL"),
    ("Passive (4 – 6)",   1341,  297, 22.15, "NORMAL"),
    ("Promoter (7 – 10)", 1242,    0,  0.00, "NORMAL"),
]

# Section 6
PROFILE = [
    ("Avg Balance",       "Rs 70,29,156",  "Rs 85,51,041"),
    ("Avg Credit Score",  "652",           "640"),
    ("Avg NPS",           "6.4 / 10",      "3.2 / 10"),
]

# Section 7
FLAGS = [
    ("ALERT",    "Premium segment churn at 25.32% breaches the 25% BankSight threshold"),
    ("CRITICAL", "Age 46–60 churn at 50.00% — 2.4x the overall baseline"),
    ("CRITICAL", "NPS Detractors churn at 59.81% — near-certain churn signal"),
    ("INSIGHT",  "Churned customers carry Rs 15.2L higher avg balance than retained customers"),
    ("INSIGHT",  "Estimated total balance at risk: ~Rs 5,826 crore (681 churned x Rs 85.5L avg)"),
    ("INSIGHT",  "NPS Promoters show 0.00% churn — NPS is a near-perfect retention predictor"),
]

# Section 8
RECS = [
    (
        "Launch Immediate Premium Retention Outreach",
        "Assign relationship managers to all Premium customers with NPS <= 6 within 30 days. "
        "Current Premium churn stands at 25.32%, breaching the 25% BankSight critical threshold. "
        "Target: reduce below 23% within 60 days through personalised engagement and product review."
    ),
    (
        "Operationalise NPS-Triggered Alerts",
        "Any customer whose NPS drops to 0–3 (Detractor band) should trigger a same-week "
        "callback by a dedicated retention specialist. 642 Detractors are currently at-risk; "
        "the 59.81% churn rate in this cohort makes this the highest-ROI intervention available."
    ),
    (
        "Build a 46–60 Age Cohort Product",
        "Design targeted banking benefits for the 46–60 demographic — retirement planning, "
        "wealth preservation tools, or senior banking benefits — to reduce switching incentive. "
        "This cohort churns at 50.00%, 2.4x the overall baseline, representing a critical gap "
        "in the current product portfolio."
    ),
]

# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------
styles = getSampleStyleSheet()

cover_title = ParagraphStyle("CoverTitle",
    fontSize=26, textColor=WHITE, alignment=TA_CENTER,
    fontName="Helvetica-Bold", leading=32, spaceAfter=6)

cover_sub = ParagraphStyle("CoverSub",
    fontSize=13, textColor=colors.HexColor("#A8C8F0"),
    alignment=TA_CENTER, fontName="Helvetica", leading=18, spaceAfter=4)

section_hdr = ParagraphStyle("SectionHdr",
    fontSize=12, textColor=NAVY, fontName="Helvetica-Bold",
    spaceBefore=14, spaceAfter=5, leading=16)

sub_hdr = ParagraphStyle("SubHdr",
    fontSize=10.5, textColor=NAVY_MID, fontName="Helvetica-Bold",
    spaceBefore=8, spaceAfter=3)

body = ParagraphStyle("Body",
    fontSize=9, textColor=colors.HexColor("#222222"),
    fontName="Helvetica", leading=14, spaceAfter=5,
    alignment=TA_JUSTIFY)

note_style = ParagraphStyle("Note",
    fontSize=8, textColor=GREY_TEXT, fontName="Helvetica",
    leading=11, spaceAfter=6)

confidential = ParagraphStyle("Conf",
    fontSize=7.5, textColor=colors.HexColor("#888888"),
    fontName="Helvetica", alignment=TA_CENTER, leading=10)

# ---------------------------------------------------------------------------
# Footer callback
# ---------------------------------------------------------------------------
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, W, 1.15*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#A8C8F0"))
    canvas.drawString(1.5*cm, 0.4*cm,
        f"BankSight AI  |  Confidential  |  {REPORT_DATE}")
    canvas.drawCentredString(W / 2, 0.4*cm,
        f"Prepared by: {PREPARED_BY}  |  Run ID: {RUN_ID}")
    canvas.drawRightString(W - 1.5*cm, 0.4*cm,
        f"Page {doc.page}")
    canvas.restoreState()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
HR       = HRFlowable(width="100%", thickness=1,   color=NAVY_MID, spaceAfter=8, spaceBefore=2)
HR_LIGHT = HRFlowable(width="100%", thickness=0.4, color=GREY_MID, spaceAfter=6)

# Status row colours
_STATUS_BG = {
    "CRITICAL": RED_LIGHT,
    "ALERT":    ORANGE_LIGHT,
    "WARNING":  YELLOW_LIGHT,
    "NORMAL":   GREEN_LIGHT,
}
_STATUS_FG = {
    "CRITICAL": RED_DARK,
    "ALERT":    ORANGE,
    "WARNING":  colors.HexColor("#7B4F00"),
    "NORMAL":   GREEN_DARK,
}


def build_table(data, col_widths, extra_cmds=None, hdr_rows=1):
    """
    Build a Table with standard BankSight header styling plus any
    extra_cmds (list of TableStyle command tuples) applied on top.
    """
    base_cmds = [
        ("BACKGROUND",    (0, 0),           (-1, hdr_rows - 1), NAVY),
        ("TEXTCOLOR",     (0, 0),           (-1, hdr_rows - 1), WHITE),
        ("FONTNAME",      (0, 0),           (-1, hdr_rows - 1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0),           (-1, hdr_rows - 1), 8.5),
        ("FONTNAME",      (0, hdr_rows),    (-1, -1),           "Helvetica"),
        ("FONTSIZE",      (0, hdr_rows),    (-1, -1),           8.5),
        ("ROWBACKGROUNDS",(0, hdr_rows),    (-1, -1),           [WHITE, ALT_ROW]),
        ("GRID",          (0, 0),           (-1, -1),           0.4, GREY_MID),
        ("VALIGN",        (0, 0),           (-1, -1),           "MIDDLE"),
        ("ALIGN",         (0, 0),           (-1, -1),           "LEFT"),
        ("ALIGN",         (1, 0),           (-1, -1),           "CENTER"),
        ("TOPPADDING",    (0, 0),           (-1, -1),           4),
        ("BOTTOMPADDING", (0, 0),           (-1, -1),           4),
        ("LEFTPADDING",   (0, 0),           (-1, -1),           6),
        ("RIGHTPADDING",  (0, 0),           (-1, -1),           6),
    ]
    if extra_cmds:
        base_cmds.extend(extra_cmds)
    tbl = Table(data, colWidths=col_widths, repeatRows=hdr_rows)
    tbl.setStyle(TableStyle(base_cmds))
    return tbl


def section_label(text):
    return Paragraph(text, section_hdr)


# ---------------------------------------------------------------------------
# Build story
# ---------------------------------------------------------------------------
story = []


# ===========================================================================
# COVER PAGE
# ===========================================================================
# Full-width navy banner block (title area)
cover_banner = Table(
    [[Paragraph("BankSight AI", cover_title)],
     [Paragraph("Churn Analysis Report", cover_sub)]],
    colWidths=[W - 3.6*cm]
)
cover_banner.setStyle(TableStyle([
    ("BACKGROUND",    (0, 0), (-1, -1), BANNER_BG),
    ("TOPPADDING",    (0, 0), (-1, -1), 18),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
    ("LEFTPADDING",   (0, 0), (-1, -1), 0),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
]))
story.append(cover_banner)
story.append(Spacer(1, 0.15*cm))

# Metadata band
meta_band = Table(
    [[Paragraph(
        f"Report Date: <b>{REPORT_DATE}</b> &nbsp;|&nbsp; "
        f"Data Source: <b>{DATA_SOURCE}</b> &nbsp;|&nbsp; "
        f"Customers Analysed: <b>{TOTAL_CUSTOMERS:,}</b> &nbsp;|&nbsp; "
        f"Period: <b>{DATA_RANGE}</b>",
        ParagraphStyle("MetaBand", fontSize=9, textColor=WHITE,
                       fontName="Helvetica", alignment=TA_CENTER, leading=14)
    )]],
    colWidths=[W - 3.6*cm], rowHeights=[0.85*cm]
)
meta_band.setStyle(TableStyle([
    ("BACKGROUND",    (0, 0), (-1, -1), NAVY_MID),
    ("TOPPADDING",    (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story.append(meta_band)
story.append(Spacer(1, 0.5*cm))

story.append(Paragraph(
    f"Prepared by: <b>{PREPARED_BY}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Run ID: <b>{RUN_ID}</b>",
    ParagraphStyle("PrepBy", fontSize=9, textColor=NAVY, fontName="Helvetica",
                   alignment=TA_CENTER, leading=13)))
story.append(Spacer(1, 0.4*cm))
story.append(HR)

# --- At-a-Glance KPI summary box ---
story.append(section_label("At-a-Glance: Three Critical Numbers"))

def kpi_cell_table(value, label, status_text, bg_color, fg_color):
    inner = [
        [Paragraph(value,
                   ParagraphStyle("KV", fontSize=20, textColor=NAVY,
                                  fontName="Helvetica-Bold", alignment=TA_CENTER, leading=24))],
        [Paragraph(label,
                   ParagraphStyle("KL", fontSize=8.5, textColor=GREY_TEXT,
                                  fontName="Helvetica", alignment=TA_CENTER, leading=12))],
        [Paragraph(status_text,
                   ParagraphStyle("KS", fontSize=8, textColor=fg_color,
                                  fontName="Helvetica-Bold", alignment=TA_CENTER, leading=10))],
    ]
    t = Table(inner, colWidths=[5.1*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg_color),
        ("BOX",           (0, 0), (-1, -1), 1.2, NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t

kpi_row = Table([[
    kpi_cell_table("21.12%",  "Overall Churn Rate",
                   "WITHIN BASELINE (21%)", GREEN_LIGHT, GREEN_DARK),
    Spacer(0.35*cm, 1),
    kpi_cell_table("25.32%",  "Premium Segment Churn",
                   "ALERT — EXCEEDS 25% THRESHOLD", ORANGE_LIGHT, ORANGE),
    Spacer(0.35*cm, 1),
    kpi_cell_table("50.00%",  "Age 46–60 Churn Rate",
                   "CRITICAL — 2.4x BASELINE", RED_LIGHT, RED_DARK),
]], colWidths=[5.1*cm, 0.35*cm, 5.1*cm, 0.35*cm, 5.1*cm])
kpi_row.setStyle(TableStyle([
    ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING",  (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING",   (0, 0), (-1, -1), 0),
    ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
]))
story.append(kpi_row)
story.append(Spacer(1, 0.5*cm))
story.append(HR)

# Alert banner
alert_banner = Table(
    [[Paragraph(
        "CRITICAL ALERT: Two cohort-level anomalies detected — Age 46–60 churn at 50.00% "
        "and NPS Detractor churn at 59.81%. Immediate retention action required.",
        ParagraphStyle("AlertBanner", fontSize=9.5, textColor=RED_DARK,
                       fontName="Helvetica-Bold", alignment=TA_CENTER, leading=14)
    )]],
    colWidths=[W - 3.6*cm], rowHeights=[0.95*cm]
)
alert_banner.setStyle(TableStyle([
    ("BACKGROUND",    (0, 0), (-1, -1), RED_LIGHT),
    ("BOX",           (0, 0), (-1, -1), 1.2, RED),
    ("TOPPADDING",    (0, 0), (-1, -1), 10),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
]))
story.append(alert_banner)
story.append(Spacer(1, 0.5*cm))

# Table of contents
toc_data = [
    ["Section", "Title", "Page"],
    ["1",  "Overall Churn Rate",                "2"],
    ["2",  "Churn by Segment",                  "2"],
    ["3",  "Churn by City",                     "2"],
    ["4",  "Churn by Age Group",                "3"],
    ["5",  "Churn by NPS Bucket",               "3"],
    ["6",  "Churned vs Retained Profile",       "3"],
    ["7",  "Key Flags and Alerts",              "4"],
    ["8",  "Recommendations",                   "4"],
    [" ",  "Methodology and Data Coverage",     "4"],
]
story.append(build_table(toc_data, [1.5*cm, 11*cm, 1.5*cm]))
story.append(PageBreak())


# ===========================================================================
# PAGE 2  — Sections 1, 2, 3
# ===========================================================================

# --- Section 1 ---
story.append(section_label("Section 1 — Overall Churn Rate"))
story.append(HR)

oc_rows = [
    ["Metric",                "Count",         "Percentage"],
    ["Total Customers",       f"{OVERALL['total']:,}",    "100.00%"],
    ["Churned",               f"{OVERALL['churned']:,}",  f"{OVERALL['churn_pct']:.2f}%"],
    ["Retained",              f"{OVERALL['retained']:,}", f"{OVERALL['retain_pct']:.2f}%"],
    ["Baseline Benchmark",    "—",                   "21.00%"],
]
story.append(build_table(oc_rows, [7*cm, 4*cm, 4*cm], extra_cmds=[
    ("BACKGROUND", (0, 2), (-1, 2), RED_LIGHT),
    ("FONTNAME",   (0, 2), (-1, 2), "Helvetica-Bold"),
    ("BACKGROUND", (0, 4), (-1, 4), GREEN_LIGHT),
]))
story.append(Paragraph(
    "Overall churn at 21.12% is marginally above the 21% baseline but within acceptable tolerance. "
    "Segment-level analysis (Section 2) reveals critical concentration risk in the Premium cohort.",
    note_style))
story.append(Spacer(1, 0.25*cm))

# --- Section 2 ---
story.append(section_label("Section 2 — Churn by Segment"))
story.append(HR)

seg_rows = [["Segment", "Total Customers", "Churned", "Churn Rate", "Status"]]
seg_extra = []
for i, (seg, total, churned, rate, status) in enumerate(SEGMENT_DATA, 1):
    seg_rows.append([seg, f"{total:,}", f"{churned:,}", f"{rate:.2f}%", status])
    bg = _STATUS_BG.get(status, WHITE)
    fg = _STATUS_FG.get(status, NAVY)
    seg_extra.extend([
        ("BACKGROUND", (0, i), (-1, i), bg),
        ("TEXTCOLOR",  (4, i), (4, i),  fg),
    ])
    if status in ("ALERT", "CRITICAL"):
        seg_extra.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))

story.append(build_table(seg_rows, [4*cm, 3.5*cm, 3*cm, 3*cm, 3.5*cm], extra_cmds=seg_extra))
story.append(Paragraph(
    "ALERT: Premium segment churn (25.32%) breaches the 25% BankSight critical threshold. "
    "With 1,659 customers, Premium represents 51.5% of the customer base and is the primary "
    "revenue risk vector. Standard and Basic segments remain within safe bounds.",
    note_style))
story.append(Spacer(1, 0.25*cm))

# --- Section 3 ---
story.append(section_label("Section 3 — Churn by City"))
story.append(HR)

city_rows = [["City", "Total Customers", "Churned", "Churn Rate", "vs 21% Baseline"]]
city_extra = []
for i, (city, total, churned, rate) in enumerate(CITY_DATA, 1):
    vs = "Above" if rate > 21.0 else "Below"
    city_rows.append([city, f"{total:,}", f"{churned:,}", f"{rate:.2f}%", vs])
    if rate > 21.0:
        city_extra.extend([
            ("BACKGROUND", (3, i), (4, i), YELLOW_LIGHT),
            ("FONTNAME",   (3, i), (4, i), "Helvetica-Bold"),
        ])

story.append(build_table(city_rows, [3.8*cm, 3.5*cm, 3*cm, 3*cm, 3.7*cm], extra_cmds=city_extra))
story.append(Paragraph(
    "Mumbai leads churn volume at 22.45%, followed by Hyderabad and Pune. All six cities "
    "are within 3 percentage points of the baseline. Geographic distribution is broadly uniform; "
    "segment-level targeting is a more effective intervention lens than city-level.",
    note_style))
story.append(PageBreak())


# ===========================================================================
# PAGE 3 — Sections 4, 5, 6
# ===========================================================================

# --- Section 4 ---
story.append(section_label("Section 4 — Churn by Age Group"))
story.append(HR)

age_rows = [["Age Group", "Total Customers", "Churned", "Churn Rate", "Status"]]
age_extra = []
for i, (grp, total, churned, rate, status) in enumerate(AGE_DATA, 1):
    age_rows.append([grp, f"{total:,}", f"{churned:,}", f"{rate:.2f}%", status])
    bg = _STATUS_BG.get(status, WHITE)
    fg = _STATUS_FG.get(status, NAVY)
    age_extra.extend([
        ("BACKGROUND", (0, i), (-1, i), bg),
        ("TEXTCOLOR",  (4, i), (4, i),  fg),
    ])
    if status in ("ALERT", "CRITICAL"):
        age_extra.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))

story.append(build_table(age_rows, [4*cm, 3.5*cm, 3*cm, 3*cm, 3.5*cm], extra_cmds=age_extra))
story.append(Paragraph(
    "CRITICAL: The 46–60 age cohort churns at 50.00% — one in two customers in this bracket "
    "exits. This is 2.4x the overall baseline and represents the most extreme demographic "
    "concentration risk. The Over 60 segment (27.01%) also exceeds the 25% alert threshold. "
    "The Under 30 cohort shows strong retention at 7.38%, suggesting early-lifecycle engagement "
    "is effective but mid-to-late career product relevance requires urgent redesign.",
    note_style))
story.append(Spacer(1, 0.25*cm))

# --- Section 5 ---
story.append(section_label("Section 5 — Churn by NPS Bucket"))
story.append(HR)

nps_rows = [["NPS Bucket", "Total Customers", "Churned", "Churn Rate", "Status"]]
nps_extra = []
for i, (bucket, total, churned, rate, status) in enumerate(NPS_DATA, 1):
    nps_rows.append([bucket, f"{total:,}", f"{churned:,}", f"{rate:.2f}%", status])
    bg = _STATUS_BG.get(status, WHITE)
    fg = _STATUS_FG.get(status, NAVY)
    nps_extra.extend([
        ("BACKGROUND", (0, i), (-1, i), bg),
        ("TEXTCOLOR",  (4, i), (4, i),  fg),
    ])
    if status == "CRITICAL":
        nps_extra.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))

story.append(build_table(nps_rows, [4.5*cm, 3.5*cm, 3*cm, 3*cm, 3*cm], extra_cmds=nps_extra))
story.append(Paragraph(
    "NPS is the single strongest predictor of churn in this dataset. Detractors (NPS 0–3) "
    "churn at 59.81% — a near-certain exit signal. Promoters (NPS 7–10) show 0.00% churn, "
    "confirming NPS as a near-perfect retention predictor. Any customer transitioning from "
    "Passive to Detractor should trigger an immediate intervention.",
    note_style))
story.append(Spacer(1, 0.25*cm))

# --- Section 6 ---
story.append(section_label("Section 6 — Churned vs Retained Customer Profile"))
story.append(HR)

prof_rows = [
    ["Metric",              "Retained Customers",  "Churned Customers"],
    ["Avg Balance",         "Rs 70,29,156",         "Rs 85,51,041"],
    ["Avg Credit Score",    "652",                  "640"],
    ["Avg NPS",             "6.4 / 10",             "3.2 / 10"],
]
prof_extra = [
    ("BACKGROUND", (0, 1), (-1, 1), YELLOW_LIGHT),
    ("FONTNAME",   (0, 1), (-1, 1), "Helvetica-Bold"),
    ("BACKGROUND", (0, 3), (-1, 3), RED_LIGHT),
    ("FONTNAME",   (0, 3), (-1, 3), "Helvetica-Bold"),
]
story.append(build_table(prof_rows, [5*cm, 5*cm, 5*cm], extra_cmds=prof_extra))
story.append(Paragraph(
    "Churned customers hold a significantly higher average balance (Rs 85,51,041 vs Rs 70,29,156 "
    "for retained) — a Rs 15.2L gap. This counter-intuitive pattern suggests that higher-value "
    "customers are actively shopping competitors or consolidating wealth elsewhere. Churned "
    "customers also score 3.2/10 on NPS vs 6.4/10 for retained, confirming NPS as the dominant "
    "signal. Estimated total balance at risk: approximately Rs 5,826 crore.",
    note_style))
story.append(PageBreak())


# ===========================================================================
# PAGE 4 — Sections 7 and 8 + Methodology
# ===========================================================================

# --- Section 7 ---
story.append(section_label("Section 7 — Key Flags and Alerts"))
story.append(HR)

_FLAG_BG = {
    "ALERT":    ORANGE_LIGHT,
    "CRITICAL": RED_LIGHT,
    "INSIGHT":  LIGHT_BLUE,
}
_FLAG_FG = {
    "ALERT":    ORANGE,
    "CRITICAL": RED_DARK,
    "INSIGHT":  NAVY,
}

flags_table_rows = []
flags_extra = []
for i, (badge, text) in enumerate(FLAGS):
    badge_para = Paragraph(badge,
        ParagraphStyle(f"Badge{i}", fontSize=8, fontName="Helvetica-Bold",
                       textColor=_FLAG_FG.get(badge, NAVY),
                       alignment=TA_CENTER, leading=10))
    text_para = Paragraph(f"{i+1}. {text}", body)
    flags_table_rows.append([badge_para, text_para])
    flags_extra.extend([
        ("BACKGROUND", (0, i), (0, i), _FLAG_BG.get(badge, WHITE)),
        ("BACKGROUND", (1, i), (1, i), WHITE),
    ])

flags_tbl = Table(flags_table_rows, colWidths=[2.2*cm, 14.8*cm])
flags_tbl.setStyle(TableStyle([
    ("GRID",          (0, 0), (-1, -1), 0.4, GREY_MID),
    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING",    (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
] + flags_extra))
story.append(flags_tbl)
story.append(Spacer(1, 0.4*cm))

# --- Section 8 ---
story.append(section_label("Section 8 — Recommendations"))
story.append(HR)

for i, (title, detail) in enumerate(RECS, 1):
    title_block = Table(
        [[Paragraph(f"{i}.  {title}",
                    ParagraphStyle(f"RecT{i}", fontSize=10, fontName="Helvetica-Bold",
                                   textColor=WHITE, alignment=TA_LEFT, leading=14))]],
        colWidths=[W - 3.6*cm], rowHeights=[0.8*cm]
    )
    title_block.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    detail_block = Table(
        [[Paragraph(detail, body)]],
        colWidths=[W - 3.6*cm]
    )
    detail_block.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GREY_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(KeepTogether([title_block, detail_block]))
    story.append(Spacer(1, 0.3*cm))

story.append(Spacer(1, 0.35*cm))
story.append(HR_LIGHT)

# --- Methodology ---
story.append(Paragraph("Methodology and Data Coverage", sub_hdr))

meth_rows = [
    ["Parameter", "Value"],
    ["Data Source",         f"{DATA_SOURCE} (SQLite, read-only via SQL Agent)"],
    ["Tables Used",         "customers, transactions, loan_emi"],
    ["Customers Analysed",  f"{TOTAL_CUSTOMERS:,}"],
    ["Churn Baseline",      "21.00% (681 / 3,225)"],
    ["CRITICAL Threshold",  "Churn rate > 25% at any segment or cohort level"],
    ["NPS Scale",           "0 – 10 (not 0 – 100)"],
    ["Currency",            "INR (Rs) — all monetary values. Not USD."],
    ["Date Format",         "DD-MMM-YYYY throughout all outputs"],
    ["Anomaly Threshold",   "Transaction amount > 2x customer monthly average"],
    ["Churn Risk Combo",    "NPS <= 3 AND Missed EMI in same calendar month"],
    ["Agents Used",         "SQL Agent | Analysis Agent | Anomaly Agent | Report Agent"],
    ["Report Generated",    f"{REPORT_DATE} by {PREPARED_BY}"],
    ["Run ID",              RUN_ID],
]
story.append(build_table(meth_rows, [5*cm, 12*cm], hdr_rows=1))
story.append(Spacer(1, 0.4*cm))

story.append(Paragraph(
    "CONFIDENTIAL — BankSight AI Internal Report — Do not distribute externally. "
    "All customer identifiers are anonymised. This report is generated automatically "
    "by the BankSight AI Report Agent and is intended for internal banking analytics "
    "and executive review only.",
    confidential))

# ---------------------------------------------------------------------------
# Build PDF
# ---------------------------------------------------------------------------
doc = SimpleDocTemplate(
    PDF_PATH,
    pagesize=A4,
    leftMargin=1.8*cm,
    rightMargin=1.8*cm,
    topMargin=1.8*cm,
    bottomMargin=1.9*cm,
    title="BankSight AI Churn Analysis Report",
    author=PREPARED_BY,
    subject="Churn Analysis — Jan 2024 to Dec 2024",
)

doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"[PDF] Saved successfully: {PDF_PATH}")
