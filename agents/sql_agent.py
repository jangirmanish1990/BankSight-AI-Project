"""
BankSight AI — SQL Agent
=========================
Converts natural language queries to SQLite SQL and executes
them against data/banking_mock.db.

Called by:
  - Claude Code agent: .claude/agents/banking-nl-sql.md
  - Streamlit UI:      app.py
  - Other agents:      analysis_agent.py, anomaly_agent.py

Spec reference: .claude/specs/02-agent-design.md
"""

import os
import re
import time
import sqlite3
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Support both local .env and Streamlit Cloud secrets
import streamlit as st
try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass  # Running locally — use .env instead

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "banking_mock.db")

ALLOWED_TABLES    = {"customers", "transactions", "loan_emi", "employee_performance"}
BLOCKED_KEYWORDS  = {"drop", "delete", "update", "insert", "alter", "truncate",
                     "create", "replace", "attach", "detach"}
DEFAULT_ROW_LIMIT = 100

# ---------------------------------------------------------------------------
# Schema context — fed to Claude for accurate SQL generation
# ---------------------------------------------------------------------------
SCHEMA_CONTEXT = """
Database: data/banking_mock.db (SQLite)
Currency: All monetary values in INR (₹). Never display as USD.
Date format: YYYY-MM-DD in DB, display as DD-MMM-YYYY.
NPS scale: 0-10 (NOT 0-100).
Churn baseline: 21% (681/3225). Alert if > 25%.

TABLES:

customers (3,225 rows)
  customer_id       INTEGER  PRIMARY KEY
  credit_score      INTEGER  (350-850)
  country           TEXT     (India)
  gender            TEXT     (Male/Female/Other)
  age               INTEGER  (18-88)
  tenure            INTEGER  (years with bank)
  balance           REAL     (INR)
  products_number   INTEGER
  credit_card       INTEGER  (1=yes, 0=no)
  active_member     INTEGER  (1=active, 0=inactive)
  estimated_salary  REAL     (INR)
  churn             INTEGER  (1=churned, 0=retained) ← TARGET
  city              TEXT     (Delhi/Mumbai/Bengaluru/Gurugram/Pune/Hyderabad/Chennai/Kolkata)
  nps_score         INTEGER  (0-10)
  segment           TEXT     (Premium/Standard/Basic)
  joining_date      TEXT     (DD-MM-YYYY)
  account_type      TEXT     (Savings/Current/Salary)
  kyc_status        TEXT     (Verified/Pending)

transactions (~50,000 rows)
  transaction_id    TEXT     PRIMARY KEY
  customer_id       INTEGER  FK → customers.customer_id
  transaction_date  TEXT     (YYYY-MM-DD, Jan-Dec 2024)
  amount            REAL     (INR ₹500-₹1,50,000)
  category          TEXT     (Food/Travel/Shopping/Utilities/Healthcare/Entertainment/EMI)
  payment_mode      TEXT     (Credit Card/Debit Card/UPI/NetBanking)
  merchant_name     TEXT
  status            TEXT     (Success/Failed/Reversed)
  is_anomaly        INTEGER  (1=spend spike >2x monthly avg, 0=normal)

loan_emi (400 rows)
  loan_id           TEXT     PRIMARY KEY
  customer_id       INTEGER  FK → customers.customer_id
  loan_type         TEXT     (Home/Personal/Auto/Credit Card)
  loan_amount       REAL     (INR)
  emi_amount        REAL     (INR)
  emi_due_date      TEXT     (day of month)
  emi_status        TEXT     (Paid/Missed/Delayed)
  interest_rate     REAL     (7.5%-18%)
  loan_start_date   TEXT     (YYYY-MM-DD)
  loan_end_date     TEXT     (YYYY-MM-DD)

employee_performance (600 rows = 50 employees × 12 months)
  employee_id       TEXT     PRIMARY KEY
  name              TEXT
  department        TEXT     (Loans/Cards/Support/Risk/Operations)
  region            TEXT     (North/South/East/West)
  target_amount     REAL     (INR)
  achieved_amount   REAL     (INR)
  quality_score     INTEGER  (0-100)
  customer_complaints INTEGER (0-20)
  month             TEXT     (Jan-Dec)
  year              INTEGER  (2024)
  performance_grade TEXT     (A/B/C/D)

IMPORTANT RULES:
- Always use SELECT only — never INSERT, UPDATE, DELETE, DROP
- JOIN always on customer_id when crossing tables
- Default LIMIT: 100 rows unless user specifies otherwise
- Monetary columns: balance, estimated_salary, loan_amount, emi_amount, amount, target_amount, achieved_amount
- Churn risk combo: nps_score <= 3 AND emi_status = 'Missed' (same customer)
- High risk: segment = 'Basic' AND credit_score < 500
"""

SQL_SYSTEM_PROMPT = f"""You are an expert SQLite SQL writer for BankSight AI banking analytics.

{SCHEMA_CONTEXT}

Your job:
1. Read the user's natural language question carefully
2. Write a valid SQLite SELECT query that answers it
3. Return ONLY the SQL query — no explanation, no markdown, no backticks
4. Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE
5. Always add LIMIT unless user asks for all rows
6. Use correct column names exactly as defined in the schema above
"""


# ---------------------------------------------------------------------------
# SQL validation — safety firewall
# ---------------------------------------------------------------------------
def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Rejects any non-SELECT or dangerous SQL before execution.
    """
    sql_clean = sql.strip().lower()

    # Must start with SELECT
    if not sql_clean.startswith("select"):
        return False, "Query must start with SELECT. Non-SELECT statements are not allowed."

    # Block dangerous keywords
    for kw in BLOCKED_KEYWORDS:
        pattern = r"\b" + kw + r"\b"
        if re.search(pattern, sql_clean):
            return False, f"Query contains blocked keyword: '{kw.upper()}'. Only SELECT is allowed."

    # Check all referenced tables are in allowed list
    referenced = set(re.findall(r"\bfrom\s+(\w+)|\bjoin\s+(\w+)", sql_clean))
    flat_referenced = {t for pair in referenced for t in pair if t}
    invalid_tables = flat_referenced - ALLOWED_TABLES
    if invalid_tables:
        return False, (
            f"Query references unknown table(s): {invalid_tables}. "
            f"Allowed tables: {ALLOWED_TABLES}"
        )

    return True, ""


# ---------------------------------------------------------------------------
# Natural language → SQL via Claude API
# ---------------------------------------------------------------------------
def generate_sql(query: str, filters: dict = None) -> str:
    """
    Calls OpenAI API to convert natural language to SQL.
    filters: optional dict with keys like segment, city, period_start, period_end
    """
    client = OpenAI()

    # Build filter context if provided
    filter_context = ""
    if filters:
        parts = []
        if filters.get("segment"):
            parts.append(f"Filter by segment = '{filters['segment']}'")
        if filters.get("city"):
            parts.append(f"Filter by city = '{filters['city']}'")
        if filters.get("period_start") and filters.get("period_end"):
            parts.append(
                f"Filter transactions between '{filters['period_start']}' "
                f"and '{filters['period_end']}'"
            )
        if filters.get("row_limit"):
            parts.append(f"Limit results to {filters['row_limit']} rows")
        if parts:
            filter_context = "\n\nApply these filters:\n" + "\n".join(
                f"- {p}" for p in parts)

    user_message = f"{query}{filter_context}"

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1000,
        messages=[
            {"role": "system", "content": SQL_SYSTEM_PROMPT},
            {"role": "user",   "content": user_message}
        ]
    )

    sql = response.choices[0].message.content.strip()

    # Strip markdown code fences if model added them
    sql = re.sub(r"```sql|```", "", sql).strip()

    return sql


# ---------------------------------------------------------------------------
# Execute SQL against banking_mock.db
# ---------------------------------------------------------------------------
def execute_sql(sql: str) -> tuple[pd.DataFrame, str]:
    """
    Executes validated SQL against banking_mock.db.
    Returns (DataFrame, error_message).
    Empty DataFrame with error_message = "" means 0 rows found.
    """
    if not os.path.exists(DB_PATH):
        return pd.DataFrame(), (
            f"Database not found at {DB_PATH}. "
            "Please run data/setup_db.py first."
        )

    try:
        conn = sqlite3.connect(DB_PATH)
        df   = pd.read_sql_query(sql, conn)
        conn.close()
        return df, ""
    except Exception as e:
        return pd.DataFrame(), f"SQL execution error: {str(e)}"


# ---------------------------------------------------------------------------
# Main agent function — called by app.py and other agents
# ---------------------------------------------------------------------------
def run_sql_agent(
    query: str,
    filters: dict = None,
    verbose: bool = True
) -> dict:
    """
    Full SQL Agent pipeline:
    1. Generate SQL from natural language
    2. Validate SQL (safety firewall)
    3. Execute against banking_mock.db
    4. Return structured output

    Args:
        query:   Natural language question
        filters: Optional dict with segment, city, period_start,
                 period_end, row_limit
        verbose: Print progress logs

    Returns dict with keys:
        dataframe   — pandas DataFrame (empty if 0 rows or error)
        sql_used    — exact SQL that was executed
        row_count   — number of rows returned
        columns     — list of column names
        status      — "success" | "empty" | "error"
        message     — friendly message for display
        time_taken  — seconds elapsed
    """
    start_time = time.time()

    if verbose:
        print(f"\n[SQL Agent] Query: {query}")
        if filters:
            print(f"[SQL Agent] Filters: {filters}")

    # Step 1 — Generate SQL
    try:
        sql = generate_sql(query, filters)
        if verbose:
            print(f"[SQL Agent] Generated SQL:\n{sql}")
    except Exception as e:
        return {
            "dataframe":  pd.DataFrame(),
            "sql_used":   "",
            "row_count":  0,
            "columns":    [],
            "status":     "error",
            "message":    f"Failed to generate SQL: {str(e)}",
            "time_taken": round(time.time() - start_time, 2),
        }

    # Step 2 — Validate SQL
    is_valid, error_msg = validate_sql(sql)
    if not is_valid:
        if verbose:
            print(f"[SQL Agent] Validation failed: {error_msg}")
        return {
            "dataframe":  pd.DataFrame(),
            "sql_used":   sql,
            "row_count":  0,
            "columns":    [],
            "status":     "error",
            "message":    f"SQL validation failed: {error_msg}",
            "time_taken": round(time.time() - start_time, 2),
        }

    # Step 3 — Execute SQL
    df, exec_error = execute_sql(sql)
    time_taken = round(time.time() - start_time, 2)

    if exec_error:
        if verbose:
            print(f"[SQL Agent] Execution error: {exec_error}")
        return {
            "dataframe":  pd.DataFrame(),
            "sql_used":   sql,
            "row_count":  0,
            "columns":    [],
            "status":     "error",
            "message":    exec_error,
            "time_taken": time_taken,
        }

    if len(df) == 0:
        if verbose:
            print("[SQL Agent] Query returned 0 rows")
        return {
            "dataframe":  df,
            "sql_used":   sql,
            "row_count":  0,
            "columns":    list(df.columns),
            "status":     "empty",
            "message":    (
                "No records found for your query. "
                "The dataset covers Jan 2024–Dec 2024. "
                "Please check your filters and try again."
            ),
            "time_taken": time_taken,
        }

    if verbose:
        print(f"[SQL Agent] Returned {len(df):,} rows in {time_taken}s ✅")

    return {
        "dataframe":  df,
        "sql_used":   sql,
        "row_count":  len(df),
        "columns":    list(df.columns),
        "status":     "success",
        "message":    f"Query returned {len(df):,} records successfully.",
        "time_taken": time_taken,
    }


# ---------------------------------------------------------------------------
# CLI — for direct testing from terminal
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_queries = [
        "Show top 10 churned customers by balance",
        "What is the churn rate by segment?",
        "Show me customers with NPS score below 3 who have missed EMI",
    ]

    for q in test_queries:
        print("\n" + "=" * 60)
        result = run_sql_agent(q)
        print(f"Status:    {result['status']}")
        print(f"Rows:      {result['row_count']}")
        print(f"Time:      {result['time_taken']}s")
        if result["status"] == "success":
            print(result["dataframe"].head(3).to_string())
