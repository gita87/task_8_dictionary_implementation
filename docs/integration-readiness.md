# QAOS MVP integration readiness

Status: the dictionary producer is library-ready for the tested Python 3.11
baseline and the `dictionary/1.0` boundary. This document records the current
repository audit; it does not claim a remote CI run or a completed tagger run.

## Requirement audit

| Area | Status | Evidence / boundary |
| --- | --- | --- |
| A. Dependency baseline | implemented | `qaos-common==0.2.2`, the pinned vendor wheel, SHA-256, `pyproject.toml`, lock file, CI, and `docs/QAOS_COMMON.md` agree. The 0.2.2 handoff was checked. |
| B. Single implementation source | implemented | `src/qaos_dictionary/` owns the implementation. `dict_docx_to_csv.py`, `src/dict_docx_to_csv.py`, `core.py`, and the CLI wrappers preserve legacy imports by delegation. |
| C. Library API | implemented | `convert_dictionary_docx` accepts a path, bytes, or binary stream and imports without Flask, browser startup, network access, `chdir`, or file publication. |
| D. Dictionary contract | implemented | Shared schema/profile/reader validation is used for `dictionary/1.0`; local ID, whitespace, WebP, ZIP/XML, and DOCX extraction rules are documented below. |
| E. Reliability/security | implemented | Bounded input, ZIP/XML preflight, image signature checks, redacted diagnostics, cooperative cancellation, atomic CLI publication, and cleanup tests are present. |
| F. Producer contract tests | implemented | Synthetic DOCX tests round-trip through `qaos_common` readers/validators and cover Unicode, BOM/CRLF, IDs, images, empty-image policy, and cancellation. |
| G. Packaging | implemented | `py.typed`, legacy modules, CLI help, optional UI dependencies, wheel/sdist checks, and `pip check` are covered by the release scripts. The complete local wheelhouse now supports an offline clean install. |
| H. Linux/handoff | implemented locally; remote unverified | CI declares Linux Python 3.11–3.13 and separate macOS performance checks. No remote CI result is inferred from the workflow file. |

## Public API

```python
from qaos_dictionary import convert_dictionary_docx

result = convert_dictionary_docx(
    "dictionary.docx",
    input_filename="dictionary.docx",
    progress_callback=lambda event: print(event.stage, event.completed),
)
csv_bytes = result.content
```

`convert_dictionary_docx` also accepts `bytes`, `bytearray`, `memoryview`, and
binary streams. It returns frozen `ConversionResult` fields: `content`,
`filename`, `row_count`, `columns`, `schema_version`, and `diagnostics`.
Input streams are read from their current position and remain owned by the
caller; the library does not close or modify them. Paths are read but never
written. Conversion is synchronous and in-memory.

Optional callbacks are `progress_callback`, `common_progress_callback`,
`checkpoint_callback`, and cooperative `cancellation`. Cancellation checks do
not preempt a currently executing XML parse or image encode; a host requiring a
hard timeout must isolate the call in a worker/process. Callback exceptions
propagate. Calls do not share mutable conversion configuration; callers should
also avoid sharing a mutable stream between concurrent calls.

Typed failures are `ConversionError`, retaining `ValueError` compatibility and
structured `diagnostic`/`as_dict()` data. Messages and contexts are redacted so
document text, credentials, and image base64 are not included in diagnostics.

## Output and preservation contract

The output is `dictionary/1.0`: UTF-8 BOM, tab delimiter, CRLF records, minimal
quoting, and columns in the exact order `unique_id`, `word`, `definition`,
`image`. IDs are generated per emitted row from `0001`, then serialized with one
leading apostrophe (`'0001`) for spreadsheet compatibility. Fully empty source
rows are skipped; partially populated required rows fail. Duplicate IDs are
rejected at shared validation, while DOCX-generated IDs are sequential and
unique. Headers are case-insensitive with collapsed whitespace. Visible text
normalizes tabs, line breaks, and repeated whitespace to one ASCII space.

Missing images remain the compatibility marker `NA`. Embedded BMP, GIF, JPEG,
PNG, TIFF, and WebP images must pass declared-MIME and decoded-signature checks,
then are converted to WebP data URIs. Invalid or oversized images fail the
conversion. Shared limits are 256 MiB input, 64 MiB cells/images, 512 MiB
output, 10,000 DOCX members, and 512 MiB expanded DOCX content.

The library returns bytes only. The CLI uses a sibling temporary file and
`os.replace` for atomic publication; a conversion or write failure leaves the
previous destination intact and removes the temporary file. The optional Flask
UI is installed only through `.[ui]` and is not imported by the base library.

## Dependency and artifact identity

The baseline is `qaos-common==0.2.2`; the vendored wheel SHA-256 is
`f0218d9a9e670fdf997dd69c16c8eccb8bc55414a196c449f64c35d3959a0588`. The
compatibility requirements file contains base dependencies only; Flask and
Gunicorn remain under the `ui` extra. The lock file is the full Python 3.11
development/UI verification environment and intentionally includes those UI
packages. `wheelhouse/` contains the runtime wheels for this producer,
including the transitive `beautifulsoup4`, `soupsieve`, and
`typing_extensions` wheels.

Build new artifacts into a new directory and do not overwrite an existing
release artifact:

```sh
python -m build --no-isolation --outdir /tmp/qaos-dictionary-build
python -m twine check /tmp/qaos-dictionary-build/*
```

## Verification evidence

The repository test suite and static gates were run locally with `.venv311`
(Python 3.11): 62 tests passed; Ruff check and format check passed; strict
mypy passed; Bandit passed. The golden producer fixture and shared
`DictionaryCSVReader`/validator tests passed. CI is configured for Linux 3.11,
3.12, and 3.13, but hosted execution remains unverified here. The optional
live tagger boundary smoke test was not run because it requires the sibling
project's isolated environment; the shared-reader contract is tested locally.

Clean-install verification uses `scripts/clean_install.py` and
`scripts/installed_smoke.py` in fresh environments outside the checkout. A
fully isolated offline install was verified with:

```sh
python -m pip install --no-index --find-links ./wheelhouse \
  dist/qaos_dictionary-1.0.0-py3-none-any.whl
python -m pip check
python -I scripts/installed_smoke.py
```

The wheel/sdist build, Twine metadata checks, offline installation, `pip check`,
package-origin check, `py.typed`, legacy imports, conversion, and CLI help all
passed locally. The Linux wheels are present for the Python 3.11 x86_64 target;
Linux execution itself remains unverified on this macOS host.

## Remaining boundaries

Library integration blockers: none identified by the local audit. Remaining
unverified items are hosted Linux execution, Windows/Word compatibility, and an
optional live tagger invocation. SaaS deployment, tenant/job orchestration,
hard timeouts, and browser/visual acceptance are intentionally outside this
library and remain host or platform responsibilities.
