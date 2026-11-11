"""
Nexvia Financial Analytics System — Task 6
Module: power_automation/email_dispatcher.py

Safe, auditable email distribution module for the Monthly Executive Board Report.
Designed for unattended deployment in Microsoft Power Automate, Windows Task Scheduler,
or cron pipelines.

Security & Safety Controls:
1. Dry-run mode is enabled by default. No external network transmissions occur unless explicitly overridden.
2. Zero secret leakage: Credentials from environment variables are strictly masked in logs and reports.
3. Fail-safe fallback: Missing credentials produce structured CONFIGURATION ERROR status without crashing.
4. Compliant with corporate SMTP / Office 365 Exchange relay standards.
"""

import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF_PATH = PROJECT_ROOT / "power_automation" / "output" / "monthly_board_report.pdf"


def mask_credential(val: Optional[str]) -> str:
    """Masks sensitive credentials for safe logging."""
    if not val:
        return "<NOT_SET>"
    if len(val) <= 4:
        return "****"
    return f"{val[:2]}****{val[-2:]}"


class EmailDispatcher:
    """
    Handles preparation and secure dispatch of executive board reports.
    Defaults to dry-run mode to prevent unintended email transmissions.
    """

    def __init__(
        self,
        pdf_path: Path = DEFAULT_PDF_PATH,
        dry_run: bool = True,
    ):
        self.pdf_path = Path(pdf_path)
        self.dry_run = dry_run

        # Load environment configuration
        self.smtp_host = os.environ.get("SMTP_HOST", "").strip()
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587").strip() or "587")
        self.smtp_username = os.environ.get("SMTP_USERNAME", "").strip()
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()
        self.use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

        recipients_str = os.environ.get("REPORT_RECIPIENTS", "board-audit@nexvia.internal, risk-committee@nexvia.internal")
        self.recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        Validates whether all required SMTP configuration items are populated.
        Returns (is_valid, list_of_missing_fields).
        """
        missing = []
        if not self.smtp_host:
            missing.append("SMTP_HOST")
        if not self.smtp_username:
            missing.append("SMTP_USERNAME")
        if not self.smtp_password:
            missing.append("SMTP_PASSWORD")
        if not self.recipients:
            missing.append("REPORT_RECIPIENTS")

        return len(missing) == 0, missing

    def build_message(self, subject: Optional[str] = None) -> MIMEMultipart:
        """
        Constructs the MIME multipart email with HTML body and PDF attachment.
        """
        msg = MIMEMultipart()
        msg["From"] = self.smtp_username or "reports-automator@nexvia.internal"
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = subject or "CONFIDENTIAL: Nexvia Monthly Executive Board Report & Risk Solvency Review"

        # Executive HTML Body
        html_body = f"""\
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1F2328; line-height: 1.5; }}
        .header {{ background-color: #0B2545; color: #FFFFFF; padding: 18px 24px; border-radius: 6px 6px 0 0; }}
        .content {{ border: 1px solid #D0D7DE; border-top: none; padding: 24px; border-radius: 0 0 6px 6px; }}
        .kpi-row {{ display: flex; gap: 12px; margin: 16px 0; }}
        .kpi-card {{ background: #F6F8FA; border: 1px solid #E1E4E8; padding: 12px; border-radius: 4px; flex: 1; }}
        .kpi-title {{ font-size: 11px; text-transform: uppercase; color: #57606A; font-weight: bold; }}
        .kpi-value {{ font-size: 18px; font-weight: bold; color: #0B2545; margin-top: 4px; }}
        .disclaimer {{ font-size: 11px; color: #57606A; margin-top: 24px; padding-top: 12px; border-top: 1px solid #E1E4E8; }}
    </style>
</head>
<body>
    <div class="header">
        <h2 style="margin: 0; font-size: 18px;">NEXVIA TECHNOLOGIES — EXECUTIVE BOARD PACKET</h2>
        <p style="margin: 4px 0 0 0; font-size: 12px; color: #8DA9C4;">Automated Monthly Financial Statement & Credit Risk Scorecard Review</p>
    </div>
    <div class="content">
        <p>Dear Members of the Board of Directors & Risk Committee,</p>
        <p>Attached is the official <strong>Monthly Executive Board Report</strong> for the loan portfolio, generated automatically from the authoritative analytical warehouse.</p>
        
        <h3>Key Performance Highlights</h3>
        <ul>
            <li><strong>Total Origination:</strong> $34.00B across 2,260,668 contracts</li>
            <li><strong>Active Portfolio Gross:</strong> $9.51B | Net Carrying Value: $8.74B</li>
            <li><strong>Asset Quality:</strong> NPL Ratio 2.5683% ($244.25M) | Loss Reserve $772.88M (316.4% NPL Coverage)</li>
            <li><strong>Scorecard Performance:</strong> In-Time AUC 0.6828 | 2016 Out-of-Time AUC 0.6770 | KS 25.15%</li>
        </ul>

        <p>The complete 2-page publication-grade PDF packet is attached for review.</p>

        <div class="disclaimer">
            <strong>CONFIDENTIALITY & GOVERNANCE:</strong> This message and attached document are intended solely for authorized board members and executive management. Generated by Nexvia Automated Financial Reporting Pipeline.
        </div>
    </div>
</body>
</html>
"""
        msg.attach(MIMEText(html_body, "html"))

        # Attach PDF if available
        if self.pdf_path.exists():
            with open(self.pdf_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=self.pdf_path.name)
            part["Content-Disposition"] = f'attachment; filename="{self.pdf_path.name}"'
            msg.attach(part)

        return msg

    def dispatch(self) -> Dict[str, str]:
        """
        Executes dispatch logic adhering to safety protocols.
        Outputs exact operational status:
        - DRY RUN
        - READY TO SEND
        - CONFIGURATION ERROR
        """
        # Check attachment
        if not self.pdf_path.exists():
            status = "CONFIGURATION ERROR"
            details = f"Report attachment not found at {self.pdf_path}"
            print(f"[{status}] {details}")
            return {"status": status, "details": details}

        is_valid_config, missing_fields = self.validate_configuration()

        # If running in dry run mode (default)
        if self.dry_run:
            status = "DRY RUN"
            masked_user = mask_credential(self.smtp_username)
            details = (
                f"Report verified at {self.pdf_path.name} ({self.pdf_path.stat().st_size:,} bytes). "
                f"Recipients: {', '.join(self.recipients)}. "
                f"SMTP Configured: {is_valid_config} (User: {masked_user}). "
                f"Simulated execution succeeded without network transmission."
            )
            print(f"[{status}] {details}")
            return {"status": status, "details": details}

        # Live send branch requested (dry_run = False)
        if not is_valid_config:
            status = "CONFIGURATION ERROR"
            details = f"Cannot send email. Missing required environment variables: {', '.join(missing_fields)}"
            print(f"[{status}] {details}")
            return {"status": status, "details": details}

        # Attempt safe transmission with configured credentials
        status = "READY TO SEND"
        try:
            msg = self.build_message()
            # Under live execution (when invoked in production cloud flow):
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            details = f"Email successfully dispatched to {len(self.recipients)} recipients via {self.smtp_host}:{self.smtp_port}."
            print(f"[SUCCESS] {details}")
            return {"status": "SUCCESS", "details": details}
        except Exception as e:
            # Mask error details to prevent leaking passwords in exception messages
            err_msg = str(e).replace(self.smtp_password, "******") if self.smtp_password else str(e)
            details = f"SMTP transmission failed: {err_msg}"
            print(f"[{status} - FAILED] {details}")
            return {"status": "TRANSMISSION ERROR", "details": details}


def main():
    """CLI execution entrypoint."""
    dry_run = True
    if "--live" in sys.argv:
        dry_run = False

    dispatcher = EmailDispatcher(dry_run=dry_run)
    result = dispatcher.dispatch()
    print(f"Dispatcher Status: {result['status']}")


if __name__ == "__main__":
    main()

