# Data Cleaning & Ingestion Pipeline

This directory contains the Python modules responsible for raw data auditing, cleaning, transformation, and validation before loading into the SQL data warehouse.

## Planned Modules (Phase 2 & Phase 3)
- `ingest_raw.py`: Streams and parses large source CSV files in optimized memory chunks.
- `clean_pipeline.py`: Implements domain-specific cleaning rules:
  - Date format standardization (`issue_d`, `last_pymnt_d`, `earliest_cr_line`).
  - Employment length parsing and ordinal encoding (`< 1 year` to `10+ years`).
  - Missing value imputation strategy (median by loan grade / explicit categorical bucket).
  - Outlier detection on annual income and debt-to-income (DTI).
- `validation_rules.py`: Automated assertions ensuring financial integrity prior to database load.
