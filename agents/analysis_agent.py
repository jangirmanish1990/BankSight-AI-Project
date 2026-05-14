"""
BankSight AI — Analysis Agent
==============================
Receives raw DataFrame from SQL Agent and generates
human-readable business insight summaries.

Called by:
  - Claude Code agent: .claude/agents/sql-insight-analyzer.md
  - Streamlit UI:      app.py
  - Report Agent:      report_agent.py

Spec reference: .claude/specs/02-agent-design.md
"""

import os
import time
import json
import anthropic
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# BankSight benchmarks — all agents must reference these
# ---------------------------------------------------------------------------
CHURN_BASELINE   = 21.0   # % — alert if current exceeds 25%
CHURN_ALERT      = 25.0   # % — CRITICAL threshold
NPS_RISK_FLOOR   = 3      # NPS <= 3 = churn risk signal
NPS_SCALE        = 10     # NPS is 0-10, NOT 0-100
CURRENCY         = "INR"  # never USD

ANALYSIS_SYSTEM_PROMPT = """You are an expert Banking Data Analyst for BankSight AI.

You receive structured query results from the SQL Agent and generate
clear, concise, actionable business insight summaries.

CRITICAL RULES:
- All monetary values are in INR (₹) — NEVER display as USD
- NPS is on a 0-10 scale — NEVER treat as percentage
- Churn baseline is 21% (681/3225 customers)
- Flag as CRITICAL if churn rate exceeds 25%
- Flag as WARNING if churn rate is between 21% and 25%
- NPS risk floor: customers with NPS <= 3 are high churn risk
- Churn risk combo: NPS <= 3 AND missed EMI = highest priority
- High risk segment: Basic segment AND credit_score < 500
- Date format: DD-MMM-YYYY (e.g. 07-May-2026)
- Dataset covers Jan 2024 to Dec 2024 only

OUTPUT FORMAT — respond with valid JSON only, no markdown:
{
  "summary": "2-3 sentence executive summary of what the data shows",
  "key_metrics": {
    "primary_kpi_label": "label of the most important metric",
    "primary_kpi_value": "value of that metric",
    "status": "CRITICAL or WARNING or NORMAL",
    "additional_metrics": {"metric_name": "value", ...}
  },
  "top_findings": [
    "Finding 1 — specific, data-backed insight",
    "Finding 2",
    "Finding 3"
  ],
  "segment_highlights": {
    "best_performer": "description",
    "worst_performer": "description"
  },
  "recommendations": [
    "Specific actionable recommendation 1",
    "Specific actionable recommendation 2"
  ],
  "confidence": "high or medium or low",
  "confidence_reason": "brief explanation"
}
"""


# ---------------------------------------------------------------------------
# Main agent function
# ---------------------------------------------------------------------------
def run_analysis_agent(
    sql_output: dict,
    context: str = "general",
    filters: dict = None,
    verbose: bool = True
) -> dict:
    """
    Analysis Agent pipeline:
    1. Validate SQL Agent output
    2. Prepare data summary for Claude
    3. Call Claude API for insight generation
    4. Return structured insight output

    Args:
        sql_output: Dict returned by sql_agent.run_sql_agent()
        context:    "churn" | "spend" | "trend" | "employee" | "general"
        filters:    Optional dict with segment, city, period info
        verbose:    Print progress logs

    Returns dict with keys:
        summary         — executive summary text
        key_metrics     — dict of important KPI values
        top_findings    — list of insight strings
        recommendations — list of action items
        segment_highlights — best/worst performer
        confidence      — "high" | "medium" | "low"
        status          — "success" | "empty" | "error"
        message         — user-facing status message
        time_taken      — seconds elapsed
    """
    start_time = time.time()

    if verbose:
        print(f"\n[Analysis Agent] Context: {context}")

    # Step 1 — Validate SQL Agent output
    if sql_output.get("status") == "empty":
        return {
            "summary":           "No data found for the specified query.",
            "key_metrics":       {},
            "top_findings":      [],
            "recommendations":   [],
            "segment_highlights": {},
            "confidence":        "low",
            "status":            "empty",
            "message":           sql_output.get("message", "No data available."),
            "time_taken":        round(time.time() - start_time, 2),
        }

    if sql_output.get("status") == "error":
        return {
            "summary":           "Analysis could not be performed due to a data error.",
            "key_metrics":       {},
            "top_findings":      [],
            "recommendations":   [],
            "segment_highlights": {},
            "confidence":        "low",
            "status":            "error",
            "message":           sql_output.get("message", "Unknown error."),
            "time_taken":        round(time.time() - start_time, 2),
        }

    df = sql_output["dataframe"]

    if verbose:
        print(f"[Analysis Agent] Received DataFrame: "
              f"{len(df):,} rows × {len(df.columns)} cols")

    # Step 2 — Prepare data summary for Claude
    data_summary = _prepare_data_summary(df, context, filters)

    # Step 3 — Call Claude API
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Analyse this banking data and generate insights.\n"
                    f"Context: {context} analysis\n"
                    f"SQL used: {sql_output.get('sql_used', 'N/A')}\n\n"
                    f"Data summary:\n{data_summary}"
                )
            }]
        )

        raw = response.content[0].text.strip()

        # Strip markdown fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        insights = json.loads(raw)

    except json.JSONDecodeError as e:
        if verbose:
            print(f"[Analysis Agent] JSON parse error: {e}")
        insights = _fallback_insights(df, context)
    except Exception as e:
        if verbose:
            print(f"[Analysis Agent] API error: {e}")
        return {
            "summary":           "Analysis failed due to API error.",
            "key_metrics":       {},
            "top_findings":      [],
            "recommendations":   [],
            "segment_highlights": {},
            "confidence":        "low",
            "status":            "error",
            "message":           str(e),
            "time_taken":        round(time.time() - start_time, 2),
        }

    time_taken = round(time.time() - start_time, 2)

    if verbose:
        print(f"[Analysis Agent] Insights generated in {time_taken}s ✅")
        print(f"[Analysis Agent] Status: {insights.get('key_metrics', {}).get('status', 'N/A')}")

    return {
        "summary":            insights.get("summary", ""),
        "key_metrics":        insights.get("key_metrics", {}),
        "top_findings":       insights.get("top_findings", []),
        "recommendations":    insights.get("recommendations", []),
        "segment_highlights": insights.get("segment_highlights", {}),
        "confidence":         insights.get("confidence", "medium"),
        "status":             "success",
        "message":            "Analysis completed successfully.",
        "raw_dataframe":      df,
        "time_taken":         time_taken,
    }


# ---------------------------------------------------------------------------
# Helper — prepare data summary for Claude
# ---------------------------------------------------------------------------
def _prepare_data_summary(
    df: pd.DataFrame,
    context: str,
    filters: dict = None
) -> str:
    """
    Converts DataFrame into a concise text summary for Claude.
    Includes descriptive stats, key distributions, and benchmarks.
    """
    lines = []
    lines.append(f"Total rows: {len(df):,}")
    lines.append(f"Columns: {list(df.columns)}")
    lines.append(f"BankSight benchmarks: churn_baseline=21%, "
                 f"churn_alert=25%, nps_risk_floor=3, nps_scale=0-10, currency=INR")

    if filters:
        lines.append(f"Active filters: {filters}")

    # Churn-specific context
    if "churn" in df.columns:
        total     = len(df)
        churned   = int(df["churn"].sum())
        rate      = round(churned / total * 100, 2) if total > 0 else 0
        status    = ("CRITICAL" if rate > CHURN_ALERT
                     else "WARNING" if rate > CHURN_BASELINE
                     else "NORMAL")
        lines.append(f"\nChurn analysis:")
        lines.append(f"  Total customers: {total:,}")
        lines.append(f"  Churned: {churned:,} ({rate}%) — Status: {status}")
        lines.append(f"  vs baseline: {CHURN_BASELINE}%")

        if "segment" in df.columns:
            seg = df.groupby("segment")["churn"].agg(
                ["sum", "count"]).reset_index()
            seg["rate"] = (seg["sum"] / seg["count"] * 100).round(2)
            lines.append(f"\nChurn by segment:")
            for _, row in seg.iterrows():
                s = ("CRITICAL" if row["rate"] > CHURN_ALERT
                     else "WARNING" if row["rate"] > CHURN_BASELINE
                     else "NORMAL")
                lines.append(
                    f"  {row['segment']}: {int(row['sum'])}/{int(row['count'])} "
                    f"= {row['rate']}% [{s}]")

        if "city" in df.columns:
            city = df.groupby("city")["churn"].agg(
                ["sum", "count"]).reset_index()
            city["rate"] = (city["sum"] / city["count"] * 100).round(2)
            city = city.sort_values("sum", ascending=False)
            lines.append(f"\nChurn by city (top 5):")
            for _, row in city.head(5).iterrows():
                lines.append(
                    f"  {row['city']}: {int(row['sum'])}/{int(row['count'])} "
                    f"= {row['rate']}%")

    # NPS context
    if "nps_score" in df.columns:
        avg_nps = round(df["nps_score"].mean(), 2)
        risk    = len(df[df["nps_score"] <= NPS_RISK_FLOOR])
        lines.append(f"\nNPS (0-10 scale):")
        lines.append(f"  Average: {avg_nps}/10")
        lines.append(f"  At or below risk floor ({NPS_RISK_FLOOR}): {risk:,} customers")

    # Balance context
    if "balance" in df.columns:
        lines.append(f"\nBalance (INR):")
        lines.append(f"  Average: ₹{df['balance'].mean():,.2f}")
        lines.append(f"  Max: ₹{df['balance'].max():,.2f}")
        lines.append(f"  Min: ₹{df['balance'].min():,.2f}")

    # EMI context
    if "emi_status" in df.columns:
        emi = df["emi_status"].value_counts().to_dict()
        total_emi = len(df)
        missed  = emi.get("Missed", 0)
        delayed = emi.get("Delayed", 0)
        stress  = round((missed + delayed) / total_emi * 100, 2)
        lines.append(f"\nEMI status:")
        for status, count in emi.items():
            lines.append(f"  {status}: {count}")
        lines.append(f"  Combined stress rate: {stress}% "
                     f"({'above' if stress > 30 else 'within'} 30% threshold)")

    # Transaction / spend context
    if "amount" in df.columns:
        lines.append(f"\nTransaction amounts (INR):")
        lines.append(f"  Total transactions: {len(df):,}")
        lines.append(f"  Average amount: ₹{df['amount'].mean():,.2f}")
        if "category" in df.columns:
            cat = df.groupby("category")["amount"].sum().sort_values(
                ascending=False)
            lines.append(f"  Top categories by spend:")
            for cat_name, total in cat.head(3).items():
                lines.append(f"    {cat_name}: ₹{total:,.2f}")
        if "is_anomaly" in df.columns:
            anomalies = int(df["is_anomaly"].sum())
            lines.append(f"  Anomalous transactions: {anomalies:,} "
                         f"({round(anomalies/len(df)*100,1)}%)")

    # Employee performance context
    if "performance_grade" in df.columns:
        grades = df["performance_grade"].value_counts().to_dict()
        lines.append(f"\nEmployee performance grades: {grades}")
        if "achieved_amount" in df.columns and "target_amount" in df.columns:
            df["achievement_pct"] = (
                df["achieved_amount"] / df["target_amount"] * 100
            ).round(2)
            lines.append(
                f"  Avg achievement: {df['achievement_pct'].mean():.1f}% of target")

    # Numeric summary for any remaining numeric columns
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        lines.append(f"\nNumeric summary:")
        lines.append(df[numeric_cols].describe().round(2).to_string())

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fallback — if Claude API returns invalid JSON
# ---------------------------------------------------------------------------
def _fallback_insights(df: pd.DataFrame, context: str) -> dict:
    """
    Generates basic insights from DataFrame directly
    when Claude API response can't be parsed.
    """
    findings = [f"Dataset contains {len(df):,} records with {len(df.columns)} fields."]

    if "churn" in df.columns:
        rate = round(df["churn"].mean() * 100, 2)
        status = ("CRITICAL" if rate > CHURN_ALERT
                  else "WARNING" if rate > CHURN_BASELINE
                  else "NORMAL")
        findings.append(f"Churn rate: {rate}% (Status: {status}, Baseline: 21%)")

    if "nps_score" in df.columns:
        avg = round(df["nps_score"].mean(), 2)
        findings.append(f"Average NPS: {avg}/10")

    if "balance" in df.columns:
        findings.append(f"Average balance: ₹{df['balance'].mean():,.2f}")

    return {
        "summary":            f"Analysis of {len(df):,} records — {context} context.",
        "key_metrics":        {"status": "NORMAL", "row_count": len(df)},
        "top_findings":       findings,
        "recommendations":    ["Review data with analyst for detailed insights."],
        "segment_highlights": {},
        "confidence":         "low",
    }


# ---------------------------------------------------------------------------
# CLI — for direct testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from agents.sql_agent import run_sql_agent

    print("Testing Analysis Agent...")
    sql_result = run_sql_agent("Show churn rate by segment")

    if sql_result["status"] == "success":
        result = run_analysis_agent(sql_result, context="churn")
        print("\n--- Analysis Results ---")
        print(f"Summary:     {result['summary']}")
        print(f"Status:      {result['key_metrics'].get('status')}")
        print(f"Findings:    {result['top_findings']}")
        print(f"Confidence:  {result['confidence']}")
        print(f"Time taken:  {result['time_taken']}s")
