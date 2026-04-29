import io
from pathlib import Path
from unittest.mock import patch

import pytest

from src import analyzer
from src.analyzer import (
    analyze_log_file,
    format_summary,
    get_busiest_hour,
    parse_hour_bucket,
    read_log_rows,
    summarize_activity_by_hour,
    summarize_levels,
    summarize_services,
    summarize_top_error_messages,
)


def patch_path_open(content: str):
    def fake_open(
        self: Path, mode: str = "r", encoding: str | None = None, newline: str | None = None
    ) -> io.StringIO:
        return io.StringIO(content)

    return patch.object(Path, "open", fake_open)


def test_read_log_rows_reads_csv_rows() -> None:
    content = (
        "timestamp,level,service,message\n"
        "2026-03-26T08:00:00Z,INFO,auth-service,Login ok\n"
        "2026-03-26T08:01:12Z,ERROR,api-gateway,Timeout\n"
    )
    file_path = Path("sample_logs.csv")

    with patch_path_open(content):
        rows = read_log_rows(file_path)

    assert len(rows) == 2
    assert rows[0]["level"] == "INFO"
    assert rows[1]["service"] == "api-gateway"


def test_summarize_levels_counts_supported_and_other_rows() -> None:
    rows = [
        {"level": "INFO"},
        {"level": "WARNING"},
        {"level": "ERROR"},
        {"level": "DEBUG"},
    ]

    summary = summarize_levels(rows)

    assert summary == {
        "total_rows": 4,
        "ERROR": 1,
        "WARNING": 1,
        "INFO": 1,
        "OTHER": 1,
    }


def test_summarize_services_sorts_by_count_and_name() -> None:
    rows = [
        {"service": "api-gateway"},
        {"service": "worker"},
        {"service": "api-gateway"},
        {"service": ""},
    ]

    summary = summarize_services(rows)

    assert summary == {
        "api-gateway": 2,
        "UNKNOWN": 1,
        "worker": 1,
    }


def test_summarize_top_error_messages_returns_most_common_items() -> None:
    rows = [
        {"level": "ERROR", "message": "Timeout"},
        {"level": "ERROR", "message": "Timeout"},
        {"level": "ERROR", "message": "Database error"},
        {"level": "INFO", "message": "Ignored"},
    ]

    summary = summarize_top_error_messages(rows)

    assert summary == [("Timeout", 2), ("Database error", 1)]


def test_parse_hour_bucket_parses_iso_timestamp() -> None:
    assert parse_hour_bucket("2026-03-26T08:07:33Z") == "2026-03-26 08:00"


def test_summarize_activity_by_hour_returns_sorted_counts() -> None:
    rows = [
        {"timestamp": "2026-03-26T09:10:00Z"},
        {"timestamp": "2026-03-26T08:05:00Z"},
        {"timestamp": "2026-03-26T09:20:00Z"},
        {"timestamp": "not-a-timestamp"},
    ]

    summary = summarize_activity_by_hour(rows)

    assert summary == {
        "2026-03-26 08:00": 1,
        "2026-03-26 09:00": 2,
    }


def test_get_busiest_hour_returns_most_active_slot() -> None:
    hourly_counts = {
        "2026-03-26 08:00": 1,
        "2026-03-26 09:00": 2,
    }

    assert get_busiest_hour(hourly_counts) == ("2026-03-26 09:00", 2)


def test_analyze_log_file_returns_complete_summary() -> None:
    content = (
        "timestamp,level,service,message\n"
        "2026-03-26T08:00:00Z,INFO,auth-service,Login ok\n"
        "2026-03-26T08:01:12Z,WARNING,api-gateway,Hidas vasteaika\n"
        "2026-03-26T09:03:45Z,ERROR,payment-service,Yhteysvirhe\n"
        "2026-03-26T09:08:45Z,ERROR,payment-service,Yhteysvirhe\n"
    )
    file_path = Path("sample_logs.csv")

    with patch_path_open(content):
        summary = analyze_log_file(file_path, top_services=2, top_errors=1)

    assert summary["file_path"] == str(file_path)
    assert summary["total_rows"] == 4
    assert summary["INFO"] == 1
    assert summary["WARNING"] == 1
    assert summary["ERROR"] == 2
    assert summary["OTHER"] == 0
    assert summary["service_counts"] == {
        "payment-service": 2,
        "api-gateway": 1,
    }
    assert summary["top_error_messages"] == [("Yhteysvirhe", 2)]
    assert summary["hourly_counts"] == {
        "2026-03-26 08:00": 2,
        "2026-03-26 09:00": 2,
    }
    assert summary["busiest_hour"] == ("2026-03-26 08:00", 2)


def test_read_log_rows_requires_level_column() -> None:
    content = (
        "timestamp,service,message\n"
        "2026-03-26T08:00:00Z,auth-service,Login ok\n"
    )
    file_path = Path("sample_logs.csv")

    with patch_path_open(content):
        with pytest.raises(ValueError, match="level"):
            read_log_rows(file_path)


def test_format_summary_returns_finnish_output() -> None:
    summary = {
        "file_path": "data/sample_logs.csv",
        "total_rows": 5,
        "ERROR": 2,
        "WARNING": 1,
        "INFO": 2,
        "OTHER": 0,
        "service_counts": {
            "api-gateway": 2,
            "auth-service": 1,
        },
        "top_error_messages": [("Timeout", 2)],
        "hourly_counts": {
            "2026-03-26 08:00": 3,
            "2026-03-26 09:00": 2,
        },
        "busiest_hour": ("2026-03-26 08:00", 3),
    }

    formatted = format_summary(summary)

    assert "Analyysi valmis tiedostolle: data/sample_logs.csv" in formatted
    assert "Riveja yhteensa: 5" in formatted
    assert "ERROR-riveja: 2" in formatted
    assert "Yleisin palvelu: api-gateway (2)" in formatted
    assert "Aktiivisin tunti: 2026-03-26 08:00 (3 rivi(a))" in formatted
    assert "- 2026-03-26 09:00: 2" in formatted
    assert "- Timeout (2)" in formatted


def test_main_prints_summary_and_report_path(capsys: pytest.CaptureFixture[str]) -> None:
    summary = {
        "file_path": "data/sample_logs.csv",
        "total_rows": 5,
        "ERROR": 2,
        "WARNING": 1,
        "INFO": 2,
        "OTHER": 0,
        "service_counts": {"api-gateway": 2},
        "top_error_messages": [("Timeout", 2)],
        "hourly_counts": {"2026-03-26 08:00": 3},
        "busiest_hour": ("2026-03-26 08:00", 3),
    }

    with patch.object(analyzer, "analyze_log_file", return_value=summary), patch.object(
        analyzer, "write_markdown_report", return_value=Path("reports/report.md")
    ), patch.object(
        analyzer, "write_html_report", return_value=Path("reports/report.html")
    ):
        exit_code = analyzer.main(["data/sample_logs.csv"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Analyysi valmis tiedostolle: data/sample_logs.csv" in captured.out
    assert "Raportti kirjoitettu tiedostoon: reports\\report.md" in captured.out
    assert "HTML-raportti kirjoitettu tiedostoon: reports\\report.html" in captured.out


def test_main_returns_error_code_and_message_for_missing_file(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch.object(analyzer, "analyze_log_file", side_effect=FileNotFoundError):
        exit_code = analyzer.main(["missing.csv"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Virhe: tiedostoa ei loytynyt: missing.csv" in captured.err
