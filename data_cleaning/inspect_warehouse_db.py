"""
Inspect warehouse.db metrics, table counts, sizes, and foreign keys.
"""
import os
import sqlite3

db_path = "warehouse.db"
size_bytes = os.path.getsize(db_path)
size_mb = size_bytes / (1024 * 1024)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [r[0] for r in cursor.fetchall()]

table_counts = {}
for t in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {t};")
    table_counts[t] = cursor.fetchone()[0]

print(f"Database File: {db_path}")
print(f"Database Size: {size_bytes:,} bytes ({size_mb:.2f} MB)")
print("Table Counts:")
for t, cnt in table_counts.items():
    print(f"  {t}: {cnt:,} rows")

cursor.execute("SELECT SUM(loan_amnt), SUM(total_pymnt), SUM(total_rec_prncp), SUM(total_rec_int), SUM(recoveries) FROM fact_accepted_loans;")
f = cursor.fetchone()
print("\nFinancial Totals in fact_accepted_loans:")
print(f"  sum(loan_amnt): ${f[0]:,.2f}")
print(f"  sum(total_pymnt): ${f[1]:,.2f}")
print(f"  sum(total_rec_prncp): ${f[2]:,.2f}")
print(f"  sum(total_rec_int): ${f[3]:,.2f}")
print(f"  sum(recoveries): ${f[4]:,.2f}")

cursor.execute("PRAGMA foreign_key_check;")
fk_violations = cursor.fetchall()
print(f"\nPRAGMA foreign_key_check violations: {len(fk_violations)}")

cursor.execute("SELECT * FROM etl_ingestion_checkpoints;")
cp = cursor.fetchall()
print("\nCheckpoints in etl_ingestion_checkpoints:")
for r in cp:
    print(f"  {r}")
