"""
BankSight AI — Anomaly Agent
==============================
Detects spend spikes, churn risk combos, and statistical
outliers from SQL Agent DataFrame output.

Called by:
  - Claude Code agent: .claude/agents/anomaly-detector.md
  - Streamlit UI:      app.py
  - Report Agent:      report_agent.py

Spec reference: .claude/specs/02-agent-design.md
"""

import os
import time
import sqlite3
import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths & BankSight thresholds
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "banking_mock.db")

# BankSight anomaly thresholds (from CLAUDE.md)
SPEND_SPIKE_MULTIPLIER = 2.0   # amount > 2x monthly avg = anomaly
NPS_RISK_FLOOR         = 3     # NPS <= 3 = churn risk signal
CHURN_ALERT_RATE       = 0.25  # >25% = CRITICAL
CHURN_BASELINE         = 0.21  # 21% baseline
EMI_STRESS_THRESHOLD   = 0.30  # >30% combined missed+delayed = WARNING
HIGH_RISK_CREDIT_SCORE = 500   # Basic + credit_score < 500 = high risk
MASS_CHURN_THRESHOLD   = 3     # 3+ Premium customers churned same week
INACTIVITY_DAYS        = 60    # inactive 60+ days before churn = flag
REVERSAL_THRESHOLD     = 3     # 3+ reversals in 30 days = flag


# ---------------------------------------------------------------------------
# Main agent function
# ---------------------------------------------------------------------------
def run_anomaly_agent(
    sql_output: dict,
    analysis_output: dict = None,
    filters: dict = None,
    verbose: bool = True
) -> dict:
    """
    Anomaly Agent pipeline:
    1. Validate inputs (SQL output required, analysis optional)
    2. Run all anomaly detection rules
    3. Return prioritised flagged list with severity levels

    Args:
        sql_output:      Dict from sql_agent.run_sql_agent()
        analysis_output: Dict from analysis_agent.run_analysis_agent()
                         (optional — used for context enrichment)
        filters:         Optional dict with segment, city etc.
        verbose:         Print progress logs

    Returns dict with keys:
        anomalies       — list of flagged anomaly dicts
        summary         — detection summary dict
        critical_count  — number of CRITICAL anomalies
        warning_count   — number of WARNING anomalies
        status          — "success" | "empty" | "error"
        message         — user-facing status message
        time_taken      — seconds elapsed
    """
    start_time = time.time()

    if verbose:
        print(f"\n[Anomaly Agent] Starting detection...")

    # Step 1 — Validate SQL Agent output
    if sql_output.get("status") == "empty":
        return _empty_result(
            "No data to scan for anomalies.",
            start_time, status="empty"
        )

    if sql_output.get("status") == "error":
        return _empty_result(
            f"Cannot run anomaly detection: {sql_output.get('message')}",
            start_time, status="error"
        )

    df = sql_output["dataframe"].copy()

    if verbose:
        print(f"[Anomaly Agent] Scanning {len(df):,} rows...")

    # Step 2 — Run all detection rules
    anomalies = []

    anomalies += _detect_churn_rate_breach(df, filters)
    anomalies += _detect_churn_risk_combo(df)
    anomalies += _detect_mass_premium_churn(df)
    anomalies += _detect_spend_spikes(df)
    anomalies += _detect_emi_stress(df)
    anomalies += _detect_inactivity_churn(df)
    anomalies += _detect_high_risk_segment(df)
    anomalies += _detect_reversal_pattern(df)
    anomalies += _detect_nps_extremes(df)

    # Enrich with analysis context if available
    if analysis_output and analysis_output.get("status") == "success":
        anomalies = _enrich_with_analysis_context(
            anomalies, analysis_output)

    # Sort by severity then score
    severity_order = {"CRITICAL": 0, "WARNING": 1, "NORMAL": 2}
    anomalies.sort(key=lambda x: (
        severity_order.get(x["severity"], 3),
        -x.get("score", 0)
    ))

    # Assign anomaly IDs
    for i, ano in enumerate(anomalies, 1):
        ano["anomaly_id"] = f"ANO-{i:03d}"

    critical_count = sum(1 for a in anomalies if a["severity"] == "CRITICAL")
    warning_count  = sum(1 for a in anomalies if a["severity"] == "WARNING")
    time_taken     = round(time.time() - start_time, 2)

    if verbose:
        print(f"[Anomaly Agent] Detected {len(anomalies)} anomalies "
              f"({critical_count} CRITICAL, {warning_count} WARNING) "
              f"in {time_taken}s ✅")

    # No anomalies = healthy signal
    if not anomalies:
        anomalies.append({
            "anomaly_id":   "ANO-001",
            "type":         "no_anomalies",
            "severity":     "NORMAL",
            "entity":       "All segments",
            "description":  "No anomalies detected. All metrics within expected ranges.",
            "deviation":    "N/A",
            "action":       "Continue monitoring. No immediate action required.",
            "score":        0,
        })

    return {
        "anomalies":      anomalies,
        "summary": {
            "total_scanned":    len(df),
            "anomalies_found":  len(anomalies),
            "critical_count":   critical_count,
            "warning_count":    warning_count,
            "methods_used":     [
                "threshold_rules", "z-score", "IQR",
                "percentage_change", "combo_detection"
            ],
            "analysis_context": "available" if analysis_output else "not_available",
            "confidence":       "high" if len(df) > 100 else "medium",
        },
        "critical_count": critical_count,
        "warning_count":  warning_count,
        "status":         "success",
        "message":        (
            f"Detected {len(anomalies)} anomaly/anomalies "
            f"({critical_count} CRITICAL, {warning_count} WARNING)."
        ),
        "time_taken":     time_taken,
    }


# ---------------------------------------------------------------------------
# Detection rules
# ---------------------------------------------------------------------------

def _detect_churn_rate_breach(df: pd.DataFrame, filters: dict = None) -> list:
    """Flag if overall or segment churn rate exceeds thresholds."""
    anomalies = []

    if "churn" not in df.columns:
        return anomalies

    total   = len(df)
    churned = int(df["churn"].sum())
    rate    = churned / total if total > 0 else 0

    if rate > CHURN_ALERT_RATE:
        anomalies.append({
            "type":        "churn_rate_breach",
            "severity":    "CRITICAL",
            "entity":      "Overall portfolio",
            "description": (
                f"Overall churn rate {rate*100:.2f}% exceeds "
                f"CRITICAL threshold of {CHURN_ALERT_RATE*100:.0f}%"
            ),
            "deviation":   f"{round((rate - CHURN_ALERT_RATE)*100, 2)}% above threshold",
            "action":      "Immediate escalation to retention team required.",
            "score":       10,
        })
    elif rate > CHURN_BASELINE:
        anomalies.append({
            "type":        "churn_rate_elevated",
            "severity":    "WARNING",
            "entity":      "Overall portfolio",
            "description": (
                f"Overall churn rate {rate*100:.2f}% is above "
                f"baseline of {CHURN_BASELINE*100:.0f}%"
            ),
            "deviation":   f"{round((rate - CHURN_BASELINE)*100, 2)}% above baseline",
            "action":      "Monitor closely. Review segment-level breakdown.",
            "score":       6,
        })

    # Segment-level churn check
    if "segment" in df.columns:
        for seg, seg_df in df.groupby("segment"):
            seg_rate = seg_df["churn"].mean()
            if seg_rate > CHURN_ALERT_RATE:
                anomalies.append({
                    "type":        "segment_churn_breach",
                    "severity":    "CRITICAL",
                    "entity":      f"{seg} segment",
                    "description": (
                        f"{seg} segment churn at {seg_rate*100:.2f}% "
                        f"exceeds CRITICAL threshold ({CHURN_ALERT_RATE*100:.0f}%)"
                    ),
                    "deviation":   f"{round((seg_rate - CHURN_ALERT_RATE)*100, 2)}% above threshold",
                    "action":      f"Activate {seg} segment retention protocol immediately.",
                    "score":       9,
                })

    return anomalies


def _detect_churn_risk_combo(df: pd.DataFrame) -> list:
    """
    Detect churn risk combo: NPS <= 3 AND missed EMI same customer.
    Highest priority flag in BankSight system.
    """
    anomalies = []

    if "nps_score" not in df.columns:
        return anomalies

    low_nps = df[df["nps_score"] <= NPS_RISK_FLOOR]
    if len(low_nps) == 0:
        return anomalies

    # If EMI data is in the same DataFrame
    if "emi_status" in df.columns:
        combo = low_nps[low_nps["emi_status"] == "Missed"]
        if len(combo) > 0:
            anomalies.append({
                "type":        "churn_risk_combo",
                "severity":    "CRITICAL",
                "entity":      f"{len(combo)} customer(s)",
                "description": (
                    f"Churn risk combo detected: {len(combo)} customer(s) "
                    f"with NPS <= {NPS_RISK_FLOOR} AND missed EMI — "
                    f"highest priority intervention required"
                ),
                "deviation":   "Full churn risk combo threshold breached",
                "action":      (
                    "Initiate immediate outreach. Assign dedicated "
                    "relationship manager within 24 hours."
                ),
                "score":       10,
            })

    # NPS-only risk (EMI not available)
    else:
        if len(low_nps) > 0:
            anomalies.append({
                "type":        "nps_risk_floor",
                "severity":    "CRITICAL",
                "entity":      f"{len(low_nps)} customer(s)",
                "description": (
                    f"{len(low_nps)} customer(s) at or below NPS risk floor "
                    f"({NPS_RISK_FLOOR}/10) — churn risk elevated"
                ),
                "deviation":   f"NPS <= {NPS_RISK_FLOOR} threshold",
                "action":      "Cross-reference with EMI data and initiate retention outreach.",
                "score":       9,
            })

    return anomalies


def _detect_mass_premium_churn(df: pd.DataFrame) -> list:
    """Flag if 3+ Premium customers churned in the same week."""
    anomalies = []

    if not all(c in df.columns for c in ["segment", "churn"]):
        return anomalies

    premium_churned = df[
        (df["segment"] == "Premium") & (df["churn"] == 1)
    ]

    if len(premium_churned) >= MASS_CHURN_THRESHOLD:
        anomalies.append({
            "type":        "mass_premium_churn",
            "severity":    "CRITICAL",
            "entity":      "Premium segment",
            "description": (
                f"Mass churn event: {len(premium_churned)} Premium customers "
                f"churned (threshold: {MASS_CHURN_THRESHOLD})"
            ),
            "deviation":   f"{len(premium_churned)} churned vs {MASS_CHURN_THRESHOLD} threshold",
            "action":      (
                "Investigate for systemic issue — competitor offer, "
                "service failure, or product gap."
            ),
            "score":       10,
        })

    return anomalies


def _detect_spend_spikes(df: pd.DataFrame) -> list:
    """Flag transactions where amount > 2x customer monthly average."""
    anomalies = []

    if "amount" not in df.columns:
        return anomalies

    # Use pre-computed is_anomaly flag if available
    if "is_anomaly" in df.columns:
        spike_count = int(df["is_anomaly"].sum())
        if spike_count > 0:
            pct = round(spike_count / len(df) * 100, 1)
            severity = "CRITICAL" if pct > 10 else "WARNING"
            anomalies.append({
                "type":        "spend_spike",
                "severity":    severity,
                "entity":      f"{spike_count:,} transactions",
                "description": (
                    f"{spike_count:,} transactions ({pct}%) flagged as spend spikes "
                    f"(amount > {SPEND_SPIKE_MULTIPLIER}x customer monthly average)"
                ),
                "deviation":   f"{pct}% of transactions above spike threshold",
                "action":      "Review pre-churn spend patterns. Flag customers for retention.",
                "score":       7 if severity == "WARNING" else 9,
            })
    else:
        # Compute on-the-fly using z-score
        z_scores = np.abs(
            (df["amount"] - df["amount"].mean()) / df["amount"].std()
        )
        outliers = df[z_scores > 2]
        if len(outliers) > 0:
            anomalies.append({
                "type":        "spend_spike_zscore",
                "severity":    "WARNING",
                "entity":      f"{len(outliers):,} transactions",
                "description": (
                    f"{len(outliers):,} transactions exceed 2σ from mean spend "
                    f"(method: z-score analysis)"
                ),
                "deviation":   "> 2 standard deviations from mean",
                "action":      "Verify if pre-churn liquidation pattern.",
                "score":       6,
            })

    return anomalies


def _detect_emi_stress(df: pd.DataFrame) -> list:
    """Flag if combined EMI missed+delayed rate exceeds 30%."""
    anomalies = []

    if "emi_status" not in df.columns:
        return anomalies

    total   = len(df)
    missed  = len(df[df["emi_status"] == "Missed"])
    delayed = len(df[df["emi_status"] == "Delayed"])
    stress  = (missed + delayed) / total if total > 0 else 0

    if stress > EMI_STRESS_THRESHOLD:
        anomalies.append({
            "type":        "emi_stress",
            "severity":    "WARNING",
            "entity":      "Loan portfolio",
            "description": (
                f"Combined EMI stress rate {stress*100:.2f}% "
                f"(Missed: {missed}, Delayed: {delayed}) "
                f"exceeds {EMI_STRESS_THRESHOLD*100:.0f}% threshold"
            ),
            "deviation":   f"{round((stress-EMI_STRESS_THRESHOLD)*100,2)}% above threshold",
            "action":      "Escalate to credit risk team. Identify overlap with low-NPS customers.",
            "score":       6,
        })

    return anomalies


def _detect_inactivity_churn(df: pd.DataFrame) -> list:
    """Flag churned customers who had active_member=0 before exit."""
    anomalies = []

    if not all(c in df.columns for c in ["active_member", "churn"]):
        return anomalies

    inactive_churned = df[
        (df["churn"] == 1) & (df["active_member"] == 0)
    ]

    if len(inactive_churned) > 0:
        anomalies.append({
            "type":        "inactivity_churn",
            "severity":    "WARNING",
            "entity":      f"{len(inactive_churned)} customer(s)",
            "description": (
                f"{len(inactive_churned)} churned customers were already "
                f"inactive (active_member=0) — inactivity is a leading churn signal"
            ),
            "deviation":   "active_member=0 before churn",
            "action":      "Add inactivity flag to real-time churn prediction model.",
            "score":       7,
        })

    return anomalies


def _detect_high_risk_segment(df: pd.DataFrame) -> list:
    """Flag Basic segment customers with credit_score < 500."""
    anomalies = []

    if not all(c in df.columns for c in ["segment", "credit_score"]):
        return anomalies

    high_risk = df[
        (df["segment"] == "Basic") &
        (df["credit_score"] < HIGH_RISK_CREDIT_SCORE)
    ]

    if len(high_risk) > 0:
        churned = int(high_risk["churn"].sum()) if "churn" in high_risk.columns else "N/A"
        anomalies.append({
            "type":        "high_risk_segment",
            "severity":    "WARNING",
            "entity":      f"{len(high_risk)} Basic segment customers",
            "description": (
                f"{len(high_risk)} customers in high-risk zone: "
                f"Basic segment AND credit_score < {HIGH_RISK_CREDIT_SCORE}. "
                f"Churned: {churned}"
            ),
            "deviation":   f"credit_score < {HIGH_RISK_CREDIT_SCORE} in Basic segment",
            "action":      "Review credit risk exposure. Consider proactive outreach.",
            "score":       7,
        })

    return anomalies


def _detect_reversal_pattern(df: pd.DataFrame) -> list:
    """Flag customers with 3+ reversed transactions."""
    anomalies = []

    if "status" not in df.columns:
        return anomalies

    reversals = df[df["status"] == "Reversed"]
    if len(reversals) == 0:
        return anomalies

    if "customer_id" in reversals.columns:
        reversal_counts = reversals.groupby("customer_id").size()
        flagged = reversal_counts[reversal_counts >= REVERSAL_THRESHOLD]
        if len(flagged) > 0:
            anomalies.append({
                "type":        "reversal_pattern",
                "severity":    "WARNING",
                "entity":      f"{len(flagged)} customer(s)",
                "description": (
                    f"{len(flagged)} customer(s) with "
                    f"{REVERSAL_THRESHOLD}+ reversed transactions — "
                    f"possible dispute or fraud signal"
                ),
                "deviation":   f">= {REVERSAL_THRESHOLD} reversals per customer",
                "action":      "Investigate for fraud, merchant disputes, or UX issues.",
                "score":       6,
            })
    else:
        total_reversals = len(reversals)
        reversal_pct = round(total_reversals / len(df) * 100, 1)
        if reversal_pct > 5:
            anomalies.append({
                "type":        "high_reversal_rate",
                "severity":    "WARNING",
                "entity":      f"{total_reversals:,} transactions",
                "description": (
                    f"High reversal rate: {total_reversals:,} "
                    f"({reversal_pct}%) transactions reversed"
                ),
                "deviation":   f"{reversal_pct}% reversal rate > 5% threshold",
                "action":      "Investigate payment processing issues.",
                "score":       5,
            })

    return anomalies


def _detect_nps_extremes(df: pd.DataFrame) -> list:
    """Flag extremely low NPS scores (0 or 1)."""
    anomalies = []

    if "nps_score" not in df.columns:
        return anomalies

    extremes = df[df["nps_score"] <= 1]
    if len(extremes) > 0:
        anomalies.append({
            "type":        "nps_extreme",
            "severity":    "CRITICAL",
            "entity":      f"{len(extremes)} customer(s)",
            "description": (
                f"{len(extremes)} customer(s) with extreme dissatisfaction "
                f"(NPS 0 or 1 out of 10) — highest churn probability"
            ),
            "deviation":   "NPS <= 1 on 0-10 scale",
            "action":      "Immediate personal outreach. Assign to senior relationship manager.",
            "score":       9,
        })

    return anomalies


# ---------------------------------------------------------------------------
# Enrich anomalies with analysis agent context
# ---------------------------------------------------------------------------
def _enrich_with_analysis_context(
    anomalies: list,
    analysis_output: dict
) -> list:
    """
    Uses analysis agent's key findings to add context
    to flagged anomalies where relevant.
    """
    findings = analysis_output.get("top_findings", [])
    if not findings:
        return anomalies

    # Add analysis context note to CRITICAL anomalies
    for ano in anomalies:
        if ano["severity"] == "CRITICAL":
            ano["analysis_context"] = (
                "Analysis Agent finding: " +
                findings[0] if findings else "See analysis summary."
            )

    return anomalies


# ---------------------------------------------------------------------------
# Helper — empty result
# ---------------------------------------------------------------------------
def _empty_result(message: str, start_time: float, status: str = "empty") -> dict:
    return {
        "anomalies":      [],
        "summary": {
            "total_scanned":   0,
            "anomalies_found": 0,
            "critical_count":  0,
            "warning_count":   0,
            "methods_used":    [],
            "confidence":      "low",
        },
        "critical_count": 0,
        "warning_count":  0,
        "status":         status,
        "message":        message,
        "time_taken":     round(time.time() - start_time, 2),
    }


# ---------------------------------------------------------------------------
# CLI — for direct testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from agents.sql_agent import run_sql_agent

    print("Testing Anomaly Agent...")
    sql_result = run_sql_agent("Show all customers with churn and segment data")

    if sql_result["status"] == "success":
        result = run_anomaly_agent(sql_result)
        print(f"\n--- Anomaly Detection Results ---")
        print(f"Total anomalies: {len(result['anomalies'])}")
        print(f"CRITICAL: {result['critical_count']}")
        print(f"WARNING:  {result['warning_count']}")
        print(f"Time:     {result['time_taken']}s")
        print("\nTop anomalies:")
        for ano in result["anomalies"][:3]:
            print(f"  [{ano['severity']}] {ano['description']}")
