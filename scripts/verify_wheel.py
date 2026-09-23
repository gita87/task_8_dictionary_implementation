"""Verify the exact common dependency before installation."""

import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for line in (root / "vendor/SHA256SUMS").read_text().splitlines():
    expected, name = line.split()
    actual = hashlib.sha256((root / "vendor" / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"Wheel checksum mismatch: {name}")
print("Vendored wheel SHA-256 verified.")
