from pathlib import Path
from unittest.mock import patch

from src.web_app import analyze_from_form_data, decode_form_data, render_dashboard_page


def test_decode_form_data_decodes_urlencoded_payload() -> None:
    payload = b"file_path=data%2Fsample_logs.csv&top_services=3&top_errors=2"

    decoded = decode_form_data(payload)

    assert decoded == {
        "file_path": "data/sample_logs.csv",
        "top_services": "3",
        "top_errors": "2",
    }


def test_analyze_from_form_data_prefers_inline_csv_text() -> None:
    form_data = {
        "csv_text": "timestamp,level,service,message\n2026-03-26T08:00:00Z,INFO,auth-service,Login ok\n",
        "source_name": "upload.csv",
        "top_services": "4",
        "top_errors": "3",
        "file_path": "ignored.csv",
    }

    mocked_summary = {
        "file_path": "upload.csv",
        "total_rows": 1,
        "ERROR": 0,
        "WARNING": 0,
        "INFO": 1,
        "OTHER": 0,
        "service_counts": {"auth-service": 1},
        "top_error_messages": [],
        "hourly_counts": {"2026-03-26 08:00": 1},
        "busiest_hour": ("2026-03-26 08:00", 1),
    }

    with patch("src.web_app.analyze_csv_text", return_value=mocked_summary) as analyze_csv_text:
        summary = analyze_from_form_data(form_data)

    assert summary["file_path"] == "upload.csv"
    analyze_csv_text.assert_called_once()


def test_render_dashboard_page_contains_ui_sections() -> None:
    summary = {
        "file_path": "data/sample_logs.csv",
        "total_rows": 10,
        "ERROR": 4,
        "WARNING": 2,
        "INFO": 4,
        "OTHER": 0,
        "service_counts": {"api-gateway": 4, "worker": 2},
        "top_error_messages": [("Upstream service timeout", 2)],
        "hourly_counts": {"2026-03-26 08:00": 5, "2026-03-26 09:00": 3},
        "busiest_hour": ("2026-03-26 08:00", 5),
    }

    page = render_dashboard_page(summary=summary, success_message="Valmis.")
    html = page.decode("utf-8")

    assert "IT Log Analyzer" in html
    assert "Valitse CSV koneelta" in html
    assert "Palvelukohtainen yhteenveto" in html
    assert "Tuntikohtainen aktiivisuus" in html
    assert "Upstream service timeout" in html
