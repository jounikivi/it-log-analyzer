import io
from pathlib import Path
from unittest.mock import patch

import pytest

from src import analyzer
from src.analyzer import analyze_log_file, format_summary, read_log_rows, summarize_levels


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


def test_analyze_log_file_returns_complete_summary() -> None:
    content = (
        "timestamp,level,service,message\n"
        "2026-03-26T08:00:00Z,INFO,auth-service,Login ok\n"
        "2026-03-26T08:01:12Z,WARNING,api-gateway,Hidas vasteaika\n"
        "2026-03-26T08:03:45Z,ERROR,payment-service,Yhteysvirhe\n"
    )
    file_path = Path("sample_logs.csv")

    with patch_path_open(content):
        summary = analyze_log_file(file_path)

    assert summary["file_path"] == str(file_path)
    assert summary["total_rows"] == 3
    assert summary["INFO"] == 1
    assert summary["WARNING"] == 1
    assert summary["ERROR"] == 1
    assert summary["OTHER"] == 0


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
    }

    formatted = format_summary(summary)

    assert "Analyysi valmis tiedostolle: data/sample_logs.csv" in formatted
    assert "Riveja yhteensa: 5" in formatted
    assert "ERROR-riveja: 2" in formatted


def test_main_prints_summary_and_report_path(capsys: pytest.CaptureFixture[str]) -> None:
    summary = {
        "file_path": "data/sample_logs.csv",
        "total_rows": 5,
        "ERROR": 2,
        "WARNING": 1,
        "INFO": 2,
        "OTHER": 0,
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
