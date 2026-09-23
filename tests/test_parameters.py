"""Exercise every public CLI option; network tests use synthetic local media."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import nico_dl
import yt_dlp


URL = 'https://www.nicovideo.jp/watch/sm9?token=synthetic%2Bvalue&expires=123'
BROWSERS = ('brave', 'chrome', 'chromium', 'edge', 'firefox', 'safari')


class ParserTests(unittest.TestCase):
    def test_defaults(self):
        args = nico_dl.parser().parse_args([URL])
        self.assertEqual(args.url, URL)
        self.assertEqual(args.output_dir, Path.home() / 'Downloads' / 'nico')
        self.assertEqual(args.quality, '1080')
        self.assertEqual(args.crf, 18)
        self.assertIsNone(args.referer)
        self.assertIsNone(args.cookies)
        self.assertIsNone(args.cookies_from_browser)
        self.assertIsNone(args.user_agent)
        self.assertFalse(args.clean or args.reencode)

    def test_all_choices_and_crf_values(self):
        for quality in ('1080', '720', '480', 'best'):
            with self.subTest(quality=quality):
                self.assertEqual(nico_dl.parser().parse_args([URL, '--quality', quality]).quality, quality)
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                self.assertEqual(nico_dl.parser().parse_args([URL, '--cookies-from-browser', browser]).cookies_from_browser, browser)
        for crf in range(52):
            with self.subTest(crf=crf):
                self.assertEqual(nico_dl.parser().parse_args([URL, '--reencode', '--crf', str(crf)]).crf, crf)

    def test_rejects_invalid_values_and_conflicting_options(self):
        cases = [[], ['file:///video.mp4'], ['https://'], ['https://user:pass@example.com/video'],
                 [URL, '--quality', '2160'], [URL, '--cookies-from-browser', 'unknown'],
                 [URL, '--crf', '-1'], [URL, '--crf', '52'], [URL, '--crf', '18.5'],
                 [URL, '--crf', 'bad'], [URL, '--clean', '--reencode'],
                 [URL, '--cookies', 'cookies.txt', '--cookies-from-browser', 'firefox'],
                 [URL, '--referer', 'file:///private'], [URL, '--unknown-option']]
        for flags in cases:
            with self.subTest(flags=flags), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                nico_dl.parser().parse_args(flags)
            self.assertEqual(caught.exception.code, 2)
        for option in ('--output-dir', '--quality', '--cookies', '--cookies-from-browser', '--referer', '--user-agent', '--crf'):
            with self.subTest(missing=option), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                nico_dl.parser().parse_args([URL, option])
            self.assertEqual(caught.exception.code, 2)

    def test_both_help_flags_exit_without_dependencies_or_download(self):
        for flag in ('-h', '--help'):
            output = io.StringIO()
            with self.subTest(flag=flag), redirect_stdout(output), patch('nico_dl.download') as download:
                with self.assertRaises(SystemExit) as caught:
                    nico_dl.main([flag])
                self.assertEqual(caught.exception.code, 0)
                download.assert_not_called()
                for option in ('--output-dir', '--quality', '--cookies', '--cookies-from-browser',
                               '--referer', '--user-agent', '--clean', '--reencode', '--crf'):
                    self.assertIn(option, output.getvalue())


class ForwardingTests(unittest.TestCase):
    def test_all_browser_names_are_accepted_by_real_yt_dlp(self):
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                options = yt_dlp.parse_options(['--ignore-config', '--cookies-from-browser', browser, URL])
                self.assertEqual(options.ydl_opts['cookiesfrombrowser'][0], browser)

    def test_each_browser_reaches_downloader_and_failures_propagate(self):
        # No personal browser profiles are read by these adapter tests.
        for browser in BROWSERS:
            with self.subTest(browser=browser), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                source = root / 'Niconico-sm9' / 'source.mp4'
                args = nico_dl.parser().parse_args([URL, '--cookies-from-browser', browser])
                def fake_download(command, stage, **kwargs):
                    self.assertEqual(command[command.index('--cookies-from-browser') + 1], browser)
                    self.assertNotIn('--cookies', command)
                    self.assertEqual(command[-2:], ['--', URL])
                    (root / 'download-path.json').write_text(json.dumps(str(source)) + '\n', encoding='utf-8')
                    return ''
                with patch('nico_dl.run', side_effect=fake_download), patch('nico_dl.inspect_media'):
                    self.assertEqual(nico_dl.download(args, root), [source.resolve()])
                with patch('nico_dl.run', side_effect=nico_dl.DownloadError('Browser unavailable')):
                    with self.assertRaisesRegex(nico_dl.DownloadError, 'Browser unavailable'):
                        nico_dl.download(args, root)

    def test_every_crf_is_forwarded_from_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for crf in range(52):
                with self.subTest(crf=crf), redirect_stdout(io.StringIO()), \
                     patch('nico_dl.shutil.which', return_value='tool'), \
                     patch('nico_dl.download', return_value=[root / 'source.mp4']), \
                     patch('nico_dl.process_media', return_value=root / 'reencoded.mp4') as process:
                    self.assertEqual(nico_dl.main([URL, '--output-dir', str(root), '--reencode', '--crf', str(crf)]), 0)
                    process.assert_called_once_with(root / 'source.mp4', reencode=True, crf=crf)

    def test_missing_cookies_and_output_path_errors_do_not_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            blocked = root / 'not-a-directory'
            blocked.write_text('keep me')
            for flags in (['--cookies', str(root / 'missing.txt')], ['--cookies', str(root)],
                          ['--output-dir', str(blocked)]):
                with self.subTest(flags=flags), redirect_stderr(io.StringIO()), \
                     patch('nico_dl.shutil.which', return_value='tool'), patch('nico_dl.download') as download:
                    self.assertEqual(nico_dl.main([URL, *flags]), 1)
                    download.assert_not_called()
            self.assertEqual(blocked.read_text(), 'keep me')


class ProtectedHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append((self.path, dict(self.headers)))
        if self.server.protected:
            if (self.headers.get('Referer') != 'https://www.nicovideo.jp/player' or
                    self.headers.get('User-Agent') != 'Nico parameter test/1.0' or
                    'nico_test=allowed' not in self.headers.get('Cookie', '')):
                self.send_error(403)
                return
        super().do_GET()

    def log_message(self, *args):
        pass


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools required')
class ParameterIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='nico options 日本語 ')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        master = ['#EXTM3U']
        for height in (480, 720, 1080, 1440):
            target = cls.root / str(height)
            target.mkdir()
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', f'testsrc2=size=256x{height}:rate=2',
                            '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '1', '-c:v', 'libx264',
                            '-preset', 'ultrafast', '-c:a', 'aac', '-f', 'hls', '-hls_list_size', '0',
                            str(target / 'video.m3u8')], check=True)
            master.extend([f'#EXT-X-STREAM-INF:BANDWIDTH={height * 1000},RESOLUTION=256x{height}',
                           f'{height}/video.m3u8'])
        (cls.root / 'master.m3u8').write_text('\n'.join(master) + '\n', encoding='utf-8')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(ProtectedHandler, directory=str(cls.root)))
        cls.server.requests = []
        cls.server.protected = False
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.addClassCleanup(cls.stop_server)
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/master.m3u8?token=synthetic%2Bvalue&expires=123'

    @classmethod
    def stop_server(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def cli(self, *flags, success=True, env=None):
        output = Path(tempfile.mkdtemp(dir=self.root, prefix='output '))
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('local_cli.py').resolve()), self.url, '--output-dir', str(output), *flags],
                                capture_output=True, encoding='utf-8', errors='replace', timeout=90, env=env)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return output, result

    def isolated_home(self):
        home = Path(tempfile.mkdtemp(dir=self.root, prefix='home 日本語 '))
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                   APPDATA=str(home / 'AppData/Roaming'), LOCALAPPDATA=str(home / 'AppData/Local'),
                   XDG_CONFIG_HOME=str(home / '.config'), PYTHONUTF8='1')
        return home, env

    def test_default_and_tilde_output_directory(self):
        home, env = self.isolated_home()
        for flags, expected in (([], home / 'Downloads/nico'),
                                (['--output-dir', '~/custom 日本語'], home / 'custom 日本語'),
                                (['--output-dir', 'relative output'], home / 'relative output')):
            with self.subTest(flags=flags):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('local_cli.py').resolve()), self.url, '--quality', '480', *flags],
                                        env=env, cwd=home, capture_output=True, encoding='utf-8', errors='replace', timeout=90)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(list(expected.glob('nico-*/*/source.*'))), 1)

    def test_firefox_extraction_with_synthetic_profile(self):
        home, env = self.isolated_home()
        if sys.platform == 'win32':
            profile = Path(env['APPDATA']) / 'Mozilla/Firefox/Profiles/test.default'
        elif sys.platform == 'darwin':
            profile = home / 'Library/Application Support/Firefox/Profiles/test.default'
        else:
            profile = home / '.mozilla/firefox/test.default'
        profile.mkdir(parents=True)
        connection = sqlite3.connect(profile / 'cookies.sqlite')
        try:
            connection.execute('CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT, path TEXT, expiry INTEGER, isSecure INTEGER)')
            connection.execute('INSERT INTO moz_cookies VALUES (?, ?, ?, ?, ?, ?)',
                               ('127.0.0.1', 'nico_test', 'allowed', '/', int(time.time()) + 3600, 0))
            connection.commit()
        finally:
            connection.close()
        self.server.protected = True
        self.server.requests.clear()
        try:
            self.cli('--cookies-from-browser', 'firefox', '--referer', 'https://www.nicovideo.jp/player',
                     '--user-agent', 'Nico parameter test/1.0', '--quality', '480', env=env)
            self.assertTrue(any('.ts' in path for path, _ in self.server.requests))
            for _, headers in self.server.requests:
                self.assertIn('nico_test=allowed', headers.get('Cookie', ''))
        finally:
            self.server.protected = False

    def test_all_crf_values_encode_and_validate(self):
        source = self.root / '480/video0.ts'
        for crf in range(52):
            with self.subTest(crf=crf):
                folder = Path(tempfile.mkdtemp(dir=self.root, prefix=f'crf-{crf}-'))
                copied = folder / 'source.ts'
                shutil.copyfile(source, copied)
                output = nico_dl.process_media(copied, reencode=True, crf=crf)
                self.assertTrue(output.is_file())
                self.assertEqual(copied.read_bytes(), source.read_bytes())

    def test_every_quality_selects_actual_matching_resolution(self):
        for quality, expected in (('480', 480), ('720', 720), ('1080', 1080), ('best', 1440)):
            with self.subTest(quality=quality):
                output, _ = self.cli('--quality', quality)
                files = list(output.glob('nico-*/*/source.*'))
                self.assertEqual(len(files), 1)
                info = nico_dl.inspect_media(files[0])
                self.assertEqual(next(s['height'] for s in info['streams'] if s['codec_type'] == 'video'), expected)
        self.assertTrue(any('token=synthetic%2Bvalue&expires=123' in path for path, _ in self.server.requests))

    def test_cookie_file_referer_and_user_agent_reach_manifest_and_segments(self):
        cookies = self.root / 'test cookies.txt'
        cookies.write_text('# Netscape HTTP Cookie File\n127.0.0.1\tFALSE\t/\tFALSE\t0\tnico_test\tallowed\n', encoding='utf-8')
        self.server.protected = True
        self.server.requests.clear()
        flags = ['--cookies', str(cookies), '--referer', 'https://www.nicovideo.jp/player',
                 '--user-agent', 'Nico parameter test/1.0', '--quality', '480']
        try:
            self.cli(*flags)
            paths = [path for path, _ in self.server.requests]
            self.assertTrue(any('master.m3u8' in path for path in paths))
            self.assertTrue(any('video.m3u8' in path for path in paths))
            self.assertTrue(any('.ts' in path for path in paths))
            for path, headers in self.server.requests:
                with self.subTest(path=path):
                    self.assertEqual(headers.get('Referer'), 'https://www.nicovideo.jp/player')
                    self.assertEqual(headers.get('User-Agent'), 'Nico parameter test/1.0')
                    self.assertIn('nico_test=allowed', headers.get('Cookie', ''))
            # Independently prove each parameter is needed by the protected endpoint.
            for option in ('--cookies', '--referer', '--user-agent'):
                reduced = list(flags)
                index = reduced.index(option)
                del reduced[index:index + 2]
                with self.subTest(omitted=option):
                    self.cli(*reduced, success=False)
        finally:
            self.server.protected = False

    def test_malformed_cookie_file_fails(self):
        cookies = self.root / 'invalid cookies.txt'
        cookies.write_text('this is not a Netscape cookies file', encoding='utf-8')
        self.cli('--cookies', str(cookies), success=False)

    def test_clean_and_crf_boundary_cli_outputs(self):
        for flags, name in ((['--clean'], 'cleaned.mkv'),
                            (['--reencode', '--crf', '0'], 'reencoded.mp4'),
                            (['--reencode', '--crf', '51'], 'reencoded.mp4')):
            with self.subTest(flags=flags):
                output, _ = self.cli('--quality', '480', *flags)
                files = list(output.glob(f'nico-*/*/{name}'))
                self.assertEqual(len(files), 1)
                info = nico_dl.inspect_media(files[0])
                self.assertEqual([s['codec_name'] for s in info['streams']], ['h264', 'aac'])
                self.assertEqual(len(list(output.glob('nico-*/*/source.*'))), 1)
                self.assertFalse(list(output.rglob('*.partial.*')))


if __name__ == '__main__':
    unittest.main()
