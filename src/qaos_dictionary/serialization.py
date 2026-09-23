"""Serialization boundary for dictionary conversion."""

from __future__ import annotations

import io

from qaos_common import ProcessingLimits
from qaos_common.csvio import DictionaryCSVProfile, DictionaryCSVWriter
from qaos_common.errors import QAOSCommonError
from qaos_common.limits import DEFAULT_LIMITS
from qaos_common.schemas import (
    DICTIONARY_COLUMNS,
    validate_dictionary_headers,
    validate_dictionary_row,
)

from .contracts import MAX_CELL_BYTES, MAX_OUTPUT_BYTES, MAX_UPLOAD_BYTES
from .models import Cancellation, ConversionError
from .operations import _check_cancelled, _error


def rows_to_csv(
    columns: tuple[str, ...],
    rows: list[dict[str, str]],
    *,
    cancellation: Cancellation | None = None,
) -> bytes:
    """Serialize with the shared dictionary profile; retain legacy subset exports."""
    output = io.BytesIO()
    limits = ProcessingLimits(
        max_upload_bytes=MAX_UPLOAD_BYTES,
        max_cell_bytes=MAX_CELL_BYTES,
        max_output_bytes=MAX_OUTPUT_BYTES,
        max_image_bytes=min(DEFAULT_LIMITS.max_image_bytes, MAX_CELL_BYTES),
    )
    canonical = set(DICTIONARY_COLUMNS).issubset(columns)
    seen_ids: set[str] = set()
    try:
        if canonical:
            validate_dictionary_headers(columns)
        with DictionaryCSVWriter(
            output, columns=columns, profile=DictionaryCSVProfile(line_ending="\r\n"), limits=limits
        ) as writer:
            for row_number, row in enumerate(rows, start=2):
                _check_cancelled(cancellation)
                exported = dict(row)
                for column, value in exported.items():
                    if len(value.encode("utf-8")) > MAX_CELL_BYTES:
                        raise _error(
                            "cell_too_large",
                            "Dictionary cell exceeds the size limit.",
                            row=row_number,
                            column=column,
                            limit_bytes=MAX_CELL_BYTES,
                        )
                if canonical:
                    validate_dictionary_row(exported, row_number=row_number, seen_ids=seen_ids)
                    if not exported["definition"].strip():
                        raise _error(
                            "required_cell_empty",
                            "Dictionary definition is empty.",
                            row=row_number,
                            columns=["definition"],
                        )
                if "unique_id" in columns:
                    exported["unique_id"] = f"'{row['unique_id']}"
                writer.write_row(exported)
    except ConversionError:
        raise
    except QAOSCommonError as error:
        code = {
            "CSV_OUTPUT_TOO_LARGE": "output_too_large",
            "CSV_CELL_TOO_LARGE": "cell_too_large",
        }.get(error.code, error.code)
        converted = ConversionError(error.message, code=code, context=error.details)
        converted.stage = error.stage
        raise converted from error
    return output.getvalue()
