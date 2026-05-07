import pandas as pd
import sqlite3
import numpy as np

# Load CSV
df = pd.read_csv(r"C:\Users\manish.jangir\Downloads\Bank Customer Churn Prediction_v2.csv")

print(f"Loaded {len(df)} rows")
print(f"Columns: {df.columns.tolist()}")

rng = np.random.default_rng(seed=42)

# 1. Replace country and city with Indian cities
indian_cities = ["Delhi", "Mumbai", "Bengaluru", "Gurugram", "Pune", "Hyderabad"]
df["country"] = "India"
df["city"] = rng.choice(indian_cities, size=len(df))

# 2. Convert balance and estimated_salary from USD to INR
USD_TO_INR = 94.28
df["balance"] = (df["balance"] * USD_TO_INR).round(2)
df["estimated_salary"] = (df["estimated_salary"] * USD_TO_INR).round(2)

# 3. Add account_type: Savings / Current / Salary (equal-ish split)
account_types = rng.choice(["Savings", "Current", "Salary"], size=len(df), p=[0.5, 0.3, 0.2])
df["account_type"] = account_types

# 4. Add kyc_status: Verified (85%) / Pending (15%)
kyc_status = rng.choice(["Verified", "Pending"], size=len(df), p=[0.85, 0.15])
df["kyc_status"] = kyc_status

print("\nSample after transformation:")
print(df[["customer_id", "country", "city", "balance", "estimated_salary", "account_type", "kyc_status"]].head(5))
print(f"\naccount_type counts:\n{df['account_type'].value_counts()}")
print(f"\nkyc_status counts:\n{df['kyc_status'].value_counts()}")
print(f"\ncity counts:\n{df['city'].value_counts()}")

# 5. Save to banking_mock.db as customers table
db_path = r"D:\BankSight AI Project\banking_mock.db"
conn = sqlite3.connect(db_path)
df.to_sql("customers", conn, if_exists="replace", index=False)
conn.close()

print(f"\nSaved {len(df)} rows to {db_path} -> customers table")
