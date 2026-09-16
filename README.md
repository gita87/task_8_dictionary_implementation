# DictFlow - DOCX to CSV

An automation engine that converts DOCX dictionary tables into tab-delimited
CSV files. Conversion is available through a web page, so users do not need to
run notebook code or individual conversion commands.

## Input and output contract

The engine selects the best top-level table containing these headers
(case-insensitive):

- `word` - required
- `definition` - required
- `image` - optional

Every exported row also receives a generated `unique_id` in the format
`0001`, `0002`, and so on. The identifier is the first output column and is
assigned after empty rows are removed.

When the `image` header is present, the first image in each cell is converted
to a WebP data URI whose value starts exactly with
`data:image/webp;base64,`. Empty image cells remain empty, and an image that
cannot be converted to WebP stops the conversion. Without the `image` header,
the output contains only `word` and `definition`. Rich text, highlights,
list/numbering formats, and nested tables are not preserved.

The output follows the reference format: a `.csv` extension, tab delimiter,
UTF-8 encoding with BOM, and CRLF line endings.

The complete mandatory contract is documented in
[`docs/OUTPUT_CONTRACT.md`](docs/OUTPUT_CONTRACT.md).

## Run locally

Prerequisite: Python 3.9 or newer.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python wsgi.py
```

For the reproducible environment used by golden and performance verification,
install `requirements-lock.txt` instead of the shorter direct-dependency file.

The default browser opens `http://127.0.0.1:8000` automatically. If the
operating system cannot open it, visit the same address manually.

## Run from the command line

Convert a DOCX file and choose the CSV output path:

```bash
.venv/bin/python cli.py input.docx output.csv
```

The output argument is optional. Without it, the CSV is created next to the
input file using the same filename:

```bash
.venv/bin/python cli.py input.docx
```

For a custom WebP image quality between 1 and 100:

```bash
.venv/bin/python cli.py input.docx output.csv --image-quality 85
```

Use quoted paths when a filename or directory contains spaces.

## Run by double-clicking an icon

Desktop launchers untuk Windows dan macOS tersedia di folder `launchers/`:

- Windows: double-click `launchers/windows/DictFlow.bat`
- macOS: double-click `launchers/mac/DictFlow.command`

Launcher menjalankan server lokal dan membuka browser default ke
`http://127.0.0.1:8000`. Asset icon untuk shortcut desktop disimpan di
`assets/icons/`; panduan lengkapnya ada di [`launchers/README.md`](launchers/README.md).

## Integrate with another Python system

Import the conversion pipeline directly from its project-specific module:

```python
from dict_docx_to_csv import convert_dictionary_docx_to_csv

with open("input.docx", "rb") as source:
    result = convert_dictionary_docx_to_csv(
        source,
        input_filename="input.docx",
    )

with open(result.filename, "wb") as output:
    output.write(result.content)
```

### Run quality assurance from the CLI

Add `--qa` to convert the DOCX, run automated checks, and open the QA report in
the default browser:

```bash
.venv/bin/python cli.py input.docx output.csv --qa
```

The first page shows the QA report. Select **View CSV results** to open the
paginated conversion preview in the same browser tab. Press `Ctrl+C` in the
terminal when the report is no longer needed.

## Run in production

Use a WSGI server and adjust the worker count to match the host capacity:

```bash
.venv/bin/gunicorn --workers 2 --bind 0.0.0.0:8000 --access-logfile - wsgi:app
```

The default upload limit is 25 MB. Change it with the `MAX_UPLOAD_BYTES`
environment variable when necessary. Place an HTTPS reverse proxy in front of
Gunicorn for a public deployment.

## Test

```bash
.venv/bin/python -m unittest discover -v
```

## Sandbox notebook

Notebook inspeksi pipeline tersedia di
[`sandbox/inspect_pipeline.ipynb`](sandbox/inspect_pipeline.ipynb). Jalankan
dengan Jupyter dari root project:

```bash
.venv/bin/python -m jupyter notebook sandbox/inspect_pipeline.ipynb
```

The test suite builds DOCX fixtures dynamically for documents with and without
images, invalid documents, unmatched tables, output-contract rules, the
approved production golden pair, performance instrumentation, and web
endpoints.

The production golden test converts the approved DOCX and compares its output
with the expected CSV byte for byte. Fixture integrity is also verified against
the SHA-256 values in `tests/fixtures/golden/manifest.json`.

## Performance test

Run the production benchmark with three isolated conversions:

```bash
.venv/bin/python -m tests.performance.benchmark_pipeline
```

The benchmark checks median duration, maximum peak RSS memory, row count, image
count, and output SHA-256. The generated report is saved as
`reports/performance/latest.json`. Thresholds and the approved local baseline
are stored in `tests/performance/`.
