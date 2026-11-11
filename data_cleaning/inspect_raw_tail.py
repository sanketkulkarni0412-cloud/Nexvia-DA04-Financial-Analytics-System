"""
Inspect the raw trailing lines of accepted_2007_to_2018Q4.csv directly from the binary stream.
"""
import os

accepted_path = "dataset/raw/accepted_2007_to_2018Q4.csv"
file_size = os.path.getsize(accepted_path)

# Seek near the end of the file (last 10 KB)
with open(accepted_path, "rb") as f:
    f.seek(max(0, file_size - 10240))
    raw_tail = f.read().decode("utf-8", errors="replace")

lines = raw_tail.splitlines()
print(f"File size: {file_size} bytes")
print(f"Total lines in last 10KB: {len(lines)}")
print("--- LAST 40 RAW LINES OF accepted_2007_to_2018Q4.csv ---")
for i, line in enumerate(lines[-40:]):
    line_num = len(lines) - 40 + i
    print(f"Line -{40 - i} (len={len(line)}): {line[:120]}")
