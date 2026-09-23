"""Domain boundaries, extractor routing, collection handling and shared options."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nico_backend
import nico_dl
from nico_urls import ALLOWED_HOSTS, default_referer, http_url, page_url
from yt_dlp.utils import DownloadError


ROUTES = {
    'https://www.nicovideo.jp/watch/sm9': 'Niconico',
    'https://nicovideo.jp/watch/nm123': 'Niconico',
    'https://sp.nicovideo.jp/watch/so123': 'Niconico',
    'https://embed.nicovideo.jp/watch/123': 'Niconico',
    'https://www.nicovideo.jp/shorts/sm123': 'Niconico',
    'https://live.nicovideo.jp/watch/lv123': 'NiconicoLive',
    'https://sp.live2.nicovideo.jp/gate/lv123': 'NiconicoLive',
    'https://nicochannel.jp/testman/video/smABC123': 'NiconicoChannelPlus',
    'https://nicochannel.jp/testman/live/smABC123': 'NiconicoChannelPlus',
    'https://nicochannel.jp/testman/videos?sort=released_at&tag=test': 'NiconicoChannelPlusChannelVideos',
    'https://nicochannel.jp/testman/lives': 'NiconicoChannelPlusChannelLives',
    'https://www.nicovideo.jp/mylist/123': 'NiconicoPlaylist',
    'https://www.nicovideo.jp/user/123/mylist/456': 'NiconicoPlaylist',
    'https://www.nicovideo.jp/series/123': 'NiconicoSeries',
    'https://www.nicovideo.jp/user/123/series/456': 'NiconicoSeries',
    'https://www.nicovideo.jp/user/123': 'NiconicoUser',
    'https://sp.nicovideo.jp/user/123/video': 'NiconicoUser',
    'https://ch.nicovideo.jp/ch2525': 'TraditionalChannel',
    'https://ch.nicovideo.jp/ch2525/video?page=2': 'TraditionalChannel',
}


class RouteTests(unittest.TestCase):
    def test_exact_hosts_and_rejected_inputs(self):
        for host in ALLOWED_HOSTS:
            self.assertEqual(http_url(f'https://{host}/'), f'https://{host}/')
        bad = ['https://example.com/watch/sm9', 'https://nicovideo.jp.evil.test/watch/sm9',
               'https://evilnicovideo.jp/watch/sm9', 'https://foo.nicovideo.jp/watch/sm9',
               'https://nico.ms/sm9', 'http://localhost/video.m3u8', 'https://127.0.0.1/a',
               'https://nicovideo.jp:123/watch/sm9', 'https://nicovideo.jp:bad/watch/sm9',
               'https://nicovideo.jp./watch/sm9', 'https://user@nicovideo.jp/watch/sm9',
               'https://@nicovideo.jp/watch/sm9', 'https://nicovideo.jp\\@evil.test/a',
               'https://nicovideo.jp/watch/\nsm9', 'ftp://nicovideo.jp/watch/sm9',
               'https://nicovideo.jp/video.m3u8', 'https://nicochannel.jp/foo/video/bad',
               'https://www.nicovideo.jp/watch/sm9/other', 'https://ch.nicovideo.jp/']
        for url in bad:
            with self.subTest(url=url), redirect_stderr(io.StringIO()), patch('nico_dl.download') as download:
                with self.assertRaises(SystemExit) as caught:
                    nico_dl.main([url])
                self.assertEqual(caught.exception.code, 2)
                download.assert_not_called()
        with self.assertRaises(argparse.ArgumentTypeError):
            http_url('https://example.com/referer')

    def test_each_route_selects_only_its_niconico_extractor(self):
        for url, expected in ROUTES.items():
            with self.subTest(url=url):
                canonical = page_url(url)
                selected = [ie.ie_key() for ie in nico_backend.EXTRACTORS if ie.suitable(canonical)]
                self.assertEqual(selected, [expected])
        self.assertEqual(page_url('HTTP://NICOVIDEO.JP:80/watch/sm9?token=a%2Bb'),
                         'https://www.nicovideo.jp/watch/sm9?token=a%2Bb')

    def test_channel_named_video_is_normalized_as_a_channel(self):
        self.assertEqual(page_url('https://ch.nicovideo.jp/video'), 'https://ch.nicovideo.jp/video/video')

    def test_backend_rejects_external_playlist_entries_and_redirects(self):
        with nico_backend.NiconicoDL({'quiet': True}) as downloader:
            self.assertNotIn('Generic', downloader._ies)
            with self.assertRaises(DownloadError):
                downloader.extract_info('https://example.com/video.mp4')
            with self.assertRaises(DownloadError):
                downloader.process_ie_result({'_type': 'url', 'url': 'https://example.com/video.mp4'})

    def test_every_route_shares_download_parameters(self):
        cases = [['--quality', q] for q in ('480', '720', '1080', 'best')]
        cases += [['--cookies-from-browser', b] for b in ('brave', 'chrome', 'chromium', 'edge', 'firefox', 'safari')]
        cases += [['--cookies', 'cookie file.txt'], ['--referer', 'https://nicovideo.jp/custom'],
                  ['--user-agent', 'Test browser/1.0']]
        for url in ROUTES:
            for flags in cases:
                with self.subTest(url=url, flags=flags), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    source = root / 'item' / 'source.mp4'
                    args = nico_dl.parser().parse_args([url, *flags])
                    def capture(command, stage, **kwargs):
                        self.assertEqual(command[2], 'nico_backend')
                        self.assertIn('--yes-playlist', command)
                        self.assertIn('--abort-on-error', command)
                        self.assertEqual(command[-2:], ['--', page_url(url)])
                        self.assertEqual(command[command.index('--referer') + 1], args.referer or default_referer(args.url))
                        expected = 'bv*+ba/b' if args.quality == 'best' else f'bv*[height<=?{args.quality}]+ba/b[height<=?{args.quality}]'
                        self.assertEqual(command[command.index('--format') + 1], expected)
                        if flags[0] in ('--cookies-from-browser', '--user-agent', '--referer'):
                            self.assertEqual(command[command.index(flags[0]) + 1], flags[1])
                        if flags[0] == '--cookies':
                            self.assertEqual(command[command.index('--cookies') + 1], str(Path(flags[1]).resolve()))
                        (root / 'download-path.json').write_text(json.dumps(str(source)) + '\n')
                        return ''
                    with patch('nico_dl.run', side_effect=capture), patch('nico_dl.inspect_media'):
                        self.assertEqual(nico_dl.download(args, root), [source])

    def test_every_route_processes_all_items_with_every_crf_and_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            sources = [root / 'one/source.mp4', root / 'two/source.mp4']
            for url in ROUTES:
                for flags in ([], ['--clean'], *[['--reencode', '--crf', str(crf)] for crf in range(52)]):
                    with self.subTest(url=url, flags=flags), redirect_stdout(io.StringIO()), \
                            patch('nico_dl.shutil.which', return_value='tool'), \
                            patch('nico_dl.download', return_value=sources), \
                            patch('nico_dl.process_media', return_value=root / 'processed.mp4') as process:
                        self.assertEqual(nico_dl.main([url, '--output-dir', str(root), *flags]), 0)
                        self.assertEqual(process.call_count, 2 if flags else 0)
                        if flags:
                            for source in sources:
                                process.assert_any_call(source, reencode=flags[0] == '--reencode',
                                                        crf=int(flags[-1]) if flags[0] == '--reencode' else 18)

    def test_manifest_batches_deduplicate_and_reject_escaping_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            sources = [root / 'one/source.mp4', root / 'two/source.mp4']
            args = nico_dl.parser().parse_args([next(iter(ROUTES))])
            for paths, valid in ((sources + sources, True), ([], False), ([root.parent / 'escape.mp4'], False)):
                with self.subTest(paths=paths):
                    (root / 'download-path.json').write_text('\n'.join(json.dumps(str(p)) for p in paths))
                    with patch('nico_dl.run'), patch('nico_dl.inspect_media'):
                        if valid:
                            self.assertEqual(nico_dl.download(args, root), sources)
                        else:
                            with self.assertRaises(nico_dl.DownloadError):
                                nico_dl.download(args, root)

    def test_traditional_channel_pagination_filters_links_and_deduplicates(self):
        first = '<a class="watchLink" href="https://www.nicovideo.jp/watch/so1">1</a>'
        first += '<a href="?sort=f&amp;page=2">next</a><a href="https://evil.test/?page=2">bad</a>'
        second = '<a class="watchLink" href="https://www.nicovideo.jp/watch/so1">duplicate</a>'
        second += '<a class="watchLink" href="https://www.nicovideo.jp/watch/so2">2</a><a href="?page=1">prev</a>'
        extractor = nico_backend.TraditionalChannelIE()
        with patch.object(extractor, '_download_webpage', side_effect=[first, second]) as download:
            entries = list(extractor._entries('https://ch.nicovideo.jp/ch2525/video', 'ch2525'))
        self.assertEqual([e['url'] for e in entries], ['https://www.nicovideo.jp/watch/so1', 'https://www.nicovideo.jp/watch/so2'])
        self.assertEqual(download.call_args_list[1].args[0], 'https://ch.nicovideo.jp/ch2525/video?sort=f&page=2')


if __name__ == '__main__':
    unittest.main()
