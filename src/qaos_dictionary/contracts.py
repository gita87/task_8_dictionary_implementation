"""Shared constants and consumer-owned DOCX safeguards."""

import re

from qaos_common.limits import DEFAULT_LIMITS
from qaos_common.schemas import MISSING_DICTIONARY_IMAGE

REQUIRED_HEADERS = ("word", "definition")
OPTIONAL_HEADERS = ("image",)
GENERATED_HEADERS = ("unique_id",)
MISSING_IMAGE_VALUE = MISSING_DICTIONARY_IMAGE
WEBP_DATA_URI_PREFIX = "data:image/webp;base64,"
DEFAULT_IMAGE_QUALITY = 75
MAX_UPLOAD_BYTES = DEFAULT_LIMITS.max_upload_bytes
MAX_CELL_BYTES = DEFAULT_LIMITS.max_cell_bytes
MAX_OUTPUT_BYTES = DEFAULT_LIMITS.max_output_bytes
MAX_UNCOMPRESSED_DOCX_BYTES = MAX_OUTPUT_BYTES
MAX_DOCX_MEMBERS = 10_000

_ALLOWED_SOURCE_MIME_TYPES = frozenset(
    {
        "image/bmp",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/webp",
    }
)
_ALLOWED_PIL_FORMATS = frozenset({"BMP", "GIF", "JPEG", "PNG", "TIFF", "WEBP"})
_MIME_TO_PIL_FORMAT = {
    "image/bmp": "BMP",
    "image/gif": "GIF",
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/tiff": "TIFF",
    "image/webp": "WEBP",
}
_WHITESPACE = re.compile(r"\s+")
