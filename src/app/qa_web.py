"""Browser pages for a QA report and paginated CSV preview."""

from __future__ import annotations

import io
import math

from flask import Blueprint, Response, abort, current_app, render_template, request, send_file

from .qa import QASession

qa_web = Blueprint("qa", __name__, url_prefix="/qa")
ROWS_PER_PAGE = 50


def _session() -> QASession:
    session = current_app.config.get("QA_SESSION")
    if not isinstance(session, QASession):
        abort(404)
    return session


@qa_web.get("")
def report() -> str:
    session = _session()
    return render_template("qa_report.html", report=session.report)


@qa_web.get("/csv")
def csv_results() -> str:
    session = _session()
    page_count = max(1, math.ceil(len(session.rows) / ROWS_PER_PAGE))
    page = request.args.get("page", default=1, type=int)
    if page < 1 or page > page_count:
        abort(404)

    start = (page - 1) * ROWS_PER_PAGE
    end = start + ROWS_PER_PAGE
    return render_template(
        "qa_csv.html",
        report=session.report,
        rows=session.rows[start:end],
        columns=session.conversion.columns,
        page=page,
        page_count=page_count,
        start_row=start + 1 if session.rows else 0,
        end_row=min(end, len(session.rows)),
    )


@qa_web.get("/download")
def download() -> Response:
    session = _session()
    response = send_file(
        io.BytesIO(session.conversion.content),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name=session.report.output_name,
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    return response
