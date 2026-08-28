"""WSGI entry point used by local development and Gunicorn."""

from __future__ import annotations

import threading
import webbrowser

from app import create_app

app = create_app()


def open_browser() -> None:
    """Open the local UI after Flask has had time to start listening."""
    webbrowser.open_new_tab("http://127.0.0.1:8000")


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=8000, debug=False)
