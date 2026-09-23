"""Extraction boundary for dictionary conversion."""

from __future__ import annotations

from collections.abc import Iterable

from docx.document import Document as DocumentType
from docx.table import Table, _Cell
from qaos_common.schemas import DICTIONARY_COLUMNS, DICTIONARY_SCHEMA_VERSION

from .contracts import (
    _WHITESPACE,
    DEFAULT_IMAGE_QUALITY,
    MISSING_IMAGE_VALUE,
    OPTIONAL_HEADERS,
    REQUIRED_HEADERS,
)
from .images import _validate_cell_size, image_to_data_uri
from .models import Cancellation, Checkpoint, CheckpointCallback, ProgressCallback
from .operations import _check_cancelled, _error, _progress


def normalize_header(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip().casefold()


def plain_cell_text(cell: _Cell) -> str:
    paragraphs = (_WHITESPACE.sub(" ", p.text).strip() for p in cell.paragraphs)
    return " ".join(text for text in paragraphs if text).strip()


def _table_headers(table: Table) -> list[str]:
    if not table.rows:
        return []
    return [normalize_header(plain_cell_text(cell)) for cell in table.rows[0].cells]


def find_dictionary_table(tables: Iterable[Table]) -> tuple[Table, list[str]]:
    required = set(REQUIRED_HEADERS)
    candidates: list[tuple[int, int, Table, list[str]]] = []
    for order, table in enumerate(tables):
        headers = _table_headers(table)
        header_set = set(headers)
        if required.issubset(header_set):
            score = sum(header in header_set for header in OPTIONAL_HEADERS)
            candidates.append((score, -order, table, headers))
    if not candidates:
        raise _error(
            "dictionary_table_not_found",
            "No table was found with the required 'word' and 'definition' headers.",
            required_headers=list(REQUIRED_HEADERS),
        )
    _, _, table, headers = max(candidates, key=lambda item: (item[0], item[1]))
    return table, headers


def extract_rows(
    document: DocumentType,
    image_quality: int = DEFAULT_IMAGE_QUALITY,
    *,
    progress_callback: ProgressCallback | None = None,
    cancellation: Cancellation | None = None,
    checkpoint_callback: CheckpointCallback | None = None,
    checkpoint_interval: int = 100,
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    table, headers = find_dictionary_table(document.tables)
    indexes = {name: headers.index(name) for name in REQUIRED_HEADERS}
    has_image = "image" in headers
    if has_image:
        indexes["image"] = headers.index("image")
    columns = DICTIONARY_COLUMNS
    rows: list[dict[str, str]] = []
    source_rows = table.rows[1:]
    total = len(source_rows)
    for processed, table_row in enumerate(source_rows, start=1):
        _check_cancelled(cancellation)
        row_number = processed + 1
        cells = table_row.cells
        row: dict[str, str] = {}
        for column in REQUIRED_HEADERS:
            index = indexes[column]
            row[column] = plain_cell_text(cells[index]) if index < len(cells) else ""
            _validate_cell_size(row[column], column, row_number)
        if has_image:
            image_index = indexes["image"]
            row["image"] = (
                image_to_data_uri(cells[image_index], image_quality)
                if image_index < len(cells)
                else MISSING_IMAGE_VALUE
            )
        else:
            row["image"] = MISSING_IMAGE_VALUE
        _validate_cell_size(row["image"], "image", row_number)
        _progress(progress_callback, "extract", processed, total, "Extracting rows")
        if checkpoint_callback is not None and (
            processed % checkpoint_interval == 0 or processed == total
        ):
            checkpoint_callback(Checkpoint(DICTIONARY_SCHEMA_VERSION, "extract", processed, total))
        if not any(row[column].strip() for column in REQUIRED_HEADERS):
            continue
        missing = [column for column in REQUIRED_HEADERS if not row[column].strip()]
        if missing:
            raise _error(
                "required_cell_empty",
                f"Dictionary table row {row_number} has empty required cell(s): {', '.join(missing)}.",
                row=row_number,
                columns=missing,
            )
        row["unique_id"] = f"{len(rows) + 1:04d}"
        rows.append(row)
    return columns, rows
