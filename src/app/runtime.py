"""WSGI entry point used by local development and Gunicorn."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
import threading
import webbrowser

from . import create_app

app = create_app()


def open_browser() -> None:
    """Open the local UI after Flask has had time to start listening."""
    url = "http://127.0.0.1:8000"
    if sys.platform == "darwin":
        # The native macOS command is more reliable than Python's browser
        # detection when this module is launched from a .command file.
        subprocess.run(["/usr/bin/open", url], check=False)  # nosec B603
    else:
        webbrowser.open_new_tab(url)


def main() -> None:
    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=8000, debug=False)
