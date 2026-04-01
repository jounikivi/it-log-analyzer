"""Lokitiedoston lukeminen ja perustason analyysi."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Iterable

from .report_generator import write_html_report, write_markdown_report

SUPPORTED_LEVELS = ("ERROR", "WARNING", "INFO")


def read_log_rows(file_path: str | Path) -> list[dict[str, str]]:
    """Lue CSV-muotoinen lokitiedosto listaksi riveja."""

    path = Path(file_path)

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("Lokitiedosto on tyhja.")

        normalized_fieldnames = [(field or "").strip().lower() for field in reader.fieldnames]
        if "level" not in normalized_fieldnames:
            raise ValueError("Lokitiedostosta puuttuu 'level'-sarake.")

        rows: list[dict[str, str]] = []
        for row in reader:
            normalized_row = {
                (key or "").strip().lower(): (value or "").strip()
                for key, value in row.items()
            }
            rows.append(normalized_row)

    return rows


def summarize_levels(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    """Laske tuettujen tasojen maarat ja niputa muut OTHER-luokkaan."""

    counter: Counter[str] = Counter({level: 0 for level in SUPPORTED_LEVELS})
    counter["OTHER"] = 0

    for row in rows:
        level = row.get("level", "").strip().upper()
        if level in SUPPORTED_LEVELS:
            counter[level] += 1
        else:
            counter["OTHER"] += 1

    total_rows = sum(counter.values())

    return {
        "total_rows": total_rows,
        "ERROR": counter["ERROR"],
        "WARNING": counter["WARNING"],
        "INFO": counter["INFO"],
        "OTHER": counter["OTHER"],
    }


def summarize_services(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    """Laske rivimaarat palveluittain."""

    counter: Counter[str] = Counter()

    for row in rows:
        service = row.get("service", "").strip() or "UNKNOWN"
        counter[service] += 1

    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0].lower())))


def summarize_top_error_messages(
    rows: Iterable[dict[str, str]], limit: int = 3
) -> list[tuple[str, int]]:
    """Palauta yleisimmat ERROR-viestit yleisyysjarjestyksessa."""

    counter: Counter[str] = Counter()

    for row in rows:
        if row.get("level", "").strip().upper() != "ERROR":
            continue

        message = row.get("message", "").strip() or "(tyhja viesti)"
        counter[message] += 1

    return sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))[:limit]


def analyze_log_file(file_path: str | Path) -> dict[str, object]:
    """Lue tiedosto ja palauta valmis yhteenveto."""

    rows = read_log_rows(file_path)
    summary = summarize_levels(rows)
    service_counts = summarize_services(rows)
    top_error_messages = summarize_top_error_messages(rows)

    return {
        "file_path": str(Path(file_path)),
        **summary,
        "service_counts": service_counts,
        "top_error_messages": top_error_messages,
    }


def format_summary(summary: dict[str, object]) -> str:
    """Muodosta analyysin tuloksista suomenkielinen tekstiyhteenveto."""

    service_counts = summary.get("service_counts", {})
    top_error_messages = summary.get("top_error_messages", [])

    lines = [
        f"Analyysi valmis tiedostolle: {summary['file_path']}",
        f"Riveja yhteensa: {summary['total_rows']}",
        f"ERROR-riveja: {summary['ERROR']}",
        f"WARNING-riveja: {summary['WARNING']}",
        f"INFO-riveja: {summary['INFO']}",
        f"Muita riveja: {summary['OTHER']}",
    ]

    if isinstance(service_counts, dict) and service_counts:
        top_service = next(iter(service_counts.items()))
        lines.append(f"Yleisin palvelu: {top_service[0]} ({top_service[1]})")
        lines.append("Palvelukohtainen yhteenveto:")
        for service, count in service_counts.items():
            lines.append(f"- {service}: {count}")

    if isinstance(top_error_messages, list):
        if top_error_messages:
            lines.append("Yleisimmat ERROR-viestit:")
            for message, count in top_error_messages:
                lines.append(f"- {message} ({count})")
        else:
            lines.append("Yleisimmat ERROR-viestit: ei virheriveja")

    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    """Luo komentoriviparseri analysoijalle."""

    parser = argparse.ArgumentParser(description="Analysoi CSV-muotoisen lokitiedoston.")
    parser.add_argument(
        "file_path",
        nargs="?",
        default="data/sample_logs.csv",
        help="Polku analysoitavaan CSV-lokitiedostoon.",
    )
    parser.add_argument(
        "--output",
        default="reports/report.md",
        help="Polku kirjoitettavaan Markdown-raporttiin.",
    )
    parser.add_argument(
        "--html-output",
        default="reports/report.html",
        help="Polku kirjoitettavaan HTML-raporttiin.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Komentorivisisaanmeno analysoijan ensimmaiselle versiolle."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)
    summary = analyze_log_file(args.file_path)
    report_path = write_markdown_report(summary, args.output)
    html_report_path = write_html_report(summary, args.html_output)
    print(format_summary(summary))
    print(f"Raportti kirjoitettu tiedostoon: {report_path}")
    print(f"HTML-raportti kirjoitettu tiedostoon: {html_report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
