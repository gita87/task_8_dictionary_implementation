"""Application factory for the DOCX to CSV web service."""

from __future__ import annotations

import os

from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from qaos_dictionary import MAX_UPLOAD_BYTES

from .qa_web import qa_web
from .web import web


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_UPLOAD_BYTES", MAX_UPLOAD_BYTES)),
        SEND_FILE_MAX_AGE_DEFAULT=0,
        TEMPLATES_AUTO_RELOAD=True,
    )

    if test_config:
        app.config.update(test_config)

    app.register_blueprint(web)
    app.register_blueprint(qa_web)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_upload(_error: RequestEntityTooLarge):
        limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return jsonify(error=f"The DOCX file exceeds the {limit_mb} MB limit."), 413

    @app.after_request
    def add_security_headers(response):
        if (
            request.endpoint == "web.index"
            or request.endpoint and request.endpoint.startswith("qa.")
            or request.path.startswith("/static/")
        ):
            response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self' data:; base-uri 'none'; form-action 'self'; "
            "frame-ancestors 'none'",
        )
        return response

    return app
