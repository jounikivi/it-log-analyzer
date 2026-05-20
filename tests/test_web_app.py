from io import BytesIO
from unittest.mock import patch

from src.web_app import (
    MAX_REQUEST_SIZE_BYTES,
    analyze_from_form_data,
    application,
    decode_multipart_form_data,
    decode_urlencoded_form_data,
    render_dashboard_page,
    render_default_dashboard,
)


def build_multipart_payload(
    fields: dict[str, str],
    *,
    file_name: str | None = None,
    file_content: bytes = b"",
) -> tuple[str, bytes]:
    boundary = "----CodexBoundary12345"
    chunks: list[bytes] = []

    for key, value in fields.items():
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )

    if file_name is not None:
        chunks.append(
            (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="upload_file"; '
                f'filename="{file_name}"\r\n'
                "Content-Type: text/csv\r\n\r\n"
            ).encode("utf-8")
        )
        chunks.append(file_content)
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return f"multipart/form-data; boundary={boundary}", b"".join(chunks)


def test_decode_urlencoded_form_data_decodes_payload() -> None:
    payload = b"mode=sample&top_services=3&top_errors=2"

    decoded = decode_urlencoded_form_data(payload)

    assert decoded == {
        "mode": "sample",
        "top_services": "3",
        "top_errors": "2",
    }


def test_decode_multipart_form_data_reads_fields_and_upload() -> None:
    content_type, body = build_multipart_payload(
        {"mode": "analyze", "top_services": "4", "top_errors": "3"},
        file_name="upload.csv",
        file_content=(
            b"timestamp,level,service,message\n"
            b"2026-03-26T08:00:00Z,INFO,auth-service,Login ok\n"
        ),
    )

    form_data, uploaded_file = decode_multipart_form_data(body, content_type)

    assert form_data == {
        "mode": "analyze",
        "top_services": "4",
        "top_errors": "3",
    }
    assert uploaded_file == {
        "filename": "upload.csv",
        "content": (
            b"timestamp,level,service,message\n"
            b"2026-03-26T08:00:00Z,INFO,auth-service,Login ok\n"
        ),
    }


def test_analyze_from_form_data_uses_uploaded_csv() -> None:
    form_data = {
        "mode": "analyze",
        "top_services": "4",
        "top_errors": "3",
        "level_filter": "ERROR",
        "service_query": "api",
        "message_query": "timeout",
    }
    uploaded_file = {
        "filename": "upload.csv",
        "content": (
            b"timestamp,level,service,message\n"
            b"2026-03-26T08:00:00Z,INFO,auth-service,Login ok\n"
        ),
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
        summary = analyze_from_form_data(form_data, uploaded_file)

    assert summary["file_path"] == "upload.csv"
    analyze_csv_text.assert_called_once_with(
        "timestamp,level,service,message\n2026-03-26T08:00:00Z,INFO,auth-service,Login ok\n",
        source_name="upload.csv",
        top_services=4,
        top_errors=3,
        level_filter="ERROR",
        service_query="api",
        message_query="timeout",
    )


def test_application_rejects_too_large_upload() -> None:
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = headers

    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/analyze",
        "CONTENT_TYPE": "multipart/form-data; boundary=ignored",
        "CONTENT_LENGTH": str(MAX_REQUEST_SIZE_BYTES + 1),
        "wsgi.input": BytesIO(b""),
    }

    body = b"".join(application(environ, start_response)).decode("utf-8")

    assert captured["status"] == "413 Payload Too Large"
    assert "Maksimikoko on 10 MB" in body


def test_render_dashboard_page_contains_updated_ui_sections() -> None:
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

    page = render_dashboard_page(
        summary=summary,
        success_message="Valmis.",
        form_state={
            "level_filter": "ERROR",
            "service_query": "api",
            "message_query": "timeout",
        },
    )
    html = page.decode("utf-8")

    assert "IT Log Analyzer" in html
    assert "Valitse CSV koneelta" in html
    assert "Komentorivi vaihtoehtona" in html
    assert "Lokitaso" in html
    assert "Palveluhaku" in html
    assert "Viestihaku" in html
    assert "Aktiiviset suodattimet" in html
    assert "Taso: ERROR" in html
    assert "Palvelukohtainen yhteenveto" in html
    assert "Tuntikohtainen aktiivisuus" in html
    assert "Upstream service timeout" in html


def test_render_default_dashboard_starts_without_sample_results() -> None:
    html = render_default_dashboard().decode("utf-8")

    assert "Ei analyysiä vielä" in html
    assert "Raporttilinkit tulevat nakyviin analyysin jalkeen." in html
    assert "Palvelukohtainen yhteenveto" not in html
