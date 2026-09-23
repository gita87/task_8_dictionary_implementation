"""Operations boundary for dictionary conversion."""

from __future__ import annotations

from qaos_common import CancellationToken

from .models import (
    Cancellation,
    ConversionError,
    Diagnostic,
    ProgressCallback,
    ProgressEvent,
)


def _error(code: str, message: str, **context: object) -> ConversionError:
    return ConversionError(Diagnostic(code, message, context=context))


def _cancelled(cancellation: Cancellation | None) -> bool:
    if cancellation is None:
        return False
    if isinstance(cancellation, CancellationToken):
        return cancellation.is_cancelled()
    if callable(cancellation):
        return bool(cancellation())
    return bool(cancellation.is_set())


def _check_cancelled(cancellation: Cancellation | None) -> None:
    if _cancelled(cancellation):
        raise _error("conversion_cancelled", "The conversion was cancelled.")


def _progress(
    callback: ProgressCallback | None, stage: str, completed: int, total: int | None, message: str
) -> None:
    if callback is not None:
        callback(ProgressEvent(stage, completed, total, message))
