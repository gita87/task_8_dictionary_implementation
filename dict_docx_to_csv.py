"""Backward-compatible facade for the former single-module API.

New integrations should import from :mod:`qaos_dictionary`.
"""

from qaos_dictionary.core import *  # noqa: F401,F403
from qaos_dictionary.core import _first_image_blob, _validated_docx_buffer
