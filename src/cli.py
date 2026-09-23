"""Compatibility entry point for the packaged CLI."""

from qaos_dictionary.cli import build_parser as build_parser
from qaos_dictionary.cli import main as main
from qaos_dictionary.cli import write_atomic as write_atomic

if __name__ == "__main__":
    raise SystemExit(main())
