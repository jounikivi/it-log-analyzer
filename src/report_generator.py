"""Raporttien muodostaminen analyysin tuloksista."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

template_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def get_service_counts(summary: Mapping[str, object]) -> dict[str, int]:
    raw_value = summary.get("service_counts", {})
    return raw_value if isinstance(raw_value, dict) else {}


def get_top_error_messages(summary: Mapping[str, object]) -> list[tuple[str, int]]:
    raw_value = summary.get("top_error_messages", [])
    return raw_value if isinstance(raw_value, list) else []


def get_hourly_counts(summary: Mapping[str, object]) -> dict[str, int]:
    raw_value = summary.get("hourly_counts", {})
    return raw_value if isinstance(raw_value, dict) else {}


def get_busiest_hour(summary: Mapping[str, object]) -> tuple[str, int] | None:
    raw_value = summary.get("busiest_hour")
    if isinstance(raw_value, tuple) and len(raw_value) == 2:
        return raw_value
    return None


def escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")


def read_report_styles() -> str:
    return (STATIC_DIR / "report.css").read_text(encoding="utf-8")


def build_report_context(summary: Mapping[str, object]) -> dict[str, object]:
    service_counts = get_service_counts(summary)
    top_error_messages = get_top_error_messages(summary)
    hourly_counts = get_hourly_counts(summary)
    busiest_hour = get_busiest_hour(summary)
    hourly_peak = max(hourly_counts.values(), default=0)

    return {
        "summary": summary,
        "service_counts": list(service_counts.items()),
        "top_error_messages": top_error_messages,
        "hourly_counts": list(hourly_counts.items()),
        "busiest_hour": busiest_hour,
        "hourly_peak": hourly_peak,
        "style_block": read_report_styles(),
    }


def generate_markdown_report(summary: Mapping[str, object]) -> str:
    """Muodosta analyysin tuloksista Markdown-raportti."""

    service_counts = get_service_counts(summary)
    top_error_messages = get_top_error_messages(summary)
    hourly_counts = get_hourly_counts(summary)
    busiest_hour = get_busiest_hour(summary)

    lines = [
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

    if busiest_hour is not None:
        lines.append(f"- Aktiivisin tunti: {busiest_hour[0]} ({busiest_hour[1]} rivi(a))")

    if service_counts:
        lines.extend(
            [
                "",
                "## Palvelukohtainen yhteenveto",
                "",
                "| Palvelu | Rivien maara |",
                "| --- | ---: |",
            ]
        )
        for service, count in service_counts.items():
            lines.append(f"| {escape_markdown_cell(service)} | {count} |")

    if hourly_counts:
        lines.extend(
            [
                "",
                "## Tuntikohtainen aktiivisuus",
                "",
                "| Tunti | Rivien maara |",
                "| --- | ---: |",
            ]
        )
        for hour, count in hourly_counts.items():
            lines.append(f"| {hour} | {count} |")

    lines.extend(["", "## Yleisimmat ERROR-viestit", ""])
    if top_error_messages:
        lines.extend(["| Viesti | Maara |", "| --- | ---: |"])
        for message, count in top_error_messages:
            lines.append(f"| {escape_markdown_cell(message)} | {count} |")
    else:
        lines.append("Ei ERROR-riveja analysoidussa tiedostossa.")

    return "\n".join(lines)


def generate_html_report(summary: Mapping[str, object]) -> str:
    """Muodosta analyysin tuloksista HTML-raportti."""

    template = template_env.get_template("report.html")
    return template.render(**build_report_context(summary))


def write_markdown_report(
    summary: Mapping[str, object], output_path: str | Path = "reports/report.md"
) -> Path:
    """Kirjoita Markdown-raportti tiedostoon ja palauta polku."""

    path = Path(output_path)
    report_content = generate_markdown_report(summary)
    path.write_text(report_content, encoding="utf-8")
    return path


def write_html_report(
    summary: Mapping[str, object], output_path: str | Path = "reports/report.html"
) -> Path:
    """Kirjoita HTML-raportti tiedostoon ja palauta polku."""

    path = Path(output_path)
    report_content = generate_html_report(summary)
    path.write_text(report_content, encoding="utf-8")
    return path
