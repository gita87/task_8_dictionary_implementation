# Input, API and diagnostics compatibility contract

Applies to the 1.x package API and `dictionary/1.0` output. Changes to accepted
valid input, public signatures, output bytes, documented fields or stable error
codes require explicit review, regression fixtures, and release notes. Security
rejections may become stricter in a compatible maintenance release and must be
documented. New optional keyword parameters and new error codes may be added.

## Input

`convert_dictionary_docx(source, input_filename=None, image_quality=75, *,
progress_callback=None, cancellation=None, checkpoint_callback=None,
checkpoint_interval=100, common_progress_callback=None)` accepts a string/Path,
bytes/bytearray/memoryview, or binary stream at its current position. Caller
streams stay open. Text streams fail with `input_read_failed`. Input is bounded
at 256 MiB; expanded ZIP content at 512 MiB and 10,000 entries. Duplicates,
unsafe ZIP names, encrypted entries, DTD/entities and malformed XML are rejected.

The top-level table must contain word and definition headers, case-insensitive
with whitespace collapsed. Prefer a table with image; ties select the first.
Empty rows are skipped; partially populated required rows fail. Nested tables,
rich text and paragraph structure are not preserved. First embedded image only;
linked images are not fetched. Missing images are `NA`; supported source images
become WebP at the requested quality (1–100). See OUTPUT_CONTRACT.md for exact
BOM/tab/CRLF/quoting and apostrophe-prefixed IDs.

## Python and CLI

All names in `qaos_dictionary.__all__` are re-exported from
`qaos_dictionary.core` and `dict_docx_to_csv`. The alias
`convert_dictionary_docx_to_csv` keeps `input_filename="dictionary.docx"` as its
historical default. ConversionResult fields are content, filename, row_count,
columns, schema_version and diagnostics. Dataclasses remain frozen.

`rows_to_csv` retains legacy subset exports. Full dictionary exports require
canonical column order, valid images, unique IDs and nonempty definitions.
IDs are supplied without the apostrophe; the exporter adds it once per call.
Private implementation functions and monkeypatching re-exported constants are
not configuration APIs. Configure host upload policy through the documented
Flask environment setting; core limits remain fixed shared defaults.

`qaos-dictionary`, `python cli.py`, and installed `python -m cli` accept the same
arguments. Exit status is 0 on success, 1 on conversion/file/QA-server error,
2 on invalid arguments, and 130 on a user interrupt during conversion. Existing
output files are atomically replaced; temporary files are removed on failure.

## Callbacks and cancellation

Legacy ProgressEvent fields: stage, completed, total, message. Stages remain
read → validate → extract (per source row) → serialize → complete.
Common events use reading/validating/parsing/writing/completed and current.
`complete` means conversion bytes are ready, before CLI publication.
Checkpoint fields remain schema_version, stage, rows_processed, total_rows;
checkpoints report source rows at configured intervals and the final row.
Callback exceptions propagate. No completion event is emitted after a detected
cancellation. Tokens from common, threading.Event, and zero-argument boolean
callables remain accepted. Cancellation raises ConversionError with
`conversion_cancelled`.

## Diagnostics and HTTP

ConversionError is both ValueError and QAOSCommonError. `str(error)` is the
human message without a prefixed code. `diagnostic` and `as_dict()` retain
`{code, message, severity, context}`. `to_dict()` supplies
`{code, message, stage, details}`; local stages may be null. Treat codes/fields as
stable, not English wording. Payloads are redacted in exported envelopes.

Existing codes include input_read_failed, input_empty, input_too_large,
invalid_docx_zip, invalid_docx_package, invalid_docx, unsupported_docx_structure,
docx_too_many_parts, docx_uncompressed_too_large, dictionary_table_not_found,
required_cell_empty, unsupported_image_mime, unsupported_image_format,
image_mime_mismatch, image_too_large, image_conversion_failed, cell_too_large,
output_too_large, conversion_cancelled, and DICTIONARY_SCHEMA_INVALID.
`invalid_docx_xml` is added for unsafe or malformed XML preflight failures.
Contexts vary by code; row/column/limit metadata never includes raw cell images.

POST /convert uses multipart field document. Missing/invalid extension returns
400, upload limit 413, conversion failure 422 with the legacy error envelope.
Success returns CSV bytes with X-Row-Count, X-CSV-Columns and X-Dictionary-Schema.
Health, download names, QA pagination and no-store/security headers remain.

Compatibility gates: golden output byte comparison, common round-trip, public
re-export identity, CLI/HTTP tests, callback/cancellation/error tests, and an
installed-wheel/sdist smoke test run outside the checkout with Python -I.
