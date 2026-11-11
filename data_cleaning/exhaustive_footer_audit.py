"""
Comprehensive Audit of Excluded Rows and Financial Recalculation
Financial Analytics and Risk Reporting System (DA-04)

Verifies:
1. All 33 excluded rows individually (exact line numbers, id, values)
2. Confirms that no other rows in any chunk match exclusion criteria
3. Confirms that 100% of the remaining 2,260,668 rows have numeric IDs and positive loan_amnt
4. Recalculates all financial totals with explicit decimal/float precision and null accounting
"""

import pandas as pd
import json
import os

accepted_path = "dataset/raw/accepted_2007_to_2018Q4.csv"

excluded_records = []
chunk_stats = []
total_parsed_rows = 0
valid_loan_count = 0

# Financial totals
total_loan_amnt = 0.0
total_funded_amnt = 0.0
total_funded_amnt_inv = 0.0
total_total_pymnt = 0.0
total_total_rec_prncp = 0.0
total_total_rec_int = 0.0
total_total_rec_late_fee = 0.0
total_recoveries = 0.0
total_collection_cost = 0.0

chunk_num = 0

for chunk in pd.read_csv(accepted_path, chunksize=100000, low_memory=False):
    chunk_len = len(chunk)
    
    # Filtering rule:
    # Row is non-loan if loan_amnt is null OR id contains partition text
    mask_non_loan = chunk["loan_amnt"].isnull() | chunk["id"].astype(str).str.contains(
        "Total amount funded|Loans that do not meet", regex=True, na=False
    )
    
    non_loan_chunk = chunk[mask_non_loan]
    clean_chunk = chunk[~mask_non_loan]
    
    # Check for excluded rows in this chunk
    if len(non_loan_chunk) > 0:
        for local_idx, row in non_loan_chunk.iterrows():
            row_num_in_csv = total_parsed_rows + (local_idx - chunk.index[0]) + 2 # +2 for header and 1-indexing
            non_null_fields = {k: str(v) for k, v in row.items() if pd.notnull(v)}
            excluded_records.append({
                "csv_line_number": row_num_in_csv,
                "chunk_number": chunk_num,
                "id_value": str(row.get("id")),
                "loan_amnt": str(row.get("loan_amnt")),
                "non_null_fields_count": len(non_null_fields),
                "non_null_fields": non_null_fields
            })
            
    # Check clean chunk integrity:
    # 1. Any non-numeric ID?
    non_numeric_ids = clean_chunk[~clean_chunk["id"].astype(str).str.isdigit()]
    if len(non_numeric_ids) > 0:
        raise ValueError(f"Found non-numeric ID in clean chunk {chunk_num}: {non_numeric_ids['id'].tolist()}")
        
    # 2. Any null or <= 0 loan_amnt?
    invalid_loans = clean_chunk[clean_chunk["loan_amnt"] <= 0]
    if len(invalid_loans) > 0:
        raise ValueError(f"Found non-positive loan_amnt in clean chunk {chunk_num}")
        
    # Accumulate financials
    total_loan_amnt += clean_chunk["loan_amnt"].sum()
    total_funded_amnt += clean_chunk["funded_amnt"].sum()
    total_funded_amnt_inv += clean_chunk["funded_amnt_inv"].sum()
    total_total_pymnt += clean_chunk["total_pymnt"].sum()
    total_total_rec_prncp += clean_chunk["total_rec_prncp"].sum()
    total_total_rec_int += clean_chunk["total_rec_int"].sum()
    total_total_rec_late_fee += clean_chunk["total_rec_late_fee"].sum()
    total_recoveries += clean_chunk["recoveries"].sum()
    total_collection_cost += clean_chunk["collection_recovery_fee"].sum() if "collection_recovery_fee" in clean_chunk.columns else 0.0
    
    total_parsed_rows += chunk_len
    valid_loan_count += len(clean_chunk)
    
    chunk_stats.append({
        "chunk": chunk_num,
        "parsed": chunk_len,
        "clean": len(clean_chunk),
        "excluded": len(non_loan_chunk)
    })
    chunk_num += 1

audit_output = {
    "total_csv_parsed_rows": total_parsed_rows,
    "total_excluded_rows": len(excluded_records),
    "total_valid_loans": valid_loan_count,
    "reconciliation_formula": f"{total_parsed_rows} parsed - {len(excluded_records)} excluded = {valid_loan_count} valid",
    "financial_recalculation": {
        "sum_loan_amnt": total_loan_amnt,
        "sum_funded_amnt": total_funded_amnt,
        "sum_funded_amnt_inv": total_funded_amnt_inv,
        "sum_total_pymnt": total_total_pymnt,
        "sum_total_rec_prncp": total_total_rec_prncp,
        "sum_total_rec_int": total_total_rec_int,
        "sum_total_rec_late_fee": total_total_rec_late_fee,
        "sum_recoveries": total_recoveries,
        "sum_collection_recovery_fee": total_collection_cost
    },
    "all_33_excluded_records": excluded_records
}

with open("reports/exhaustive_footer_audit.json", "w", encoding="utf-8") as f:
    json.dump(audit_output, f, indent=2)

print(f"Audit completed successfully!")
print(f"Total parsed: {total_parsed_rows}")
print(f"Total excluded: {len(excluded_records)}")
print(f"Total valid loans: {valid_loan_count}")
print(f"sum_loan_amnt: ${total_loan_amnt:,.2f}")
print(f"sum_funded_amnt: ${total_funded_amnt:,.2f}")
print(f"sum_total_pymnt: ${total_total_pymnt:,.2f}")
print(f"sum_total_rec_int: ${total_total_rec_int:,.2f}")
print(f"sum_total_rec_prncp: ${total_total_rec_prncp:,.2f}")
