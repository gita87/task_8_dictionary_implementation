"""Create an unsigned local/CI build manifest; release mode rejects a dirty checkout."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import tomllib
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--release", action="store_true")
args = parser.parse_args()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


dirty = bool(git("status", "--porcelain"))
if args.release and dirty:
    raise SystemExit("Release provenance requires a clean committed checkout")
artifacts = sorted([*(root / "dist").glob("*.whl"), *(root / "dist").glob("*.tar.gz")])
if len(artifacts) != 2:
    raise SystemExit("Build exactly one wheel and one sdist before provenance")
metadata = tomllib.loads((root / "pyproject.toml").read_text())["project"]
if args.release and os.environ.get("GITHUB_REF_TYPE") == "tag":
    if os.environ["GITHUB_REF_NAME"] != f"v{metadata['version']}":
        raise SystemExit("Release tag does not match package version")
manifest = {
    "schema": "qaos-dictionary-build/1",
    "package": metadata["name"],
    "version": metadata["version"],
    "created_utc": datetime.now(UTC).isoformat(),
    "git_commit": git("rev-parse", "HEAD"),
    "dirty": dirty,
    "assurance": "unsigned build manifest",
    "environment": {"python": platform.python_version(), "platform": platform.platform()},
    "tools": {name: version(name) for name in ("build", "setuptools", "wheel")},
    "artifacts": {p.name: {"sha256": digest(p), "bytes": p.stat().st_size} for p in artifacts},
    "shared_dependency": {p.name: digest(p) for p in (root / "vendor").glob("*.whl")},
    "lock_sha256": digest(root / "requirements-lock.txt"),
    "golden_manifest_sha256": digest(root / "tests/fixtures/golden/manifest.json"),
    "performance_budget_sha256": digest(root / "tests/performance/thresholds.json"),
    "ci": {
        k: os.environ.get(k)
        for k in ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")
    },
}
(root / "dist/provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
(root / "dist/SHA256SUMS").write_text("".join(f"{digest(p)}  {p.name}\n" for p in artifacts))
print("Wrote dist/provenance.json and dist/SHA256SUMS")
