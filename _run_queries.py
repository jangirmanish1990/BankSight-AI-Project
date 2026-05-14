import sqlite3
import pandas as pd

db_path = r"D:\BankSight AI Project\banking_mock.db"
conn = sqlite3.connect(db_path)

queries = {
    "Q1 Overall Churn Rate": '''
        SELECT churn, COUNT(*) as count,
               ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM customers),2) as pct
        FROM customers GROUP BY churn
    ''',
    "Q2 Churn by Segment": '''
        SELECT segment, COUNT(*) as total, SUM(churn) as churned,
               ROUND(SUM(churn)*100.0/COUNT(*),2) as churn_rate
        FROM customers GROUP BY segment ORDER BY churn_rate DESC
    ''',
    "Q3 Churn by City Top 10": '''
        SELECT city, COUNT(*) as total, SUM(churn) as churned,
               ROUND(SUM(churn)*100.0/COUNT(*),2) as churn_rate
        FROM customers GROUP BY city ORDER BY churn_rate DESC LIMIT 10
    ''',
    "Q4 Churn by Age Group": '''
        SELECT CASE WHEN age < 30 THEN "Under 30"
                    WHEN age BETWEEN 30 AND 45 THEN "30-45"
                    WHEN age BETWEEN 46 AND 60 THEN "46-60"
                    ELSE "Over 60" END as age_group,
               COUNT(*) as total, SUM(churn) as churned,
               ROUND(SUM(churn)*100.0/COUNT(*),2) as churn_rate
        FROM customers GROUP BY age_group ORDER BY churn_rate DESC
    ''',
    "Q5 Churn by NPS Bucket": '''
        SELECT CASE WHEN nps_score <= 3 THEN "Detractor (0-3)"
                    WHEN nps_score <= 6 THEN "Passive (4-6)"
                    ELSE "Promoter (7-10)" END as nps_bucket,
               COUNT(*) as total, SUM(churn) as churned,
               ROUND(SUM(churn)*100.0/COUNT(*),2) as churn_rate
        FROM customers GROUP BY nps_bucket ORDER BY churn_rate DESC
    ''',
    "Q6 Avg Balance Credit Score NPS Churned vs Retained": '''
        SELECT churn, ROUND(AVG(balance),0) as avg_balance_inr,
               ROUND(AVG(credit_score),0) as avg_credit_score,
               ROUND(AVG(nps_score),1) as avg_nps
        FROM customers GROUP BY churn
    '''
}

for label, sql in queries.items():
    df = pd.read_sql_query(sql, conn)
    print("")
    print("=" * 68)
    print("  " + label)
    print("=" * 68)
    print(df.to_string(index=False))
    print("  Rows: " + str(len(df)))

conn.close()
