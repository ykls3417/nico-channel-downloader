"""Test-only Generic extractor for the isolated local media fixture."""

from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nico_backend
from yt_dlp.extractor.generic import GenericIE

if __name__ == '__main__':
    with patch('nico_backend.page_url', side_effect=lambda value: value), \
            patch('nico_backend.EXTRACTORS', (GenericIE,)):
        sys.exit(nico_backend.main())
