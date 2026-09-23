"""Test-only adapter: exercise real yt-dlp/FFmpeg against synthetic localhost HLS."""

from pathlib import Path
import sys
from unittest.mock import patch

import nico_dl

real_run = nico_dl.run


def local_download(command, stage, **kwargs):
    if stage == 'Download':
        command = [command[0], str(Path(__file__).with_name('local_backend.py').resolve()), *command[3:]]
    return real_run(command, stage, **kwargs)


if __name__ == '__main__':
    with patch('nico_dl.page_url', side_effect=lambda value: value), patch('nico_dl.run', side_effect=local_download):
        sys.exit(nico_dl.main())
