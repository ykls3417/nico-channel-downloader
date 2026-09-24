"""Cancellation must stop the downloader and its media-process descendants."""

from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import nico_dl


class ProcessTests(unittest.TestCase):
    def test_cancellation_stops_child_and_grandchild(self):
        with tempfile.TemporaryDirectory() as directory:
            heartbeat = Path(directory) / 'heartbeat'
            child = (f'from pathlib import Path; import time; p = Path({str(heartbeat)!r})\n'
                     'while True:\n p.write_text(str(time.monotonic())); time.sleep(0.05)\n')
            parent = (f'import subprocess, sys, time; subprocess.Popen([sys.executable, "-c", {child!r}]); '
                      'time.sleep(60)')
            communicate = subprocess.Popen.communicate
            interrupted = []

            def interrupt_once(process, *args, **kwargs):
                if not interrupted:
                    interrupted.append(process)
                    deadline = time.monotonic() + 10
                    while not heartbeat.exists() and time.monotonic() < deadline:
                        time.sleep(0.05)
                    # Exercise cleanup even if the child failed to start.
                    raise KeyboardInterrupt
                return communicate(process, *args, **kwargs)

            with patch.object(subprocess.Popen, 'communicate', interrupt_once), self.assertRaises(KeyboardInterrupt):
                nico_dl.run([sys.executable, '-c', parent], 'Test process', capture=True)
            self.assertIsNotNone(interrupted[0].poll())
            self.assertTrue(heartbeat.exists(), 'The grandchild must have started before cancellation')
            before = heartbeat.read_text()
            time.sleep(0.3)
            self.assertEqual(heartbeat.read_text(), before, 'Grandchild kept running after cancellation')


if __name__ == '__main__':
    unittest.main()
