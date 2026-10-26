"""Output rendering helpers shared by all commands.

This module intentionally knows nothing about summary/timeline/grep
semantics — it only provides:
  - output-target resolution (stdout vs. file, per --format rules)
  - writing/printing with the correct confirmation behavior
  - small text/markdown/json building blocks (tables, bar charts, datetime
    serialization) that command modules compose into their own reports.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

VALID_FORMATS = ("text", "json", "md")


def resolve_output_path(
    log_path: str,
    command: str,
    fmt: str,
    output_option: Optional[str],
) -> Optional[str]:
    """Decide where output should go.

    - md: always a file. Uses --output if given, otherwise
      '<logfile-stem>_<command>_report.md' next to the current directory.
    - text/json: a file only if --output was explicitly given, else None
      (meaning stdout).
    """
    if fmt == "md":
        if output_option:
            return output_option
        stem = Path(log_path).stem
        return f"{stem}_{command}_report.md"
    return output_option


def print_confirmation(target_path: Optional[str], fmt: str) -> None:
    """Print the short confirmation line for a file that was already written.

    Used both by `write_output` (below) and by commands that stream their
    own content directly to a file handle (e.g. `grep`) instead of building
    the whole body as one string first.
    """
    if target_path is None:
        return
    if fmt == "md":
        print(f"Markdown report written to {target_path}")
    else:
        print(f"Output written to {target_path}")


def write_output(content: str, target_path: Optional[str], fmt: str) -> None:
    """Write `content` to `target_path`, or print it to stdout if None.

    For `md`, the body is never printed — only a short confirmation line
    with the path that was written.
    """
    if target_path is None:
        print(content)
        return

    text = content if content.endswith("\n") else content + "\n"
    with open(target_path, "w", encoding="utf-8") as handle:
        handle.write(text)

    print_confirmation(target_path, fmt)


def json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def dump_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=json_default)


def format_timestamp(ts: Optional[datetime]) -> Optional[str]:
    return ts.isoformat() if ts is not None else None


# --- text helpers -----------------------------------------------------

def text_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Render a simple aligned plain-text table."""
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells: Sequence[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines = [fmt_row(headers), fmt_row(["-" * w for w in widths])]
    lines.extend(fmt_row(row) for row in str_rows)
    return "\n".join(lines)


def bar_chart(
    labels: Sequence[str],
    values: Sequence[int],
    width: int = 40,
    bar_char: str = "#",
) -> str:
    """Render a horizontal text bar chart, one line per label/value pair."""
    if not labels:
        return "(no data)"
    max_value = max(values) if values else 0
    label_width = max(len(label) for label in labels)
    lines = []
    for label, value in zip(labels, values):
        if max_value > 0:
            bar_len = round((value / max_value) * width)
        else:
            bar_len = 0
        bar = bar_char * bar_len
        lines.append(f"{label.ljust(label_width)} | {bar} {value}")
    return "\n".join(lines)


# --- markdown helpers ---------------------------------------------------

def md_heading(text: str, level: int = 2) -> str:
    return f"{'#' * level} {text}"


def _md_escape_cell(value: Any) -> str:
    text = str(value).replace("|", "\\|")
    return text.replace("\n", " ")


def md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = [
        "| " + " | ".join(_md_escape_cell(cell) for cell in row) + " |" for row in rows
    ]
    return "\n".join([header_line, separator, *row_lines])


def md_bullet_list(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def md_code_block(text: str, lang: str = "") -> str:
    return f"```{lang}\n{text}\n```"


def md_document(title: str, sections: Sequence[Tuple[str, str]]) -> str:
    """Assemble a markdown document from (heading, body) section pairs."""
    parts: List[str] = [md_heading(title, level=1), ""]
    for heading, body in sections:
        parts.append(md_heading(heading, level=2))
        parts.append(body)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
