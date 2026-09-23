"""Pipeline boundary for dictionary conversion."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from qaos_common.progress import ProgressEvent as CommonProgressEvent

from .contracts import DEFAULT_IMAGE_QUALITY
from .extraction import extract_rows
from .models import (
    Cancellation,
    CheckpointCallback,
    ConversionError,
    ConversionResult,
    InputSource,
    ProgressCallback,
    ProgressEvent,
)
from .operations import _check_cancelled, _error, _progress
from .serialization import rows_to_csv
from .source import _read_source, _validated_docx_buffer


def _output_filename(input_filename: str) -> str:
    return f"{Path(input_filename).stem.strip() or 'dictionary'}.csv"


def convert_dictionary_docx(
    source: InputSource,
    input_filename: str | None = None,
    image_quality: int = DEFAULT_IMAGE_QUALITY,
    *,
    progress_callback: ProgressCallback | None = None,
    cancellation: Cancellation | None = None,
    checkpoint_callback: CheckpointCallback | None = None,
    checkpoint_interval: int = 100,
    common_progress_callback: Callable[[CommonProgressEvent], None] | None = None,
) -> ConversionResult:
    """Convert a DOCX path, byte string, or binary stream to dictionary/1.0 CSV."""
    if not 1 <= image_quality <= 100:
        raise ValueError("image_quality must be between 1 and 100.")
    if checkpoint_interval < 1:
        raise ValueError("checkpoint_interval must be at least 1.")
    legacy_callback = progress_callback
    if common_progress_callback is not None:

        def emit(event: ProgressEvent) -> None:
            if legacy_callback is not None:
                legacy_callback(event)
            common_progress_callback(event.to_common())

        progress_callback = emit
    _check_cancelled(cancellation)
    _progress(progress_callback, "read", 0, None, "Reading input")
    payload, filename = _read_source(source, input_filename)
    _check_cancelled(cancellation)
    _progress(progress_callback, "validate", 1, 1, "Validating DOCX")
    try:
        document = Document(_validated_docx_buffer(payload))
    except ConversionError:
        raise
    except (PackageNotFoundError, KeyError, OSError, ValueError) as error:
        raise _error("invalid_docx", "The file could not be read as a valid DOCX.") from error
    except Exception as error:
        raise _error(
            "unsupported_docx_structure", "The DOCX structure is corrupted or unsupported."
        ) from error
    _check_cancelled(cancellation)
    columns, rows = extract_rows(
        document,
        image_quality=image_quality,
        progress_callback=progress_callback,
        cancellation=cancellation,
        checkpoint_callback=checkpoint_callback,
        checkpoint_interval=checkpoint_interval,
    )
    _check_cancelled(cancellation)
    _progress(progress_callback, "serialize", 0, 1, "Serializing CSV")
    content = rows_to_csv(columns, rows, cancellation=cancellation)
    _check_cancelled(cancellation)
    _progress(progress_callback, "complete", 1, 1, "Conversion complete")
    return ConversionResult(content, _output_filename(filename), len(rows), columns)


def convert_dictionary_docx_to_csv(
    source: InputSource,
    input_filename: str = "dictionary.docx",
    image_quality: int = DEFAULT_IMAGE_QUALITY,
    *,
    progress_callback: ProgressCallback | None = None,
    cancellation: Cancellation | None = None,
    checkpoint_callback: CheckpointCallback | None = None,
    checkpoint_interval: int = 100,
    common_progress_callback: Callable[[CommonProgressEvent], None] | None = None,
) -> ConversionResult:
    """Backward-compatible alias for :func:`convert_dictionary_docx`."""
    return convert_dictionary_docx(
        source,
        input_filename,
        image_quality,
        progress_callback=progress_callback,
        cancellation=cancellation,
        checkpoint_callback=checkpoint_callback,
        checkpoint_interval=checkpoint_interval,
        common_progress_callback=common_progress_callback,
    )
