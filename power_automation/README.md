# Power Automate & Executive Board Report Pipeline

This module implements the automated data refresh, PDF report generation, and enterprise distribution pipeline for the **Nexvia Financial Analytics System** (Step 6 / Task 5).

> [!NOTE]
> **Environment & Governance Disclosure:**
> Live Microsoft Power Automate Cloud and Desktop services were not present on this local workstation. In adherence to strict analytical integrity standards, no fake cloud execution logs or fabricated email dispatches are produced. Instead, this directory delivers:
> 1. A working, headless Python reporting engine generating publication-grade vector PDF board packets.
> 2. A fail-safe email dispatcher module supporting SMTP / Exchange relay with default dry-run execution.
> 3. A complete, production-ready Microsoft Power Automate flow specification ready for Microsoft 365 cloud deployment.

---

## 1. Directory Structure

```
power_automation/
├── generate_monthly_packet.py    # Headless engine querying warehouse.db and producing PDF
├── email_dispatcher.py           # Safe SMTP/Exchange dispatcher with dry-run protection
├── power_automate_flow_spec.md   # Complete Microsoft Power Automate Cloud Flow blueprint
├── README.md                     # Architecture, operations, and security guide
└── output/
    └── monthly_board_report.pdf  # Generated 2-page publication-grade executive PDF packet
```

---

## 2. Local Execution

### Step A: Generate Monthly Board Report PDF
The reporting pipeline reads authoritative metrics from `vw_portfolio_pnl_monthly`, `vw_portfolio_balance_sheet_summary`, and `reports/credit_risk_final_scorecard.json`.

```bash
# Run headless PDF generation
python power_automation/generate_monthly_packet.py
```
**Output:**
- `power_automation/output/monthly_board_report.pdf` (vector PDF, 2 pages, ~68 KB)
- **Page 1:** Executive Summary, 6 KPI Headline Cards, Cumulative P&L Cash Flow Table, Balance Sheet Solvency Waterfall.
- **Page 2:** Credit Risk Scorecard Architecture, 10 Predictor WOE/IV & Model Coefficients Table, 2016 Out-of-Time Decile Calibration Table, Model Governance & SR 11-7 Note.

### Step B: Test Email Dispatcher (Dry-Run Mode)
The email dispatcher defaults to `--dry-run` to protect against accidental email transmission.

```bash
# Verify dry-run output (default)
python power_automation/email_dispatcher.py
```
**Expected Output:**
```
[DRY RUN] Report verified at monthly_board_report.pdf (68,217 bytes). Recipients: board-audit@nexvia.internal, risk-committee@nexvia.internal. SMTP Configured: False (User: <NOT_SET>). Simulated execution succeeded without network transmission.
Dispatcher Status: DRY RUN
```

### Step C: Test Configuration Validation
When running with `--live` without required environment variables, the script safely catches missing parameters:

```bash
python power_automation/email_dispatcher.py --live
```
**Expected Output:**
```
[CONFIGURATION ERROR] Cannot send email. Missing required environment variables: SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD
Dispatcher Status: CONFIGURATION ERROR
```

---

## 3. Environment Variables

To configure live email transmission in a staging or production environment, define:

| Environment Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `SMTP_HOST` | Hostname of SMTP or Exchange relay server | `smtp.office365.com` |
| `SMTP_PORT` | Port for SMTP transmission | `587` |
| `SMTP_USERNAME` | Service account or relay username | `reports@nexvia.internal` |
| `SMTP_PASSWORD` | Service account application password | *(Secret / Vault)* |
| `SMTP_USE_TLS` | Enable TLS encryption | `true` |
| `REPORT_RECIPIENTS`| Comma-separated list of target email recipients | `board@nexvia.internal, risk@nexvia.internal` |

---

## 4. Microsoft Power Automate Cloud Deployment

To deploy this automation in an enterprise Microsoft 365 environment:

1. **Import Blueprint:** Open Microsoft Power Automate (`flow.microsoft.com`) and create a new **Automated Cloud Flow**.
2. **Follow Specification:** Configure triggers and action blocks according to [power_automate_flow_spec.md](file:///D:/nexvia%20-%201/Financial-Analytics-System/power_automation/power_automate_flow_spec.md).
3. **Connect Data Gateway:** Link the Python action block to an Azure Automation runbook or an On-Premises Data Gateway hosting the financial analytics system.
4. **Connect Office 365 Outlook & SharePoint:** Authorize the enterprise service principal with `Mail.Send` and `Sites.Selected` permissions.
5. **Configure Run-After Error Scopes:** Ensure failure branches trigger P1 alerts to the engineering on-call team.

---

## 5. Security & Audit Compliance

- **Zero Credential Logging:** `email_dispatcher.py` implements credential masking (`mask_credential()`) to prevent secrets or passwords from appearing in stdout, logs, or error dumps.
- **Strict Read-Only Data Ingestion:** All database connections are opened with SQLite URI `file:warehouse.db?mode=ro`.
- **Model Risk Management (SR 11-7 / OCC 2011-12):** Scorecard metrics in the board report document in-time vs out-of-time stability, ensuring executive and regulatory visibility.
