"""
BankSight AI — PBIP Generator
================================
Generates a Power BI Project (.pbip) file from query results.

PBIP is a folder structure of plain JSON files that Power BI Desktop
can open directly. No Power BI Desktop needs to be running during
generation — the file is built entirely in Python.

Structure generated:
    BankSight.pbip                          ← pointer file
    BankSight.Report/
        report.json                         ← report metadata
        pages.json                          ← page list
    BankSight.SemanticModel/
        model.bim                           ← semantic model (JSON)

Called by:
    app.py — after pipeline runs, offers PBIP download button

Reference:
    https://learn.microsoft.com/en-us/power-bi/developer/projects/
"""

import os
import json
import uuid
import zipfile
import tempfile
import shutil
import pandas as pd
from datetime import datetime


# ---------------------------------------------------------------------------
# Entry point — called from app.py
# ---------------------------------------------------------------------------
def generate_pbip(
    df: pd.DataFrame,
    report_title: str = "BankSight AI",
    context: str = "churn",
    analysis_output: dict = None,
    anomaly_output: dict = None,
) -> bytes:
    """
    Generates a complete PBIP file from a query result DataFrame.

    Args:
        df:              Query result DataFrame from SQL Agent
        report_title:    Title shown in Power BI report
        context:         "churn" | "spend" | "trend" | "employee"
        analysis_output: Dict from analysis_agent (optional)
        anomaly_output:  Dict from anomaly_agent (optional)

    Returns:
        bytes — ZIP file containing the full PBIP folder structure
                ready for download and opening in Power BI Desktop
    """
    # Create temp directory for PBIP folder structure
    tmp_dir    = tempfile.mkdtemp()
    label      = datetime.now().strftime("%Y%m%d")
    proj_name  = f"BankSight_{context.capitalize()}_{label}"

    try:
        pbip_dir     = os.path.join(tmp_dir, proj_name)
        report_dir   = os.path.join(pbip_dir, f"{proj_name}.Report")
        semantic_dir = os.path.join(pbip_dir, f"{proj_name}.SemanticModel")

        os.makedirs(report_dir,   exist_ok=True)
        os.makedirs(semantic_dir, exist_ok=True)

        # Export CSV data for the semantic model to reference
        csv_path = os.path.join(semantic_dir, "data.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # Build all PBIP files
        _write_pbip_pointer(pbip_dir, proj_name)
        _write_semantic_model(semantic_dir, df, proj_name)
        _write_report(report_dir, df, report_title, context,
                      analysis_output, anomaly_output, proj_name)

        # Zip the entire PBIP folder
        zip_bytes = _zip_pbip(pbip_dir, proj_name)
        return zip_bytes

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# PBIP pointer file
# ---------------------------------------------------------------------------
def _write_pbip_pointer(pbip_dir: str, proj_name: str):
    """
    The .pbip file is a tiny JSON pointer that tells Power BI Desktop
    where to find the Report and SemanticModel folders.
    """
    pbip_content = {
        "version": "1.0",
        "artifacts": [
            {
                "report": {
                    "path": f"{proj_name}.Report"
                }
            }
        ],
        "settings": {
            "enableAutoRecovery": True
        }
    }
    path = os.path.join(pbip_dir, f"{proj_name}.pbip")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pbip_content, f, indent=2)


# ---------------------------------------------------------------------------
# Semantic model (model.bim) — defines tables, columns, measures
# ---------------------------------------------------------------------------
def _write_semantic_model(
    semantic_dir: str,
    df: pd.DataFrame,
    proj_name: str,
):
    """
    Generates model.bim — the semantic model in TMSL/BIM format.
    Defines the data table, column types, and DAX measures.
    """
    # Detect column types
    columns = []
    for col in df.columns:
        dtype  = df[col].dtype
        if pd.api.types.is_integer_dtype(dtype):
            data_type = "int64"
        elif pd.api.types.is_float_dtype(dtype):
            data_type = "double"
        elif pd.api.types.is_bool_dtype(dtype):
            data_type = "boolean"
        else:
            data_type = "string"

        columns.append({
            "name":        col,
            "dataType":    data_type,
            "sourceColumn": col,
            "summarizeBy": "none" if data_type == "string" else "sum",
        })

    # Build DAX measures based on context
    measures = _build_measures(df)

    model_bim = {
        "name":                  "SemanticModel",
        "compatibilityLevel":    1567,
        "model": {
            "culture":    "en-IN",
            "dataSources": [
                {
                    "type":        "structured",
                    "name":        "CSV_Source",
                    "connectionDetails": {
                        "protocol": "csv",
                        "address": {
                            "path": "data.csv"
                        }
                    },
                    "credential": {
                        "AuthenticationKind": "Anonymous",
                        "kind":               "Anonymous",
                        "path":               "data.csv",
                    }
                }
            ],
            "tables": [
                {
                    "name":    "BankSightData",
                    "columns": columns,
                    "measures": measures,
                    "partitions": [
                        {
                            "name":   "BankSightData",
                            "mode":   "import",
                            "source": {
                                "type":       "m",
                                "expression": _build_m_expression()
                            }
                        }
                    ]
                }
            ],
            "annotations": [
                {
                    "name":  "PBI_QueryOrder",
                    "value": "[\"BankSightData\"]"
                },
                {
                    "name":  "_TM_ExtProp_DbType",
                    "value": "auto"
                }
            ]
        }
    }

    path = os.path.join(semantic_dir, "model.bim")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model_bim, f, indent=2)


def _build_m_expression() -> list:
    """Power Query M expression to load data.csv."""
    return [
        "let",
        "    Source = Csv.Document(",
        "        File.Contents(\"data.csv\"),",
        "        [Delimiter=\",\", Columns=null, Encoding=65001,",
        "         QuoteStyle=QuoteStyle.Csv]",
        "    ),",
        "    #\"Promoted Headers\" = Table.PromoteHeaders(",
        "        Source, [PromoteAllScalars=true]",
        "    ),",
        "    #\"Changed Types\" = Table.TransformColumnTypes(",
        "        #\"Promoted Headers\",",
        "        List.Transform(",
        "            Table.ColumnNames(#\"Promoted Headers\"),",
        "            each {_, type text}",
        "        )",
        "    )",
        "in",
        "    #\"Changed Types\""
    ]


def _build_measures(df: pd.DataFrame) -> list:
    """
    Build context-aware DAX measures based on available columns.
    These appear in Power BI as pre-built calculations.
    """
    measures = []
    cols     = [c.lower() for c in df.columns]

    if "churn" in cols:
        measures += [
            {
                "name":        "Total Customers",
                "expression":  "COUNTROWS(BankSightData)",
                "formatString": "#,0",
                "displayFolder": "Churn KPIs"
            },
            {
                "name":        "Churned Customers",
                "expression":  "CALCULATE(COUNTROWS(BankSightData), BankSightData[churn] = 1)",
                "formatString": "#,0",
                "displayFolder": "Churn KPIs"
            },
            {
                "name":        "Churn Rate %",
                "expression":  "DIVIDE(CALCULATE(COUNTROWS(BankSightData), BankSightData[churn]=1), COUNTROWS(BankSightData)) * 100",
                "formatString": "0.00\"% \"",
                "displayFolder": "Churn KPIs"
            },
            {
                "name":        "Churn Rate Status",
                "expression":  "IF([Churn Rate %] > 25, \"CRITICAL\", IF([Churn Rate %] > 21, \"WARNING\", \"NORMAL\"))",
                "displayFolder": "Churn KPIs"
            },
        ]

    if "nps_score" in cols:
        measures.append({
            "name":        "Avg NPS Score",
            "expression":  "AVERAGE(BankSightData[nps_score])",
            "formatString": "0.00",
            "displayFolder": "NPS KPIs"
        })

    if "balance" in cols:
        measures.append({
            "name":        "Avg Balance (INR)",
            "expression":  "AVERAGE(BankSightData[balance])",
            "formatString": "₹#,0.00",
            "displayFolder": "Financial KPIs"
        })

    if "amount" in cols:
        measures += [
            {
                "name":        "Total Spend (INR)",
                "expression":  "SUM(BankSightData[amount])",
                "formatString": "₹#,0.00",
                "displayFolder": "Spend KPIs"
            },
            {
                "name":        "Avg Transaction (INR)",
                "expression":  "AVERAGE(BankSightData[amount])",
                "formatString": "₹#,0.00",
                "displayFolder": "Spend KPIs"
            },
            {
                "name":        "Anomaly Count",
                "expression":  "CALCULATE(COUNTROWS(BankSightData), BankSightData[is_anomaly] = 1)",
                "formatString": "#,0",
                "displayFolder": "Spend KPIs"
            },
        ]

    if "quality_score" in cols:
        measures.append({
            "name":        "Avg Quality Score",
            "expression":  "AVERAGE(BankSightData[quality_score])",
            "formatString": "0.0",
            "displayFolder": "Employee KPIs"
        })

    # Always add a row count measure
    measures.append({
        "name":        "Record Count",
        "expression":  "COUNTROWS(BankSightData)",
        "formatString": "#,0",
        "displayFolder": "General"
    })

    return measures


# ---------------------------------------------------------------------------
# Report definition
# ---------------------------------------------------------------------------
def _write_report(
    report_dir: str,
    df: pd.DataFrame,
    report_title: str,
    context: str,
    analysis_output: dict,
    anomaly_output: dict,
    proj_name: str,
):
    """
    Writes report.json and pages.json for the Power BI report.
    Generates context-appropriate visuals based on query result columns.
    """
    # Build pages with visuals
    pages = _build_pages(df, report_title, context,
                         analysis_output, anomaly_output)

    # report.json — main report metadata
    report_json = {
        "id":                str(uuid.uuid4()),
        "reportSchemaVersion": "1.0",
        "pods": [],
        "resourcePackages": [],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode":                   1,
            "isPrintAreaEnabled":               True,
        },
        "theme": {
            "name":    "BankSight",
            "version": "1.109",
            "themeJson": {
                "name":       "BankSight",
                "dataColors": [
                    "#1F3864", "#3A6BC4", "#E8A020",
                    "#1E8A44", "#D93025", "#F5A623",
                    "#6B7A99", "#DCE6F1"
                ],
                "background":  "#FFFFFF",
                "foreground":  "#1A2340",
                "tableAccent": "#1F3864"
            }
        },
        "sections": pages,
    }

    # pages.json — page order and display
    pages_json = {
        "sections": [
            {
                "name":        p["name"],
                "displayName": p.get("displayName", p["name"]),
                "ordinal":     i
            }
            for i, p in enumerate(pages)
        ]
    }

    with open(os.path.join(report_dir, "report.json"), "w",
              encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)

    with open(os.path.join(report_dir, "pages.json"), "w",
              encoding="utf-8") as f:
        json.dump(pages_json, f, indent=2)


# ---------------------------------------------------------------------------
# Page builder — context-aware visuals
# ---------------------------------------------------------------------------
def _build_pages(
    df: pd.DataFrame,
    report_title: str,
    context: str,
    analysis_output: dict,
    anomaly_output: dict,
) -> list:
    """
    Builds Power BI report pages with visuals based on available columns.
    Generates 2 pages:
      Page 1 — Executive Summary (KPI cards + key charts)
      Page 2 — Detailed Analysis (tables + drill-down charts)
    """
    cols     = [c.lower() for c in df.columns]
    pages    = []
    run_date = datetime.now().strftime("%d-%b-%Y %H:%M")

    # ── Page 1 — Executive Summary ────────────────────────────────────
    page1_visuals = []
    x, y = 20, 20

    # Title text box
    page1_visuals.append(_make_text_box(
        x=20, y=20, w=1200, h=60,
        text=f"{report_title} — {context.capitalize()} Analysis",
        font_size=24, bold=True, color="#1F3864"
    ))

    # Subtitle
    page1_visuals.append(_make_text_box(
        x=20, y=85, w=1200, h=30,
        text=f"Generated by BankSight AI  |  {run_date}  |  {len(df):,} records  |  Currency: INR (₹)",
        font_size=11, bold=False, color="#6B7A99"
    ))

    y = 140

    # KPI cards row
    card_x = 20
    if "churn" in cols:
        total   = len(df)
        churned = int(df["churn"].sum())
        rate    = round(churned / total * 100, 2) if total > 0 else 0
        status  = "CRITICAL" if rate > 25 else "WARNING" if rate > 21 else "NORMAL"

        page1_visuals.append(_make_card(
            x=card_x, y=y, w=270, h=100,
            measure="Churn Rate %",
            title="Churn Rate",
            value=f"{rate}%",
            color="#D93025" if status == "CRITICAL" else
                  "#F5A623" if status == "WARNING" else "#1E8A44"
        ))
        card_x += 290

        page1_visuals.append(_make_card(
            x=card_x, y=y, w=270, h=100,
            measure="Churned Customers",
            title="Churned Customers",
            value=f"{churned:,}",
            color="#1F3864"
        ))
        card_x += 290

    if "nps_score" in cols:
        avg_nps = round(df["nps_score"].mean(), 2)
        page1_visuals.append(_make_card(
            x=card_x, y=y, w=270, h=100,
            measure="Avg NPS Score",
            title="Avg NPS (0-10)",
            value=f"{avg_nps}/10",
            color="#D93025" if avg_nps <= 3 else "#1E8A44"
        ))
        card_x += 290

    if "balance" in cols:
        avg_bal = round(df["balance"].mean(), 2)
        page1_visuals.append(_make_card(
            x=card_x, y=y, w=270, h=100,
            measure="Avg Balance (INR)",
            title="Avg Balance",
            value=f"₹{avg_bal:,.0f}",
            color="#1F3864"
        ))

    if "amount" in cols:
        total_spend = df["amount"].sum()
        page1_visuals.append(_make_card(
            x=card_x, y=y, w=270, h=100,
            measure="Total Spend (INR)",
            title="Total Spend",
            value=f"₹{total_spend:,.0f}",
            color="#1F3864"
        ))
        card_x += 290

    y += 130

    # Charts row — based on available columns
    chart_x = 20

    if "segment" in cols and "churn" in cols:
        page1_visuals.append(_make_bar_chart(
            x=chart_x, y=y, w=580, h=300,
            title="Churn Rate by Segment (%)",
            category_col="segment",
            value_col="churn",
            chart_type="clusteredBarChart",
            color="#1F3864"
        ))
        chart_x += 600

    if "city" in cols and "churn" in cols:
        page1_visuals.append(_make_bar_chart(
            x=chart_x, y=y, w=580, h=300,
            title="Churn by City",
            category_col="city",
            value_col="churn",
            chart_type="clusteredBarChart",
            color="#3A6BC4"
        ))
        chart_x += 600

    if "category" in cols and "amount" in cols:
        page1_visuals.append(_make_bar_chart(
            x=chart_x, y=y, w=580, h=300,
            title="Spend by Category (INR)",
            category_col="category",
            value_col="amount",
            chart_type="clusteredBarChart",
            color="#E8A020"
        ))
        chart_x += 600

    if "transaction_date" in cols and "amount" in cols:
        page1_visuals.append(_make_line_chart(
            x=chart_x, y=y, w=580, h=300,
            title="Spend Trend Over Time",
            axis_col="transaction_date",
            value_col="amount",
            color="#1F3864"
        ))

    if "department" in cols and "quality_score" in cols:
        page1_visuals.append(_make_bar_chart(
            x=chart_x, y=y, w=580, h=300,
            title="Quality Score by Department",
            category_col="department",
            value_col="quality_score",
            chart_type="clusteredBarChart",
            color="#1E8A44"
        ))

    y += 320

    # Analysis summary text box
    if analysis_output and analysis_output.get("summary"):
        page1_visuals.append(_make_text_box(
            x=20, y=y, w=1180, h=80,
            text=f"AI Insight: {analysis_output['summary']}",
            font_size=11, bold=False, color="#1A2340"
        ))
        y += 95

    # Anomaly alert text box
    if anomaly_output and anomaly_output.get("critical_count", 0) > 0:
        critical = anomaly_output["critical_count"]
        page1_visuals.append(_make_text_box(
            x=20, y=y, w=1180, h=50,
            text=f"⚠ CRITICAL ALERT: {critical} critical anomaly/anomalies detected — review Anomaly Details page",
            font_size=12, bold=True, color="#D93025"
        ))

    pages.append({
        "name":        _make_id(),
        "displayName": "Executive Summary",
        "ordinal":     0,
        "height":      720,
        "width":       1280,
        "visualContainers": page1_visuals,
        "background": {
            "transparency": 100
        }
    })

    # ── Page 2 — Data Table ──────────────────────────────────────────
    page2_visuals = []

    page2_visuals.append(_make_text_box(
        x=20, y=20, w=1200, h=50,
        text="Detailed Data — " + report_title,
        font_size=20, bold=True, color="#1F3864"
    ))

    # Main data table
    display_cols = [c for c in df.columns
                    if c not in ("customer_id",)][:12]
    page2_visuals.append(_make_table(
        x=20, y=80, w=1200, h=500,
        title="Query Results",
        columns=display_cols
    ))

    # Key findings list if available
    if analysis_output and analysis_output.get("top_findings"):
        findings_text = "Key Findings:\n" + "\n".join(
            f"  {i+1}. {f}"
            for i, f in enumerate(analysis_output["top_findings"][:5])
        )
        page2_visuals.append(_make_text_box(
            x=20, y=595, w=1200, h=100,
            text=findings_text,
            font_size=10, bold=False, color="#1A2340"
        ))

    pages.append({
        "name":        _make_id(),
        "displayName": "Detailed Data",
        "ordinal":     1,
        "height":      720,
        "width":       1280,
        "visualContainers": page2_visuals,
        "background": {"transparency": 100}
    })

    # ── Page 3 — Anomaly Details (if anomalies exist) ─────────────────
    if anomaly_output and anomaly_output.get("anomalies"):
        page3_visuals = []

        page3_visuals.append(_make_text_box(
            x=20, y=20, w=1200, h=50,
            text="Anomaly Detection Results",
            font_size=20, bold=True, color="#D93025"
        ))

        # Summary cards
        page3_visuals.append(_make_card(
            x=20, y=80, w=200, h=80,
            measure="Record Count",
            title="Total Scanned",
            value=str(anomaly_output["summary"].get("total_scanned", len(df))),
            color="#1F3864"
        ))
        page3_visuals.append(_make_card(
            x=230, y=80, w=200, h=80,
            measure="Record Count",
            title="Critical",
            value=str(anomaly_output["critical_count"]),
            color="#D93025"
        ))
        page3_visuals.append(_make_card(
            x=440, y=80, w=200, h=80,
            measure="Record Count",
            title="Warnings",
            value=str(anomaly_output["warning_count"]),
            color="#F5A623"
        ))

        # Anomaly list as text
        y_pos = 180
        for ano in anomaly_output["anomalies"][:8]:
            sev   = ano.get("severity", "NORMAL")
            color = ("#D93025" if sev == "CRITICAL"
                     else "#F5A623" if sev == "WARNING"
                     else "#1E8A44")
            icon  = "🔴" if sev == "CRITICAL" else "🟡" if sev == "WARNING" else "🟢"
            text  = (f"{icon} [{ano.get('anomaly_id','')}] "
                     f"{ano.get('description','')}  |  "
                     f"Action: {ano.get('action','')}")
            page3_visuals.append(_make_text_box(
                x=20, y=y_pos, w=1200, h=45,
                text=text, font_size=10, bold=(sev=="CRITICAL"), color=color
            ))
            y_pos += 50

        pages.append({
            "name":        _make_id(),
            "displayName": "Anomaly Details",
            "ordinal":     2,
            "height":      720,
            "width":       1280,
            "visualContainers": page3_visuals,
            "background":  {"transparency": 100}
        })

    return pages


# ---------------------------------------------------------------------------
# Visual builders — return Power BI visual container dicts
# ---------------------------------------------------------------------------

def _make_id() -> str:
    """Generate a short unique ID for Power BI objects."""
    return uuid.uuid4().hex[:20]


def _make_text_box(
    x: int, y: int, w: int, h: int,
    text: str, font_size: int = 12,
    bold: bool = False, color: str = "#1A2340"
) -> dict:
    return {
        "id":     _make_id(),
        "x": x, "y": y, "z": 0,
        "width":  w, "height": h,
        "config": json.dumps({
            "name":    _make_id(),
            "layouts": [{
                "id": 0,
                "position": {"x": x, "y": y, "z": 0,
                             "width": w, "height": h},
            }],
            "singleVisual": {
                "visualType": "textbox",
                "objects": {
                    "general": [{
                        "properties": {
                            "paragraphs": [{
                                "textRuns": [{
                                    "value": text,
                                    "textStyle": {
                                        "fontWeight": "bold" if bold else "normal",
                                        "fontSize":   f"{font_size}pt",
                                        "color":      {"solid": {"color": color}},
                                    }
                                }],
                                "horizontalTextAlignment": "Left",
                            }]
                        }
                    }]
                }
            }
        }),
        "filters": "[]",
    }


def _make_card(
    x: int, y: int, w: int, h: int,
    measure: str, title: str,
    value: str, color: str = "#1F3864"
) -> dict:
    return {
        "id":     _make_id(),
        "x": x, "y": y, "z": 1,
        "width":  w, "height": h,
        "config": json.dumps({
            "name":    _make_id(),
            "layouts": [{
                "id": 0,
                "position": {"x": x, "y": y, "z": 1,
                             "width": w, "height": h},
            }],
            "singleVisual": {
                "visualType": "card",
                "projections": {
                    "Values": [{"queryRef": f"BankSightData.{measure}"}]
                },
                "objects": {
                    "labels": [{
                        "properties": {
                            "show":      {"expr": {"Literal": {"Value": "true"}}},
                            "color":     {"solid": {"color": color}},
                            "fontSize":  {"expr": {"Literal": {"Value": "24D"}}},
                            "fontFamily":{"expr": {"Literal": {"Value": "'DM Sans'"}}},
                        }
                    }],
                    "categoryLabels": [{
                        "properties": {
                            "show":     {"expr": {"Literal": {"Value": "true"}}},
                            "color":    {"solid": {"color": "#6B7A99"}},
                            "fontSize": {"expr": {"Literal": {"Value": "11D"}}},
                        }
                    }]
                },
                "vcObjects": {
                    "title": [{
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                        }
                    }],
                    "border": [{
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                        }
                    }]
                }
            }
        }),
        "filters": "[]",
    }


def _make_bar_chart(
    x: int, y: int, w: int, h: int,
    title: str, category_col: str, value_col: str,
    chart_type: str = "clusteredBarChart",
    color: str = "#1F3864"
) -> dict:
    return {
        "id":     _make_id(),
        "x": x, "y": y, "z": 1,
        "width":  w, "height": h,
        "config": json.dumps({
            "name":    _make_id(),
            "layouts": [{
                "id": 0,
                "position": {"x": x, "y": y, "z": 1,
                             "width": w, "height": h},
            }],
            "singleVisual": {
                "visualType": chart_type,
                "projections": {
                    "Category": [{"queryRef": f"BankSightData.{category_col}"}],
                    "Y":        [{"queryRef": f"BankSightData.{value_col}"}],
                },
                "objects": {
                    "dataColors": [{
                        "properties": {
                            "defaultColor": {"solid": {"color": color}}
                        }
                    }]
                },
                "vcObjects": {
                    "title": [{
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                            "fontColor": {"solid": {"color": "#1F3864"}},
                        }
                    }]
                }
            }
        }),
        "filters": "[]",
    }


def _make_line_chart(
    x: int, y: int, w: int, h: int,
    title: str, axis_col: str, value_col: str,
    color: str = "#1F3864"
) -> dict:
    return {
        "id":     _make_id(),
        "x": x, "y": y, "z": 1,
        "width":  w, "height": h,
        "config": json.dumps({
            "name":    _make_id(),
            "layouts": [{
                "id": 0,
                "position": {"x": x, "y": y, "z": 1,
                             "width": w, "height": h},
            }],
            "singleVisual": {
                "visualType": "lineChart",
                "projections": {
                    "Category": [{"queryRef": f"BankSightData.{axis_col}"}],
                    "Y":        [{"queryRef": f"BankSightData.{value_col}"}],
                },
                "objects": {
                    "dataColors": [{
                        "properties": {
                            "defaultColor": {"solid": {"color": color}}
                        }
                    }]
                },
                "vcObjects": {
                    "title": [{
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                        }
                    }]
                }
            }
        }),
        "filters": "[]",
    }


def _make_table(
    x: int, y: int, w: int, h: int,
    title: str, columns: list
) -> dict:
    projections = {
        "Values": [
            {"queryRef": f"BankSightData.{col}"}
            for col in columns
        ]
    }
    return {
        "id":     _make_id(),
        "x": x, "y": y, "z": 1,
        "width":  w, "height": h,
        "config": json.dumps({
            "name":    _make_id(),
            "layouts": [{
                "id": 0,
                "position": {"x": x, "y": y, "z": 1,
                             "width": w, "height": h},
            }],
            "singleVisual": {
                "visualType":  "tableEx",
                "projections": projections,
                "objects": {
                    "grid": [{
                        "properties": {
                            "gridVertical":          {"expr": {"Literal": {"Value": "true"}}},
                            "gridVerticalColor":     {"solid": {"color": "#D8E0F0"}},
                            "gridHorizontal":        {"expr": {"Literal": {"Value": "true"}}},
                            "gridHorizontalColor":   {"solid": {"color": "#D8E0F0"}},
                            "rowPadding":            {"expr": {"Literal": {"Value": "4D"}}},
                            "fontColor":             {"solid": {"color": "#1A2340"}},
                            "backgroundColor":       {"solid": {"color": "#FFFFFF"}},
                        }
                    }],
                    "columnHeaders": [{
                        "properties": {
                            "fontColor":       {"solid": {"color": "#FFFFFF"}},
                            "backColor":       {"solid": {"color": "#1F3864"}},
                            "fontWeight":      {"expr": {"Literal": {"Value": "'bold'"}}},
                        }
                    }]
                },
                "vcObjects": {
                    "title": [{
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                        }
                    }]
                }
            }
        }),
        "filters": "[]",
    }


# ---------------------------------------------------------------------------
# ZIP the PBIP folder for download
# ---------------------------------------------------------------------------
def _zip_pbip(pbip_dir: str, proj_name: str) -> bytes:
    """
    Zips the entire PBIP folder structure into bytes.
    User downloads this ZIP, extracts it, and opens the .pbip file
    in Power BI Desktop.
    """
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(pbip_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname   = os.path.relpath(full_path, os.path.dirname(pbip_dir))
                zf.write(full_path, arcname)
    buffer.seek(0)
    return buffer.read()


# ---------------------------------------------------------------------------
# CLI — for direct testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sqlite3

    print("Testing PBIP Generator...")
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH  = os.path.join(BASE_DIR, "data", "banking_mock.db")

    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        df   = pd.read_sql(
            "SELECT * FROM customers WHERE churn=1 LIMIT 100", conn)
        conn.close()
    else:
        # Demo DataFrame if DB not available
        df = pd.DataFrame({
            "customer_id":  range(1, 11),
            "segment":      ["Premium"] * 5 + ["Basic"] * 5,
            "churn":        [1] * 10,
            "nps_score":    [2, 3, 1, 4, 2, 5, 3, 2, 1, 4],
            "balance":      [100000 * i for i in range(1, 11)],
            "city":         ["Delhi", "Mumbai", "Bengaluru",
                             "Pune", "Gurugram"] * 2,
        })

    pbip_bytes = generate_pbip(
        df,
        report_title="BankSight AI Test",
        context="churn",
    )

    out_path = os.path.join(BASE_DIR, "dashboard",
                            "BankSight_Test.zip")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(pbip_bytes)

    print(f"✅ PBIP ZIP generated: {out_path}")
    print(f"   Size: {len(pbip_bytes):,} bytes")
    print("   Extract the ZIP and open the .pbip file in Power BI Desktop")
