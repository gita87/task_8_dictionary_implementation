from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path
from typing import Optional, Sequence

import resource

from dict_docx_to_csv import (
    WEBP_DATA_URI_PREFIX,
    convert_dictionary_docx_to_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIRECTORY = PROJECT_ROOT / "tests" / "fixtures" / "golden"
DEFAULT_INPUT = GOLDEN_DIRECTORY / "production_dictionary.docx"
DEFAULT_THRESHOLDS = Path(__file__).with_name("thresholds.json")
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "performance" / "latest.json"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def run_once(input_path: Path) -> dict[str, object]:
    started_at = time.perf_counter()
    with input_path.open("rb") as source:
        result = convert_dictionary_docx_to_csv(
            source,
            input_filename=input_path.name,
        )
    duration_seconds = time.perf_counter() - started_at

    return {
        "duration_seconds": round(duration_seconds, 6),
        "peak_rss_bytes": _peak_rss_bytes(),
        "input_size_bytes": input_path.stat().st_size,
        "output_size_bytes": len(result.content),
        "row_count": result.row_count,
        "image_count": result.content.count(WEBP_DATA_URI_PREFIX.encode("ascii")),
        "output_sha256": _sha256(result.content),
    }


def _worker_command(input_path: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "tests.performance.benchmark_pipeline",
        "--worker",
        str(input_path),
    ]


def run_isolated(input_path: Path) -> dict[str, object]:
    completed = subprocess.run(
        _worker_command(input_path),
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def summarize(input_path: Path, iterations: int) -> dict[str, object]:
    runs = [run_isolated(input_path) for _ in range(iterations)]
    durations = [float(run["duration_seconds"]) for run in runs]
    peak_values = [int(run["peak_rss_bytes"]) for run in runs]
    reference = runs[0]

    stable_fields = (
        "input_size_bytes",
        "output_size_bytes",
        "row_count",
        "image_count",
        "output_sha256",
    )
    for run in runs[1:]:
        for field in stable_fields:
            if run[field] != reference[field]:
                raise RuntimeError(f"Benchmark output changed between runs: {field}")

    return {
        "benchmark": "dictionary_docx_to_csv_production",
        "input_file": input_path.name,
        "iterations": iterations,
        "duration_seconds": {
            "minimum": round(min(durations), 6),
            "median": round(statistics.median(durations), 6),
            "maximum": round(max(durations), 6),
        },
        "peak_rss_bytes": {
            "minimum": min(peak_values),
            "median": int(statistics.median(peak_values)),
            "maximum": max(peak_values),
        },
        "result": {field: reference[field] for field in stable_fields},
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "pillow": version("Pillow"),
            "python_docx": version("python-docx"),
            "lxml": version("lxml"),
        },
        "runs": runs,
    }


def threshold_failures(report: dict[str, object], thresholds: dict) -> list[str]:
    failures: list[str] = []
    duration = float(report["duration_seconds"]["median"])
    peak_memory = int(report["peak_rss_bytes"]["maximum"])
    result = report["result"]

    if duration > thresholds["maximum_median_duration_seconds"]:
        failures.append(
            f"Median duration {duration:.3f}s exceeds "
            f"{thresholds['maximum_median_duration_seconds']:.3f}s."
        )
    maximum_memory_bytes = thresholds["maximum_peak_rss_mb"] * 1024 * 1024
    if peak_memory > maximum_memory_bytes:
        failures.append(
            f"Peak RSS {peak_memory / 1024 / 1024:.1f} MB exceeds "
            f"{thresholds['maximum_peak_rss_mb']} MB."
        )
    if result["row_count"] != thresholds["expected_row_count"]:
        failures.append("Row count does not match the performance contract.")
    if result["image_count"] != thresholds["expected_image_count"]:
        failures.append("Image count does not match the performance contract.")
    if result["output_sha256"] != thresholds["expected_output_sha256"]:
        failures.append("Output SHA-256 does not match the approved golden output.")

    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark duration and peak RSS for the production DOCX pipeline."
    )
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--no-thresholds", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.expanduser().resolve()

    if not input_path.is_file():
        raise SystemExit(f"Performance fixture does not exist: {input_path}")
    if args.iterations < 1:
        raise SystemExit("--iterations must be at least 1")

    if args.worker:
        print(json.dumps(run_once(input_path), sort_keys=True))
        return 0

    report = summarize(input_path, args.iterations)
    failures: list[str] = []
    if not args.no_thresholds:
        thresholds = json.loads(args.thresholds.read_text(encoding="utf-8"))
        failures = threshold_failures(report, thresholds)

    report["status"] = "FAILED" if failures else "PASSED"
    report["failures"] = failures
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    median_duration = report["duration_seconds"]["median"]
    peak_mb = report["peak_rss_bytes"]["maximum"] / 1024 / 1024
    print(f"Median duration: {median_duration:.3f} seconds")
    print(f"Maximum peak RSS: {peak_mb:.1f} MB")
    print(f"Rows: {report['result']['row_count']}")
    print(f"Images: {report['result']['image_count']}")
    print(f"Report: {args.report}")

    for failure in failures:
        print(f"FAILED: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
