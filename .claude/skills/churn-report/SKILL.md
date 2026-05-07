---
name: churn-report
description: >
  Runs the full BankSight AI churn analysis pipeline end-to-end —
  SQL Agent → Analysis Agent → Anomaly Agent → Report Agent.
  Use this skill whenever the user mentions churn, churned customers,
  customer retention, attrition, churn rate, at-risk customers, churn
  analysis, or asks to identify customers who have left or are likely
  to leave — even if they don't explicitly say "churn report". Also
  triggers automatically when the user asks for a monthly review,
  customer health report, or retention summary. Always invoke this
  skill proactively for any churn-related query rather than answering
  from general knowledge.
when_to_use: >
  Trigger when user uses words like: churn, churned, attrition,
  retention, at-risk, customer loss, dropped customers, inactive
  customers, monthly review, customer health, NPS drop, or any
  combination of these with time periods (this month, last quarter,
  May 2026, last 30 days etc.)
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep, TaskStop
---

# Churn Report Skill

Runs the complete BankSight AI churn analysis pipeline and delivers
structured reports in the user's chosen format.

---

## Step 0 — Collect Required Inputs Before Starting

Before running the pipeline, confirm two things with the user:

### 1. Time Period (always required — no default)
Ask the user to specify the time period explicitly:
```
"Which time period should I analyse?
 e.g. May 2026 / Last 30 days / Q1 2026 / Jan–Mar 2026"
```
Do NOT assume current month. Do NOT proceed without a clear
time period from the user.

### 2. Output Format (user chooses every time)
Ask the user which outputs they want:
```
"Which outputs do you need?
 A) Excel (.xlsx) only
 B) PDF only
 C) CSV only (for Power BI refresh)
 D) Excel + PDF
 E) Excel + PDF + CSV (full suite)
 F) Just show insights in chat — no files"
```
Wait for the user's answer before proceeding to Step 1.

---

## Step 1 — SQL Agent

Call the SQL Agent (`banking-nl-sql`) with the following query
based on the user's specified time period:

```
Fetch all churned customers (churn = 1) for [TIME_PERIOD]
with these fields:
customer_id, credit_score, balance, estimated_salary,
nps_score, segment, city, tenure, products_number,
active_member, joining_date, account_type, kyc_status

Also fetch:
- Total customer count for the period
- Total churned count
- Churn rate (churned / total * 100)
- Average balance of churned customers
- Average NPS score of churned customers
- Churn breakdown by segment (Premium / Standard / Basic)
- Churn breakdown by city
- Top 10 churned customers ranked by balance DESC
```

**Pass the returned DataFrame to Step 2 and Step 3 simultaneously.**

---

## Step 2 — Analysis Agent

Pass the SQL Agent DataFrame to the Analysis Agent
(`sql-insight-analyzer`) with this context:

```
Analyse churn patterns for [TIME_PERIOD].
Baseline churn rate is 21% (681/3225 customers).
Flag as critical if current rate exceeds 25%.
NPS scale is 0–10 (not 0–100).
All monetary values are in INR (₹).
Focus on: segment performance, city-wise patterns,
tenure vs churn correlation, NPS vs churn correlation.
```

Capture the full insight summary output for Step 4.

---

## Step 3 — Anomaly Agent

Pass the SQL Agent DataFrame to the Anomaly Agent
(`anomaly-detector`) with this context:

```
Scan for churn anomalies in [TIME_PERIOD] data.
Apply BankSight thresholds:
- Churn risk combo: NPS ≤ 3 + missed EMI in same month
- High risk segment: Basic + credit_score < 500
- Mass churn alert: 3+ Premium customers churned in same week
- Inactivity flag: active_member = 0 for 60+ days before churn
Flag severity as: CRITICAL / WARNING / NORMAL
```

Capture the anomaly flags output for Step 4.

**Note:** Steps 2 and 3 can run in parallel — both only need
the SQL Agent DataFrame as input.

---

## Step 4 — Report Agent

Once both Analysis Agent and Anomaly Agent have completed,
pass ALL THREE outputs to the Report Agent (`report-generator`):

```
Inputs:
- SQL Agent DataFrame (raw data)
- Analysis Agent insight summary
- Anomaly Agent flagged list

Generate outputs as per user's choice from Step 0:
- Excel  → reports/ChurnReport_[YYYY-MM-DD]_[PERIOD].xlsx
- PDF    → reports/ChurnReport_[YYYY-MM-DD]_[PERIOD].pdf
- CSV    → dashboard/PowerBI_Churn_[YYYY-MM-DD].csv

Excel structure (if requested):
  Sheet 1 — Executive Summary (KPIs + traffic light status)
  Sheet 2 — Raw Churn Data (full customer table)
  Sheet 3 — Analysis Results (trends, segment breakdown)
  Sheet 4 — Anomaly Flags (🔴 Critical / 🟡 Warning colour coded)
  Sheet 5 — Methodology (data source, date range, run timestamp)

PDF structure (if requested):
  Page 1 — Executive Summary (key findings, churn rate vs baseline)
  Page 2 — Analysis Insights (segment, city, NPS, tenure patterns)
  Page 3 — Anomaly Alerts (ranked by severity with actions)
  Page 4 — Data Appendix (row counts, field descriptions)
```

After local file save, auto-upload to Google Drive folder:
`BankSight AI/Reports/[YYYY-MM]/`
using Google Drive MCP tools and return a shareable link.

---

## Step 5 — Display in Chat UI

After all outputs are generated, display this summary in the
Streamlit chat interface:

```
## 📊 Churn Report — [TIME_PERIOD]

### Key Metrics
| Metric              | Value         | Status  |
|---------------------|---------------|---------|
| Total Customers     | X             |         |
| Churned Customers   | X             |         |
| Churn Rate          | X%            | 🔴/🟢   |
| Baseline Rate       | 21%           |         |
| Avg NPS (churned)   | X / 10        |         |
| Avg Balance (churned)| ₹X           |         |

### Top 3 Findings
1. [From Analysis Agent]
2. [From Analysis Agent]
3. [From Analysis Agent]

### 🔴 Critical Anomalies
[From Anomaly Agent — list CRITICAL items only]

### 📁 Generated Files
[Show download buttons only for formats user requested]
[Show Google Drive shareable link]
```

---

## Formatting Rules (always apply)

- Currency: INR (₹) format — e.g. ₹1,45,000 — never USD
- Dates: DD-MMM-YYYY format — e.g. 07-May-2026
- NPS: displayed as X/10 — never as percentage
- Churn rate: show as % with 2 decimal places — e.g. 21.13%
- Churn status indicator:
  - 🟢 Green  → churn rate ≤ 21% (at or below baseline)
  - 🟡 Yellow → churn rate 21%–25% (elevated, monitor closely)
  - 🔴 Red    → churn rate > 25% (critical — flag immediately)
- Never expose raw customer_id or personal names in chat display
- Always include report generation timestamp in all file outputs

---

## Edge Cases

**If SQL Agent returns 0 rows for the period:**
→ Inform user: "No churned customers found for [TIME_PERIOD].
  The dataset covers Jan 2024–Dec 2024. Please verify your
  date range and try again."
→ Do NOT proceed to Analysis or Anomaly agents.

**If user requests a period outside Jan 2024–Dec 2024:**
→ Warn user: "The dataset covers Jan 2024–Dec 2024 only.
  Results for [TIME_PERIOD] may be incomplete or unavailable."
→ Ask if they want to proceed anyway.

**If Analysis Agent output is unavailable:**
→ Generate report with raw data only.
→ Add disclaimer note in report header: "Insight summary
  unavailable — raw data only."

**If Anomaly Agent output is unavailable:**
→ Generate report without risk/anomaly section.
→ Add disclaimer: "Anomaly detection was not run for
  this report."

**If user chooses "Just show insights in chat" (Option F):**
→ Skip Report Agent entirely.
→ Display Step 5 chat summary only.
→ Offer to generate files at end: "Would you like me to
  export this as Excel, PDF, or CSV?"
