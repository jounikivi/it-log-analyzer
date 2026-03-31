from pathlib import Path
from unittest.mock import patch

from src.report_generator import (
    generate_html_report,
    generate_markdown_report,
    write_html_report,
    write_markdown_report,
)


def test_generate_markdown_report_contains_summary_values() -> None:
    summary = {
        "file_path": "data/sample_logs.csv",
        "total_rows": 5,
        "ERROR": 2,
        "WARNING": 1,
        "INFO": 2,
        "OTHER": 0,
    }

    report = generate_markdown_report(summary)

    assert "# IT Log Analyzer - raportti" in report
    assert "- Tiedosto: `data/sample_logs.csv`" in report
    assert "- Riveja yhteensa: 5" in report
    assert "- ERROR-riveja: 2" in report


def test_write_markdown_report_writes_content_to_target_file() -> None:
    summary = {
        "file_path": "data/sample_logs.csv",
        "total_rows": 5,
        "ERROR": 2,
        "WARNING": 1,
        "INFO": 2,
        "OTHER": 0,
    }
    written: dict[str, str] = {}

    def fake_write_text(self: Path, content: str, encoding: str = "utf-8") -> int:
        written["path"] = str(self)
        written["content"] = content
        return len(content)

    with patch.object(Path, "write_text", fake_write_text):
        output_path = write_markdown_report(summary, "reports/report.md")

    assert output_path == Path("reports/report.md")
    assert written["path"] == "reports\\report.md"
    assert "# IT Log Analyzer - raportti" in written["content"]


def test_generate_html_report_contains_summary_values() -> None:
    summary = {
        "file_path": "data/sample_logs.csv",
        "total_rows": 5,
        "ERROR": 2,
        "WARNING": 1,
        "INFO": 2,
        "OTHER": 0,
    }

    report = generate_html_report(summary)

    assert "<title>IT Log Analyzer - raportti</title>" in report
    assert "Automaattisesti generoitu yhteenveto" in report
    assert "data/sample_logs.csv" in report
    assert ">2<" in report


def test_write_html_report_writes_content_to_target_file() -> None:
    summary = {
        "file_path": "data/sample_logs.csv",
        "total_rows": 5,
        "ERROR": 2,
        "WARNING": 1,
        "INFO": 2,
        "OTHER": 0,
    }
    written: dict[str, str] = {}

    def fake_write_text(self: Path, content: str, encoding: str = "utf-8") -> int:
        written["path"] = str(self)
        written["content"] = content
        return len(content)

    with patch.object(Path, "write_text", fake_write_text):
        output_path = write_html_report(summary, "reports/report.html")

    assert output_path == Path("reports/report.html")
    assert written["path"] == "reports\\report.html"
    assert "<!doctype html>" in written["content"]
