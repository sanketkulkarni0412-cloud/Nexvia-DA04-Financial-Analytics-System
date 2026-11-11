"""
Inspect all 32 footer rows from accepted_2007_to_2018Q4.csv
Examines exact row index, line content, and why they occur.
"""
import pandas as pd
import json

accepted_path = "dataset/raw/accepted_2007_to_2018Q4.csv"

# Stream to the last chunk
last_chunk = None
total_rows = 0

for chunk in pd.read_csv(accepted_path, chunksize=100000, low_memory=False):
    total_rows += len(chunk)
    last_chunk = chunk

null_mask = last_chunk["loan_amnt"].isnull()
null_rows = last_chunk[null_mask]

print(f"Total rows parsed in file: {total_rows}")
print(f"Number of null loan_amnt rows in last chunk: {len(null_rows)}")

footers_list = []
for idx, (original_idx, row) in enumerate(null_rows.iterrows()):
    non_null_cols = {col: str(val) for col, val in row.items() if pd.notnull(val)}
    footers_list.append({
        "footer_num": idx + 1,
        "chunk_row_index": int(original_idx),
        "non_null_fields": non_null_cols
    })
    print(f"Footer #{idx+1}: {non_null_cols}")

with open("reports/inspect_footers.json", "w", encoding="utf-8") as f:
    json.dump(footers_list, f, indent=2)

print("\nWrote details to reports/inspect_footers.json")
