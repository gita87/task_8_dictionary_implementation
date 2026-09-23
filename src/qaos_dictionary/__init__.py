"""Stable public conversion API; implementation lives in narrow boundaries."""

from qaos_common import CancellationToken as CancellationToken
from qaos_common import ProcessingLimits as ProcessingLimits
from qaos_common.schemas import DICTIONARY_COLUMNS as DICTIONARY_COLUMNS
from qaos_common.schemas import DICTIONARY_SCHEMA_VERSION as DICTIONARY_SCHEMA_VERSION

from .contracts import DEFAULT_IMAGE_QUALITY as DEFAULT_IMAGE_QUALITY
from .contracts import MAX_CELL_BYTES as MAX_CELL_BYTES
from .contracts import MAX_OUTPUT_BYTES as MAX_OUTPUT_BYTES
from .contracts import MAX_UPLOAD_BYTES as MAX_UPLOAD_BYTES
from .contracts import MISSING_IMAGE_VALUE as MISSING_IMAGE_VALUE
from .contracts import WEBP_DATA_URI_PREFIX as WEBP_DATA_URI_PREFIX
from .extraction import extract_rows as extract_rows
from .extraction import find_dictionary_table as find_dictionary_table
from .extraction import normalize_header as normalize_header
from .extraction import plain_cell_text as plain_cell_text
from .images import image_to_data_uri as image_to_data_uri
from .models import Checkpoint as Checkpoint
from .models import ConversionError as ConversionError
from .models import ConversionResult as ConversionResult
from .models import Diagnostic as Diagnostic
from .models import ProgressEvent as ProgressEvent
from .pipeline import convert_dictionary_docx as convert_dictionary_docx
from .pipeline import convert_dictionary_docx_to_csv as convert_dictionary_docx_to_csv
from .serialization import rows_to_csv as rows_to_csv

__all__ = [
    "DICTIONARY_COLUMNS",
    "ProcessingLimits",
    "DEFAULT_IMAGE_QUALITY",
    "DICTIONARY_SCHEMA_VERSION",
    "MAX_CELL_BYTES",
    "MAX_OUTPUT_BYTES",
    "MAX_UPLOAD_BYTES",
    "MISSING_IMAGE_VALUE",
    "WEBP_DATA_URI_PREFIX",
    "CancellationToken",
    "Checkpoint",
    "ConversionError",
    "ConversionResult",
    "Diagnostic",
    "ProgressEvent",
    "convert_dictionary_docx",
    "convert_dictionary_docx_to_csv",
    "extract_rows",
    "find_dictionary_table",
    "image_to_data_uri",
    "normalize_header",
    "plain_cell_text",
    "rows_to_csv",
]
