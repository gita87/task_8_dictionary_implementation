"""Images boundary for dictionary conversion."""

from __future__ import annotations

import base64
import io

from docx.table import _Cell
from PIL import Image, ImageOps, UnidentifiedImageError

from .contracts import (
    _ALLOWED_PIL_FORMATS,
    _ALLOWED_SOURCE_MIME_TYPES,
    _MIME_TO_PIL_FORMAT,
    DEFAULT_IMAGE_QUALITY,
    MAX_CELL_BYTES,
    MISSING_IMAGE_VALUE,
    WEBP_DATA_URI_PREFIX,
)
from .models import ConversionError
from .operations import _error


def _first_image_blob(cell: _Cell) -> tuple[bytes, str] | None:
    for blip in cell._tc.xpath(".//a:blip"):
        relationship_id = blip.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
        )
        if not relationship_id:
            continue
        image_part = cell.part.related_parts.get(relationship_id)
        if image_part is not None and hasattr(image_part, "blob"):
            mime = getattr(image_part, "content_type", "application/octet-stream")
            return image_part.blob, mime.casefold()
    return None


def _validate_cell_size(value: str, column: str, row_number: int) -> None:
    size = len(value.encode("utf-8"))
    if size > MAX_CELL_BYTES:
        raise _error(
            "cell_too_large",
            f"Dictionary table row {row_number} column '{column}' exceeds the cell size limit.",
            row=row_number,
            column=column,
            size_bytes=size,
            limit_bytes=MAX_CELL_BYTES,
        )


def image_to_data_uri(cell: _Cell, quality: int = DEFAULT_IMAGE_QUALITY) -> str:
    image_data = _first_image_blob(cell)
    if image_data is None:
        return MISSING_IMAGE_VALUE
    blob, content_type = image_data
    if content_type not in _ALLOWED_SOURCE_MIME_TYPES:
        raise _error(
            "unsupported_image_mime",
            "An embedded image uses an unsupported MIME type.",
            mime_type=content_type,
            allowed_mime_types=sorted(_ALLOWED_SOURCE_MIME_TYPES),
        )
    if len(blob) > MAX_CELL_BYTES:
        raise _error(
            "image_too_large",
            "An embedded image exceeds the image size limit.",
            size_bytes=len(blob),
            limit_bytes=MAX_CELL_BYTES,
        )
    try:
        with Image.open(io.BytesIO(blob)) as source:
            if source.format not in _ALLOWED_PIL_FORMATS:
                raise _error(
                    "unsupported_image_format",
                    "An embedded image uses an unsupported image format.",
                    detected_format=source.format,
                )
            if source.format != _MIME_TO_PIL_FORMAT[content_type]:
                raise _error(
                    "image_mime_mismatch",
                    "An embedded image MIME type does not match its content.",
                    mime_type=content_type,
                    detected_format=source.format,
                )
            image = ImageOps.exif_transpose(source)
            image.load()
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            output = io.BytesIO()
            image.save(output, format="WEBP", quality=quality, method=6)
            value = WEBP_DATA_URI_PREFIX + base64.b64encode(output.getvalue()).decode("ascii")
            _validate_cell_size(value, "image", 0)
            return value
    except ConversionError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as error:
        raise _error(
            "image_conversion_failed",
            "An embedded image could not be converted to the required WebP format.",
            mime_type=content_type,
        ) from error
