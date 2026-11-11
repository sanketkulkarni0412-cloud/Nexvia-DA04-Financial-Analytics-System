"""
Scan the complete accepted_2007_to_2018Q4.csv dataset for:
1. All rows where loan_amnt is null
2. All rows where id contains non-numeric strings
3. All rows with missing key fields
4. Exact count of records, sum of loan_amnt, sum of total_pymnt, etc.
"""
import pandas as pd
import json

accepted_path = "dataset/raw/accepted_2007_to_2018Q4.csv"

total_rows = 0
null_loan_amnt_rows = []
non_numeric_id_rows = []

chunk_idx = 0
total_loan_amnt = 0.0
total_total_pymnt = 0.0
total_funded_amnt = 0.0
total_funded_amnt_inv = 0.0
total_total_rec_prncp = 0.0
total_total_rec_int = 0.0
total_total_rec_late_fee = 0.0
total_recoveries = 0.0

for chunk in pd.read_csv(accepted_path, chunksize=100000, low_memory=False):
    # Check null loan_amnt
    null_mask = chunk["loan_amnt"].isnull()
    if null_mask.any():
        for sub_idx, row in chunk[null_mask].iterrows():
            null_loan_amnt_rows.append({
                "chunk": chunk_idx,
                "global_row_idx": total_rows + (sub_idx - chunk.index[0]),
                "id": str(row.get("id")),
                "loan_amnt": str(row.get("loan_amnt")),
                "term": str(row.get("term"))
            })
            
    # Check non-numeric id
    clean_chunk = chunk[~null_mask]
    non_num_mask = ~clean_chunk["id"].astype(str).str.isdigit()
    if non_num_mask.any():
        for sub_idx, row in clean_chunk[non_num_mask].iterrows():
            non_numeric_id_rows.append({
                "chunk": chunk_idx,
                "global_row_idx": total_rows + (sub_idx - clean_chunk.index[0]),
                "id": str(row.get("id")),
                "loan_amnt": str(row.get("loan_amnt"))
            })
            
    # Accumulate sums
    total_loan_amnt += clean_chunk["loan_amnt"].sum()
    total_funded_amnt += clean_chunk["funded_amnt"].sum()
    total_funded_amnt_inv += clean_chunk["funded_amnt_inv"].sum()
    total_total_pymnt += clean_chunk["total_pymnt"].sum()
    total_total_rec_prncp += clean_chunk["total_rec_prncp"].sum()
    total_total_rec_int += clean_chunk["total_rec_int"].sum()
    total_total_rec_late_fee += clean_chunk["total_rec_late_fee"].sum()
    total_recoveries += clean_chunk["recoveries"].sum()
    
    total_rows += len(chunk)
    chunk_idx += 1

results = {
    "total_rows_parsed": total_rows,
    "null_loan_amnt_count": len(null_loan_amnt_rows),
    "null_loan_amnt_details": null_loan_amnt_rows,
    "non_numeric_id_in_valid_loans": len(non_numeric_id_rows),
    "non_numeric_id_details": non_numeric_id_rows,
    "valid_loans_count": total_rows - len(null_loan_amnt_rows),
    "financial_totals": {
        "sum_loan_amnt": total_loan_amnt,
        "sum_funded_amnt": total_funded_amnt,
        "sum_funded_amnt_inv": total_funded_amnt_inv,
        "sum_total_pymnt": total_total_pymnt,
        "sum_total_rec_prncp": total_total_rec_prncp,
        "sum_total_rec_int": total_total_rec_int,
        "sum_total_rec_late_fee": total_total_rec_late_fee,
        "sum_recoveries": total_recoveries
    }
}

print(json.dumps(results, indent=2))

with open("reports/independent_financial_reconciliation.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nWrote full audit to reports/independent_financial_reconciliation.json")
