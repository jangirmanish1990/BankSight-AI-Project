---
name: anomaly
description: >
  Detects unusual patterns, outliers, spend spikes, churn risk
  combinations, and statistical anomalies in banking data.
  Use this skill whenever the user asks about anomalies, outliers,
  unusual activity, suspicious transactions, flagged customers,
  at-risk customers, spend spikes, EMI defaults, churn risk combos,
  or anything that deviates from expected banking behaviour.
  Trigger words include: anomaly, anomalies, unusual, outlier,
  spike, flag, suspicious, at-risk, risk, alert, deviate, abnormal,
  irregular, unexpected, detect, find problems, what looks wrong,
  anything off, red flags. Also triggers automatically when the
  Analysis Agent or SQL Agent output contains values that exceed
  BankSight thresholds (churn > 25%, NPS ≤ 3, EMI stress > 30%).
  Always invoke this skill for anomaly/risk questions rather than
  using /analyze.
when_to_use: >
  Trigger when user asks about anomalies, unusual patterns, outliers,
  flagged transactions, at-risk customers, spend spikes, or any
  risk-detection question. Also auto-trigger when upstream agent
  outputs breach BankSight thresholds.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep, TaskStop
---

# Anomaly Skill

Detects spend spikes, churn risk patterns, and statistical outliers
using the SQL Agent → Anomaly Agent pipeline.

---

## Step 0 — Collect Inputs

Before calling any agent, confirm two things:

### 1. What type of anomaly to scan for?
If not specified, scan ALL types (default):
```
"Which anomaly types should I scan for?
 A) Spend spikes (transactions > 2x customer monthly avg)
 B) Churn risk combo (NPS ≤ 3 + missed EMI same month)
 C) High risk segment (Basic + credit_score < 500)
 D) Inactivity flag (inactive 60+ days before churn)
 E) Mass churn alert (3+ Premium customers churned same week)
 F) All of the above (recommended)"
```

### 2. What time period?
```
"Which period should I scan?
 Dataset covers Jan 2024–Dec 2024.
 e.g. May 2024 / Q1 2024 / Full year"
```

If user types `/anomaly` with no arguments → scan ALL types
for the FULL dataset. Do not ask — proceed immediately.

---

## Step 1 — SQL Agent

Call the SQL Agent (`banking-nl-sql`) with queries
targeting anomaly detection:

**Query set based on anomaly types selected:**

```sql
-- Spend spikes: transactions > 2x customer monthly average
WITH monthly_avg AS (
  SELECT customer_id,
         strftime('%Y-%m', transaction_date) AS month,
         AVG(amount) AS avg_spend
  FROM transactions
  GROUP BY customer_id, month
)
SELECT t.customer_id, t.transaction_id, t.amount,
       t.transaction_date, t.category, t.merchant_name,
       m.avg_spend,
       ROUND(t.amount / m.avg_spend, 2) AS spike_ratio
FROM transactions t
JOIN monthly_avg m
  ON t.customer_id = m.customer_id
  AND strftime('%Y-%m', t.transaction_date) = m.month
WHERE t.amount > (2 * m.avg_spend)
ORDER BY spike_ratio DESC
LIMIT 100

-- Churn risk combo: NPS ≤ 3 + Missed EMI
SELECT c.customer_id, c.nps_score, c.segment,
       c.city, c.credit_score, c.balance, c.churn,
       l.emi_status, l.loan_type, l.emi_amount
FROM customers c
JOIN loan_emi l ON c.customer_id = l.customer_id
WHERE c.nps_score <= 3
  AND l.emi_status = 'Missed'
ORDER BY c.balance DESC

-- High risk segment
SELECT customer_id, segment, credit_score,
       nps_score, balance, churn, active_member
FROM customers
WHERE segment = 'Basic'
  AND credit_score < 500
ORDER BY credit_score ASC

-- Inactivity flag: inactive customers who churned
SELECT customer_id, active_member, churn,
       tenure, nps_score, balance, segment, city
FROM customers
WHERE active_member = 0
  AND churn = 1
ORDER BY balance DESC
LIMIT 50
```

Pass all relevant query results as separate DataFrames
to the Anomaly Agent.

---

## Step 2 — Anomaly Agent

Pass SQL Agent output to Anomaly Agent (`anomaly-detector`)
with full BankSight threshold context:

```
Scan for anomalies using these BankSight thresholds:
- Spend spike:      amount > 2× customer monthly average
- Churn risk combo: NPS ≤ 3 AND missed EMI same month
- High risk:        Basic segment AND credit_score < 500
- Inactivity:       active_member = 0 for 60+ days before churn
- Mass churn alert: 3+ Premium customers churned same week
- Churn rate alert: flag if monthly rate exceeds 25%
- EMI stress:       flag if Missed + Delayed > 30%

Severity classification:
  CRITICAL → immediate action required
  WARNING  → monitor closely within 48h
  NORMAL   → within expected parameters

Currency: INR (₹) | NPS scale: 0–10 | Date: DD-MMM-YYYY
```

**Fallback if Analysis Agent output is unavailable:**
→ Proceed with SQL output only.
→ Add note: "Running without Analysis Agent context —
  confidence may be reduced."

---

## Step 3 — Display in Chat

Show anomaly results in this format:

```
## 🚨 Anomaly Detection Report — [PERIOD]

### Detection Summary
Total records scanned:  X
🔴 Critical anomalies:  X  (immediate action required)
🟡 Warning anomalies:   X  (monitor within 48h)
🟢 Normal:              X  (within expected range)

### 🔴 Critical Anomalies
| ID      | Description              | Severity | Action  |
|---------|--------------------------|----------|---------|
| ANO-001 | [description]            | CRITICAL | [action]|

### 🟡 Warning Anomalies
| ID      | Description              | Severity | Action  |
|---------|--------------------------|----------|---------|
| ANO-006 | [description]            | WARNING  | [action]|

### 🟢 Normal Range
[Brief confirmation of metrics within expected parameters]

### Detection Methods Used
[z-score / IQR / threshold-based — list which applied]

### Confidence Level
[High / Medium / Low] — [brief explanation]
```

---

## Formatting Rules

- Currency: INR (₹) — e.g. ₹1,45,000 — never USD
- Dates: DD-MMM-YYYY — e.g. 07-May-2026
- NPS: X/10 format — never as percentage
- Never expose raw customer_id or names in output
- Always show recommended action for every CRITICAL item
- Always state which detection method was used
- Distinguish between data quality issues and true anomalies

---

## BankSight Anomaly Thresholds Reference

```
Spend spike:        amount > 2× customer monthly average
Churn risk combo:   NPS ≤ 3 + missed EMI in same month
Mass churn alert:   3+ Premium customers churned same week
Inactivity spike:   inactive 60+ days then large transaction
High risk segment:  Basic segment + credit_score < 500
Churn rate alert:   monthly rate > 25% (baseline is 21%)
EMI stress alert:   Missed + Delayed EMIs > 30% of total
```

---

## Edge Cases

**No anomalies detected:**
→ Report: "No anomalies detected for [PERIOD].
  All metrics within BankSight expected ranges.
  Churn rate, NPS, EMI stress all within baseline."

**User runs /anomaly with no arguments:**
→ Scan ALL anomaly types for FULL dataset.
→ Do NOT ask for input — proceed immediately.

**Analysis Agent output available from prior run:**
→ Use it as additional context for risk prioritisation.
→ Correlate anomaly flags with insight summary findings.

**User wants to export anomaly report:**
→ After chat display, offer:
  "Would you like a full anomaly report in Excel + PDF?"
→ If yes → call Report Agent with anomaly output only
  (Sheet 4 — Anomaly Flags + priority intervention list).

**Data quality issue found (nulls, impossible values):**
→ Flag separately BEFORE anomaly analysis:
  "Data quality issue detected: [description].
   This may affect anomaly accuracy. Proceeding with
   available data."
