"""Selainkayttoliittyma IT Log Analyzerille."""

from __future__ import annotations

from argparse import ArgumentParser
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from typing import Callable, Mapping, TypedDict
from urllib.parse import parse_qs
import mimetypes

from jinja2 import Environment, FileSystemLoader, select_autoescape
from wsgiref.simple_server import make_server

from .analyzer import LogSummary, analyze_csv_text, analyze_log_file, normalize_level_filter, positive_int
from .report_generator import write_html_report, write_markdown_report

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
REPORTS_DIR = BASE_DIR / "reports"
SAMPLE_DATA_PATH = BASE_DIR / "data" / "sample_logs.csv"
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MAX_REQUEST_SIZE_BYTES = MAX_UPLOAD_SIZE_BYTES + 256 * 1024

template_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


class UploadedFile(TypedDict):
    filename: str
    content: bytes


class RequestTooLargeError(ValueError):
    """Poikkeus liian suurille upload-pyynnoille."""


def get_default_form_state() -> dict[str, str]:
    return {
        "top_services": "5",
        "top_errors": "5",
        "level_filter": "",
        "service_query": "",
        "message_query": "",
    }


def decode_urlencoded_form_data(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def decode_multipart_form_data(body: bytes, content_type: str) -> tuple[dict[str, str], UploadedFile | None]:
    if not body:
        return {}, None

    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise ValueError("Lomakedataa ei voitu tulkita tiedoston lataukseksi.")

    form_data: dict[str, str] = {}
    uploaded_file: UploadedFile | None = None

    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue

        field_name = part.get_param("name", header="content-disposition")
        if not field_name:
            continue

        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename:
            uploaded_file = {
                "filename": Path(filename).name,
                "content": payload,
            }
            continue

        charset = part.get_content_charset() or "utf-8"
        form_data[field_name] = payload.decode(charset, errors="replace")

    return form_data, uploaded_file


def decode_request_data(body: bytes, content_type: str) -> tuple[dict[str, str], UploadedFile | None]:
    if "multipart/form-data" in content_type:
        return decode_multipart_form_data(body, content_type)
    return decode_urlencoded_form_data(body), None


def parse_positive_option(form_data: Mapping[str, str], key: str, default: int) -> int:
    raw_value = form_data.get(key, "").strip()
    if not raw_value:
        return default

    try:
        return positive_int(raw_value)
    except Exception as error:
        raise ValueError(f"Kentta '{key}' ei ollut kelvollinen numero.") from error


def parse_filter_text(form_data: Mapping[str, str], key: str) -> str:
    return form_data.get(key, "").strip()


def build_active_filters(form_state: Mapping[str, str]) -> list[str]:
    filters: list[str] = []

    if form_state.get("level_filter", "").strip():
        filters.append(f"Taso: {form_state['level_filter'].strip().upper()}")

    if form_state.get("service_query", "").strip():
        filters.append(f"Palvelu: {form_state['service_query'].strip()}")

    if form_state.get("message_query", "").strip():
        filters.append(f"Viesti: {form_state['message_query'].strip()}")

    return filters


def replace_summary_source_name(summary: LogSummary, source_name: str) -> LogSummary:
    return {
        "file_path": source_name,
        "total_rows": summary["total_rows"],
        "ERROR": summary["ERROR"],
        "WARNING": summary["WARNING"],
        "INFO": summary["INFO"],
        "OTHER": summary["OTHER"],
        "service_counts": dict(summary["service_counts"]),
        "top_error_messages": list(summary["top_error_messages"]),
        "hourly_counts": dict(summary["hourly_counts"]),
        "busiest_hour": summary["busiest_hour"],
    }


def decode_uploaded_text(uploaded_file: UploadedFile) -> str:
    try:
        return uploaded_file["content"].decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Ladattu tiedosto ei ole kelvollinen UTF-8-koodattu CSV-tiedosto.") from error


def analyze_from_form_data(
    form_data: Mapping[str, str],
    uploaded_file: UploadedFile | None = None,
) -> LogSummary:
    mode = form_data.get("mode", "").strip().lower()
    top_services = parse_positive_option(form_data, "top_services", 5)
    top_errors = parse_positive_option(form_data, "top_errors", 5)
    level_filter = normalize_level_filter(parse_filter_text(form_data, "level_filter"))
    service_query = parse_filter_text(form_data, "service_query")
    message_query = parse_filter_text(form_data, "message_query")

    if mode == "sample":
        summary = analyze_log_file(
            SAMPLE_DATA_PATH,
            top_services=top_services,
            top_errors=top_errors,
            level_filter=level_filter,
            service_query=service_query,
            message_query=message_query,
        )
        return replace_summary_source_name(summary, "data/sample_logs.csv")

    if uploaded_file is None:
        raise ValueError("Valitse CSV-tiedosto tai kayta sample-dataa.")

    if len(uploaded_file["content"]) > MAX_UPLOAD_SIZE_BYTES:
        raise RequestTooLargeError(
            f"Ladattu tiedosto on liian suuri. Maksimikoko on {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."
        )

    if Path(uploaded_file["filename"]).suffix.lower() != ".csv":
        raise ValueError("Valitse CSV-tiedosto (.csv).")

    csv_text = decode_uploaded_text(uploaded_file)
    if not csv_text.strip():
        raise ValueError("Ladattu tiedosto on tyhja.")

    return analyze_csv_text(
        csv_text,
        source_name=uploaded_file["filename"] or "ladattu_lokitiedosto.csv",
        top_services=top_services,
        top_errors=top_errors,
        level_filter=level_filter,
        service_query=service_query,
        message_query=message_query,
    )


def build_form_state(form_data: Mapping[str, str] | None = None) -> dict[str, str]:
    state = get_default_form_state()
    if form_data is None:
        return state

    state["top_services"] = form_data.get("top_services", state["top_services"])
    state["top_errors"] = form_data.get("top_errors", state["top_errors"])
    state["level_filter"] = form_data.get("level_filter", state["level_filter"])
    state["service_query"] = form_data.get("service_query", state["service_query"])
    state["message_query"] = form_data.get("message_query", state["message_query"])
    return state


def read_request_body(environ: Mapping[str, object]) -> bytes:
    raw_content_length = str(environ.get("CONTENT_LENGTH", "0") or "0")
    try:
        content_length = int(raw_content_length)
    except ValueError as error:
        raise ValueError("Pyynnon koko oli virheellinen.") from error

    if content_length > MAX_REQUEST_SIZE_BYTES:
        raise RequestTooLargeError(
            f"Ladattu tiedosto on liian suuri. Maksimikoko on {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."
        )

    return environ["wsgi.input"].read(content_length) if content_length > 0 else b""


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
    state = build_form_state(form_state)

    html = template.render(
        summary=summary,
        error_message=error_message,
        success_message=success_message,
        form_state=state,
        report_markdown_url="/reports/report.md",
        report_html_url="/reports/report.html",
        max_hourly_count=max_hourly_count,
        max_upload_size_mb=MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
        level_filter_options=("", "ERROR", "WARNING", "INFO", "OTHER"),
        active_filters=build_active_filters(state),
    )
    return html.encode("utf-8")


def render_default_dashboard() -> bytes:
    return render_dashboard_page(summary=None)


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
    if resolved_content_type.startswith("text/") or resolved_content_type in {"application/javascript", "application/json"}:
        header_value = f"{resolved_content_type}; charset=utf-8"
    else:
        header_value = resolved_content_type

    return "200 OK", [("Content-Type", header_value)], file_path.read_bytes()


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
        try:
            body = read_request_body(environ)
            form_data, uploaded_file = decode_request_data(body, str(environ.get("CONTENT_TYPE", "")))
            summary = analyze_from_form_data(form_data, uploaded_file)
            write_markdown_report(summary, REPORTS_DIR / "report.md")
            write_html_report(summary, REPORTS_DIR / "report.html")
            response_body = render_dashboard_page(
                summary=summary,
                success_message="Analyysi valmistui onnistuneesti.",
                form_state=form_data,
            )
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [response_body]
        except RequestTooLargeError as error:
            response_body = render_dashboard_page(
                summary=None,
                error_message=str(error),
                form_state={},
            )
            start_response("413 Payload Too Large", [("Content-Type", "text/html; charset=utf-8")])
            return [response_body]
        except ValueError as error:
            response_body = render_dashboard_page(
                summary=None,
                error_message=str(error),
                form_state=locals().get("form_data", {}),
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
