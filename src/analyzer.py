"""Lokitiedoston lukeminen ja perustason analyysi."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable, TextIO, TypedDict

from .report_generator import write_html_report, write_markdown_report

SUPPORTED_LEVELS = ("ERROR", "WARNING", "INFO")


class LogSummary(TypedDict):
    file_path: str
    total_rows: int
    ERROR: int
    WARNING: int
    INFO: int
    OTHER: int
    service_counts: dict[str, int]
    top_error_messages: list[tuple[str, int]]
    hourly_counts: dict[str, int]
    busiest_hour: tuple[str, int] | None


def read_log_rows_from_stream(stream: TextIO) -> list[dict[str, str]]:
    """Lue CSV-muotoinen lokidata tiedostovirrasta listaksi riveja."""

    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        raise ValueError("Lokitiedosto on tyhja.")

    normalized_fieldnames = [(field or "").strip().lower() for field in reader.fieldnames]
    if "level" not in normalized_fieldnames:
        raise ValueError("Lokitiedostosta puuttuu 'level'-sarake.")

    rows: list[dict[str, str]] = []
    for row in reader:
        normalized_row = {
            (key or "").strip().lower(): (value or "").strip() for key, value in row.items()
        }
        rows.append(normalized_row)

    return rows


def read_log_rows_from_text(csv_text: str) -> list[dict[str, str]]:
    """Lue CSV-muotoinen lokidata tekstista."""

    return read_log_rows_from_stream(io.StringIO(csv_text))


def read_log_rows(file_path: str | Path) -> list[dict[str, str]]:
    """Lue CSV-muotoinen lokitiedosto listaksi riveja."""

    path = Path(file_path)

    with path.open("r", encoding="utf-8", newline="") as file:
        return read_log_rows_from_stream(file)


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
    rows: Iterable[dict[str, str]], limit: int = 5
) -> list[tuple[str, int]]:
    """Palauta yleisimmat ERROR-viestit yleisyysjarjestyksessa."""

    counter: Counter[str] = Counter()

    for row in rows:
        if row.get("level", "").strip().upper() != "ERROR":
            continue

        message = row.get("message", "").strip() or "(tyhja viesti)"
        counter[message] += 1

    return sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))[:limit]


def parse_hour_bucket(timestamp: str) -> str | None:
    """Muunna ISO-aikaleima tuntitason ryhmittelyavaimeksi."""

    normalized = timestamp.strip()
    if not normalized:
        return None

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    return parsed.strftime("%Y-%m-%d %H:00")


def summarize_activity_by_hour(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    """Laske lokirivien maarat tunneittain aikaleiman perusteella."""

    counter: Counter[str] = Counter()

    for row in rows:
        hour_bucket = parse_hour_bucket(row.get("timestamp", ""))
        if hour_bucket is not None:
            counter[hour_bucket] += 1

    return dict(sorted(counter.items(), key=lambda item: item[0]))


def get_busiest_hour(hourly_counts: dict[str, int]) -> tuple[str, int] | None:
    """Palauta aktiivisin tunti tai None jos aikaleimoja ei voitu tulkita."""

    if not hourly_counts:
        return None

    return sorted(hourly_counts.items(), key=lambda item: (-item[1], item[0]))[0]


def positive_int(value: str) -> int:
    """Argparse-apuri positiivisille kokonaisluvuille."""

    integer = int(value)
    if integer < 1:
        raise argparse.ArgumentTypeError("arvon tulee olla positiivinen kokonaisluku")
    return integer


def analyze_log_rows(
    rows: list[dict[str, str]],
    source_name: str,
    top_services: int = 5,
    top_errors: int = 5,
) -> LogSummary:
    """Luo valmis yhteenveto jo luetuista lokiriveista."""

    summary = summarize_levels(rows)
    service_counts = dict(list(summarize_services(rows).items())[:top_services])
    top_error_messages = summarize_top_error_messages(rows, limit=top_errors)
    hourly_counts = summarize_activity_by_hour(rows)
    busiest_hour = get_busiest_hour(hourly_counts)

    return {
        "file_path": source_name,
        **summary,
        "service_counts": service_counts,
        "top_error_messages": top_error_messages,
        "hourly_counts": hourly_counts,
        "busiest_hour": busiest_hour,
    }


def analyze_csv_text(
    csv_text: str,
    source_name: str = "syotetty_lokidata.csv",
    top_services: int = 5,
    top_errors: int = 5,
) -> LogSummary:
    """Analysoi selaimesta tai muualta saatua CSV-tekstia."""

    rows = read_log_rows_from_text(csv_text)
    return analyze_log_rows(
        rows,
        source_name=source_name,
        top_services=top_services,
        top_errors=top_errors,
    )


def analyze_log_file(
    file_path: str | Path, top_services: int = 5, top_errors: int = 5
) -> LogSummary:
    """Lue tiedosto ja palauta valmis yhteenveto."""

    rows = read_log_rows(file_path)
    return analyze_log_rows(
        rows,
        source_name=str(Path(file_path)),
        top_services=top_services,
        top_errors=top_errors,
    )


def format_summary(summary: LogSummary) -> str:
    """Muodosta analyysin tuloksista suomenkielinen tekstiyhteenveto."""

    lines = [
        f"Analyysi valmis tiedostolle: {summary['file_path']}",
        f"Riveja yhteensa: {summary['total_rows']}",
        f"ERROR-riveja: {summary['ERROR']}",
        f"WARNING-riveja: {summary['WARNING']}",
        f"INFO-riveja: {summary['INFO']}",
        f"Muita riveja: {summary['OTHER']}",
    ]

    if summary["service_counts"]:
        top_service = next(iter(summary["service_counts"].items()))
        lines.append(f"Yleisin palvelu: {top_service[0]} ({top_service[1]})")
        lines.append("Palvelukohtainen yhteenveto:")
        for service, count in summary["service_counts"].items():
            lines.append(f"- {service}: {count}")

    if summary["busiest_hour"] is not None:
        lines.append(
            f"Aktiivisin tunti: {summary['busiest_hour'][0]} ({summary['busiest_hour'][1]} rivi(a))"
        )

    if summary["hourly_counts"]:
        lines.append("Tuntikohtainen aktiivisuus:")
        for hour, count in summary["hourly_counts"].items():
            lines.append(f"- {hour}: {count}")

    if summary["top_error_messages"]:
        lines.append("Yleisimmat ERROR-viestit:")
        for message, count in summary["top_error_messages"]:
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
    parser.add_argument(
        "--top-services",
        type=positive_int,
        default=5,
        help="Kuinka monta palvelua naytetaan yhteenvedoissa.",
    )
    parser.add_argument(
        "--top-errors",
        type=positive_int,
        default=5,
        help="Kuinka monta ERROR-viestia naytetaan yhteenvedoissa.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Komentorivisisaanmeno analysoijan ensimmaiselle versiolle."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        summary = analyze_log_file(
            args.file_path,
            top_services=args.top_services,
            top_errors=args.top_errors,
        )
        report_path = write_markdown_report(summary, args.output)
        html_report_path = write_html_report(summary, args.html_output)
    except FileNotFoundError:
        print(f"Virhe: tiedostoa ei loytynyt: {args.file_path}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Virhe: {error}", file=sys.stderr)
        return 1

    print(format_summary(summary))
    print(f"Raportti kirjoitettu tiedostoon: {report_path}")
    print(f"HTML-raportti kirjoitettu tiedostoon: {html_report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
