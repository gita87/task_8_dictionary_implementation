"""Audit installed runtime/UI dependency closure; local packages use source/hash review."""

import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

root = Path(__file__).resolve().parents[1]
report = root / "reports/security"
report.mkdir(parents=True, exist_ok=True)
queue = [("qaos-dictionary", frozenset({"ui"}))]
visited = set()
pins = {}
while queue:
    name, extras = queue.pop()
    key = (canonicalize_name(name), extras)
    if key in visited:
        continue
    visited.add(key)
    package = distribution(name)
    if key[0] not in {"qaos-dictionary", "qaos-common"}:
        pins[key[0]] = package.version
    for raw in package.requires or []:
        requirement = Requirement(raw)
        if requirement.marker is None or any(
            requirement.marker.evaluate({"extra": extra}) for extra in ({""} | set(extras))
        ):
            queue.append((requirement.name, frozenset(requirement.extras)))
requirements = report / "runtime-requirements.txt"
requirements.write_text("".join(f"{name}=={value}\n" for name, value in sorted(pins.items())))
print(
    "Auditing third-party runtime/UI closure. Local qaos packages: source review + wheel hash.",
    flush=True,
)
subprocess.run(
    [
        sys.executable,
        "-m",
        "pip_audit",
        "--no-deps",
        "--disable-pip",
        "-r",
        str(requirements),
        "--format",
        "json",
        "--output",
        str(report / "dependencies.json"),
    ],
    check=True,
)
