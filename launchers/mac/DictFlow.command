#!/bin/zsh

# Resolve the project directory from this launcher, so it works from any folder.
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR" || exit 1

if [[ -x ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON" ]]; then
    echo "DictFlow membutuhkan Python 3.11 hingga 3.13."
    read -r "?Tekan Enter untuk menutup..."
    exit 1
fi

if ! "$PYTHON" -c 'import sys; raise SystemExit(not ((3, 11) <= sys.version_info[:2] < (3, 14)))'; then
    echo "DictFlow membutuhkan Python 3.11 hingga 3.13."
    read -r "?Tekan Enter untuk menutup..."
    exit 1
fi

echo "Starting DictFlow..."
"$PYTHON" wsgi.py

status=$?
if [[ $status -ne 0 ]]; then
    echo
    echo "DictFlow gagal dijalankan. Pastikan dependency sudah ter-install."
    read -r "?Tekan Enter untuk menutup..."
fi
exit $status
