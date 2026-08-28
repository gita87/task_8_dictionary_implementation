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

When the `image` header is present, the first image in each cell is converted
to a WebP data URI. Without that header, the output contains only `word` and
`definition`. Rich text, highlights, list/numbering formats, and nested tables
are not preserved.

The output follows the reference format: a `.csv` extension, tab delimiter,
UTF-8 encoding with BOM, and CRLF line endings.

## Run locally

Prerequisite: Python 3.9 or newer.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python wsgi.py
```

The default browser opens `http://127.0.0.1:8000` automatically. If the
operating system cannot open it, visit the same address manually.

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

The test suite builds DOCX fixtures dynamically for documents with and without
images, invalid documents, unmatched tables, and web endpoints.
