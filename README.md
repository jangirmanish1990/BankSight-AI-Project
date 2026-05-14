# 🏦 BankSight AI — Agentic Banking Analytics Assistant

> A conversational AI system built with Claude Code that takes natural
> language queries, orchestrates specialised subagents, and delivers
> automated banking analytics reports.

## 🎯 Live Demo
👉 [Launch BankSight AI](https://your-app.streamlit.app)

## 🏗️ Architecture

User Query → Orchestrator (Claude Code)
                    ↓
             SQL Agent (NL→SQL)
                    ↓
        ┌───────────┴───────────┐
   Analysis Agent         Anomaly Agent
   (Insights)             (Risk Detection)
        └───────────┬───────────┘
               Report Agent
          (Excel + PDF + CSV)
                    ↓
            Power BI Dashboard

## 🤖 Agentic AI Stack
- **Claude Code** — orchestration, subagents, skills, CLAUDE.md
- **4 Specialised Agents** — SQL, Analysis, Anomaly, Report
- **Custom Skills** — /churn-report, /analyze, /trend, /anomaly
- **MCP Integration** — Google Drive auto-upload

## 📊 Analytics Stack
- **Data** — SQLite (3,225 customers, 50K transactions, 400 loans)
- **BI** — Power BI dashboard with live CSV refresh
- **Visualisation** — Plotly charts in Streamlit UI
- **Reports** — Auto-generated Excel (5 sheets) + PDF (4 pages)

## 🛠️ Tech Stack
Claude Code · Python · SQLite · Streamlit · OpenAI API
Pandas · Plotly · openpyxl · ReportLab · SQLAlchemy

## 📁 Project Structure
.claude/
├── agents/          ← 4 agent definitions (.md)
├── skills/          ← /churn-report, /analyze, /trend, /anomaly
└── specs/           ← data setup + agent design specs

agents/
├── sql_agent.py     ← NL → SQL → DataFrame
├── analysis_agent.py← DataFrame → Insights
├── anomaly_agent.py ← Anomaly detection (9 rules)
└── report_agent.py  ← Excel + PDF + CSV generation

data/
└── setup_db.py      ← loads Kaggle CSVs → SQLite

app.py               ← Streamlit UI (dashboard + chat)

## 🚀 Run Locally
# 1. Clone
git clone https://github.com/your-username/banksight-ai.git
cd banksight-ai

# 2. Install
pip install -r requirements.txt

# 3. Set API key
echo "OPENAI_API_KEY=your-key" > .env

# 4. Setup database
python data/setup_db.py

# 5. Launch
streamlit run app.py

## 👤 Built By
Manish Jangir — Data Analytics Lead, Coforge Limited
[LinkedIn](https://linkedin.com/in/your-profile) |
[GitHub](https://github.com/your-username)

## 📌 Domain Context
Built on 6+ years of BFSI analytics experience (Moody's Analytics,
Fifth Third Bank). Mock dataset modelled on real banking use cases:
credit card churn, EMI stress, NPS scoring, employee scorecards.