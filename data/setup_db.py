"""
BankSight AI — Database Setup Script
=====================================
Reads raw CSVs from data/raw/, cleans and transforms them,
then loads all 4 tables into data/banking_mock.db (SQLite).

Run once before starting any agent session:
    python data/setup_db.py

Spec reference: .claude/specs/01-data-setup.md
"""

import os
import sys
import random
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy import create_engine

sys.stdout.reconfigure(encoding="utf-8")

random.seed(42)
fake = Faker("en_IN")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR   = os.path.join(BASE_DIR, "data", "raw")
DB_PATH   = os.path.join(BASE_DIR, "data", "banking_mock.db")

CUSTOMERS_CSV    = os.path.join(RAW_DIR, "customers.csv")
TRANSACTIONS_CSV = os.path.join(RAW_DIR, "transactions.csv")
LOAN_CSV         = os.path.join(RAW_DIR, "loan_emi.csv")

INDIAN_CITIES = [
    "Delhi", "Mumbai", "Bengaluru", "Gurugram",
    "Pune", "Hyderabad", "Chennai", "Kolkata"
]

CHURN_BASELINE   = 0.21   # 21%
CHURN_ALERT      = 0.25   # 25% = CRITICAL
USD_TO_INR       = 83


# ===========================================================================
# Step 1 — customers table
# ===========================================================================
def load_customers():
    print("\n[Step 1] Loading customers table...")

    if not os.path.exists(CUSTOMERS_CSV):
        raise FileNotFoundError(
            f"Missing: {CUSTOMERS_CSV}\n"
            "Download 'Bank Customer Churn Prediction' dataset from Kaggle "
            "and save as data/raw/customers.csv"
        )

    df = pd.read_csv(CUSTOMERS_CSV)
    print(f"  Raw rows: {len(df):,}  |  Columns: {list(df.columns)}")

    # 1a — Replace European locations with Indian cities
    df["city"]    = [random.choice(INDIAN_CITIES) for _ in range(len(df))]
    df["country"] = "India"

    # 1b — Convert USD amounts to INR
    if df["balance"].mean() < 100000:          # still in USD range
        df["balance"]          = (df["balance"]          * USD_TO_INR).round(2)
        df["estimated_salary"] = (df["estimated_salary"] * USD_TO_INR).round(2)

    # 1c — Add missing columns
    df["account_type"] = random.choices(
        ["Savings", "Current", "Salary"],
        weights=[60, 25, 15], k=len(df)
    )
    df["kyc_status"] = random.choices(
        ["Verified", "Pending"],
        weights=[85, 15], k=len(df)
    )

    # 1d — Standardise column names
    rename_map = {
        "Exited":         "churn",
        "CreditScore":    "credit_score",
        "Geography":      "country",
        "Gender":         "gender",
        "Age":            "age",
        "Tenure":         "tenure",
        "Balance":        "balance",
        "NumOfProducts":  "products_number",
        "HasCrCard":      "credit_card",
        "IsActiveMember": "active_member",
        "EstimatedSalary":"estimated_salary",
        "CustomerId":     "customer_id",
        "Surname":        "surname",
        "RowNumber":      "row_number",
    }
    df.rename(columns={k: v for k, v in rename_map.items()
                       if k in df.columns}, inplace=True)

    # Add joining_date if missing
    if "joining_date" not in df.columns:
        base_date = datetime(2018, 1, 1)
        df["joining_date"] = [
            (base_date + timedelta(days=random.randint(0, 365 * 6))
             ).strftime("%d-%m-%Y")
            for _ in range(len(df))
        ]

    # Add nps_score if missing
    if "nps_score" not in df.columns:
        df["nps_score"] = [random.randint(0, 10) for _ in range(len(df))]

    # Add segment if missing
    if "segment" not in df.columns:
        df["segment"] = random.choices(
            ["Premium", "Standard", "Basic"],
            weights=[51, 13, 36], k=len(df)
        )

    # Drop columns not in schema
    keep_cols = [
        "customer_id", "credit_score", "country", "gender",
        "age", "tenure", "balance", "products_number",
        "credit_card", "active_member", "estimated_salary",
        "churn", "city", "nps_score", "segment",
        "joining_date", "account_type", "kyc_status"
    ]
    df = df[[c for c in keep_cols if c in df.columns]]

    # 1e — Validate
    assert df["churn"].isin([0, 1]).all(),            "Invalid churn values"
    assert df["nps_score"].between(0, 10).all(),      "NPS out of 0-10 range"
    assert df["credit_score"].between(300, 900).all(),"Credit score out of range"
    assert df.isnull().sum().sum() == 0,              "Nulls found in customers"

    churned = df["churn"].sum()
    rate    = round(churned / len(df) * 100, 2)
    print(f"  Rows: {len(df):,}  |  Churned: {churned:,} ({rate}%)  ✅")
    return df


# ===========================================================================
# Step 2 — transactions table
# ===========================================================================
def load_transactions(customers_df):
    print("\n[Step 2] Loading transactions table...")

    customer_ids = customers_df["customer_id"].tolist()

    if os.path.exists(TRANSACTIONS_CSV):
        df = pd.read_csv(TRANSACTIONS_CSV)
        print(f"  Raw rows: {len(df):,}")

        # 2a — Add customer_id FK if missing
        if "customer_id" not in df.columns:
            df["customer_id"] = random.choices(customer_ids, k=len(df))

        # 2b — Standardise category names
        category_map = {
            "Food":          "Food",
            "Travel":        "Travel",
            "Shopping":      "Shopping",
            "Bills":         "Utilities",
            "Entertainment": "Entertainment",
            "Fuel":          "Travel",
            "Grocery":       "Food",
            "Health":        "Healthcare",
        }
        if "category" in df.columns:
            df["category"] = df["category"].map(category_map).fillna("Shopping")
        elif "Exp Type" in df.columns:
            df["category"] = df["Exp Type"].map(category_map).fillna("Shopping")

        # 2c — Standardise amount column
        if "Amount" in df.columns:
            df.rename(columns={"Amount": "amount"}, inplace=True)
        if df["amount"].mean() < 10000:
            df["amount"] = (df["amount"] * USD_TO_INR).round(2)
        df["amount"] = df["amount"].clip(500, 150000)

        # 2d — Standardise date column
        for col in ["Date", "transaction_date", "date"]:
            if col in df.columns:
                df["transaction_date"] = pd.to_datetime(
                    df[col], dayfirst=True, errors="coerce"
                ).dt.strftime("%Y-%m-%d")
                break

    else:
        print("  transactions.csv not found — generating mock data...")
        categories   = ["Food", "Travel", "Shopping", "Utilities",
                        "Healthcare", "Entertainment", "EMI"]
        merchants    = {
            "Food":          ["Swiggy", "Zomato", "Dominos"],
            "Travel":        ["MakeMyTrip", "IRCTC", "Ola"],
            "Shopping":      ["Amazon", "Flipkart", "Myntra"],
            "Utilities":     ["BSES", "Jio", "Airtel"],
            "Healthcare":    ["Apollo", "Practo", "MedPlus"],
            "Entertainment": ["BookMyShow", "Netflix", "Hotstar"],
            "EMI":           ["HDFC EMI", "SBI EMI", "ICICI EMI"],
        }
        rows = []
        start = datetime(2024, 1, 1)
        for i in range(50000):
            cat  = random.choice(categories)
            txn_date = start + timedelta(days=random.randint(0, 364))
            rows.append({
                "transaction_id":   f"TXN{i+1:06d}",
                "customer_id":      random.choice(customer_ids),
                "transaction_date": txn_date.strftime("%Y-%m-%d"),
                "amount":           round(random.uniform(500, 150000), 2),
                "category":         cat,
                "payment_mode":     random.choices(
                    ["Credit Card", "Debit Card", "UPI", "NetBanking"],
                    weights=[40, 20, 30, 10])[0],
                "merchant_name":    random.choice(merchants[cat]),
                "status":           random.choices(
                    ["Success", "Failed", "Reversed"],
                    weights=[92, 5, 3])[0],
            })
        df = pd.DataFrame(rows)

    # 2d — Add payment_mode if missing
    if "payment_mode" not in df.columns:
        df["payment_mode"] = random.choices(
            ["Credit Card", "Debit Card", "UPI", "NetBanking"],
            weights=[40, 20, 30, 10], k=len(df)
        )

    # 2e — Add status if missing
    if "status" not in df.columns:
        df["status"] = random.choices(
            ["Success", "Failed", "Reversed"],
            weights=[92, 5, 3], k=len(df)
        )

    # 2f — Add transaction_id if missing
    if "transaction_id" not in df.columns:
        df["transaction_id"] = [f"TXN{i+1:06d}" for i in range(len(df))]

    # 2g — Add merchant_name if missing
    if "merchant_name" not in df.columns:
        df["merchant_name"] = "Unknown"

    # 2h — Add is_anomaly flag: amount > 2x customer monthly average
    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    df["month_key"] = df["transaction_date"].str[:7]
    monthly_avg = df.groupby(
        ["customer_id", "month_key"]
    )["amount"].transform("mean")
    df["is_anomaly"] = (df["amount"] > 2 * monthly_avg).astype(int)
    df.drop(columns=["month_key"], inplace=True)

    # Keep only schema columns
    keep_cols = [
        "transaction_id", "customer_id", "transaction_date",
        "amount", "category", "payment_mode", "merchant_name",
        "status", "is_anomaly"
    ]
    df = df[[c for c in keep_cols if c in df.columns]]

    anomalies = df["is_anomaly"].sum()
    print(f"  Rows: {len(df):,}  |  Anomalies flagged: {anomalies:,} "
          f"({round(anomalies/len(df)*100,1)}%)  ✅")
    return df


# ===========================================================================
# Step 3 — loan_emi table
# ===========================================================================
def load_loan_emi(customers_df):
    print("\n[Step 3] Loading loan_emi table...")

    customer_ids = customers_df["customer_id"].tolist()

    if os.path.exists(LOAN_CSV):
        df = pd.read_csv(LOAN_CSV)
        print(f"  Raw rows: {len(df):,}")

        # Standardise loan type
        loan_type_map = {
            "MORTGAGE": "Home",   "HOME": "Home",
            "PERSONAL": "Personal",
            "AUTO":     "Auto",
            "CREDIT":   "Credit Card",
        }
        if "loan_type" in df.columns:
            df["loan_type"] = df["loan_type"].str.upper().map(
                loan_type_map).fillna("Personal")

        # Standardise EMI status
        status_map = {
            "Fully Paid":  "Paid",   "Current":    "Paid",
            "Charged Off": "Missed", "Default":    "Missed",
            "Late":        "Delayed","Late (31-60 days)": "Delayed",
            "Late (16-30 days)": "Delayed",
        }
        for col in ["loan_status", "emi_status"]:
            if col in df.columns:
                df["emi_status"] = df[col].map(status_map).fillna("Paid")
                break

        # Convert loan amounts to INR
        if "loan_amnt" in df.columns:
            df["loan_amount"] = (df["loan_amnt"] * USD_TO_INR).round(2)

        # Assign customer_ids
        loan_customers = random.sample(
            customer_ids, min(400, len(df), len(customer_ids)))
        df = df.head(len(loan_customers)).copy()
        df["customer_id"] = loan_customers

    else:
        print("  loan_emi.csv not found — generating mock data...")
        loan_customers = random.sample(customer_ids, min(400, len(customer_ids)))
        rows = []
        start = datetime(2020, 1, 1)
        for i, cid in enumerate(loan_customers):
            loan_amt    = round(random.uniform(100000, 5000000), 2)
            term_months = random.choice([12, 24, 36, 48, 60, 120, 240])
            rate        = round(random.uniform(7.5, 18.0), 2)
            emi_amt     = round(
                loan_amt * (rate/1200) /
                (1 - (1 + rate/1200) ** (-term_months)), 2
            )
            loan_start  = start + timedelta(days=random.randint(0, 365*4))
            loan_end    = loan_start + timedelta(days=term_months * 30)
            rows.append({
                "loan_id":        f"L{i+1:04d}",
                "customer_id":    cid,
                "loan_type":      random.choice(
                    ["Home", "Personal", "Auto", "Credit Card"]),
                "loan_amount":    loan_amt,
                "emi_amount":     emi_amt,
                "emi_due_date":   "15",
                "emi_status":     random.choices(
                    ["Paid", "Missed", "Delayed"],
                    weights=[65, 15, 20])[0],
                "interest_rate":  rate,
                "loan_start_date": loan_start.strftime("%Y-%m-%d"),
                "loan_end_date":  loan_end.strftime("%Y-%m-%d"),
            })
        df = pd.DataFrame(rows)

    # Add loan_id if missing
    if "loan_id" not in df.columns:
        df["loan_id"] = [f"L{i+1:04d}" for i in range(len(df))]

    # Ensure required columns
    if "emi_due_date" not in df.columns:
        df["emi_due_date"] = "15"
    if "interest_rate" not in df.columns:
        df["interest_rate"] = round(random.uniform(7.5, 18.0), 2)

    # Keep only schema columns
    keep_cols = [
        "loan_id", "customer_id", "loan_type", "loan_amount",
        "emi_amount", "emi_due_date", "emi_status",
        "interest_rate", "loan_start_date", "loan_end_date"
    ]
    df = df[[c for c in keep_cols if c in df.columns]]

    missed  = len(df[df["emi_status"] == "Missed"])
    delayed = len(df[df["emi_status"] == "Delayed"])
    stress  = round((missed + delayed) / len(df) * 100, 2)
    print(f"  Rows: {len(df):,}  |  Missed: {missed}  "
          f"Delayed: {delayed}  Stress rate: {stress}%  ✅")
    return df


# ===========================================================================
# Step 4 — employee_performance table (always generated via Faker)
# ===========================================================================
def generate_employee_performance():
    print("\n[Step 4] Generating employee_performance table...")

    departments = ["Loans", "Cards", "Support", "Risk", "Operations"]
    regions     = ["North", "South", "East", "West"]
    months      = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    rows = []

    for emp_num in range(1, 51):
        emp_name = fake.name()
        dept     = random.choice(departments)
        region   = random.choice(regions)

        for month in months:
            target   = random.randint(1000000, 5000000)
            achieved = int(target * random.uniform(0.6, 1.3))
            quality  = random.randint(60, 100)
            complaints = random.randint(0, 20)

            if achieved >= target * 1.1:
                grade = "A"
            elif achieved >= target:
                grade = "B"
            elif achieved >= target * 0.8:
                grade = "C"
            else:
                grade = "D"

            rows.append({
                "employee_id":         f"E{emp_num:03d}",
                "name":                emp_name,
                "department":          dept,
                "region":              region,
                "target_amount":       target,
                "achieved_amount":     achieved,
                "quality_score":       quality,
                "customer_complaints": complaints,
                "month":               month,
                "year":                2024,
                "performance_grade":   grade,
            })

    df = pd.DataFrame(rows)
    grades = df["performance_grade"].value_counts().to_dict()
    print(f"  Rows: {len(df):,}  |  Grade split: {grades}  ✅")
    return df


# ===========================================================================
# Step 5 — Load all tables to SQLite
# ===========================================================================
def load_to_sqlite(customers_df, transactions_df, loan_emi_df, employee_df):
    print(f"\n[Step 5] Loading all tables to {DB_PATH}...")

    engine = create_engine(f"sqlite:///{DB_PATH}")

    # Load in dependency order — customers first
    customers_df.to_sql(
        "customers", engine, if_exists="replace", index=False)
    print("  customers table loaded ✅")

    transactions_df.to_sql(
        "transactions", engine, if_exists="replace", index=False)
    print("  transactions table loaded ✅")

    loan_emi_df.to_sql(
        "loan_emi", engine, if_exists="replace", index=False)
    print("  loan_emi table loaded ✅")

    employee_df.to_sql(
        "employee_performance", engine, if_exists="replace", index=False)
    print("  employee_performance table loaded ✅")


# ===========================================================================
# Step 6 — Post-setup validation
# ===========================================================================
def validate_db():
    print(f"\n[Step 6] Validating {DB_PATH}...")

    conn = sqlite3.connect(DB_PATH)

    checks = {
        "customers rows":          "SELECT COUNT(*) FROM customers",
        "churned customers":       "SELECT COUNT(*) FROM customers WHERE churn=1",
        "transactions rows":       "SELECT COUNT(*) FROM transactions",
        "anomaly flagged txns":    "SELECT COUNT(*) FROM transactions WHERE is_anomaly=1",
        "loan_emi rows":           "SELECT COUNT(*) FROM loan_emi",
        "missed EMI count":        "SELECT COUNT(*) FROM loan_emi WHERE emi_status='Missed'",
        "employee rows":           "SELECT COUNT(*) FROM employee_performance",
        "orphan transactions":     """
            SELECT COUNT(*) FROM transactions t
            LEFT JOIN customers c ON t.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
        """,
    }

    all_passed = True
    for label, query in checks.items():
        result = conn.execute(query).fetchone()[0]
        status = "✅" if result > 0 or "orphan" in label else "⚠️"
        if "orphan" in label and result > 0:
            status = "⚠️  WARNING"
            all_passed = False
        print(f"  {label:<30} {result:>8,}  {status}")

    conn.close()

    if all_passed:
        print("\n  All validations passed ✅")
    else:
        print("\n  ⚠️  Some validations need attention — check orphan transactions")

    return all_passed


# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("BankSight AI — Database Setup")
    print("=" * 60)
    print(f"Database path: {DB_PATH}")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    customers_df    = load_customers()
    transactions_df = load_transactions(customers_df)
    loan_emi_df     = load_loan_emi(customers_df)
    employee_df     = generate_employee_performance()

    load_to_sqlite(customers_df, transactions_df, loan_emi_df, employee_df)
    validate_db()

    print("\n" + "=" * 60)
    print("Setup complete! banking_mock.db is ready.")
    print("Next step: streamlit run app.py")
    print("=" * 60)
