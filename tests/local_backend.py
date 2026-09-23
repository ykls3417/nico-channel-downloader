"""Test-only Generic extractor for the isolated local media fixture."""

import sys
from unittest.mock import patch

import nico_backend
from yt_dlp.extractor.generic import GenericIE

if __name__ == '__main__':
    with patch('nico_backend.page_url', side_effect=lambda value: value), \
            patch('nico_backend.EXTRACTORS', (GenericIE,)):
        sys.exit(nico_backend.main())
