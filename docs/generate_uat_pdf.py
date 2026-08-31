#!/usr/bin/env python3
"""Render PrepVilla's Markdown UAT script as a dependency-free PDF."""

from __future__ import annotations

import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path


PAGE_WIDTH = 595.28
PAGE_HEIGHT = 841.89
LEFT = 48.0
RIGHT = 48.0
TOP = 66.0
BOTTOM = 52.0
CONTENT_WIDTH = PAGE_WIDTH - LEFT - RIGHT


@dataclass
class Style:
    font: str
    size: float
    leading: float
    before: float
    after: float
    color: tuple[float, float, float]
    indent: float = 0.0


STYLES = {
    "h1": Style("F2", 20.0, 24.0, 2.0, 12.0, (0.08, 0.16, 0.27)),
    "h2": Style("F2", 14.0, 18.0, 12.0, 7.0, (0.48, 0.16, 0.12)),
    "h3": Style("F2", 11.3, 14.5, 10.0, 4.5, (0.08, 0.16, 0.27)),
    "body": Style("F1", 8.9, 12.0, 0.0, 4.0, (0.08, 0.08, 0.09)),
    "label": Style("F2", 8.8, 11.8, 0.0, 3.0, (0.08, 0.08, 0.09)),
    "list": Style("F1", 8.8, 11.8, 0.0, 2.2, (0.08, 0.08, 0.09), 14.0),
    "table": Style("F1", 7.7, 10.1, 0.0, 1.8, (0.12, 0.12, 0.14)),
}


def clean_markdown(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = text.replace("**", "")
    return text.strip()


def estimate_width(text: str, size: float) -> float:
    total = 0.0
    for char in text:
        if char in " ilI.,:;'!|":
            factor = 0.27
        elif char in "MW@%#":
            factor = 0.86
        elif char.isupper() or char.isdigit():
            factor = 0.59
        else:
            factor = 0.50
        total += factor * size
    return total


def wrap_text(text: str, style: Style, first_prefix: str = "", continuation_prefix: str = "") -> list[str]:
    available = CONTENT_WIDTH - style.indent
    first_available = max(60.0, available - estimate_width(first_prefix, style.size))
    subsequent_available = max(60.0, available - estimate_width(continuation_prefix, style.size))
    words = text.split()
    if not words:
        return [first_prefix.rstrip()]

    lines: list[str] = []
    current = ""
    current_limit = first_available
    while words:
        word = words.pop(0)
        candidate = word if not current else f"{current} {word}"
        if estimate_width(candidate, style.size) <= current_limit:
            current = candidate
            continue
        if current:
            lines.append((first_prefix if not lines else continuation_prefix) + current)
            current = ""
            current_limit = subsequent_available
            words.insert(0, word)
            continue
        # A single very long token (for example, a path) is split conservatively.
        max_chars = max(8, int(current_limit / (style.size * 0.52)))
        parts = textwrap.wrap(word, width=max_chars, break_long_words=True, break_on_hyphens=False)
        lines.append((first_prefix if not lines else continuation_prefix) + parts[0])
        words = parts[1:] + words
        current_limit = subsequent_available
    if current:
        lines.append((first_prefix if not lines else continuation_prefix) + current)
    return lines


def parse_blocks(markdown: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append(("body", clean_markdown(" ".join(paragraph))))
            paragraph.clear()

    for raw in markdown.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith("### "):
            flush()
            blocks.append(("h3", clean_markdown(stripped[4:])))
        elif stripped.startswith("## "):
            flush()
            blocks.append(("h2", clean_markdown(stripped[3:])))
        elif stripped.startswith("# "):
            flush()
            blocks.append(("h1", clean_markdown(stripped[2:])))
        elif re.match(r"^\|(?:\s*:?-+:?\s*\|)+$", stripped):
            flush()
        elif stripped.startswith("|") and stripped.endswith("|"):
            flush()
            cells = [clean_markdown(cell) for cell in stripped.strip("|").split("|")]
            blocks.append(("table", " | ".join(cells)))
        elif re.match(r"^\d+\.\s+", stripped):
            flush()
            match = re.match(r"^(\d+\.)\s+(.*)$", stripped)
            assert match
            blocks.append(("list", f"{match.group(1)}\t{clean_markdown(match.group(2))}"))
        elif stripped.startswith("- "):
            flush()
            blocks.append(("list", f"-\t{clean_markdown(stripped[2:])}"))
        elif any(
            stripped.startswith(prefix)
            for prefix in (
                "Priority:",
                "Status:",
                "Tester:",
                "Objective:",
                "Preconditions / test data:",
                "Expected result:",
                "Actual result / evidence:",
                "Defect ID:",
                "Product:",
                "Application reviewed:",
                "Prepared date:",
                "Execution status values:",
                "Roles in this document:",
            )
        ):
            flush()
            blocks.append(("label", clean_markdown(stripped.rstrip("  "))))
        else:
            paragraph.append(stripped.rstrip("  "))
    flush()
    return blocks


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def command_for_text(text: str, x: float, y: float, style: Style) -> str:
    r, g, b = style.color
    escaped = pdf_escape(text)
    return (
        f"BT /{style.font} {style.size:.2f} Tf {r:.3f} {g:.3f} {b:.3f} rg "
        f"1 0 0 1 {x:.2f} {y:.2f} Tm ({escaped}) Tj ET"
    )


def layout(markdown: str) -> list[list[str]]:
    pages: list[list[str]] = [[]]
    y = PAGE_HEIGHT - TOP

    def new_page() -> None:
        nonlocal y
        pages.append([])
        y = PAGE_HEIGHT - TOP

    for kind, text in parse_blocks(markdown):
        style = STYLES[kind]
        if kind == "h3" and y < BOTTOM + 130:
            new_page()
        if kind == "h2" and y < BOTTOM + 95:
            new_page()

        y -= style.before
        if kind == "list":
            prefix, value = text.split("\t", 1)
            hanging = " " * (len(prefix) + 1)
            lines = wrap_text(value, style, f"{prefix} ", hanging)
        else:
            lines = wrap_text(text, style)

        for line in lines:
            if y - style.leading < BOTTOM:
                new_page()
            pages[-1].append(command_for_text(line, LEFT + style.indent, y, style))
            y -= style.leading
        y -= style.after

    total = len(pages)
    header_style = Style("F1", 7.6, 9.0, 0, 0, (0.35, 0.35, 0.38))
    footer_style = Style("F1", 7.6, 9.0, 0, 0, (0.35, 0.35, 0.38))
    for index, commands in enumerate(pages, start=1):
        header = command_for_text("PrepVilla Teacher and Student User Acceptance Test", LEFT, PAGE_HEIGHT - 33, header_style)
        footer_text = f"PrepVilla UAT | Page {index} of {total}"
        footer_x = PAGE_WIDTH - RIGHT - estimate_width(footer_text, footer_style.size)
        footer = command_for_text(footer_text, footer_x, 25, footer_style)
        rule_top = f"0.82 0.82 0.84 RG 0.5 w {LEFT:.2f} {PAGE_HEIGHT - 42:.2f} m {PAGE_WIDTH - RIGHT:.2f} {PAGE_HEIGHT - 42:.2f} l S"
        rule_bottom = f"0.82 0.82 0.84 RG 0.5 w {LEFT:.2f} 39 m {PAGE_WIDTH - RIGHT:.2f} 39 l S"
        commands[:0] = [header, rule_top]
        commands.extend([rule_bottom, footer])
    return pages


def build_pdf(pages: list[list[str]], output_path: Path) -> None:
    objects: list[bytes | None] = [None, None, None, None, None]
    # Object indexes 1-4 are Catalog, Pages, Helvetica, and Helvetica-Bold.
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    objects[4] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"

    page_refs: list[int] = []
    for commands in pages:
        page_obj = len(objects)
        content_obj = page_obj + 1
        page_refs.append(page_obj)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH:.2f} {PAGE_HEIGHT:.2f}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_obj} 0 R >>"
            ).encode("ascii")
        )
        stream = ("\n".join(commands) + "\n").encode("latin-1", "replace")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"endstream")

    kids = " ".join(f"{ref} 0 R" for ref in page_refs)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >>".encode("ascii")

    info_obj = len(objects)
    objects.append(
        b"<< /Title (PrepVilla Teacher and Student User Acceptance Test) "
        b"/Author (PrepVilla QA) /Subject (User Acceptance Testing) "
        b"/Creator (PrepVilla dependency-free UAT PDF generator) >>"
    )

    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * len(objects)
    for index in range(1, len(objects)):
        offsets[index] = len(data)
        data.extend(f"{index} 0 obj\n".encode("ascii"))
        assert objects[index] is not None
        data.extend(objects[index] or b"")
        data.extend(b"\nendobj\n")

    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects)}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for index in range(1, len(objects)):
        data.extend(f"{offsets[index]:010d} 00000 n \n".encode("ascii"))
    data.extend(
        (
            f"trailer\n<< /Size {len(objects)} /Root 1 0 R /Info {info_obj} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    output_path.write_bytes(data)


def main() -> int:
    base = Path(__file__).resolve().parent
    source = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else base / "prepvilla_teacher_student_uat.md"
    output = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else base / "prepvilla_teacher_student_uat.pdf"
    markdown = source.read_text(encoding="utf-8")
    pages = layout(markdown)
    build_pdf(pages, output)
    print(f"Generated {output} ({len(pages)} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
