"""
BankSight AI — Streamlit Application
======================================
Full dashboard with metrics cards, charts, filters at top
and a chat interface at the bottom.

Run:
    streamlit run app.py

Requires:
    - data/banking_mock.db (run data/setup_db.py first)
    - .env file with ANTHROPIC_API_KEY
"""

import os
import sys
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Path setup — add project root to sys.path so agents can be imported
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agents.sql_agent      import run_sql_agent
from agents.analysis_agent import run_analysis_agent
from agents.anomaly_agent  import run_anomaly_agent
from agents.report_agent   import run_report_agent

DB_PATH = os.path.join(BASE_DIR, "data", "banking_mock.db")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="BankSight AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — refined dark-blue banking aesthetic
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Google Fonts ─────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Root variables ───────────────────────────────────── */
:root {
    --navy:      #1F3864;
    --navy-mid:  #2E4D8A;
    --navy-light:#3A6BC4;
    --accent:    #E8A020;
    --red:       #D93025;
    --green:     #1E8A44;
    --yellow:    #F5A623;
    --bg:        #F4F6FB;
    --card-bg:   #FFFFFF;
    --border:    #D8E0F0;
    --text:      #1A2340;
    --muted:     #6B7A99;
    --font-head: 'DM Serif Display', serif;
    --font-body: 'DM Sans', sans-serif;
}

/* ── Global ───────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: var(--font-body) !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

/* ── Header ───────────────────────────────────────────── */
.bs-header {
    background: linear-gradient(135deg, #1F3864 0%, #2E4D8A 60%, #3A6BC4 100%);
    border-radius: 14px;
    padding: 24px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 4px 24px rgba(31,56,100,0.18);
}
.bs-header-icon { font-size: 40px; }
.bs-header-title {
    font-family: var(--font-head);
    font-size: 28px;
    color: #FFFFFF;
    margin: 0;
    letter-spacing: -0.5px;
}
.bs-header-sub {
    font-size: 13px;
    color: rgba(255,255,255,0.65);
    margin: 0;
}

/* ── Metric cards ─────────────────────────────────────── */
.metric-card {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 18px 20px;
    border: 1px solid var(--border);
    box-shadow: 0 2px 8px rgba(31,56,100,0.06);
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    background: var(--navy-light);
    border-radius: 4px 0 0 4px;
}
.metric-card.critical::before { background: var(--red); }
.metric-card.warning::before  { background: var(--yellow); }
.metric-card.normal::before   { background: var(--green); }
.metric-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 6px;
}
.metric-value {
    font-family: var(--font-head);
    font-size: 26px;
    color: var(--text);
    line-height: 1;
}
.metric-delta {
    font-size: 11px;
    color: var(--muted);
    margin-top: 4px;
}
.metric-delta.up   { color: var(--red); }
.metric-delta.down { color: var(--green); }

/* ── Section headers ──────────────────────────────────── */
.section-head {
    font-family: var(--font-head);
    font-size: 18px;
    color: var(--navy);
    border-bottom: 2px solid var(--border);
    padding-bottom: 8px;
    margin: 24px 0 16px;
}

/* ── Skill buttons ────────────────────────────────────── */
.skill-grid { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
.skill-btn {
    background: var(--card-bg);
    border: 1.5px solid var(--border);
    border-radius: 10px;
    padding: 10px 18px;
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 600;
    color: var(--navy);
    cursor: pointer;
    display: flex; align-items: center; gap: 8px;
    transition: all 0.15s;
    box-shadow: 0 1px 4px rgba(31,56,100,0.06);
}
.skill-btn:hover {
    background: var(--navy);
    color: #FFF;
    border-color: var(--navy);
}

/* ── Chat messages ────────────────────────────────────── */
.chat-user {
    background: var(--navy);
    color: #FFF;
    border-radius: 14px 14px 4px 14px;
    padding: 12px 16px;
    margin: 8px 0;
    max-width: 75%;
    margin-left: auto;
    font-size: 14px;
    line-height: 1.5;
}
.chat-ai {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 14px 14px 14px 4px;
    padding: 14px 18px;
    margin: 8px 0;
    max-width: 85%;
    font-size: 14px;
    line-height: 1.6;
    box-shadow: 0 2px 6px rgba(31,56,100,0.05);
}
.agent-tag {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 2px 8px;
    border-radius: 20px;
    margin-bottom: 8px;
}
.tag-sql      { background: #E8F0FE; color: #1A73E8; }
.tag-analysis { background: #E6F4EA; color: #1E8A44; }
.tag-anomaly  { background: #FEF3E2; color: #E8A020; }
.tag-report   { background: #FCE8E6; color: #D93025; }

/* ── Status badges ────────────────────────────────────── */
.badge-critical { background:#FCE8E6; color:#D93025; font-weight:700;
                  padding:2px 10px; border-radius:20px; font-size:11px; }
.badge-warning  { background:#FEF3E2; color:#E8A020; font-weight:700;
                  padding:2px 10px; border-radius:20px; font-size:11px; }
.badge-normal   { background:#E6F4EA; color:#1E8A44; font-weight:700;
                  padding:2px 10px; border-radius:20px; font-size:11px; }

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--navy) !important;
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label { color: rgba(255,255,255,0.6) !important; }

/* ── Streamlit overrides ──────────────────────────────── */
.stButton > button {
    background: var(--navy) !important;
    color: #FFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    background: var(--navy-mid) !important;
    box-shadow: 0 2px 8px rgba(31,56,100,0.2) !important;
}
.stTextInput > div > input {
    border-radius: 10px !important;
    border: 1.5px solid var(--border) !important;
    font-family: var(--font-body) !important;
    font-size: 14px !important;
}
.stDownloadButton > button {
    background: var(--green) !important;
    color: #FFF !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
.stSpinner { color: var(--navy) !important; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ===========================================================================
# Session state initialisation
# ===========================================================================
def init_session():
    defaults = {
        "messages":        [],
        "last_sql_output": None,
        "last_analysis":   None,
        "last_anomaly":    None,
        "last_report":     None,
        "db_summary":      None,
        "active_skill":    None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ===========================================================================
# Database helpers
# ===========================================================================
@st.cache_data(ttl=300)
def load_db_summary():
    """Load summary KPIs from banking_mock.db for the dashboard header."""
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        customers = pd.read_sql("SELECT * FROM customers", conn)
        loans     = pd.read_sql("SELECT * FROM loan_emi", conn)
        txns      = pd.read_sql(
            "SELECT COUNT(*) as cnt, "
            "SUM(CASE WHEN is_anomaly=1 THEN 1 ELSE 0 END) as anomalies "
            "FROM transactions", conn)
        conn.close()

        total     = len(customers)
        churned   = int(customers["churn"].sum())
        rate      = round(churned / total * 100, 2)
        avg_nps   = round(customers["nps_score"].mean(), 2)
        avg_bal   = round(customers["balance"].mean(), 2)
        missed    = len(loans[loans["emi_status"] == "Missed"])
        delayed   = len(loans[loans["emi_status"] == "Delayed"])
        stress    = round((missed + delayed) / len(loans) * 100, 2)
        txn_count = int(txns["cnt"].iloc[0])
        ano_count = int(txns["anomalies"].iloc[0])

        status = ("CRITICAL" if rate > 25
                  else "WARNING" if rate > 21
                  else "NORMAL")

        return {
            "total_customers": total,
            "total_churned":   churned,
            "churn_rate":      rate,
            "churn_status":    status,
            "avg_nps":         avg_nps,
            "avg_balance":     avg_bal,
            "emi_stress":      stress,
            "txn_count":       txn_count,
            "anomaly_txns":    ano_count,
            "customers_df":    customers,
            "loans_df":        loans,
        }
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300)
def load_chart_data():
    """Load data for dashboard charts."""
    if not os.path.exists(DB_PATH):
        return {}
    try:
        conn = sqlite3.connect(DB_PATH)
        seg  = pd.read_sql("""
            SELECT segment,
                   COUNT(*) as total,
                   SUM(churn) as churned,
                   ROUND(AVG(nps_score),2) as avg_nps
            FROM customers GROUP BY segment
        """, conn)
        seg["churn_rate"] = (seg["churned"] / seg["total"] * 100).round(2)

        city = pd.read_sql("""
            SELECT city,
                   COUNT(*) as total,
                   SUM(churn) as churned
            FROM customers GROUP BY city
        """, conn)
        city["churn_rate"] = (city["churned"] / city["total"] * 100).round(2)

        spend = pd.read_sql("""
            SELECT category, ROUND(SUM(amount),2) as total_spend
            FROM transactions GROUP BY category
            ORDER BY total_spend DESC
        """, conn)

        trend = pd.read_sql("""
            SELECT SUBSTR(transaction_date,1,7) as month,
                   ROUND(SUM(amount),2) as total_spend,
                   COUNT(*) as txn_count
            FROM transactions
            GROUP BY month ORDER BY month
        """, conn)

        emp = pd.read_sql("""
            SELECT department,
                   ROUND(AVG(quality_score),1) as avg_quality,
                   ROUND(AVG(CAST(achieved_amount AS FLOAT)/
                         CAST(target_amount AS FLOAT)*100),1) as achievement_pct
            FROM employee_performance GROUP BY department
        """, conn)

        conn.close()
        return {
            "segment": seg, "city": city,
            "spend": spend, "trend": trend, "emp": emp
        }
    except Exception as e:
        return {"error": str(e)}


# ===========================================================================
# Sidebar — filters & quick info
# ===========================================================================
def render_sidebar(summary):
    with st.sidebar:
        st.markdown("""
        <div style="padding:20px 0 10px;">
          <div style="font-size:22px; font-weight:700; 
                      letter-spacing:-0.5px;">🏦 BankSight AI</div>
          <div style="font-size:11px; opacity:0.55; margin-top:4px;">
            Agentic Banking Analytics
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # DB status
        if os.path.exists(DB_PATH):
            st.success("✅ Database connected")
        else:
            st.error("❌ Database not found")
            st.caption("Run: `python data/setup_db.py`")
            return {}

        # Quick stats
        if summary and "error" not in summary:
            st.markdown("**📊 Dataset Overview**")
            st.caption(f"Customers: {summary['total_customers']:,}")
            st.caption(f"Churned: {summary['total_churned']:,} "
                       f"({summary['churn_rate']}%)")
            st.caption(f"Transactions: {summary['txn_count']:,}")
            st.caption(f"Anomaly txns: {summary['anomaly_txns']:,}")

        st.divider()
        st.markdown("**🔍 Filters**")

        # Filters
        segments = ["All", "Premium", "Standard", "Basic"]
        cities   = ["All", "Delhi", "Mumbai", "Bengaluru",
                    "Gurugram", "Pune", "Hyderabad", "Chennai", "Kolkata"]

        filters = {
            "segment": st.selectbox("Segment", segments),
            "city":    st.selectbox("City",    cities),
            "churn_only": st.checkbox("Churned customers only", value=False),
            "nps_max":    st.slider("Max NPS score", 0, 10, 10),
        }

        # Convert "All" to None
        filters["segment"] = None if filters["segment"] == "All" else filters["segment"]
        filters["city"]    = None if filters["city"]    == "All" else filters["city"]

        st.divider()

        # Output format
        st.markdown("**📁 Report Outputs**")
        formats = st.multiselect(
            "Generate formats",
            ["excel", "pdf", "csv"],
            default=["excel", "csv"]
        )
        filters["formats"] = formats

        st.divider()
        st.markdown("""
        <div style="font-size:10px; opacity:0.45; text-align:center;">
          BankSight AI v1.0<br>
          Powered by Claude Sonnet
        </div>
        """, unsafe_allow_html=True)

    return filters


# ===========================================================================
# Dashboard header
# ===========================================================================
def render_header(summary):
    st.markdown("""
    <div class="bs-header">
      <div class="bs-header-icon">🏦</div>
      <div>
        <p class="bs-header-title">BankSight AI</p>
        <p class="bs-header-sub">
          Agentic Banking Analytics Assistant — 
          Powered by Claude Code · SQL · Analysis · Anomaly · Report Agents
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not summary or "error" in summary:
        st.warning("⚠️ Database not connected. Run `python data/setup_db.py` first.")
        return

    # Metric cards
    status    = summary["churn_status"].lower()
    c1,c2,c3,c4,c5 = st.columns(5)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Total Customers</div>
          <div class="metric-value">{summary['total_customers']:,}</div>
          <div class="metric-delta">Full dataset</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card {status}">
          <div class="metric-label">Churn Rate</div>
          <div class="metric-value">{summary['churn_rate']}%</div>
          <div class="metric-delta {'up' if summary['churn_rate']>21 else 'down'}">
            Baseline: 21.00%
          </div>
        </div>""", unsafe_allow_html=True)

    with c3:
        nps_cls = "critical" if summary["avg_nps"] <= 3 else "normal"
        st.markdown(f"""
        <div class="metric-card {nps_cls}">
          <div class="metric-label">Avg NPS Score</div>
          <div class="metric-value">{summary['avg_nps']}/10</div>
          <div class="metric-delta">Risk floor: 3.0</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        stress_cls = "warning" if summary["emi_stress"] > 30 else "normal"
        st.markdown(f"""
        <div class="metric-card {stress_cls}">
          <div class="metric-label">EMI Stress Rate</div>
          <div class="metric-value">{summary['emi_stress']}%</div>
          <div class="metric-delta">Missed + Delayed</div>
        </div>""", unsafe_allow_html=True)

    with c5:
        ano_pct = round(summary["anomaly_txns"] / summary["txn_count"] * 100, 1)
        ano_cls = "warning" if ano_pct > 5 else "normal"
        st.markdown(f"""
        <div class="metric-card {ano_cls}">
          <div class="metric-label">Anomaly Transactions</div>
          <div class="metric-value">{summary['anomaly_txns']:,}</div>
          <div class="metric-delta">{ano_pct}% of total txns</div>
        </div>""", unsafe_allow_html=True)


# ===========================================================================
# Dashboard charts
# ===========================================================================
def render_charts(chart_data):
    if not chart_data or "error" in chart_data:
        return

    st.markdown('<div class="section-head">📊 Analytics Overview</div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    # Chart 1 — Churn rate by segment
    with c1:
        seg = chart_data.get("segment", pd.DataFrame())
        if not seg.empty:
            colors_map = {
                "Premium":  "#D93025",
                "Standard": "#F5A623",
                "Basic":    "#1E8A44",
            }
            fig = px.bar(
                seg, x="segment", y="churn_rate",
                color="segment",
                color_discrete_map=colors_map,
                title="Churn Rate by Segment (%)",
                text=seg["churn_rate"].apply(lambda x: f"{x}%"),
                labels={"churn_rate": "Churn Rate (%)", "segment": "Segment"},
            )
            fig.add_hline(y=21, line_dash="dash", line_color="#6B7A99",
                          annotation_text="Baseline 21%",
                          annotation_position="bottom right",
                          annotation_font_size=11,
                          annotation_font_color="#6B7A99")
            fig.add_hline(y=25, line_dash="dot", line_color="#D93025",
                          annotation_text="Critical 25%",
                          annotation_position="bottom left",
                          annotation_font_size=11,
                          annotation_font_color="#D93025")
            fig.update_layout(
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                font_family="DM Sans", showlegend=False,
                title_font_size=14, title_font_color="#1F3864",
                margin=dict(t=40, b=20, l=10, r=10),
                height=300,
                yaxis=dict(range=[0, 32]),
            )
            fig.update_traces(textposition="outside", textfont_size=12)
            st.plotly_chart(fig, use_container_width=True)

    # Chart 2 — Churn rate by city
    with c2:
        city = chart_data.get("city", pd.DataFrame())
        if not city.empty:
            city_sorted = city.sort_values("churn_rate", ascending=True)
            fig2 = px.bar(
                city_sorted, x="churn_rate", y="city",
                orientation="h",
                title="Churn Rate by City (%)",
                labels={"churn_rate": "Churn Rate (%)", "city": "City"},
                color="churn_rate",
                color_continuous_scale=["#1E8A44", "#F5A623", "#D93025"],
            )
            fig2.add_vline(x=21, line_dash="dash", line_color="#6B7A99")
            fig2.update_layout(
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                font_family="DM Sans", showlegend=False,
                coloraxis_showscale=False,
                title_font_size=14, title_font_color="#1F3864",
                margin=dict(t=40, b=20, l=10, r=10),
                height=280,
            )
            st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)

    # Chart 3 — Spend by category (donut)
    with c3:
        spend = chart_data.get("spend", pd.DataFrame())
        if not spend.empty:
            fig3 = px.pie(
                spend, names="category", values="total_spend",
                title="Spend by Category (INR)",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig3.update_layout(
                font_family="DM Sans",
                title_font_size=14, title_font_color="#1F3864",
                margin=dict(t=40, b=20, l=10, r=10),
                height=280,
                legend=dict(orientation="h", yanchor="bottom",
                            y=-0.2, xanchor="center", x=0.5),
            )
            fig3.update_traces(
                textposition="inside", textinfo="percent",
                hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<extra></extra>",
            )
            st.plotly_chart(fig3, use_container_width=True)

    # Chart 4 — Monthly spend trend
    with c4:
        trend = chart_data.get("trend", pd.DataFrame())
        if not trend.empty:
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(
                x=trend["month"], y=trend["total_spend"],
                mode="lines+markers",
                name="Monthly Spend (₹)",
                line=dict(color="#1F3864", width=2.5),
                marker=dict(size=6, color="#3A6BC4"),
                fill="tozeroy",
                fillcolor="rgba(31,56,100,0.07)",
                hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<extra></extra>",
            ))
            fig4.update_layout(
                title="Monthly Transaction Spend (INR)",
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                font_family="DM Sans",
                title_font_size=14, title_font_color="#1F3864",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#F0F4FB"),
                margin=dict(t=40, b=20, l=10, r=10),
                height=280, showlegend=False,
            )
            st.plotly_chart(fig4, use_container_width=True)


# ===========================================================================
# Skill quick-launch buttons
# ===========================================================================
SKILLS = [
    {"icon": "📉", "label": "Churn Report",
     "key": "churn",
     "prompt": "Run a full churn analysis report for all customers"},
    {"icon": "🔍", "label": "Analyze",
     "key": "analyze",
     "prompt": "Analyze the overall banking data — key metrics, trends, and insights"},
    {"icon": "📈", "label": "Trend",
     "key": "trend",
     "prompt": "Show monthly spend trends and transaction patterns for 2024"},
    {"icon": "⚠️", "label": "Anomaly",
     "key": "anomaly",
     "prompt": "Detect anomalies — spend spikes, churn risk combos, and EMI stress"},
]

def render_skill_buttons():
    st.markdown('<div class="section-head">⚡ Quick Skills</div>',
                unsafe_allow_html=True)
    cols = st.columns(len(SKILLS))
    for i, skill in enumerate(SKILLS):
        with cols[i]:
            if st.button(
                f"{skill['icon']}  {skill['label']}",
                key=f"skill_{skill['key']}",
                use_container_width=True,
            ):
                st.session_state.active_skill = skill["prompt"]


# ===========================================================================
# Pipeline runner
# ===========================================================================
def run_pipeline(user_query: str, filters: dict, formats: list) -> dict:
    """Runs the full SQL → Analysis → Anomaly → Report pipeline."""

    # Build filter dict for agents
    agent_filters = {}
    if filters.get("segment"):
        agent_filters["segment"] = filters["segment"]
    if filters.get("city"):
        agent_filters["city"] = filters["city"]

    # Enrich query with filter context
    enriched_query = user_query
    if filters.get("churn_only"):
        enriched_query += " (filter: churned customers only, churn=1)"
    if filters.get("nps_max", 10) < 10:
        enriched_query += f" (filter: NPS score <= {filters['nps_max']})"

    results = {}

    # Step 1 — SQL Agent
    sql_out = run_sql_agent(
        enriched_query, filters=agent_filters, verbose=False)
    results["sql"] = sql_out

    if sql_out["status"] == "empty":
        results["message"] = sql_out["message"]
        return results

    if sql_out["status"] == "error":
        results["message"] = sql_out["message"]
        return results

    # Step 2 — Analysis Agent
    context = ("churn"    if "churn"    in user_query.lower()
               else "trend"    if "trend"    in user_query.lower()
               else "employee" if "employee" in user_query.lower()
               else "spend"    if "spend"    in user_query.lower()
               else "general")

    analysis_out = run_analysis_agent(
        sql_out, context=context, verbose=False)
    results["analysis"] = analysis_out

    # Step 3 — Anomaly Agent
    anomaly_out = run_anomaly_agent(
        sql_out, analysis_out, verbose=False)
    results["anomaly"] = anomaly_out

    # Step 4 — Report Agent (if formats requested)
    if formats:
        report_out = run_report_agent(
            sql_output=sql_out,
            analysis_output=analysis_out,
            anomaly_output=anomaly_out,
            report_config={
                "formats":      formats,
                "report_type":  context,
                "period_label": datetime.now().strftime("%b %Y"),
            },
            verbose=False,
        )
        results["report"] = report_out

    return results


# ===========================================================================
# Chat message renderer
# ===========================================================================
def render_agent_response(results: dict):
    """Renders structured pipeline results as formatted chat response."""

    sql = results.get("sql", {})
    ana = results.get("analysis", {})
    ano = results.get("anomaly", {})
    rep = results.get("report", {})

    # Error / empty handling
    if sql.get("status") == "error":
        st.error(f"❌ SQL Agent: {sql.get('message')}")
        return
    if sql.get("status") == "empty":
        st.info(f"ℹ️ {sql.get('message')}")
        return

    # SQL Agent summary
    st.markdown(
        f'<span class="agent-tag tag-sql">🗄 SQL Agent</span> '
        f'Returned **{sql["row_count"]:,} records** in {sql["time_taken"]}s',
        unsafe_allow_html=True)

    # Analysis summary
    if ana and ana.get("status") == "success":
        st.markdown(
            '<span class="agent-tag tag-analysis">📊 Analysis Agent</span>',
            unsafe_allow_html=True)
        km     = ana.get("key_metrics", {})
        status = km.get("status", "NORMAL")
        badge  = (f'<span class="badge-{status.lower()}">{status}</span>'
                  if status in ("CRITICAL","WARNING","NORMAL") else "")

        st.markdown(
            f"{badge} {ana.get('summary', '')}",
            unsafe_allow_html=True)

        if ana.get("top_findings"):
            with st.expander("📋 Key Findings", expanded=True):
                for i, f in enumerate(ana["top_findings"], 1):
                    st.markdown(f"**{i}.** {f}")

        if ana.get("recommendations"):
            with st.expander("💡 Recommendations"):
                for i, r in enumerate(ana["recommendations"], 1):
                    st.markdown(f"**{i}.** {r}")

    # Data table
    df = sql["dataframe"]
    with st.expander(f"🗂 Raw Data ({len(df):,} rows)", expanded=False):
        # Format INR columns
        inr_cols = [c for c in df.columns
                    if c in ("balance","estimated_salary","loan_amount",
                             "emi_amount","amount","target_amount","achieved_amount")]
        display_df = df.copy()
        for col in inr_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: f"₹{x:,.2f}" if pd.notna(x) else "")
        if "nps_score" in display_df.columns:
            display_df["nps_score"] = display_df["nps_score"].apply(
                lambda x: f"{int(x)}/10" if pd.notna(x) else "")
        st.dataframe(display_df, use_container_width=True, height=300)

    # Inline chart from query results
    _render_inline_chart(df)

    # Anomaly Agent results
    if ano and ano.get("status") == "success":
        st.markdown(
            f'<span class="agent-tag tag-anomaly">⚠️ Anomaly Agent</span> '
            f'Detected **{len(ano["anomalies"])}** anomaly/anomalies — '
            f'{ano["critical_count"]} CRITICAL, {ano["warning_count"]} WARNING',
            unsafe_allow_html=True)

        if ano["anomalies"]:
            with st.expander("🚨 Anomaly Details", expanded=ano["critical_count"] > 0):
                for a in ano["anomalies"]:
                    sev = a.get("severity", "NORMAL")
                    icon = ("🔴" if sev == "CRITICAL"
                            else "🟡" if sev == "WARNING" else "🟢")
                    st.markdown(
                        f"{icon} **{a.get('anomaly_id')}** — "
                        f"{a.get('description')}  \n"
                        f"*Action: {a.get('action')}*")

    # Report Agent — download buttons
    if rep and rep.get("status") in ("success", "partial"):
        st.markdown(
            '<span class="agent-tag tag-report">📁 Report Agent</span>',
            unsafe_allow_html=True)
        for f in rep.get("files_generated", []):
            fpath = f["path"]
            ftype = f["type"].upper()
            fsize = f["size_kb"]
            if os.path.exists(fpath):
                with open(fpath, "rb") as fh:
                    data = fh.read()
                mime = {
                    "EXCEL": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "PDF":   "application/pdf",
                    "CSV":   "text/csv",
                }.get(ftype, "application/octet-stream")
                st.download_button(
                    label=f"⬇️ Download {ftype} ({fsize} KB)",
                    data=data,
                    file_name=os.path.basename(fpath),
                    mime=mime,
                    key=f"dl_{ftype}_{id(fpath)}",
                )


def _render_inline_chart(df: pd.DataFrame):
    """Auto-detect best chart from DataFrame columns."""
    if len(df) < 2:
        return

    # Churn by segment bar chart
    if "segment" in df.columns and "churn" in df.columns and len(df) > 10:
        seg = df.groupby("segment")["churn"].agg(
            ["sum","count"]).reset_index()
        seg["churn_rate"] = (seg["sum"] / seg["count"] * 100).round(2)
        fig = px.bar(
            seg, x="segment", y="churn_rate",
            color="segment", title="Churn Rate by Segment (%)",
            color_discrete_sequence=["#D93025","#F5A623","#1E8A44"],
            text=seg["churn_rate"].apply(lambda x: f"{x}%"),
        )
        fig.add_hline(y=21, line_dash="dash", line_color="#6B7A99",
                      annotation_text="Baseline 21%",
                      annotation_position="bottom right",
                      annotation_font_size=11,
                      annotation_font_color="#6B7A99")
        fig.update_layout(
            height=280, showlegend=False,
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
            margin=dict(t=36,b=10,l=10,r=10),
            font_family="DM Sans",
            yaxis=dict(range=[0, 32]),
        )
        fig.update_traces(textposition="outside", textfont_size=12)
        st.plotly_chart(fig, use_container_width=True)

    # Transaction spend trend
    elif ("transaction_date" in df.columns and "amount" in df.columns
          and len(df) > 5):
        df2 = df.copy()
        df2["month"] = pd.to_datetime(
            df2["transaction_date"], errors="coerce"
        ).dt.strftime("%Y-%m")
        monthly = df2.groupby("month")["amount"].sum().reset_index()
        monthly.columns = ["month","total_spend"]
        if len(monthly) > 1:
            fig = px.line(
                monthly, x="month", y="total_spend",
                title="Transaction Spend Trend (INR)",
                markers=True,
                color_discrete_sequence=["#1F3864"],
            )
            fig.update_layout(
                height=260, showlegend=False,
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                margin=dict(t=36,b=10,l=10,r=10),
                font_family="DM Sans",
            )
            fig.update_traces(
                fill="tozeroy",
                fillcolor="rgba(31,56,100,0.07)")
            st.plotly_chart(fig, use_container_width=True)

    # City churn horizontal bar
    elif "city" in df.columns and "churn" in df.columns and len(df) > 10:
        city = df.groupby("city")["churn"].agg(
            ["sum","count"]).reset_index()
        city["churn_rate"] = (city["sum"] / city["count"] * 100).round(2)
        city = city.sort_values("churn_rate")
        fig = px.bar(
            city, x="churn_rate", y="city",
            orientation="h",
            title="Churn Rate by City (%)",
            color="churn_rate",
            color_continuous_scale=["#1E8A44","#F5A623","#D93025"],
        )
        fig.add_vline(x=21, line_dash="dash", line_color="#6B7A99")
        fig.update_layout(
            height=260, showlegend=False,
            coloraxis_showscale=False,
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
            margin=dict(t=36,b=10,l=10,r=10),
            font_family="DM Sans",
        )
        st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# Chat interface
# ===========================================================================
def render_chat(filters: dict):
    st.markdown('<div class="section-head">💬 Chat with BankSight AI</div>',
                unsafe_allow_html=True)

    # Display chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-user">{msg["content"]}</div>',
                unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown('<div class="chat-ai">', unsafe_allow_html=True)
                # Re-render stored result
                if isinstance(msg.get("results"), dict):
                    render_agent_response(msg["results"])
                else:
                    st.markdown(msg["content"])
                st.markdown("</div>", unsafe_allow_html=True)

    # Handle skill button trigger
    if st.session_state.active_skill:
        prompt = st.session_state.active_skill
        st.session_state.active_skill = None
        _process_query(prompt, filters)
        st.rerun()

    # Chat input
    col_input, col_clear = st.columns([5, 1])
    with col_input:
        user_input = st.chat_input(
            "Ask anything… e.g. 'Show top 10 churned Premium customers'")
    with col_clear:
        if st.button("🗑️ Clear", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()

    if user_input:
        _process_query(user_input, filters)
        st.rerun()


def _process_query(query: str, filters: dict):
    """Add user message, run pipeline, store results."""
    st.session_state.messages.append({
        "role":    "user",
        "content": query,
    })

    formats = filters.get("formats", ["excel", "csv"])

    with st.spinner("🤖 Running agent pipeline…"):
        results = run_pipeline(query, filters, formats)

    st.session_state.messages.append({
        "role":    "assistant",
        "content": "pipeline_result",
        "results": results,
    })

    # Store latest outputs in session state
    st.session_state.last_sql_output = results.get("sql")
    st.session_state.last_analysis   = results.get("analysis")
    st.session_state.last_anomaly    = results.get("anomaly")
    st.session_state.last_report     = results.get("report")


# ===========================================================================
# Main
# ===========================================================================
def main():
    # Load data
    summary    = load_db_summary()
    chart_data = load_chart_data()

    # Sidebar filters
    filters = render_sidebar(summary)

    # Header metrics
    render_header(summary)

    # Dashboard charts
    if summary and "error" not in summary:
        render_charts(chart_data)

    # Skill quick-launch buttons
    render_skill_buttons()

    st.divider()

    # Chat interface
    render_chat(filters)


if __name__ == "__main__":
    main()
