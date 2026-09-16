"""Quality-assurance analysis for DOCX-to-CSV conversion results."""

from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from dict_docx_to_csv import ConversionResult, WEBP_DATA_URI_PREFIX


PASS = "pass"
WARNING = "warning"
FAIL = "fail"
_RICH_TEXT_TAG = re.compile(
    r"</?(?:b|strong|i|em|span|mark|table|ul|ol|li)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class QACheck:
    name: str
    status: str
    details: str


@dataclass(frozen=True)
class QAReport:
    input_name: str
    output_name: str
    input_size: int
    output_size: int
    row_count: int
    columns: tuple[str, ...]
    image_count: int
    duration_seconds: float
    input_sha256: str
    output_sha256: str
    status: str
    checks: tuple[QACheck, ...]

    @property
    def passed_count(self) -> int:
        return sum(check.status == PASS for check in self.checks)

    @property
    def warning_count(self) -> int:
        return sum(check.status == WARNING for check in self.checks)

    @property
    def failed_count(self) -> int:
        return sum(check.status == FAIL for check in self.checks)


@dataclass(frozen=True)
class QASession:
    report: QAReport
    conversion: ConversionResult
    rows: tuple[Mapping[str, str], ...]

    @property
    def page_count(self) -> int:
        return max(1, math.ceil(len(self.rows) / 50))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_csv(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    current_limit = csv.field_size_limit()
    if len(content) > current_limit:
        csv.field_size_limit(len(content))

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    rows = [dict(row) for row in reader]
    return list(reader.fieldnames or []), rows


def _image_metrics(rows: Sequence[Mapping[str, str]]) -> tuple[int, int]:
    populated = 0
    valid = 0

    for row in rows:
        value = (row.get("image") or "").strip()
        if not value or value == "NA":
            continue
        populated += 1

        if not value.startswith(WEBP_DATA_URI_PREFIX):
            continue

        payload = value[len(WEBP_DATA_URI_PREFIX) :]
        if not payload:
            continue
        try:
            base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError):
            continue

        valid += 1

    return populated, valid


def build_qa_session(
    input_path: Path,
    output_path: Path,
    conversion: ConversionResult,
    duration_seconds: float,
) -> QASession:
    """Build a deterministic QA report from a completed conversion."""
    checks: list[QACheck] = []

    has_bom = conversion.content.startswith(b"\xef\xbb\xbf")
    checks.append(
        QACheck(
            "UTF-8 BOM",
            PASS if has_bom else FAIL,
            "The CSV starts with the UTF-8 byte-order mark."
            if has_bom
            else "The CSV does not start with the required UTF-8 byte-order mark.",
        )
    )

    body = conversion.content[3:] if has_bom else conversion.content
    has_only_crlf = b"\r\n" in body and re.search(rb"(?<!\r)\n", body) is None
    checks.append(
        QACheck(
            "CRLF line endings",
            PASS if has_only_crlf else FAIL,
            "Every CSV row uses CRLF line endings."
            if has_only_crlf
            else "One or more CSV rows do not use CRLF line endings.",
        )
    )

    try:
        fieldnames, rows = _parse_csv(conversion.content)
        parse_error = None
    except (UnicodeDecodeError, csv.Error) as error:
        fieldnames, rows = [], []
        parse_error = str(error)

    schema_valid = tuple(fieldnames) == conversion.columns
    count_valid = len(rows) == conversion.row_count
    checks.append(
        QACheck(
            "Tab-delimited schema",
            PASS if schema_valid and count_valid else FAIL,
            f"Parsed {len(rows)} rows with columns: {', '.join(fieldnames)}."
            if parse_error is None
            else f"CSV parsing failed: {parse_error}",
        )
    )

    required_columns = {"word", "definition"}
    required_valid = required_columns.issubset(conversion.columns)
    checks.append(
        QACheck(
            "Required columns",
            PASS if required_valid else FAIL,
            "Both word and definition columns are present."
            if required_valid
            else "The word or definition column is missing.",
        )
    )

    checks.append(
        QACheck(
            "Data rows",
            PASS if conversion.row_count > 0 else FAIL,
            f"The conversion produced {conversion.row_count} data rows.",
        )
    )

    empty_words = sum(not (row.get("word") or "").strip() for row in rows)
    empty_definitions = sum(not (row.get("definition") or "").strip() for row in rows)
    missing_required = empty_words + empty_definitions
    checks.append(
        QACheck(
            "Required cell completeness",
            PASS if missing_required == 0 else FAIL,
            "Every row contains both a word and a definition."
            if missing_required == 0
            else f"Found {empty_words} empty word cells and {empty_definitions} empty definition cells.",
        )
    )

    rich_text_cells = sum(
        bool(_RICH_TEXT_TAG.search(row.get(column) or ""))
        for row in rows
        for column in ("word", "definition")
    )
    checks.append(
        QACheck(
            "Plain-text output",
            PASS if rich_text_cells == 0 else WARNING,
            "No supported rich-text tags were found in word or definition cells."
            if rich_text_cells == 0
            else f"Found {rich_text_cells} cells containing rich-text-like tags.",
        )
    )

    image_count = 0
    if "image" in conversion.columns:
        populated, valid = _image_metrics(rows)
        image_count = valid
        if populated == 0:
            image_status = WARNING
            image_details = "The image column is present, but every image cell is empty."
        elif valid != populated:
            image_status = FAIL
            image_details = (
                f"Validated {valid} of {populated} populated image cells as "
                f"{WEBP_DATA_URI_PREFIX} values."
            )
        else:
            image_status = PASS
            image_details = f"Validated {valid} WebP base64 image data URIs."
    else:
        image_status = PASS
        image_details = "The image column is present in the output schema."

    checks.append(QACheck("Adaptive image output", image_status, image_details))

    if any(check.status == FAIL for check in checks):
        overall_status = "FAILED"
    elif any(check.status == WARNING for check in checks):
        overall_status = "PASSED WITH WARNINGS"
    else:
        overall_status = "PASSED"

    report = QAReport(
        input_name=input_path.name,
        output_name=output_path.name,
        input_size=input_path.stat().st_size,
        output_size=len(conversion.content),
        row_count=conversion.row_count,
        columns=conversion.columns,
        image_count=image_count,
        duration_seconds=duration_seconds,
        input_sha256=_sha256_file(input_path),
        output_sha256=hashlib.sha256(conversion.content).hexdigest(),
        status=overall_status,
        checks=tuple(checks),
    )
    return QASession(report=report, conversion=conversion, rows=tuple(rows))
