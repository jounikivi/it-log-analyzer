"""Markdown-raportin muodostaminen analyysin tuloksista."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping


def generate_markdown_report(summary: Mapping[str, int | str]) -> str:
    """Muodosta analyysin tuloksista Markdown-raportti."""

    return "\n".join(
        [
            "# IT Log Analyzer - raportti",
            "",
            "## Lahdetiedosto",
            f"- Tiedosto: `{summary['file_path']}`",
            "",
            "## Yhteenveto",
            f"- Riveja yhteensa: {summary['total_rows']}",
            f"- ERROR-riveja: {summary['ERROR']}",
            f"- WARNING-riveja: {summary['WARNING']}",
            f"- INFO-riveja: {summary['INFO']}",
            f"- Muita riveja: {summary['OTHER']}",
        ]
    )


def write_markdown_report(
    summary: Mapping[str, int | str], output_path: str | Path = "reports/report.md"
) -> Path:
    """Kirjoita Markdown-raportti tiedostoon ja palauta polku."""

    path = Path(output_path)
    report_content = generate_markdown_report(summary)
    path.write_text(report_content, encoding="utf-8")
    return path
