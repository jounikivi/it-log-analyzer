"""Raporttien muodostaminen analyysin tuloksista."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Mapping


def get_service_counts(summary: Mapping[str, object]) -> dict[str, int]:
    raw_value = summary.get("service_counts", {})
    return raw_value if isinstance(raw_value, dict) else {}


def get_top_error_messages(summary: Mapping[str, object]) -> list[tuple[str, int]]:
    raw_value = summary.get("top_error_messages", [])
    return raw_value if isinstance(raw_value, list) else []


def escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")


def generate_markdown_report(summary: Mapping[str, object]) -> str:
    """Muodosta analyysin tuloksista Markdown-raportti."""

    service_counts = get_service_counts(summary)
    top_error_messages = get_top_error_messages(summary)

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

    file_path = escape(str(summary["file_path"]))
    service_counts = get_service_counts(summary)
    top_error_messages = get_top_error_messages(summary)

    service_rows = "\n".join(
        [
            f"              <tr><td>{escape(service)}</td><td>{count}</td></tr>"
            for service, count in service_counts.items()
        ]
    )
    error_rows = "\n".join(
        [
            f"              <tr><td>{escape(message)}</td><td>{count}</td></tr>"
            for message, count in top_error_messages
        ]
    )

    return f"""<!doctype html>
<html lang="fi">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>IT Log Analyzer - raportti</title>
    <style>
      :root {{
        --bg: #f4f7fb;
        --panel: #ffffff;
        --text: #1b2430;
        --muted: #5a6b7f;
        --border: #d7e0ea;
        --accent: #1f5f8b;
        --error: #b42318;
        --warning: #b54708;
        --info: #175cd3;
        --other: #667085;
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        background:
          radial-gradient(circle at top left, #dceeff 0%, transparent 35%),
          linear-gradient(180deg, #f9fbfd 0%, var(--bg) 100%);
        color: var(--text);
      }}

      main {{
        max-width: 900px;
        margin: 0 auto;
        padding: 48px 20px 64px;
      }}

      .hero {{
        margin-bottom: 24px;
      }}

      .eyebrow {{
        display: inline-block;
        margin-bottom: 12px;
        padding: 6px 10px;
        border-radius: 999px;
        background: #d9ecfb;
        color: var(--accent);
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
      }}

      h1 {{
        margin: 0 0 8px;
        font-size: clamp(2rem, 4vw, 3rem);
        line-height: 1.1;
      }}

      p {{
        margin: 0;
        color: var(--muted);
        line-height: 1.6;
      }}

      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
        margin: 28px 0;
      }}

      .card {{
        padding: 18px;
        border: 1px solid var(--border);
        border-radius: 18px;
        background: var(--panel);
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
      }}

      .label {{
        margin-bottom: 8px;
        color: var(--muted);
        font-size: 0.92rem;
      }}

      .value {{
        font-size: 2rem;
        font-weight: 700;
        line-height: 1;
      }}

      .error .value {{
        color: var(--error);
      }}

      .warning .value {{
        color: var(--warning);
      }}

      .info .value {{
        color: var(--info);
      }}

      .other .value {{
        color: var(--other);
      }}

      .source {{
        margin-top: 24px;
        padding: 20px;
        border-radius: 18px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.78);
      }}

      .details {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 18px;
        margin-top: 24px;
      }}

      .panel-title {{
        margin: 0 0 14px;
        font-size: 1.1rem;
      }}

      table {{
        width: 100%;
        border-collapse: collapse;
      }}

      th,
      td {{
        padding: 10px 0;
        border-bottom: 1px solid var(--border);
        text-align: left;
      }}

      th:last-child,
      td:last-child {{
        text-align: right;
      }}

      .empty-state {{
        color: var(--muted);
      }}

      code {{
        font-family: Consolas, "Courier New", monospace;
        font-size: 0.95rem;
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <div class="eyebrow">Analyysiraportti</div>
        <h1>IT Log Analyzer</h1>
        <p>Automaattisesti generoitu yhteenveto lokitiedoston tapahtumatasoista.</p>
      </section>

      <section class="grid" aria-label="Yhteenveto">
        <article class="card">
          <div class="label">Riveja yhteensa</div>
          <div class="value">{summary["total_rows"]}</div>
        </article>
        <article class="card error">
          <div class="label">ERROR-riveja</div>
          <div class="value">{summary["ERROR"]}</div>
        </article>
        <article class="card warning">
          <div class="label">WARNING-riveja</div>
          <div class="value">{summary["WARNING"]}</div>
        </article>
        <article class="card info">
          <div class="label">INFO-riveja</div>
          <div class="value">{summary["INFO"]}</div>
        </article>
        <article class="card other">
          <div class="label">Muita riveja</div>
          <div class="value">{summary["OTHER"]}</div>
        </article>
      </section>

      <section class="source">
        <div class="label">Lahdetiedosto</div>
        <code>{file_path}</code>
      </section>

      <section class="details">
        <article class="card">
          <h2 class="panel-title">Palvelukohtainen yhteenveto</h2>
          <table>
            <thead>
              <tr>
                <th>Palvelu</th>
                <th>Riveja</th>
              </tr>
            </thead>
            <tbody>
{service_rows}
            </tbody>
          </table>
        </article>

        <article class="card">
          <h2 class="panel-title">Yleisimmat ERROR-viestit</h2>
{"          <table>\n            <thead>\n              <tr>\n                <th>Viesti</th>\n                <th>Maara</th>\n              </tr>\n            </thead>\n            <tbody>\n" + error_rows + "\n            </tbody>\n          </table>" if top_error_messages else '          <p class="empty-state">Ei ERROR-riveja analysoidussa tiedostossa.</p>'}
        </article>
      </section>
    </main>
  </body>
</html>
"""


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
