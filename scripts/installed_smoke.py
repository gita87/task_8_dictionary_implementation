"""Executed with -I in a fresh environment, outside the source checkout."""

import io
import sys
from importlib import import_module, resources
from pathlib import Path

from docx import Document

import qaos_dictionary
from qaos_dictionary import convert_dictionary_docx

installed = Path(qaos_dictionary.__file__).resolve()
if not installed.is_relative_to(Path(sys.prefix).resolve()):
    raise SystemExit(f"Package was not imported from clean environment: {installed}")
if not resources.files("qaos_dictionary").joinpath("py.typed").is_file():
    raise SystemExit("py.typed is missing from wheel")
for name in ("cli", "dict_docx_to_csv", "qaos_dictionary.core"):
    module = import_module(name)
    if not Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()):
        raise SystemExit(f"Compatibility module is not installed: {name}")
document = Document()
table = document.add_table(rows=2, cols=2)
for cell, text in zip(table.rows[0].cells, ("word", "definition"), strict=True):
    cell.text = text
for cell, text in zip(table.rows[1].cells, ("alpha", "first"), strict=True):
    cell.text = text
stream = io.BytesIO()
document.save(stream)
result = convert_dictionary_docx(stream.getvalue())
expected = b"\xef\xbb\xbfunique_id\tword\tdefinition\timage\r\n'0001\talpha\tfirst\tNA\r\n"
if result.content != expected:
    raise SystemExit("Installed conversion changed the byte contract")
if "--ui" in sys.argv:
    from app import create_app
    from wsgi import app as wsgi_app

    if wsgi_app.name != "app":
        raise SystemExit("Installed WSGI facade failed")

    client = create_app({"TESTING": True}).test_client()
    for path in ("/", "/health", "/static/style.css"):
        response = client.get(path)
        if response.status_code != 200:
            raise SystemExit(f"Installed UI resource failed: {path}")
        response.close()
else:
    from importlib.util import find_spec

    if find_spec("flask") is not None:
        raise SystemExit("Base install unexpectedly requires Flask")
print("Clean installed package, compatibility imports, resources and conversion passed.")
