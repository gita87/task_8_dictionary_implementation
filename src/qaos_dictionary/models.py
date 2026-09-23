"""Models boundary for dictionary conversion."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Protocol, TypeAlias, cast

from qaos_common import CancellationToken
from qaos_common.errors import QAOSCommonError, redact_sensitive
from qaos_common.progress import ProgressEvent as CommonProgressEvent
from qaos_common.schemas import DICTIONARY_SCHEMA_VERSION


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: str = "error"
    context: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return cast(
            dict[str, object],
            redact_sensitive(
                {
                    "code": self.code,
                    "message": self.message,
                    "severity": self.severity,
                    "context": dict(self.context),
                }
            ),
        )


class ConversionError(QAOSCommonError, ValueError):
    """Conversion failure carrying a stable structured diagnostic."""

    def __init__(
        self,
        diagnostic: Diagnostic | str,
        *,
        code: str = "conversion_failed",
        context: Mapping[str, object] | None = None,
    ) -> None:
        if isinstance(diagnostic, str):
            diagnostic = Diagnostic(code, diagnostic, context=context or {})
        super().__init__(diagnostic.message, code=diagnostic.code, details=diagnostic.context)
        self.diagnostic = Diagnostic(self.code, self.message, diagnostic.severity, self.details)

    def __str__(self) -> str:
        return self.message

    def as_dict(self) -> dict[str, object]:
        return self.diagnostic.as_dict()


@dataclass(frozen=True)
class ProgressEvent:
    stage: str
    completed: int
    total: int | None
    message: str

    def to_common(self) -> CommonProgressEvent:
        stages = {
            "read": "reading",
            "validate": "validating",
            "extract": "parsing",
            "serialize": "writing",
            "complete": "completed",
        }
        return CommonProgressEvent(stages[self.stage], self.completed, self.total, self.message)


@dataclass(frozen=True)
class Checkpoint:
    schema_version: str
    stage: str
    rows_processed: int
    total_rows: int | None


class _EventLike(Protocol):
    def is_set(self) -> bool: ...


InputSource: TypeAlias = str | Path | bytes | bytearray | memoryview | IO[bytes]
ProgressCallback: TypeAlias = Callable[[ProgressEvent], None]
CheckpointCallback: TypeAlias = Callable[[Checkpoint], None]
Cancellation: TypeAlias = CancellationToken | _EventLike | Callable[[], bool]


@dataclass(frozen=True)
class ConversionResult:
    content: bytes
    filename: str
    row_count: int
    columns: tuple[str, ...]
    schema_version: str = DICTIONARY_SCHEMA_VERSION
    diagnostics: tuple[Diagnostic, ...] = ()
