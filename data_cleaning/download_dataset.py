"""
Dataset Acquisition Script for Financial Analytics and Risk Reporting System (DA-04)
Source: Authentic Lending Club Accepted Loans Dataset (2007-2018Q4)
Mirrored from Kaggle 'wordsforthewise/lending-club'
"""
import os
import sys
import urllib.request
import time

SOURCE_URL = "https://huggingface.co/datasets/codesignal/lending-club-loan-accepted/resolve/main/accepted_2007_to_2018Q4.csv"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "dataset", "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "lending_club_loans.csv")
TARGET_BYTES = 35 * 1024 * 1024  # 35 MB provides ~45,000 to 50,000 authentic loan records

def download_authentic_lending_club_data():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"Target file: {os.path.abspath(OUTPUT_FILE)}")
    print(f"Source URL:  {SOURCE_URL}")
    print(f"Target size: {TARGET_BYTES / (1024*1024):.2f} MB")
    print("Initiating stream request with HTTP Range header...")
    
    req = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Range": f"bytes=0-{TARGET_BYTES}"
        }
    )
    
    start_time = time.time()
    with urllib.request.urlopen(req) as response:
        chunk_size = 1024 * 1024  # 1 MB chunks
        received_bytes = bytearray()
        downloaded = 0
        
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            received_bytes.extend(chunk)
            downloaded += len(chunk)
            elapsed = time.time() - start_time
            speed = (downloaded / (1024 * 1024)) / max(elapsed, 0.001)
            percent = (downloaded / TARGET_BYTES) * 100
            print(f"\rProgress: {downloaded / (1024*1024):.2f} MB / {TARGET_BYTES / (1024*1024):.2f} MB ({percent:.1f}%) | Speed: {speed:.2f} MB/s", end="", flush=True)

    print("\nDownload complete. Truncating incomplete trailing row...")
    
    # Ensure we truncate cleanly at the last complete newline
    last_newline_idx = received_bytes.rfind(b"\n")
    if last_newline_idx != -1:
        clean_bytes = received_bytes[:last_newline_idx + 1]
    else:
        clean_bytes = received_bytes

    with open(OUTPUT_FILE, "wb") as f:
        f.write(clean_bytes)

    final_size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"Saved authentic Lending Club dataset to: {OUTPUT_FILE}")
    print(f"Final file size: {final_size_mb:.2f} MB")
    return OUTPUT_FILE

if __name__ == "__main__":
    download_authentic_lending_club_data()
