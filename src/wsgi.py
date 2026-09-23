"""Compatibility WSGI and development-server entry point."""

from app.runtime import app as app
from app.runtime import main as main
from app.runtime import open_browser as open_browser

if __name__ == "__main__":
    main()
