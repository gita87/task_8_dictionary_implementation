"""HTTP routes for upload, conversion, and CSV download."""

from __future__ import annotations

import io

from flask import Blueprint, jsonify, render_template, request, send_file
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from qaos_dictionary import ConversionError, convert_dictionary_docx

web = Blueprint("web", __name__)


@web.get("/")
def index() -> str:
    return render_template("index.html")


@web.get("/health")
def health() -> ResponseReturnValue:
    return jsonify(status="ok")


@web.post("/convert")
def convert() -> ResponseReturnValue:
    upload = request.files.get("document")
    if upload is None or not upload.filename:
        return jsonify(error="Select a DOCX file first."), 400

    safe_name = secure_filename(upload.filename)
    if not safe_name.lower().endswith(".docx"):
        return jsonify(error="The file must use the .docx format."), 400

    try:
        result = convert_dictionary_docx(
            upload.stream,
            input_filename=safe_name,
        )
    except ConversionError as error:
        return jsonify(error=error.as_dict()), 422

    response = send_file(
        io.BytesIO(result.content),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name=result.filename,
        max_age=0,
    )
    response.headers["X-Row-Count"] = str(result.row_count)
    response.headers["X-CSV-Columns"] = ",".join(result.columns)
    response.headers["X-Dictionary-Schema"] = result.schema_version
    response.headers["Cache-Control"] = "no-store"
    return response
