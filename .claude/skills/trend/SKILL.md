---
name: trend
description: >
  Analyses time-based patterns, movements, and changes across any
  banking metric over a specified period. Use this skill whenever
  the user asks about trends, patterns over time, monthly changes,
  growth, decline, week-over-week, month-over-month, quarterly
  comparisons, historical patterns, seasonality, or any question
  involving how a metric has changed over time. Trigger words
  include: trend, over time, by month, monthly, weekly, quarterly,
  last N months, historical, pattern, change, growth, decline,
  increase, decrease, spike, dip, compare periods, how has X changed.
  Always invoke this skill for time-series questions rather than
  using /analyze.
when_to_use: >
  Trigger when user asks how something has changed over time,
  requests a monthly/weekly/quarterly breakdown, uses words like
  trend, pattern, growth, decline, over time, or asks to compare
  two time periods for any banking metric.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep, TaskStop
---

# Trend Skill

Analyses time-based patterns across banking metrics using the
SQL Agent → Analysis Agent pipeline with time-series focus.

---

## Step 0 — Collect Required Inputs

Before calling any agent, confirm:

### 1. What metric to trend?
If not specified, ask:
```
"Which metric would you like to see the trend for?
 A) Credit card spend (by month/category)
 B) Churn rate (monthly)
 C) Transaction volume (count or amount)
 D) NPS score (average over time)
 E) EMI stress rate (Missed + Delayed by month)
 F) Employee performance (by month)
 G) Custom — describe what you want"
```

### 2. What time granularity?
```
"What time breakdown do you want?
 A) Monthly (recommended — full year view)
 B) Quarterly (Q1/Q2/Q3/Q4 2024)
 C) Weekly"
```

### 3. What time period?
```
"Which period? Dataset covers Jan 2024–Dec 2024.
 e.g. Full year / Jan–Jun 2024 / Q1 2024"
```

Do NOT proceed without at least a metric and granularity confirmed.

---

## Step 1 — SQL Agent

Call the SQL Agent (`banking-nl-sql`) with a time-series query:

**Template queries by metric:**

```sql
-- Spend trend by month
SELECT strftime('%Y-%m', transaction_date) AS month,
       SUM(amount)                         AS total_spend,
       COUNT(*)                            AS txn_count,
       AVG(amount)                         AS avg_spend
FROM transactions
GROUP BY month
ORDER BY month

-- Churn trend by month (joining_date as proxy)
SELECT strftime('%Y-%m', joining_date) AS cohort_month,
       COUNT(*)                         AS total,
       SUM(churn)                       AS churned,
       ROUND(AVG(churn)*100, 2)         AS churn_rate_pct
FROM customers
GROUP BY cohort_month
ORDER BY cohort_month

-- NPS trend by segment over time
SELECT segment,
       strftime('%Y-%m', joining_date) AS month,
       ROUND(AVG(nps_score), 2)        AS avg_nps
FROM customers
GROUP BY segment, month
ORDER BY month

-- EMI stress trend by month
SELECT strftime('%Y-%m', emi_due_date) AS month,
       COUNT(*)                         AS total_emis,
       SUM(CASE WHEN emi_status='Missed'  THEN 1 ELSE 0 END) AS missed,
       SUM(CASE WHEN emi_status='Delayed' THEN 1 ELSE 0 END) AS delayed
FROM loan_emi
GROUP BY month
ORDER BY month
```

Pass time granularity filter from Step 0 to SQL Agent.

---

## Step 2 — Analysis Agent

Pass the time-series DataFrame to Analysis Agent
(`sql-insight-analyzer`) with this context:

```
Analyse the TIME-SERIES pattern in this data.
Metric: [metric from Step 0]
Granularity: [monthly/quarterly/weekly]
Period: [period from Step 0]

Focus on:
1. Overall direction (upward/downward/stable)
2. Highest and lowest points in the period
3. Month-over-month or quarter-over-quarter % change
4. Any spikes or dips worth flagging
5. Comparison against BankSight benchmarks:
   - Churn baseline: 21%
   - NPS risk floor: 3.0/10
   - EMI stress threshold: 30%
   - Currency: INR (₹)
   - Date format: DD-MMM-YYYY
```

---

## Step 3 — Display in Chat

Show the trend response in this format:

```
## 📈 Trend Analysis — [METRIC] | [PERIOD]

### Direction
[One sentence: upward / downward / stable / volatile]

### Key Data Points
| Period   | Value      | MoM Change |
|----------|------------|------------|
| Jan 2024 | ₹X         | —          |
| Feb 2024 | ₹X         | +X%        |
| ...      | ...        | ...        |

### Highest Point
[Period]: [Value] — [brief reason if identifiable]

### Lowest Point
[Period]: [Value] — [brief reason if identifiable]

### Insight
[2–3 sentence interpretation of the trend]

### Benchmark Comparison
[How does this trend compare to BankSight baselines?]
```

---

## Formatting Rules

- Currency: INR (₹) — e.g. ₹1,45,000 — never USD
- Dates: DD-MMM-YYYY — e.g. Jan-2024, Feb-2024
- NPS: X/10 format — never as percentage
- MoM change: show as % with + or − prefix
- Highlight 🔴 if metric crosses a critical threshold
- Highlight 🟢 if metric is improving vs baseline
- Never expose raw customer_id or names in output

---

## Edge Cases

**User asks for trend without specifying metric:**
→ Ask Step 0 question before proceeding.

**Only 1–2 data points returned:**
→ Inform user: "Not enough data points for a meaningful
  trend. Try a wider time period or different granularity."

**Flat trend (no change):**
→ Report as "Stable — no significant movement detected
  across the period."

**User wants to export trend data:**
→ After chat display, offer:
  "Would you like this exported as Excel with a chart?"
→ If yes → call Report Agent for Excel only
  (Sheet: Raw trend data + Sheet: MoM change table).

**User asks to compare two specific periods:**
→ SQL Agent runs two separate queries and returns both.
→ Analysis Agent compares them side by side.
→ Example: "Compare Q1 2024 vs Q2 2024 spend"
