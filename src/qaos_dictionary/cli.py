"""Command-line interface for DOCX dictionary-table conversion."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

from qaos_dictionary import ConversionError, ProgressEvent, convert_dictionary_docx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a DOCX dictionary table into a tab-delimited CSV file."
    )
    parser.add_argument("input", type=Path, help="Path to the input .docx file.")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="Path to the output .csv file. Defaults to the input filename with a .csv extension.",
    )
    parser.add_argument(
        "--image-quality",
        type=int,
        default=75,
        metavar="1-100",
        help="WebP quality for embedded images (default: 75).",
    )
    parser.add_argument(
        "--qa",
        action="store_true",
        help="Run QA checks and open the browser report after conversion.",
    )
    parser.add_argument(
        "--qa-port",
        type=int,
        default=0,
        metavar="PORT",
        help="Local QA report port. The default selects an available port automatically.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the QA report server without opening the browser automatically.",
    )
    return parser


def write_atomic(path: Path, content: bytes) -> None:
    """Write bytes to a temporary sibling file and replace the target atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary_path, path)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = args.input.expanduser()
    output_path = (args.output or input_path.with_suffix(".csv")).expanduser()

    if input_path.suffix.casefold() != ".docx":
        parser.error("the input file must use the .docx extension")
    if not input_path.is_file():
        parser.error(f"input file does not exist: {input_path}")
    if output_path.suffix.casefold() != ".csv":
        parser.error("the output file must use the .csv extension")
    if input_path.resolve() == output_path.resolve():
        parser.error("the input and output paths must be different")
    if not 1 <= args.image_quality <= 100:
        parser.error("--image-quality must be between 1 and 100")
    if not 0 <= args.qa_port <= 65535:
        parser.error("--qa-port must be between 0 and 65535")
    if args.no_browser and not args.qa:
        parser.error("--no-browser can only be used together with --qa")

    try:
        print(f"[1/3] Converting {input_path.name}...", flush=True)
        started_at = time.perf_counter()
        last_progress = -1

        def report_progress(event: ProgressEvent) -> None:
            nonlocal last_progress
            if event.stage == "extract" and event.total:
                percent = event.completed * 100 // event.total
                if percent >= last_progress + 10 or percent == 100:
                    last_progress = percent
                    print(f"      {percent}% rows processed", flush=True)

        result = convert_dictionary_docx(
            input_path,
            image_quality=args.image_quality,
            progress_callback=report_progress,
        )
        duration_seconds = time.perf_counter() - started_at
        write_atomic(output_path, result.content)
        qa_session = None
        if args.qa:
            from app.qa import build_qa_session

            print("[2/3] Running QA checks...", flush=True)
            qa_session = build_qa_session(
                input_path,
                output_path,
                result,
                duration_seconds,
            )
    except ConversionError as error:
        print(
            f"Conversion failed [{error.diagnostic.code}]: {error}",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("Conversion cancelled by user.", file=sys.stderr)
        return 130
    except OSError as error:
        print(f"File operation failed: {error}", file=sys.stderr)
        return 1

    columns = ", ".join(result.columns)
    print(f"Created {output_path} ({result.row_count} rows; columns: {columns})")

    if qa_session is not None:
        from app.qa_server import serve_qa_report

        try:
            print("[3/3] Starting QA report server...", flush=True)
            serve_qa_report(
                qa_session,
                port=args.qa_port,
                open_browser=not args.no_browser,
            )
        except OSError as error:
            print(f"QA report server failed: {error}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
