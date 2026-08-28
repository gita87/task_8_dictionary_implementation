"""Command-line interface for DOCX dictionary-table conversion."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Sequence

from app.converter import ConversionError, convert_docx


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
    return parser


def write_atomic(path: Path, content: bytes) -> None:
    """Write bytes to a temporary sibling file and replace the target atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            temporary_path = Path(stream.name)

        os.replace(temporary_path, path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def main(argv: Optional[Sequence[str]] = None) -> int:
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

    try:
        with input_path.open("rb") as source:
            result = convert_docx(
                source,
                input_filename=input_path.name,
                image_quality=args.image_quality,
            )
        write_atomic(output_path, result.content)
    except ConversionError as error:
        print(f"Conversion failed: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"File operation failed: {error}", file=sys.stderr)
        return 1

    columns = ", ".join(result.columns)
    print(f"Created {output_path} ({result.row_count} rows; columns: {columns})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

