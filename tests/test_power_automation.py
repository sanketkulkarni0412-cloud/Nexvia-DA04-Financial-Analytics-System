"""
Nexvia Financial Analytics System — Task 6 Tests
Module: tests/test_power_automation.py

Unit and integration tests for the Power Automate monthly board report pipeline,
PDF generation, email dispatcher security, and cloud flow specification.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from power_automation.generate_monthly_packet import MonthlyBoardReportGenerator
from power_automation.email_dispatcher import EmailDispatcher, mask_credential


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def temp_output_dir(tmp_path):
    out_dir = tmp_path / "power_automation_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


class TestMonthlyBoardReportGenerator:
    """Tests for the PDF generation pipeline."""

    def test_extracted_metrics_correctness(self, project_root):
        """Verifies that all extracted metrics match authoritative SQL views and scorecard outputs."""
        generator = MonthlyBoardReportGenerator(
            db_path=project_root / "warehouse.db",
            scorecard_path=project_root / "reports" / "credit_risk_final_scorecard.json"
        )
        metrics = generator.extract_metrics()

        # Core P&L and Balance Sheet Metrics
        assert metrics["total_funded_amount"] == pytest.approx(34004208600.0, rel=1e-4)
        assert metrics["principal_received"] == pytest.approx(21489393643.58, rel=1e-4)
        assert metrics["active_gross_balance"] == pytest.approx(9510001923.03, rel=1e-4)
        assert metrics["npl_balance"] == pytest.approx(244246366.02, rel=1e-4)
        assert metrics["npl_ratio"] == pytest.approx(2.5683, rel=1e-2)
        assert metrics["loss_reserve"] == pytest.approx(772880427.48, rel=1e-4)
        assert metrics["net_carrying_value"] == pytest.approx(8737121495.55, rel=1e-4)

        # Scorecard Performance Metrics
        assert metrics["scorecard_in_time_auc"] == pytest.approx(0.6828, rel=1e-3)
        assert metrics["scorecard_oot_auc"] == pytest.approx(0.6770, rel=1e-3)
        assert metrics["scorecard_oot_ks"] == pytest.approx(25.15, rel=1e-2)

    def test_pdf_generation_produces_valid_file(self, project_root, temp_output_dir):
        """Verifies that generate_pdf creates a non-empty, multi-page vector PDF."""
        generator = MonthlyBoardReportGenerator(
            db_path=project_root / "warehouse.db",
            scorecard_path=project_root / "reports" / "credit_risk_final_scorecard.json",
            output_dir=temp_output_dir
        )
        pdf_path = generator.generate_pdf("test_board_report.pdf")

        assert pdf_path.exists()
        assert pdf_path.is_file()
        file_size = pdf_path.stat().st_size
        # Valid PDF with 2 pages and styled elements should be > 25 KB
        assert file_size > 25_000, f"Generated PDF unexpectedly small: {file_size} bytes"

        # Verify PDF header magic bytes
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-", "Generated file is missing standard %PDF- magic signature."


class TestEmailDispatcher:
    """Tests for the safe email distribution module."""

    def test_credential_masking(self):
        """Verifies that sensitive credentials are never displayed in full."""
        assert mask_credential("SuperSecretPassword123!") == "Su****3!"
        assert mask_credential("short") == "sh****rt"
        assert mask_credential("1234") == "****"
        assert mask_credential("") == "<NOT_SET>"
        assert mask_credential(None) == "<NOT_SET>"

    def test_dispatcher_dry_run_mode(self, project_root):
        """Verifies that dry-run mode succeeds safely without network calls."""
        pdf_path = project_root / "power_automation" / "output" / "monthly_board_report.pdf"
        dispatcher = EmailDispatcher(pdf_path=pdf_path, dry_run=True)
        res = dispatcher.dispatch()

        assert res["status"] == "DRY RUN"
        assert "Simulated execution succeeded" in res["details"]
        assert "Recipients" in res["details"]

    def test_dispatcher_missing_credentials_fails_safely(self, project_root, monkeypatch):
        """Verifies that missing credentials in live mode triggers CONFIGURATION ERROR cleanly."""
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("SMTP_USERNAME", raising=False)
        monkeypatch.delenv("SMTP_PASSWORD", raising=False)

        pdf_path = project_root / "power_automation" / "output" / "monthly_board_report.pdf"
        dispatcher = EmailDispatcher(pdf_path=pdf_path, dry_run=False)
        res = dispatcher.dispatch()

        assert res["status"] == "CONFIGURATION ERROR"
        assert "Missing required environment variables" in res["details"]

    def test_email_message_structure(self, project_root):
        """Verifies that the constructed email contains HTML body and PDF attachment."""
        pdf_path = project_root / "power_automation" / "output" / "monthly_board_report.pdf"
        dispatcher = EmailDispatcher(pdf_path=pdf_path, dry_run=True)
        msg = dispatcher.build_message()

        assert msg["Subject"].startswith("CONFIDENTIAL:")
        assert "board-audit@nexvia.internal" in msg["To"]

        # Check payload attachments
        payloads = msg.get_payload()
        assert len(payloads) >= 2  # Text part + Attachment part
        attachment_names = [p.get_filename() for p in payloads if p.get_filename()]
        assert "monthly_board_report.pdf" in attachment_names


class TestPowerAutomateFlowSpec:
    """Verifies that the Microsoft Power Automate flow specification is complete and compliant."""

    def test_spec_file_exists_and_contains_required_sections(self, project_root):
        spec_path = project_root / "power_automation" / "power_automate_flow_spec.md"
        assert spec_path.exists()

        content = spec_path.read_text(encoding="utf-8")

        # Required architectural elements
        assert "DESIGN/SPECIFICATION — LIVE CLOUD FLOW NOT EXECUTED IN THIS LOCAL ENVIRONMENT" in content
        assert "Recurrence" in content
        assert "06:00 UTC" in content
        assert "SharePoint" in content
        assert "Office 365 Outlook" in content
        assert "Microsoft Teams" in content
        assert "hasFailed" in content
        assert "Scope_Error_Handling" in content
