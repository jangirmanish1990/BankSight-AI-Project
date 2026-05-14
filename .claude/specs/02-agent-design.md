# Spec 02 — Agent Design & Pipeline Architecture

**Project:** BankSight AI — Agentic Banking Analytics Assistant
**File:** `.claude/specs/02-agent-design.md`
**Purpose:** Defines agent responsibilities, input/output contracts,
pipeline flows, and communication rules between all agents.
**Read by:** Claude Code orchestrator before routing any user query

---

## Agent Inventory

| Agent File | Agent Name | Role | Position |
|---|---|---|---|
| `.claude/agents/banking-nl-sql.md` | `banking-nl-sql` | SQL Query Executor | 1st |
| `.claude/agents/sql-insight-analyzer.md` | `sql-insight-analyzer` | Insight Generator | 2nd |
| `.claude/agents/anomaly-detector.md` | `anomaly-detector` | Anomaly Detector | 2nd (parallel) |
| `.claude/agents/report-generator.md` | `report-generator` | Report Assembler | 3rd |

---

## Full Pipeline Architecture

```
User Query (natural language)
          │
          ▼
┌─────────────────────────────┐
│      Orchestrator           │
│   (Claude Code + CLAUDE.md) │
│                             │
│  Reads: CLAUDE.md           │
│         02-agent-design.md  │
│  Routes intent to agents    │
└──────────────┬──────────────┘
               │
               ▼
┌──────────────────────────────┐
│   banking-nl-sql             │  AGENT 1
│                              │
│   Input:  Natural language   │
│           query + time period│
│   Output: pandas DataFrame   │
│           + row count        │
│           + SQL query used   │
└──────┬───────────────────────┘
       │
       │ DataFrame passed to both agents simultaneously
       ├─────────────────────┐
       ▼                     ▼
┌─────────────┐    ┌──────────────────┐
│sql-insight  │    │anomaly-detector  │  AGENT 2 (parallel)
│-analyzer    │    │                  │
│             │    │                  │
│Input:       │    │Input:            │
│ DataFrame   │    │ DataFrame        │
│             │    │ + Analysis       │
│Output:      │    │   summary        │
│ Insight     │    │   (if available) │
│ summary     │    │                  │
│ Key metrics │    │Output:           │
│ dict        │    │ Anomaly flags    │
│             │    │ Severity list    │
└──────┬──────┘    └────────┬─────────┘
       │                    │
       └──────────┬──────────┘
                  │
                  │ All 3 outputs collected
                  ▼
┌─────────────────────────────────────┐
│          report-generator           │  AGENT 3
│                                     │
│  Input:  SQL DataFrame              │
│          Analysis summary           │
│          Anomaly flags list         │
│                                     │
│  Output: Excel (.xlsx) → reports/   │
│          PDF (.pdf)    → reports/   │
│          CSV (.csv)    → dashboard/ │
│          Google Drive shareable link│
└─────────────────────────────────────┘
```

---

## Agent 1 — banking-nl-sql

### Responsibility
Convert natural language queries to SQLite SQL and execute
against `data/banking_mock.db`. Acts as the sole gateway to
the database — no other agent queries the database directly.

### Input Contract
```
{
  "query":       string,   // natural language query from user
  "time_period": string,   // e.g. "May 2026", "Q1 2024", "last 30 days"
  "context":     string    // optional: "churn", "spend", "anomaly", "employee"
}
```

### Output Contract
```
{
  "dataframe":   DataFrame,  // pandas DataFrame with query results
  "sql_used":    string,     // exact SQL query executed
  "row_count":   int,        // number of rows returned
  "columns":     list,       // column names in DataFrame
  "status":      string      // "success" | "empty" | "error"
  "message":     string      // friendly message if status != success
}
```

### Rules
- SELECT only — reject any non-SELECT SQL before execution
- Validate table names against allowed list before executing
- Reject queries containing: DROP, DELETE, UPDATE, INSERT,
  ALTER, TRUNCATE
- Default row limit: 100 rows (override if user specifies)
- If 0 rows returned: set status = "empty", do NOT call
  Analysis or Anomaly agents
- Always log: query received, SQL generated, rows returned,
  time taken

### Allowed Tables
```
customers, transactions, loan_emi, employee_performance
```

---

## Agent 2a — sql-insight-analyzer

### Responsibility
Transform raw DataFrame from SQL Agent into human-readable
business insight summary. Never queries the database.

### Input Contract
```
{
  "dataframe":   DataFrame,  // from banking-nl-sql output
  "context":     string,     // "churn" | "spend" | "trend" | "employee"
  "time_period": string,     // same period as SQL Agent query
  "benchmarks": {
    "churn_baseline":  0.21, // 21% — flag if current exceeds 25%
    "nps_scale":       10,   // NPS is 0–10 not 0–100
    "currency":        "INR" // all amounts in INR (₹)
  }
}
```

### Output Contract
```
{
  "summary":      string,    // full narrative insight text
  "key_metrics": {
    "total_records":   int,
    "primary_kpi":     float, // e.g. churn_rate, avg_spend
    "secondary_kpis":  dict,  // additional metrics
    "status":          string // "critical"|"warning"|"normal"
  },
  "top_findings":  list,     // top 3–5 findings as strings
  "recommendations": list,   // 2–4 actionable recommendations
  "confidence":    string    // "high"|"medium"|"low"
}
```

### Rules
- Never fabricate numbers not present in the DataFrame
- Always compare churn rate against 21% baseline
- Display all monetary values in INR (₹) format
- Display NPS as X/10 format
- If DataFrame has 0 rows: return friendly "no data" message
- Pass output to both report-generator AND anomaly-detector

---

## Agent 2b — anomaly-detector

### Responsibility
Scan DataFrame for spend spikes, churn risk patterns, and
statistical outliers. Never queries the database directly.

### Input Contract
```
{
  "dataframe":        DataFrame, // from banking-nl-sql output
  "analysis_summary": dict,      // from sql-insight-analyzer
                                 // (optional — use if available)
  "thresholds": {
    "spend_spike":    "amount > 2x customer monthly average",
    "churn_risk":     "NPS <= 3 AND missed EMI same month",
    "mass_churn":     "3+ Premium customers churned same week",
    "inactivity":     "active_member=0 for 60+ days before churn",
    "high_risk_seg":  "Basic segment AND credit_score < 500",
    "churn_alert":    0.25        // flag if rate exceeds 25%
  }
}
```

### Output Contract
```
{
  "anomalies": [
    {
      "type":        string,  // "spend_spike"|"churn_risk"|"mass_churn"
      "severity":    string,  // "CRITICAL"|"WARNING"|"NORMAL"
      "entity":      string,  // customer_id or segment affected
      "description": string,  // human-readable explanation
      "deviation":   string,  // "X% above baseline" or "Xσ from mean"
      "action":      string   // recommended immediate action
    }
  ],
  "summary": {
    "total_scanned":   int,
    "critical_count":  int,
    "warning_count":   int,
    "methods_used":    list,  // ["z-score", "IQR", "threshold"]
    "confidence":      string
  }
}
```

### Fallback — Direct /anomaly Invocation
If Analysis Agent output is not available (user ran /anomaly
directly without /analyze first):
- Proceed with SQL DataFrame only
- Note in summary: "Analysis Agent context unavailable —
  confidence may be reduced"
- Still apply all threshold rules from Input Contract

---

## Agent 3 — report-generator

### Responsibility
Collect outputs from all 3 upstream agents and assemble
final deliverables in user-requested formats. Last agent
in every pipeline run.

### Input Contract
```
{
  "sql_output": {
    "dataframe":  DataFrame,
    "sql_used":   string,
    "row_count":  int
  },
  "analysis_output": {
    "summary":      string,
    "key_metrics":  dict,
    "top_findings": list
  },
  "anomaly_output": {
    "anomalies": list,
    "summary":   dict
  },
  "report_config": {
    "formats":      list,   // ["excel","pdf","csv"] — user chosen
    "time_period":  string,
    "generated_at": datetime
  }
}
```

### Output Contract
```
{
  "files_generated": [
    {
      "type":     string,  // "excel"|"pdf"|"csv"
      "path":     string,  // local file path
      "drive_url": string  // Google Drive shareable link
    }
  ],
  "summary": {
    "records_processed": int,
    "critical_anomalies": int,
    "data_coverage":      string,  // date range covered
    "generation_time":    string   // timestamp
  }
}
```

### File Naming Convention
```
Excel: reports/ChurnReport_[YYYY-MM-DD]_[PERIOD].xlsx
PDF:   reports/ChurnReport_[YYYY-MM-DD]_[PERIOD].pdf
CSV:   dashboard/PowerBI_Churn_[YYYY-MM-DD].csv
```

### Behaviour if Input Missing
```
SQL output missing    → STOP immediately, alert user
Analysis missing      → Generate with raw data only,
                        add disclaimer in report header
Anomaly missing       → Generate without risk section,
                        add disclaimer in report header
```

### Google Drive Auto-Upload
After local file save, upload to:
`BankSight AI/Reports/[YYYY-MM]/`
using `mcp__claude_ai_Google_Drive__create_file`
Return shareable link in chat response.

---

## Skill-to-Agent Routing Map

| Skill Invoked | Agents Called | Order |
|---|---|---|
| `/churn-report` | All 4 agents | SQL → Analysis + Anomaly → Report |
| `/analyze` | SQL + Analysis | SQL → Analysis |
| `/trend` | SQL + Analysis | SQL → Analysis (time-series query) |
| `/anomaly` | SQL + Anomaly | SQL → Anomaly |

---

## Agent Communication Rules

1. **SQL Agent is always first** — no agent queries the
   database directly except banking-nl-sql

2. **Analysis and Anomaly agents run in parallel** — both
   receive SQL output simultaneously for faster pipeline

3. **Report Agent is always last** — waits for both
   Analysis and Anomaly to complete before assembling

4. **No agent modifies the database** — all agents are
   strictly read-only consumers of banking_mock.db

5. **Empty DataFrame stops the pipeline** — if SQL Agent
   returns 0 rows, downstream agents are not called

6. **Context passes forward** — time_period and benchmarks
   are passed to every agent so outputs stay consistent

7. **All outputs are logged** — every agent logs: agent
   name, input received, output produced, time taken

---

## BankSight Global Benchmarks
(All agents must reference these values)

```
Churn baseline:       21% (681/3225) — alert if > 25%
NPS scale:            0–10 (not 0–100)
Currency:             INR (₹) only — never USD
Date format:          DD-MMM-YYYY (e.g. 07-May-2026)
Spend anomaly rule:   amount > 2× customer monthly average
Churn risk combo:     NPS ≤ 3 + missed EMI in same month
High risk segment:    Basic + credit_score < 500
Row limit per query:  100 (unless user specifies otherwise)
Report save path:     reports/ (Excel/PDF), dashboard/ (CSV)
Google Drive folder:  BankSight AI/Reports/[YYYY-MM]/
Dataset date range:   Jan 2024 – Dec 2024
```
