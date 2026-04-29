"""Selainkayttoliittyma IT Log Analyzerille."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import parse_qs
import mimetypes

from jinja2 import Environment, FileSystemLoader, select_autoescape
from wsgiref.simple_server import make_server

from .analyzer import LogSummary, analyze_csv_text, analyze_log_file, positive_int
from .report_generator import write_html_report, write_markdown_report

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
REPORTS_DIR = BASE_DIR / "reports"
SAMPLE_DATA_PATH = BASE_DIR / "data" / "sample_logs.csv"

template_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def get_default_form_state() -> dict[str, str]:
    return {
        "file_path": "",
        "top_services": "5",
        "top_errors": "5",
    }


def decode_form_data(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def parse_positive_option(form_data: Mapping[str, str], key: str, default: int) -> int:
    raw_value = form_data.get(key, "").strip()
    if not raw_value:
        return default

    try:
        return positive_int(raw_value)
    except Exception as error:
        raise ValueError(f"Kentta '{key}' ei ollut kelvollinen numero.") from error


def resolve_analysis_path(file_path: str) -> Path:
    path = Path(file_path)
    return path if path.is_absolute() else BASE_DIR / path


def replace_summary_source_name(summary: LogSummary, source_name: str) -> LogSummary:
    updated = dict(summary)
    updated["file_path"] = source_name
    return updated  # type: ignore[return-value]


def analyze_from_form_data(form_data: Mapping[str, str]) -> LogSummary:
    mode = form_data.get("mode", "").strip().lower()
    csv_text = form_data.get("csv_text", "")
    source_name = form_data.get("source_name", "").strip() or "ladattu_lokitiedosto.csv"
    file_path = form_data.get("file_path", "").strip()
    top_services = parse_positive_option(form_data, "top_services", 5)
    top_errors = parse_positive_option(form_data, "top_errors", 5)

    if mode == "sample" or (not csv_text and not file_path):
        summary = analyze_log_file(SAMPLE_DATA_PATH, top_services=top_services, top_errors=top_errors)
        return replace_summary_source_name(summary, "data/sample_logs.csv")

    if csv_text:
        return analyze_csv_text(
            csv_text,
            source_name=source_name,
            top_services=top_services,
            top_errors=top_errors,
        )

    if not file_path:
        raise ValueError("Anna tiedostopolku tai valitse CSV-tiedosto.")

    summary = analyze_log_file(
        resolve_analysis_path(file_path),
        top_services=top_services,
        top_errors=top_errors,
    )
    return replace_summary_source_name(summary, file_path)


def build_form_state(form_data: Mapping[str, str] | None = None) -> dict[str, str]:
    state = get_default_form_state()
    if form_data is None:
        return state

    state["file_path"] = form_data.get("file_path", "")
    state["top_services"] = form_data.get("top_services", state["top_services"])
    state["top_errors"] = form_data.get("top_errors", state["top_errors"])
    return state


def render_dashboard_page(
    *,
    summary: LogSummary | None,
    error_message: str | None = None,
    success_message: str | None = None,
    form_state: Mapping[str, str] | None = None,
) -> bytes:
    template = template_env.get_template("dashboard.html")
    max_hourly_count = 0
    if summary is not None and summary["hourly_counts"]:
        max_hourly_count = max(summary["hourly_counts"].values())

    html = template.render(
        summary=summary,
        error_message=error_message,
        success_message=success_message,
        form_state=build_form_state(form_state),
        sample_path=str(SAMPLE_DATA_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
        report_markdown_url="/reports/report.md",
        report_html_url="/reports/report.html",
        max_hourly_count=max_hourly_count,
    )
    return html.encode("utf-8")


def render_default_dashboard() -> bytes:
    try:
        summary = replace_summary_source_name(analyze_log_file(SAMPLE_DATA_PATH), "data/sample_logs.csv")
        write_markdown_report(summary, REPORTS_DIR / "report.md")
        write_html_report(summary, REPORTS_DIR / "report.html")
        return render_dashboard_page(summary=summary)
    except Exception as error:
        return render_dashboard_page(
            summary=None,
            error_message=f"Sample-datan lataus ei onnistunut: {error}",
        )


def ensure_safe_child_path(base_dir: Path, requested_name: str) -> Path:
    candidate = (base_dir / requested_name.lstrip("/")).resolve()
    base_resolved = base_dir.resolve()
    if candidate != base_resolved and base_resolved not in candidate.parents:
        raise FileNotFoundError
    return candidate


def serve_file_response(file_path: Path, content_type: str | None = None) -> tuple[str, list[tuple[str, str]], bytes]:
    if not file_path.exists() or not file_path.is_file():
        return "404 Not Found", [("Content-Type", "text/plain; charset=utf-8")], b"Tiedostoa ei loytynyt."

    resolved_content_type = content_type or mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return "200 OK", [("Content-Type", f"{resolved_content_type}; charset=utf-8")], file_path.read_bytes()


def application(
    environ: Mapping[str, object],
    start_response: Callable[[str, list[tuple[str, str]]], None],
):
    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    path = str(environ.get("PATH_INFO", "/"))

    if method == "GET" and path == "/":
        body = render_default_dashboard()
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    if method == "POST" and path == "/analyze":
        content_length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        body = environ["wsgi.input"].read(content_length) if content_length > 0 else b""
        form_data = decode_form_data(body)

        try:
            summary = analyze_from_form_data(form_data)
            write_markdown_report(summary, REPORTS_DIR / "report.md")
            write_html_report(summary, REPORTS_DIR / "report.html")
            response_body = render_dashboard_page(
                summary=summary,
                success_message="Analyysi valmistui onnistuneesti.",
                form_state=form_data,
            )
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [response_body]
        except FileNotFoundError:
            response_body = render_dashboard_page(
                summary=None,
                error_message=f"Tiedostoa ei loytynyt: {form_data.get('file_path', '')}",
                form_state=form_data,
            )
            start_response("400 Bad Request", [("Content-Type", "text/html; charset=utf-8")])
            return [response_body]
        except ValueError as error:
            response_body = render_dashboard_page(
                summary=None,
                error_message=str(error),
                form_state=form_data,
            )
            start_response("400 Bad Request", [("Content-Type", "text/html; charset=utf-8")])
            return [response_body]

    if method == "GET" and path.startswith("/static/"):
        try:
            safe_path = ensure_safe_child_path(STATIC_DIR, path.removeprefix("/static/"))
            status, headers, body = serve_file_response(safe_path)
        except FileNotFoundError:
            status, headers, body = (
                "404 Not Found",
                [("Content-Type", "text/plain; charset=utf-8")],
                b"Tiedostoa ei loytynyt.",
            )
        start_response(status, headers)
        return [body]

    if method == "GET" and path.startswith("/reports/"):
        try:
            safe_path = ensure_safe_child_path(REPORTS_DIR, path.removeprefix("/reports/"))
            status, headers, body = serve_file_response(safe_path)
        except FileNotFoundError:
            status, headers, body = (
                "404 Not Found",
                [("Content-Type", "text/plain; charset=utf-8")],
                b"Tiedostoa ei loytynyt.",
            )
        start_response(status, headers)
        return [body]

    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Sivua ei loytynyt."]


def build_argument_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Kaynnista IT Log Analyzerin selainkayttoliittyma.")
    parser.add_argument("--host", default="127.0.0.1", help="Palvelimen host-osoite.")
    parser.add_argument("--port", type=int, default=8000, help="Palvelimen portti.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    with make_server(args.host, args.port, application) as server:
        print(f"Kayttoliittyma kaynnissa osoitteessa http://{args.host}:{args.port}")
        print("Pysayta palvelin painamalla Ctrl+C.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nPalvelin pysaytetty.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
