import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import nico_dl


class URLTests(unittest.TestCase):
    def test_invalid_inputs(self):
        for url in ("file:///etc/passwd", "--help", "https://user:secret@example.com/v", "https://example.com/a b"):
            with self.subTest(url=url), self.assertRaises(argparse.ArgumentTypeError):
                nico_dl.http_url(url)

    def test_signed_url_is_preserved(self):
        url = "https://example.com/video.m3u8?token=a%2Bb&expires=123"
        self.assertEqual(nico_dl.http_url(url), url)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nico 日本語 ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.mkv"
        metadata = self.root / "metadata.txt"
        metadata.write_text(";FFMETADATA1\ntitle=Private title\ncomment=Private comment\n"
                            "[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=1000\ntitle=Private chapter\n")
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=10",
                        "-f", "lavfi", "-i", "sine=frequency=440", "-i", str(metadata),
                        "-map", "0:v", "-map", "1:a", "-map_metadata", "2", "-map_chapters", "2",
                        "-metadata:s:a:0", "title=Private track", "-t", "2", "-c:v", "libx264",
                        "-c:a", "aac", str(self.source)], check=True)

    def test_cleanup_and_reencode(self):
        original = self.source.read_bytes()
        for reencode in (False, True):
            with self.subTest(reencode=reencode):
                output = nico_dl.process_media(self.source, reencode=reencode)
                info = nico_dl.inspect_media(output)
                tags = str(info["format"].get("tags", {})) + str([s.get("tags", {}) for s in info["streams"]])
                self.assertNotIn("Private", tags)
                self.assertEqual(info["chapters"], [])
                self.assertEqual(self.source.read_bytes(), original)
                self.assertFalse(list(self.root.glob("*.partial.*")))
                if reencode:
                    self.assertEqual([s["codec_name"] for s in info["streams"]], ["h264", "aac"])

    def test_failed_conversion_preserves_original(self):
        original = self.source.read_bytes()
        real_run = nico_dl.run

        def fail_processing(command, stage, **kwargs):
            if stage == "FFmpeg processing":
                Path(command[-1]).write_bytes(b"incomplete")
                raise nico_dl.DownloadError("Simulated encoder failure")
            return real_run(command, stage, **kwargs)

        with patch("nico_dl.run", side_effect=fail_processing), self.assertRaises(nico_dl.DownloadError):
            nico_dl.process_media(self.source, reencode=True)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertFalse((self.root / "reencoded.mp4").exists())
        self.assertTrue((self.root / "reencoded.partial.mp4").exists())

    def test_decode_failure_does_not_publish_final(self):
        real_run = nico_dl.run

        def fail_validation(command, stage, **kwargs):
            if stage == "Full decode validation":
                raise nico_dl.DownloadError("Simulated decoding failure")
            return real_run(command, stage, **kwargs)

        with patch("nico_dl.run", side_effect=fail_validation), self.assertRaises(nico_dl.DownloadError):
            nico_dl.process_media(self.source, reencode=False)
        self.assertTrue(self.source.exists())
        self.assertFalse((self.root / "cleaned.mkv").exists())

    def test_refuses_overwrite(self):
        destination = self.root / "reencoded.mp4"
        destination.write_bytes(b"existing video")
        with self.assertRaises(nico_dl.DownloadError):
            nico_dl.process_media(self.source, reencode=True)
        self.assertEqual(destination.read_bytes(), b"existing video")

    def test_download_and_process_local_hls(self):
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(self.source), "-c", "copy",
                        "-f", "hls", "-hls_time", "1", "-hls_list_size", "0",
                        str(self.root / "video.m3u8")], check=True)
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(self.root)))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/video.m3u8"
            for flags, expected in (([], "source.*"), (["--clean"], "cleaned.mkv"), (["--reencode"], "reencoded.mp4")):
                with self.subTest(flags=flags):
                    output = self.root / ("out" + expected.replace("*", "all"))
                    result = subprocess.run([sys.executable, "-m", "nico_dl", url, "--output-dir", str(output),
                                             *flags], capture_output=True, encoding="utf-8", errors="replace")
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(len(list(output.glob(f"nico-*/{expected}"))), 1)
                    self.assertEqual(len(list(output.glob("nico-*/source.*"))), 1)
            bad_output = self.root / "failed"
            result = subprocess.run([sys.executable, "-m", "nico_dl", url.replace("video.m3u8", "missing.m3u8"),
                                     "--output-dir", str(bad_output)], capture_output=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(list(bad_output.rglob("reencoded.mp4")))
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == "__main__":
    unittest.main()
