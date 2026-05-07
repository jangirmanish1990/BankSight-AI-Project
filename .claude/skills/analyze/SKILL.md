---
name: analyze
description: >
  Answers any freeform natural language banking data question by
  querying banking_mock.db and generating a human-readable insight
  summary. Use this skill whenever the user asks an ad-hoc question
  about banking data, customers, transactions, credit scores, balances,
  segments, or any data-driven question that does not specifically
  require a churn report, trend analysis, or anomaly detection.
  Also triggers for questions like: "show me", "how many", "what is",
  "give me", "find", "list", "compare", "breakdown", "summary of",
  "top", "bottom", "average", "total" — even if phrased casually.
  Always invoke this skill for any data question rather than guessing
  from general knowledge.
when_to_use: >
  Trigger when user asks any open-ended data question about customers,
  transactions, loans, employees, segments, cities, balances, credit
  scores, NPS, or any combination of these — without specifying churn,
  trend, or anomaly context explicitly.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep, TaskStop
---

# Analyze Skill

Answers any freeform natural language banking data question using
the SQL Agent → Analysis Agent pipeline.

---

## Step 0 — Understand the Query

Before calling any agent, confirm:

1. **What is the user asking for?**
   Parse the intent — is it a count, average, ranking, comparison,
   or breakdown?

2. **Which table(s) are involved?**
   ```
   customers           → demographics, churn, NPS, segment, city
   transactions        → spend, category, merchant, anomaly flag
   loan_emi            → loan type, EMI status, amounts
   employee_performance → scorecard, grades, targets, quality
   ```

3. **Is a time period specified?**
   If yes → pass to SQL Agent as filter.
   If no  → query full dataset (Jan 2024–Dec 2024).

4. **Is this actually a churn, trend, or anomaly question?**
   If yes → redirect to the appropriate skill:
   - Churn focus → `/churn-report`
   - Time pattern → `/trend`
   - Outlier focus → `/anomaly`

---

## Step 1 — SQL Agent

Call the SQL Agent (`banking-nl-sql`) with:

```
Query:   [user's natural language question]
Context: [table(s) identified in Step 0]
Period:  [time filter if specified, else full dataset]
Limit:   100 rows (unless user specifies otherwise)
```

**If SQL Agent returns 0 rows:**
→ Inform user: "No records found for your query.
  Please check filters or rephrase and try again."
→ Stop — do not call Analysis Agent.

---

## Step 2 — Analysis Agent

Pass the SQL Agent DataFrame to the Analysis Agent
(`sql-insight-analyzer`) with this context:

```
Answer this question: [user's original question]
Apply BankSight benchmarks:
- Churn baseline: 21% — flag if exceeded
- NPS scale: 0–10 (not 0–100)
- Currency: INR (₹) — never USD
- Date format: DD-MMM-YYYY
Focus: direct answer first, supporting data second
```

---

## Step 3 — Display in Chat

Show the response in this format:

```
## 📊 Analysis Result

### Answer
[Direct answer to the user's question — 1–3 sentences]

### Supporting Data
[Key numbers, table, or breakdown from the DataFrame]

### Insight
[1–2 sentence interpretation of what the data means]

### Data Source
Tables used: [list] | Records analysed: [count]
```

---

## Formatting Rules

- Currency: INR (₹) — e.g. ₹1,45,000 — never USD
- Dates: DD-MMM-YYYY — e.g. 07-May-2026
- NPS: X/10 format — never as percentage
- Never expose raw customer_id or names in output
- If result is a single number → display prominently
- If result is a list → show as table (max 20 rows in chat)
- If result is > 20 rows → show top 10 + offer to export

---

## Examples

```
User: "How many customers are in the Premium segment?"
→ SQL Agent: SELECT COUNT(*) FROM customers WHERE segment='Premium'
→ Analysis Agent: "1,659 customers are in the Premium segment,
  representing 51.5% of total customers."

User: "What is the average credit score by city?"
→ SQL Agent: SELECT city, AVG(credit_score) FROM customers
             GROUP BY city ORDER BY AVG(credit_score) DESC
→ Analysis Agent: Tabular breakdown with interpretation

User: "Show me top 5 merchants by transaction volume"
→ SQL Agent: SELECT merchant_name, COUNT(*), SUM(amount)
             FROM transactions GROUP BY merchant_name
             ORDER BY COUNT(*) DESC LIMIT 5
→ Analysis Agent: Ranked list with spend totals in INR
```

---

## Edge Cases

**Ambiguous question:**
→ Ask one clarifying question before querying.
→ Example: "Did you mean by number of customers or by balance?"

**Question spans multiple tables:**
→ SQL Agent uses JOIN on customer_id.
→ Always JOIN customers as the primary table.

**User asks for export:**
→ After displaying in chat, offer:
  "Would you like me to export this as Excel or CSV?"
→ If yes → call Report Agent for file generation only
   (skip PDF, generate Excel + CSV only).

**Question outside dataset scope:**
→ Inform user: "The dataset covers Jan 2024–Dec 2024
  with 3,225 customers and 50,000 transactions.
  Your question may be outside this scope."
