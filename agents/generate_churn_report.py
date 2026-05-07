"""
BankSight AI — Churn Report Generator
Report Agent: ChurnReport_2026-05-07_Apr-May-2024
Generates Excel, PDF, and PowerBI CSV from SQL + Analysis + Anomaly Agent outputs.
"""

import os
import csv
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

EXCEL_PATH = os.path.join(REPORTS_DIR, "ChurnReport_2026-05-07_Apr-May-2024.xlsx")
PDF_PATH   = os.path.join(REPORTS_DIR, "ChurnReport_2026-05-07_Apr-May-2024.pdf")
CSV_PATH   = os.path.join(DASHBOARD_DIR, "PowerBI_Churn_2026-05-07.csv")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(DASHBOARD_DIR, exist_ok=True)

RUN_TS = "07-May-2026 00:00"

# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------
KPIS = [
    ("Total Customers",           "3,225"),
    ("Total Churned",             "681"),
    ("Churn Rate",                "21.12%"),
    ("Baseline Churn Rate",       "21.00%"),
    ("Avg Balance (Churned)",     u"₹85,51,041.11"),
    ("Avg NPS (Churned)",         "3.16 / 10"),
    ("Avg Credit Score (Churned)","639.88"),
]

SEGMENT_DATA = [
    ("Premium",  420, 1659, 25.32, "CRITICAL"),
    ("Standard",  89,  431, 20.65, "NORMAL"),
    ("Basic",    172, 1135, 15.15, "NORMAL"),
]

CITY_DATA = [
    ("Mumbai",    119, 530, 22.45),
    ("Hyderabad", 117, 547, 21.39),
    ("Bengaluru", 116, 548, 21.17),
    ("Pune",      113, 530, 21.32),
    ("Gurugram",  108, 524, 20.61),
    ("Delhi",     108, 546, 19.78),
]

TOP10_CUSTOMERS = [
    (1,  "2,36,54,671.93", 655, 4, "Premium",  "Pune",      3),
    (2,  "2,00,95,423.74", 584, 3, "Premium",  "Bengaluru", 2),
    (3,  "1,99,66,081.95", 850, 4, "Premium",  "Bengaluru", 1),
    (4,  "1,97,76,861.99", 672, 3, "Premium",  "Delhi",     2),
    (5,  "1,92,06,264.34", 705, 1, "Premium",  "Delhi",     5),
    (6,  "1,90,15,905.48", 625, 4, "Premium",  "Delhi",     8),
    (7,  "1,88,26,725.12", 487, 2, "Premium",  "Delhi",     4),
    (8,  "1,80,88,986.00", 742, 5, "Premium",  "Pune",      2),
    (9,  "1,79,34,644.93", 667, 5, "Premium",  "Hyderabad", 8),
    (10, "1,75,25,854.39", 713, 0, "Premium",  "Gurugram",  0),
]

LOAN_EMI = [
    ("Total Loans",               "400"),
    ("Missed EMIs",               "67 (16.75%)"),
    ("Delayed EMIs",              "57 (14.25%)"),
    ("Combined Stress Rate",      "31%"),
    ("Churned + Missed EMI",      "16 customers"),
]

KEY_FINDINGS = [
    "Premium segment churn at 25.32% has crossed the CRITICAL threshold (>25%).",
    "Churned customers average NPS of 3.16/10 — dangerously close to the 3.0 churn risk floor.",
    "Top 10 churned customers by balance are exclusively Premium; skewed heavily toward short-tenure (0-5 years).",
    "100% of top 100 transactions from churned customers in the reference period are flagged as anomalies.",
    "31% combined EMI stress rate signals systemic repayment pressure.",
    "Mumbai leads churn volume (119); Delhi has the lowest rate (19.78%) — geographic divergence worth investigating.",
]

RECOMMENDATIONS = [
    ("Activate Premium Segment Retention Protocol Immediately",
     "Deploy targeted retention campaign; assign dedicated relationship managers to all Premium customers "
     "with NPS <= 4; focus on Delhi and Bengaluru where high-balance exits are concentrated. "
     "Target: reduce Premium churn below 23% within 60 days."),
    ("Implement Pre-Churn Transaction Spike Alert as Real-Time Trigger",
     "Configure Anomaly Agent to escalate customers with 2+ anomalous transactions in 30-day window "
     "+ NPS <= 4 directly to retention desk within 24 hours."),
    ("Cross-Reference EMI Stress List Against NPS to Identify Next-Wave Churn Cohort",
     "Run query joining loan_emi (Missed/Delayed) against customers with NPS <= 3; estimated 30-50 "
     "customers at immediate risk; initiate outreach by 14-May-2026."),
]

ANOMALIES = [
    ("ANO-001", "Premium Segment Churn Rate Breach (25.32% > 25%)",                    "CRITICAL", 9,  "New"),
    ("ANO-002", "Mass High-Balance Premium Churn — 10 customers above Rs 1 Cr",        "CRITICAL", 10, "New"),
    ("ANO-003", "Churn Risk Combo — NPS 3 + Missed EMI (1 confirmed customer)",        "CRITICAL", 9,  "New"),
    ("ANO-004", "Churn Risk Combo — NPS 3 (1 customer, EMI verification pending)",     "CRITICAL", 8,  "New"),
    ("ANO-005", "Churn Risk Combo — NPS 0 and NPS 1 (2 extreme dissatisfaction cases)","CRITICAL", 9,  "New"),
    ("ANO-006", "Portfolio EMI Stress Rate 31% (threshold 30%)",                        "WARNING",  6,  "New"),
    ("ANO-007", "Inactivity Flag — 3 high-balance Premium customers inactive before churn","WARNING",7, "New"),
    ("ANO-008", "Segment-Credit Score Mismatch — Premium customer with credit_score 487","WARNING", 7,  "New"),
    ("ANO-009", "Spend Spike Pre-Churn — 100 anomalous transactions in period",         "WARNING",  6,  "New"),
    ("ANO-010", "In-Period Missed EMI — 2 churned customers with missed EMI in window", "WARNING",  6,  "New"),
]

PRIORITY_LIST = [
    (1, "Premium, Rs 1.75Cr balance, NPS 0, Tenure 0 yrs",
        "Absolute minimum NPS; immediate acquisition-and-loss event"),
    (2, "Premium, Rs 2.36Cr balance, NPS 4, active_member=1",
        "Highest balance loss; possible retention window remaining"),
    (3, "Premium, Rs 1.92Cr balance, NPS 1, active_member=0, Tenure 5 yrs",
        "Triple-signal: low NPS + inactive + long tenure loyalty failure"),
    (4, "Premium, Rs 1.90Cr balance, NPS 3, Missed EMI Rs 86,139",
        "Only confirmed full churn risk combo (NPS<=3 + missed EMI)"),
    (5, "Premium, Rs 1.88Cr balance, NPS 2, credit_score 487",
        "Segmentation mismatch + NPS below threshold"),
]

METHODOLOGY = [
    ("Data Source",           "data/banking_mock.db (SQLite)"),
    ("Tables Used",           "customers, transactions, loan_emi"),
    ("Date Range Analysed",   "08-Apr-2024 to 07-May-2024"),
    ("Customers Analysed",    "3,225"),
    ("Transactions Analysed", "50,000"),
    ("Loan Records Analysed", "400"),
    ("Churn Baseline",        "21% (681/3225)"),
    ("Anomaly Threshold",     "amount > 2x customer monthly average"),
    ("Report Generated",      "07-May-2026"),
    ("Currency",              "INR (Rs)"),
    ("NPS Scale",             "0-10"),
]

# ===========================================================================
# EXCEL REPORT
# ===========================================================================
def build_excel():
    from openpyxl import Workbook
    from openpyxl.styles import (PatternFill, Font, Alignment, Border, Side,
                                 numbers)
    from openpyxl.styles.numbers import FORMAT_NUMBER_COMMA_SEPARATED1
    from openpyxl.utils import get_column_letter

    wb = Workbook()

    # Colour palette
    DARK_BLUE   = "1F3864"
    WHITE       = "FFFFFF"
    RED_FILL    = "FF0000"
    RED_LIGHT   = "FFB3B3"
    ORANGE_FILL = "FF6600"
    YELLOW_FILL = "FFFF00"
    YELLOW_LIGHT= "FFF2CC"
    GREEN_FILL  = "00B050"
    ALT_ROW     = "DCE6F1"
    HEADER_FONT = Font(name="Calibri", bold=True, color=WHITE, size=11)
    BODY_FONT   = Font(name="Calibri", size=10)
    TITLE_FONT  = Font(name="Calibri", bold=True, size=14, color=DARK_BLUE)
    BOLD_FONT   = Font(name="Calibri", bold=True, size=10, color=DARK_BLUE)
    THIN        = Side(style="thin", color="B8CCE4")
    BORDER      = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
    CENTER      = Alignment(horizontal="center", vertical="center", wrap_text=True)
    LEFT        = Alignment(horizontal="left",   vertical="center", wrap_text=True)

    def hdr_fill(hex_color=DARK_BLUE):
        return PatternFill("solid", fgColor=hex_color)

    def alt_fill():
        return PatternFill("solid", fgColor=ALT_ROW)

    def style_header_row(ws, row_num, col_count, bg=DARK_BLUE):
        for c in range(1, col_count + 1):
            cell = ws.cell(row=row_num, column=c)
            cell.fill = hdr_fill(bg)
            cell.font = HEADER_FONT
            cell.alignment = CENTER
            cell.border = BORDER

    def style_data_row(ws, row_num, col_count, alternate=False):
        for c in range(1, col_count + 1):
            cell = ws.cell(row=row_num, column=c)
            if alternate:
                cell.fill = alt_fill()
            cell.font = BODY_FONT
            cell.alignment = LEFT
            cell.border = BORDER

    def write_section_title(ws, row, text, col_span=6):
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=col_span)
        cell = ws.cell(row=row, column=1, value=text)
        cell.font = TITLE_FONT
        cell.alignment = LEFT
        return row + 1

    # -----------------------------------------------------------------------
    # Sheet 1 — Executive Summary
    # -----------------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "Executive Summary"
    ws1.sheet_view.showGridLines = False
    ws1.column_dimensions["A"].width = 32
    ws1.column_dimensions["B"].width = 28
    ws1.column_dimensions["C"].width = 18
    ws1.column_dimensions["D"].width = 22

    row = 1
    # Report title block
    ws1.merge_cells("A1:D1")
    ws1["A1"] = "BankSight AI — Churn Analysis Report"
    ws1["A1"].font = Font(name="Calibri", bold=True, size=16, color=DARK_BLUE)
    ws1["A1"].alignment = CENTER
    ws1["A1"].fill = PatternFill("solid", fgColor="D6E4F7")

    ws1.merge_cells("A2:D2")
    ws1["A2"] = "Period: 08-Apr-2024 to 07-May-2024   |   Report Date: 07-May-2026   |   Generated: " + RUN_TS
    ws1["A2"].font = Font(name="Calibri", italic=True, size=10, color="4472C4")
    ws1["A2"].alignment = CENTER
    ws1.row_dimensions[1].height = 30
    ws1.row_dimensions[2].height = 18

    row = 4
    row = write_section_title(ws1, row, "Key Performance Indicators", 4)
    headers = ["Metric", "Value", "Status", "Note"]
    for c, h in enumerate(headers, 1):
        ws1.cell(row=row, column=c, value=h)
    style_header_row(ws1, row, 4)
    row += 1

    # Traffic light function
    def churn_status_flag(rate_str):
        try:
            r = float(rate_str.replace("%",""))
            if r > 25: return ("CRITICAL", RED_LIGHT)
            if r > 21: return ("MONITOR", YELLOW_LIGHT)
            return ("NORMAL", "E2EFDA")
        except:
            return ("", "FFFFFF")

    kpi_notes = {
        "Churn Rate":         "vs 21.00% baseline",
        "Avg NPS (Churned)":  "Risk floor: 3.0/10",
        "Avg Balance (Churned)": "INR; Premium-heavy",
    }

    for i, (metric, value) in enumerate(KPIS):
        alt = (i % 2 == 0)
        ws1.cell(row=row, column=1, value=metric)
        ws1.cell(row=row, column=2, value=value)
        note = kpi_notes.get(metric, "")
        ws1.cell(row=row, column=4, value=note)
        if "Rate" in metric and "%" in value:
            status_text, status_color = churn_status_flag(value)
            cell_s = ws1.cell(row=row, column=3, value=status_text)
            cell_s.fill = PatternFill("solid", fgColor=status_color)
            cell_s.font = Font(name="Calibri", bold=True, size=10,
                               color=(RED_FILL if "CRITICAL" in status_text else "375623"))
        else:
            ws1.cell(row=row, column=3, value="")
        style_data_row(ws1, row, 4, alt)
        row += 1

    row += 1
    row = write_section_title(ws1, row, "Anomaly Count Summary", 4)
    ws1.cell(row=row, column=1, value="Severity")
    ws1.cell(row=row, column=2, value="Count")
    ws1.cell(row=row, column=3, value="Action Required")
    ws1.cell(row=row, column=4, value="Status")
    style_header_row(ws1, row, 4)
    row += 1
    for sev, count, action, color in [
        ("CRITICAL", 5, "Immediate escalation required", RED_LIGHT),
        ("WARNING",  5, "Monitor and review within 48h", YELLOW_LIGHT),
    ]:
        ws1.cell(row=row, column=1, value=sev)
        ws1.cell(row=row, column=2, value=count)
        ws1.cell(row=row, column=3, value=action)
        ws1.cell(row=row, column=4, value="New")
        for c in range(1, 5):
            ws1.cell(row=row, column=c).fill = PatternFill("solid", fgColor=color)
            ws1.cell(row=row, column=c).font = BODY_FONT
            ws1.cell(row=row, column=c).border = BORDER
            ws1.cell(row=row, column=c).alignment = LEFT
        row += 1

    row += 1
    row = write_section_title(ws1, row, "Top 3 Actionable Recommendations", 4)
    for i, (title, detail) in enumerate(RECOMMENDATIONS, 1):
        ws1.merge_cells(start_row=row, start_column=1,
                        end_row=row, end_column=4)
        cell = ws1.cell(row=row, column=1,
                        value=f"{i}. {title}")
        cell.font = BOLD_FONT
        cell.fill = PatternFill("solid", fgColor="D6E4F7")
        cell.alignment = LEFT
        cell.border = BORDER
        ws1.row_dimensions[row].height = 16
        row += 1
        ws1.merge_cells(start_row=row, start_column=1,
                        end_row=row, end_column=4)
        d_cell = ws1.cell(row=row, column=1, value=detail)
        d_cell.font = BODY_FONT
        d_cell.alignment = Alignment(horizontal="left", vertical="center",
                                     wrap_text=True)
        d_cell.border = BORDER
        ws1.row_dimensions[row].height = 48
        row += 1

    # -----------------------------------------------------------------------
    # Sheet 2 — Churn by Segment & City
    # -----------------------------------------------------------------------
    ws2 = wb.create_sheet("Churn by Segment & City")
    ws2.sheet_view.showGridLines = False
    for col, w in zip(["A","B","C","D","E","F","G"], [18,12,10,12,16,18,14]):
        ws2.column_dimensions[col].width = w

    ws2.merge_cells("A1:G1")
    ws2["A1"] = "Churn Breakdown — 08-Apr-2024 to 07-May-2024"
    ws2["A1"].font = Font(name="Calibri", bold=True, size=14, color=DARK_BLUE)
    ws2["A1"].alignment = CENTER
    ws2["A1"].fill = PatternFill("solid", fgColor="D6E4F7")

    row = 3
    row = write_section_title(ws2, row, "Churn by Segment", 5)
    for c, h in enumerate(["Segment","Churned","Total","Churn Rate","Status"], 1):
        ws2.cell(row=row, column=c, value=h)
    style_header_row(ws2, row, 5)
    row += 1
    STATUS_COLORS = {"CRITICAL": RED_LIGHT, "NORMAL": "E2EFDA"}
    for i, (seg, churned, total, rate, status) in enumerate(SEGMENT_DATA):
        ws2.cell(row=row, column=1, value=seg)
        ws2.cell(row=row, column=2, value=churned)
        ws2.cell(row=row, column=3, value=total)
        ws2.cell(row=row, column=4, value=f"{rate:.2f}%")
        ws2.cell(row=row, column=5, value=status)
        for c in range(1, 6):
            fill_c = STATUS_COLORS.get(status, "FFFFFF")
            ws2.cell(row=row, column=c).fill = PatternFill("solid", fgColor=fill_c)
            ws2.cell(row=row, column=c).font = Font(name="Calibri", size=10,
                bold=(status == "CRITICAL"))
            ws2.cell(row=row, column=c).border = BORDER
            ws2.cell(row=row, column=c).alignment = LEFT
        row += 1

    row += 1
    row = write_section_title(ws2, row, "Churn by City", 5)
    for c, h in enumerate(["City","Churned","Total","Churn Rate","vs Baseline"], 1):
        ws2.cell(row=row, column=c, value=h)
    style_header_row(ws2, row, 5)
    row += 1
    for i, (city, churned, total, rate) in enumerate(CITY_DATA):
        alt = (i % 2 == 0)
        vs = "Above" if rate > 21.0 else "Below"
        ws2.cell(row=row, column=1, value=city)
        ws2.cell(row=row, column=2, value=churned)
        ws2.cell(row=row, column=3, value=total)
        ws2.cell(row=row, column=4, value=f"{rate:.2f}%")
        ws2.cell(row=row, column=5, value=vs)
        style_data_row(ws2, row, 5, alt)
        row += 1

    row += 1
    row = write_section_title(ws2, row, "Top 10 Churned Customers by Balance (Anonymised)", 7)
    t10_headers = ["Rank","Balance (Rs)","Credit Score","NPS","Segment","City","Tenure (yrs)"]
    for c, h in enumerate(t10_headers, 1):
        ws2.cell(row=row, column=c, value=h)
    style_header_row(ws2, row, 7)
    row += 1
    for i, (rank, bal, cs, nps, seg, city, tenure) in enumerate(TOP10_CUSTOMERS):
        alt = (i % 2 == 0)
        ws2.cell(row=row, column=1, value=rank)
        ws2.cell(row=row, column=2, value=u"₹" + bal)
        ws2.cell(row=row, column=3, value=cs)
        ws2.cell(row=row, column=4, value=f"{nps}/10")
        ws2.cell(row=row, column=5, value=seg)
        ws2.cell(row=row, column=6, value=city)
        ws2.cell(row=row, column=7, value=tenure)
        style_data_row(ws2, row, 7, alt)
        row += 1

    # -----------------------------------------------------------------------
    # Sheet 3 — Analysis Insights
    # -----------------------------------------------------------------------
    ws3 = wb.create_sheet("Analysis Insights")
    ws3.sheet_view.showGridLines = False
    ws3.column_dimensions["A"].width = 6
    ws3.column_dimensions["B"].width = 100

    ws3.merge_cells("A1:B1")
    ws3["A1"] = "Analysis Insights — 08-Apr-2024 to 07-May-2024"
    ws3["A1"].font = Font(name="Calibri", bold=True, size=14, color=DARK_BLUE)
    ws3["A1"].alignment = CENTER
    ws3["A1"].fill = PatternFill("solid", fgColor="D6E4F7")

    row = 3
    ws3.merge_cells(f"A{row}:B{row}")
    ws3.cell(row=row, column=1, value="Key Findings")
    ws3.cell(row=row, column=1).font = Font(name="Calibri", bold=True, size=12, color=DARK_BLUE)
    ws3.cell(row=row, column=1).fill = PatternFill("solid", fgColor="BDD7EE")
    ws3.cell(row=row, column=1).alignment = LEFT
    row += 1

    for i, finding in enumerate(KEY_FINDINGS, 1):
        alt = (i % 2 == 0)
        ws3.cell(row=row, column=1, value=str(i))
        ws3.merge_cells(f"B{row}:B{row}")
        ws3.cell(row=row, column=2, value=finding)
        style_data_row(ws3, row, 2, alt)
        ws3.row_dimensions[row].height = 30
        row += 1

    insights = [
        ("Segment Analysis",
         "The Premium segment, representing 51.5% of total customers, has breached the critical 25% churn "
         "threshold at 25.32%. This is the highest-value cohort and the primary revenue risk vector. "
         "Standard (20.65%) and Basic (15.15%) segments remain within acceptable bounds."),
        ("NPS vs Churn Correlation",
         "Churned customers carry an average NPS of 3.16/10, just above the 3.0 risk floor that triggers "
         "the churn risk combo alert. Any further decline in NPS among active customers should be treated "
         "as a leading indicator of upcoming churn."),
        ("Tenure vs Churn",
         "Top 10 churned customers by balance have tenures ranging from 0 to 8 years, with the majority "
         "(7 of 10) in the 0-5 year range. Short-tenure Premium customers represent the highest attrition "
         "risk and may not yet have sufficient product stickiness."),
        ("Transaction Anomaly Pattern",
         "All 100 transactions sampled from churned customers in the reference period (08-Apr-2024 to "
         "07-May-2024) are flagged as spend spikes (amount > 2x customer monthly average, range "
         "Rs 1,33,222 - Rs 1,49,558). This pattern suggests concentrated high-value spending "
         "immediately preceding churn — a potential pre-exit liquidation signal."),
        ("Loan/EMI Stress Overlap",
         "The combined EMI stress rate stands at 31% (Missed 16.75% + Delayed 14.25%), marginally "
         "above the 30% monitoring threshold. 16 customers present the full churn risk combo of "
         "churned status + missed EMI. These represent the highest-priority outreach targets."),
    ]

    row += 1
    for section, text in insights:
        ws3.merge_cells(f"A{row}:B{row}")
        ws3.cell(row=row, column=1, value=section)
        ws3.cell(row=row, column=1).font = Font(name="Calibri", bold=True, size=11, color=DARK_BLUE)
        ws3.cell(row=row, column=1).fill = PatternFill("solid", fgColor="BDD7EE")
        ws3.cell(row=row, column=1).alignment = LEFT
        ws3.cell(row=row, column=1).border = BORDER
        row += 1
        ws3.merge_cells(f"A{row}:B{row}")
        ws3.cell(row=row, column=1, value=text)
        ws3.cell(row=row, column=1).font = BODY_FONT
        ws3.cell(row=row, column=1).alignment = Alignment(horizontal="left",
                                                           vertical="center", wrap_text=True)
        ws3.cell(row=row, column=1).border = BORDER
        ws3.row_dimensions[row].height = 60
        row += 2

    # -----------------------------------------------------------------------
    # Sheet 4 — Anomaly Flags
    # -----------------------------------------------------------------------
    ws4 = wb.create_sheet("Anomaly Flags")
    ws4.sheet_view.showGridLines = False
    for col, w in zip(["A","B","C","D","E"], [12, 64, 12, 8, 10]):
        ws4.column_dimensions[col].width = w

    ws4.merge_cells("A1:E1")
    ws4["A1"] = "Anomaly Flags — 07-May-2026"
    ws4["A1"].font = Font(name="Calibri", bold=True, size=14, color=DARK_BLUE)
    ws4["A1"].alignment = CENTER
    ws4["A1"].fill = PatternFill("solid", fgColor="D6E4F7")

    row = 3
    for c, h in enumerate(["Anomaly ID","Description","Severity","Score","Status"], 1):
        ws4.cell(row=row, column=c, value=h)
    style_header_row(ws4, row, 5)
    row += 1

    SEV_FILL = {"CRITICAL": "FFB3B3", "WARNING": "FFF2CC"}
    for ano_id, desc, sev, score, status in ANOMALIES:
        fill_hex = SEV_FILL.get(sev, "FFFFFF")
        ws4.cell(row=row, column=1, value=ano_id)
        ws4.cell(row=row, column=2, value=desc)
        ws4.cell(row=row, column=3, value=sev)
        ws4.cell(row=row, column=4, value=score)
        ws4.cell(row=row, column=5, value=status)
        for c in range(1, 6):
            ws4.cell(row=row, column=c).fill = PatternFill("solid", fgColor=fill_hex)
            ws4.cell(row=row, column=c).font = Font(name="Calibri", size=10,
                bold=(sev == "CRITICAL"))
            ws4.cell(row=row, column=c).border = BORDER
            ws4.cell(row=row, column=c).alignment = Alignment(horizontal="left",
                                                               vertical="center", wrap_text=True)
        ws4.row_dimensions[row].height = 30
        row += 1

    row += 1
    ws4.merge_cells(f"A{row}:E{row}")
    ws4.cell(row=row, column=1, value="Priority Intervention List (Anonymised)")
    ws4.cell(row=row, column=1).font = Font(name="Calibri", bold=True, size=12, color=DARK_BLUE)
    ws4.cell(row=row, column=1).fill = PatternFill("solid", fgColor="BDD7EE")
    ws4.cell(row=row, column=1).alignment = LEFT
    row += 1

    for c, h in enumerate(["Priority","Profile","Intervention Reason"], 1):
        ws4.cell(row=row, column=c, value=h)
    style_header_row(ws4, row, 3)
    ws4.column_dimensions["B"].width = 45
    ws4.column_dimensions["C"].width = 55
    row += 1

    for priority, profile, reason in PRIORITY_LIST:
        alt = (priority % 2 == 0)
        ws4.cell(row=row, column=1, value=priority)
        ws4.cell(row=row, column=2, value=profile)
        ws4.cell(row=row, column=3, value=reason)
        style_data_row(ws4, row, 3, alt)
        ws4.row_dimensions[row].height = 36
        row += 1

    # -----------------------------------------------------------------------
    # Sheet 5 — Methodology
    # -----------------------------------------------------------------------
    ws5 = wb.create_sheet("Methodology")
    ws5.sheet_view.showGridLines = False
    ws5.column_dimensions["A"].width = 30
    ws5.column_dimensions["B"].width = 55

    ws5.merge_cells("A1:B1")
    ws5["A1"] = "Methodology & Data Sources"
    ws5["A1"].font = Font(name="Calibri", bold=True, size=14, color=DARK_BLUE)
    ws5["A1"].alignment = CENTER
    ws5["A1"].fill = PatternFill("solid", fgColor="D6E4F7")

    row = 3
    for c, h in enumerate(["Parameter","Value"], 1):
        ws5.cell(row=row, column=c, value=h)
    style_header_row(ws5, row, 2)
    row += 1

    for i, (param, value) in enumerate(METHODOLOGY):
        alt = (i % 2 == 0)
        ws5.cell(row=row, column=1, value=param)
        ws5.cell(row=row, column=2, value=value)
        style_data_row(ws5, row, 2, alt)
        row += 1

    row += 2
    ws5.merge_cells(f"A{row}:B{row}")
    ws5.cell(row=row, column=1,
             value="Agents Used: SQL Agent | Analysis Agent | Anomaly Agent | Report Agent")
    ws5.cell(row=row, column=1).font = Font(name="Calibri", italic=True, size=10, color="4472C4")
    ws5.cell(row=row, column=1).alignment = LEFT
    row += 1
    ws5.merge_cells(f"A{row}:B{row}")
    ws5.cell(row=row, column=1,
             value="CONFIDENTIAL — BankSight AI Internal Report — Do not distribute externally")
    ws5.cell(row=row, column=1).font = Font(name="Calibri", bold=True, size=10, color="FF0000")
    ws5.cell(row=row, column=1).alignment = CENTER

    wb.save(EXCEL_PATH)
    print(f"[Excel] Saved: {EXCEL_PATH}")


# ===========================================================================
# PDF REPORT
# ===========================================================================
def build_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak, HRFlowable)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    DARK_BLUE_RL = colors.HexColor("#1F3864")
    LIGHT_BLUE   = colors.HexColor("#D6E4F7")
    RED_RL       = colors.HexColor("#FF0000")
    RED_LIGHT_RL = colors.HexColor("#FFB3B3")
    YELLOW_RL    = colors.HexColor("#FFF2CC")
    ALT_RL       = colors.HexColor("#DCE6F1")
    WHITE_RL     = colors.white
    ORANGE_RL    = colors.HexColor("#FF6600")

    W, H = A4

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle",
        parent=styles["Heading1"],
        fontSize=18, textColor=DARK_BLUE_RL,
        alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle",
        parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#4472C4"),
        alignment=TA_CENTER, spaceAfter=12, italic=True)
    section_style = ParagraphStyle("Section",
        parent=styles["Heading2"],
        fontSize=13, textColor=DARK_BLUE_RL,
        spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("Body",
        parent=styles["Normal"],
        fontSize=9.5, leading=14, alignment=TA_JUSTIFY,
        spaceAfter=6)
    bullet_style = ParagraphStyle("Bullet",
        parent=styles["Normal"],
        fontSize=9.5, leading=14, leftIndent=14,
        bulletIndent=4, spaceAfter=3)
    label_style = ParagraphStyle("Label",
        parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#4472C4"),
        italic=True, spaceAfter=2)
    confidential_style = ParagraphStyle("Conf",
        parent=styles["Normal"],
        fontSize=8, textColor=RED_RL, alignment=TA_CENTER)
    alert_style = ParagraphStyle("Alert",
        parent=styles["Normal"],
        fontSize=10, textColor=RED_RL, alignment=TA_CENTER,
        fontName="Helvetica-Bold", spaceAfter=4)

    def tbl_style_base(data, header_rows=1):
        cols = len(data[0])
        row_count = len(data)
        commands = [
            ("BACKGROUND",  (0, 0),           (-1, header_rows - 1), DARK_BLUE_RL),
            ("TEXTCOLOR",   (0, 0),           (-1, header_rows - 1), WHITE_RL),
            ("FONTNAME",    (0, 0),           (-1, header_rows - 1), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0),           (-1, header_rows - 1), 9),
            ("FONTNAME",    (0, header_rows), (-1, -1),              "Helvetica"),
            ("FONTSIZE",    (0, header_rows), (-1, -1),              8.5),
            ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [WHITE_RL, ALT_RL]),
            ("GRID",        (0, 0),           (-1, -1),  0.5, colors.HexColor("#B8CCE4")),
            ("VALIGN",      (0, 0),           (-1, -1),  "MIDDLE"),
            ("ALIGN",       (0, 0),           (-1, -1),  "LEFT"),
            ("TOPPADDING",  (0, 0),           (-1, -1),  4),
            ("BOTTOMPADDING",(0, 0),          (-1, -1),  4),
            ("LEFTPADDING", (0, 0),           (-1, -1),  5),
        ]
        return TableStyle(commands)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#4472C4"))
        canvas.drawString(1.5*cm, 1.0*cm,
            "CONFIDENTIAL — BankSight AI Internal Report — Do not distribute externally")
        canvas.drawRightString(W - 1.5*cm, 1.0*cm,
            f"Page {doc.page}  |  Generated: 07-May-2026")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        PDF_PATH, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.8*cm, bottomMargin=2.2*cm,
        onFirstPage=footer, onLaterPages=footer
    )

    story = []
    HR = HRFlowable(width="100%", thickness=1.2,
                    color=DARK_BLUE_RL, spaceAfter=8)

    # -------------------------------------------------------------------
    # Page 1 — Executive Summary
    # -------------------------------------------------------------------
    story.append(Paragraph("BankSight AI", title_style))
    story.append(Paragraph("Churn Analysis Report", title_style))
    story.append(Paragraph(
        "Period: 08-Apr-2024 to 07-May-2024 &nbsp;&nbsp;|&nbsp;&nbsp; "
        "Report Date: 07-May-2026 &nbsp;&nbsp;|&nbsp;&nbsp; Run: " + RUN_TS,
        subtitle_style))
    story.append(HR)

    story.append(Paragraph("1. Executive Summary", section_style))

    # KPI table
    kpi_data = [["Metric", "Value", "Status"]]
    for metric, value in KPIS:
        if "Rate" in metric and "%" in value:
            rate_f = float(value.replace("%",""))
            if rate_f > 25:
                status = "CRITICAL"
            elif rate_f > 21:
                status = "MONITOR"
            else:
                status = "NORMAL"
        else:
            status = "-"
        kpi_data.append([metric, value, status])

    kpi_tbl = Table(kpi_data, colWidths=[8*cm, 6*cm, 4*cm])
    kpi_ts = tbl_style_base(kpi_data)
    # colour status cells
    for r_idx, (metric, value) in enumerate(KPIS, 1):
        if "Rate" in metric and "%" in value:
            rate_f = float(value.replace("%",""))
            if rate_f > 25:
                kpi_ts.add("BACKGROUND", (2, r_idx), (2, r_idx), RED_LIGHT_RL)
                kpi_ts.add("TEXTCOLOR",  (2, r_idx), (2, r_idx), RED_RL)
                kpi_ts.add("FONTNAME",   (2, r_idx), (2, r_idx), "Helvetica-Bold")
            elif rate_f > 21:
                kpi_ts.add("BACKGROUND", (2, r_idx), (2, r_idx), YELLOW_RL)
            else:
                kpi_ts.add("BACKGROUND", (2, r_idx), (2, r_idx),
                            colors.HexColor("#E2EFDA"))
    kpi_tbl.setStyle(kpi_ts)
    story.append(kpi_tbl)
    story.append(Spacer(1, 0.3*cm))

    # Overall status
    story.append(Paragraph(
        "Overall Churn Status: NORMAL — 21.12% vs 21.00% baseline (within tolerance)",
        ParagraphStyle("OK", parent=styles["Normal"], fontSize=9.5,
                       textColor=colors.HexColor("#375623"), fontName="Helvetica-Bold",
                       backColor=colors.HexColor("#E2EFDA"), borderPad=4, spaceAfter=6,
                       alignment=TA_CENTER)))

    # CRITICAL alert box
    story.append(Paragraph(
        "CRITICAL ALERT: Premium Segment churn at 25.32% exceeds 25% threshold — "
        "immediate retention action required",
        ParagraphStyle("CritAlert", parent=styles["Normal"], fontSize=9.5,
                       textColor=RED_RL, fontName="Helvetica-Bold",
                       backColor=RED_LIGHT_RL, borderPad=4, spaceAfter=8,
                       alignment=TA_CENTER)))

    story.append(Paragraph("Anomaly Count: 5 CRITICAL | 5 WARNING", alert_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("Top 3 Recommendations", section_style))
    for i, (title, detail) in enumerate(RECOMMENDATIONS, 1):
        story.append(Paragraph(f"<b>{i}. {title}</b>", bullet_style))
        story.append(Paragraph(detail, ParagraphStyle("RecDetail",
            parent=styles["Normal"], fontSize=9, leftIndent=20, spaceAfter=6,
            leading=13, alignment=TA_JUSTIFY)))

    story.append(PageBreak())

    # -------------------------------------------------------------------
    # Page 2 — Analysis Insights
    # -------------------------------------------------------------------
    story.append(Paragraph("2. Analysis Insights", section_style))
    story.append(HR)

    story.append(Paragraph("Segment Performance", ParagraphStyle("SubSection",
        parent=styles["Heading3"], fontSize=11, textColor=DARK_BLUE_RL,
        spaceBefore=6, spaceAfter=4)))

    seg_data = [["Segment", "Churned", "Total", "Churn Rate", "Status"]]
    for seg, churned, total, rate, status in SEGMENT_DATA:
        seg_data.append([seg, str(churned), str(total), f"{rate:.2f}%", status])
    seg_tbl = Table(seg_data, colWidths=[4.2*cm, 2.8*cm, 2.8*cm, 3.2*cm, 4*cm])
    seg_ts = tbl_style_base(seg_data)
    for r_idx, (seg, churned, total, rate, status) in enumerate(SEGMENT_DATA, 1):
        c = RED_LIGHT_RL if status == "CRITICAL" else colors.HexColor("#E2EFDA")
        seg_ts.add("BACKGROUND", (0, r_idx), (-1, r_idx), c)
        if status == "CRITICAL":
            seg_ts.add("FONTNAME", (0, r_idx), (-1, r_idx), "Helvetica-Bold")
    seg_tbl.setStyle(seg_ts)
    story.append(seg_tbl)
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("City-wise Churn Breakdown", ParagraphStyle("SubSection",
        parent=styles["Heading3"], fontSize=11, textColor=DARK_BLUE_RL,
        spaceBefore=6, spaceAfter=4)))

    city_data = [["City", "Churned", "Total", "Churn Rate", "vs Baseline"]]
    for city, churned, total, rate in CITY_DATA:
        vs = "Above" if rate > 21.0 else "Below"
        city_data.append([city, str(churned), str(total), f"{rate:.2f}%", vs])
    city_tbl = Table(city_data, colWidths=[4.2*cm, 2.8*cm, 2.8*cm, 3.2*cm, 4*cm])
    city_tbl.setStyle(tbl_style_base(city_data))
    story.append(city_tbl)
    story.append(Spacer(1, 0.3*cm))

    sub_sec = ParagraphStyle("SubSection2", parent=styles["Heading3"],
        fontSize=11, textColor=DARK_BLUE_RL, spaceBefore=8, spaceAfter=3)
    for section, text in [
        ("NPS vs Churn Correlation",
         "Churned customers carry an average NPS of 3.16/10, just above the 3.0 risk floor. "
         "This is a strong leading indicator — active customers trending below NPS 4 should be "
         "treated as pre-churn signals and escalated to relationship managers immediately."),
        ("Tenure vs Churn",
         "7 of the top 10 churned customers by balance have tenures of 0-5 years, suggesting "
         "insufficient product embedding in the early relationship lifecycle. Onboarding and "
         "engagement improvements within the first 5 years may reduce Premium churn significantly."),
        ("Transaction Anomaly Pattern",
         "100% of sampled transactions from churned customers in the period are flagged as spend "
         "spikes (Rs 1,33,222 - Rs 1,49,558). This pattern — high-value transactions immediately "
         "preceding account closure — should be codified as a real-time churn trigger in the "
         "Anomaly Agent pipeline."),
        ("Loan/EMI Stress",
         "31% combined EMI stress rate (Missed 16.75% + Delayed 14.25%) marginally exceeds the "
         "30% monitoring threshold. 16 customers are both churned and carry missed EMI status, "
         "representing the most at-risk cohort for credit loss coinciding with churn."),
    ]:
        story.append(Paragraph(section, sub_sec))
        story.append(Paragraph(text, body_style))

    story.append(PageBreak())

    # -------------------------------------------------------------------
    # Page 3 — Anomaly Alerts
    # -------------------------------------------------------------------
    story.append(Paragraph("3. Anomaly Alerts", section_style))
    story.append(HR)

    ano_data = [["ID", "Description", "Severity", "Score", "Status"]]
    for ano_id, desc, sev, score, status in ANOMALIES:
        ano_data.append([ano_id, desc, sev, str(score), status])

    ano_tbl = Table(ano_data, colWidths=[1.8*cm, 8.5*cm, 2.4*cm, 1.5*cm, 1.8*cm])
    ano_ts = tbl_style_base(ano_data)
    for r_idx, (ano_id, desc, sev, score, status) in enumerate(ANOMALIES, 1):
        c = RED_LIGHT_RL if sev == "CRITICAL" else YELLOW_RL
        ano_ts.add("BACKGROUND", (0, r_idx), (-1, r_idx), c)
        if sev == "CRITICAL":
            ano_ts.add("FONTNAME", (0, r_idx), (-1, r_idx), "Helvetica-Bold")
    ano_tbl.setStyle(ano_ts)
    story.append(ano_tbl)
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("Priority Intervention List (Anonymised)", sub_sec))
    pri_data = [["Priority", "Profile", "Intervention Reason"]]
    for priority, profile, reason in PRIORITY_LIST:
        pri_data.append([str(priority), profile, reason])
    pri_tbl = Table(pri_data, colWidths=[1.8*cm, 7*cm, 8.2*cm])
    pri_tbl.setStyle(tbl_style_base(pri_data))
    story.append(pri_tbl)
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph(
        "Note: All customer identifiers have been anonymised in this report. "
        "Data coverage period: 08-Apr-2024 to 07-May-2024. "
        "Anomaly detection uses threshold: transaction amount > 2x customer monthly average.",
        ParagraphStyle("Caveat", parent=styles["Normal"], fontSize=8.5,
                       textColor=colors.grey, italic=True, alignment=TA_LEFT)))

    story.append(PageBreak())

    # -------------------------------------------------------------------
    # Page 4 — Data Appendix
    # -------------------------------------------------------------------
    story.append(Paragraph("4. Data Appendix", section_style))
    story.append(HR)

    story.append(Paragraph("Record Counts by Source Table", sub_sec))
    rc_data = [
        ["Table", "Row Count", "Scope"],
        ["customers",           "3,225",  "Full customer master — primary analysis table"],
        ["transactions",        "50,000", "Full transaction history Jan-Dec 2024"],
        ["loan_emi",            "400",    "All active and closed loan records"],
        ["Churned customers",   "681",    "Subset: churn = 1 (21.12% of total)"],
        ["Period transactions",  "864",   "Transactions from churned customers, Apr-May 2024 window"],
    ]
    rc_tbl = Table(rc_data, colWidths=[4.5*cm, 2.5*cm, 10*cm])
    rc_tbl.setStyle(tbl_style_base(rc_data))
    story.append(rc_tbl)
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("Key Field Descriptions", sub_sec))
    fd_data = [
        ["Field",            "Description"],
        ["churn",            "1 = customer exited, 0 = retained. Target variable."],
        ["nps_score",        "Net Promoter Score on 0-10 scale. Risk floor: <= 3."],
        ["balance",          "Account balance in INR (Rs). Original USD * 83 conversion applied."],
        ["segment",          "Customer tier: Premium / Standard / Basic."],
        ["is_anomaly",       "1 = transaction flagged as spend spike (> 2x monthly avg)."],
        ["emi_status",       "Paid / Missed / Delayed. Missed + Delayed = stress indicator."],
        ["credit_score",     "Range 350-850. Used in segmentation risk analysis."],
        ["active_member",    "1 = active account, 0 = inactive. Inactivity is a churn signal."],
    ]
    fd_tbl = Table(fd_data, colWidths=[4.5*cm, 12.5*cm])
    fd_tbl.setStyle(tbl_style_base(fd_data))
    story.append(fd_tbl)
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("Methodology Notes", sub_sec))
    for note in [
        "Data source: data/banking_mock.db (SQLite) — read-only access via SQL Agent.",
        "Churn baseline: 21% (681 / 3,225). CRITICAL alert threshold: > 25%.",
        "Anomaly detection: transaction amount > 2x that customer's monthly average spend.",
        "Churn risk combo: NPS <= 3 AND missed EMI in the same calendar month.",
        "High-risk segment definition: Basic tier + credit_score < 500.",
        "Currency: all monetary values in INR (Rs). USD conversion rate applied during setup: 1 USD = Rs 83.",
        "NPS scale: 0-10 (not 0-100). Do not normalise to percentage.",
        "Report generated by BankSight AI Report Agent on 07-May-2026.",
    ]:
        story.append(Paragraph(u"• " + note, bullet_style))

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(
        "CONFIDENTIAL — BankSight AI Internal Report — Do not distribute externally",
        confidential_style))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"[PDF] Saved: {PDF_PATH}")


# ===========================================================================
# POWERBI CSV
# ===========================================================================
def build_csv():
    headers = [
        "report_date", "period_start", "period_end",
        "total_customers", "total_churned", "churn_rate_pct", "baseline_rate_pct",
        "avg_balance_churned", "avg_nps_churned", "avg_credit_score_churned",
        "premium_churn_rate", "standard_churn_rate", "basic_churn_rate",
        "mumbai_churn_rate", "delhi_churn_rate", "bengaluru_churn_rate",
        "pune_churn_rate", "hyderabad_churn_rate", "gurugram_churn_rate",
        "emi_stress_rate", "critical_anomalies", "warning_anomalies",
        "period_transactions_churned",
        "report_file_excel", "report_file_pdf",
    ]

    row = [
        "07-May-2026",
        "08-Apr-2024",
        "07-May-2024",
        3225,
        681,
        21.12,
        21.00,
        8551041.11,   # plain number, no Rs symbol
        3.16,
        639.88,
        25.32,
        20.65,
        15.15,
        22.45,
        19.78,
        21.17,
        21.32,
        21.39,
        20.61,
        31.00,
        5,
        5,
        864,
        "ChurnReport_2026-05-07_Apr-May-2024.xlsx",
        "ChurnReport_2026-05-07_Apr-May-2024.pdf",
    ]

    # Write UTF-8 BOM for PowerBI/Excel compatibility
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row)

    print(f"[CSV]  Saved: {CSV_PATH}")


# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    print("BankSight AI — Report Agent starting...")
    build_excel()
    build_pdf()
    build_csv()
    print("\nAll three reports generated successfully.")
    print(f"  Excel : {EXCEL_PATH}")
    print(f"  PDF   : {PDF_PATH}")
    print(f"  CSV   : {CSV_PATH}")
