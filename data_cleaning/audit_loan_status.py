"""
Compute exact value counts of loan_status across the entire accepted_2007_to_2018Q4.csv dataset.
"""
import pandas as pd
import json

accepted_path = "dataset/raw/accepted_2007_to_2018Q4.csv"
status_counts = {}

for chunk in pd.read_csv(accepted_path, chunksize=200000, usecols=["loan_status", "loan_amnt"], low_memory=False):
    # Only valid loans (non-null loan_amnt)
    valid_chunk = chunk[chunk["loan_amnt"].notnull()]
    counts = valid_chunk["loan_status"].value_counts(dropna=False)
    for status, count in counts.items():
        status_counts[str(status)] = status_counts.get(str(status), 0) + int(count)

print("Exact loan_status distribution across valid loans:")
for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
    pct = count / 2260668 * 100
    print(f"  {status}: {count:,} ({pct:.3f}%)")

with open("reports/loan_status_distribution.json", "w", encoding="utf-8") as f:
    json.dump(status_counts, f, indent=2)
