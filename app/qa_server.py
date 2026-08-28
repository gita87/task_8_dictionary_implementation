"""Local HTTP server used to display CLI-generated QA results."""

from __future__ import annotations

import threading
import webbrowser

from werkzeug.serving import make_server

from . import create_app
from .qa import QASession


def serve_qa_report(
    session: QASession,
    port: int = 0,
    open_browser: bool = True,
) -> None:
    """Serve a QA session locally until the user presses Ctrl+C."""
    app = create_app({"QA_SESSION": session})
    server = make_server("127.0.0.1", port, app, threaded=True)
    report_url = f"http://127.0.0.1:{server.server_port}/qa"

    print(f"QA report: {report_url}")
    print("Press Ctrl+C to stop the QA report server.")

    if open_browser:
        timer = threading.Timer(0.5, webbrowser.open_new_tab, args=(report_url,))
        timer.daemon = True
        timer.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

