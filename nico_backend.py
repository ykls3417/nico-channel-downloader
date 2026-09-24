"""Restricted yt-dlp entry point, including traditional channel pagination."""

import argparse
from html.parser import HTMLParser
import sys
from urllib.parse import parse_qs, urljoin, urlsplit

import yt_dlp
from yt_dlp.downloader.niconico import NiconicoLiveFD
from yt_dlp.extractor.bilibili import BiliBiliIE
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.extractor.niconico import (
    NiconicoIE, NiconicoLiveIE, NiconicoPlaylistIE, NiconicoSeriesIE, NiconicoUserIE,
)
from yt_dlp.extractor.niconicochannelplus import (
    NiconicoChannelPlusIE, NiconicoChannelPlusChannelVideosIE, NiconicoChannelPlusChannelLivesIE,
)
from yt_dlp.extractor.youtube import YoutubeIE
from yt_dlp.utils import DownloadError, ExtractorError

from nico_urls import page_url


class ChannelLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.videos = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
            if 'watchLink' in attrs.get('class', '').split():
                self.videos.append(attrs['href'])


class TraditionalChannelIE(InfoExtractor):
    IE_NAME = 'niconico:channel'
    _VALID_URL = r'https://ch\.nicovideo\.jp/(?P<id>[\w-]+)/video(?:[?#]|$)'

    def _entries(self, url, channel):
        visited, videos = set(), set()
        while url and url not in visited:
            visited.add(url)
            webpage = self._download_webpage(url, channel)
            links = ChannelLinks()
            links.feed(webpage)
            if 'sensitiveContents' in webpage:
                self.report_warning('Some entries are hidden by account content settings; this list may be incomplete.')
            if not links.videos and len(visited) == 1:
                raise ExtractorError('No visible channel videos found. Check login, content settings, and the channel URL.', expected=True)
            for link in links.videos:
                try:
                    video = page_url(urljoin(url, link))
                except argparse.ArgumentTypeError as error:
                    raise ExtractorError('Channel contains an unsupported video link.', expected=True) from error
                if not NiconicoIE.suitable(video):
                    raise ExtractorError('Channel contains a non-video link.', expected=True)
                if video not in videos:
                    videos.add(video)
                    yield self.url_result(video, NiconicoIE)
            current = urlsplit(url)
            try:
                page = int(parse_qs(current.query).get('page', ['1'])[0])
            except ValueError as error:
                raise ExtractorError('Invalid channel page number.', expected=True) from error
            url = None
            for link in links.links:
                candidate = urljoin(current.geturl(), link)
                parts = urlsplit(candidate)
                if (parts.scheme == current.scheme and parts.netloc == current.netloc
                        and parts.path == current.path
                        and parse_qs(parts.query).get('page') == [str(page + 1)]):
                    url = candidate
                    break

    def _real_extract(self, url):
        channel = self._match_id(url)
        return self.playlist_result(self._entries(url, channel), channel, channel)


EXTRACTORS = (TraditionalChannelIE, NiconicoIE, NiconicoLiveIE, NiconicoPlaylistIE,
              NiconicoSeriesIE, NiconicoUserIE, NiconicoChannelPlusIE,
              NiconicoChannelPlusChannelVideosIE, NiconicoChannelPlusChannelLivesIE,
              YoutubeIE, BiliBiliIE)


class RestrictedDL(yt_dlp.YoutubeDL):
    def __init__(self, options):
        super().__init__(options, auto_init=False)
        for extractor in EXTRACTORS:
            self.add_info_extractor(extractor())

    def extract_info(self, url, *args, **kwargs):
        # Also validate playlist entries and extractor redirects; no generic fallback.
        try:
            url = page_url(url)
        except argparse.ArgumentTypeError as error:
            self.report_error(str(error))
            return None
        return super().extract_info(url, *args, **kwargs)

    def process_video_result(self, info_dict, download=True):
        # One quality scale for landscape videos and portrait Shorts.
        for fmt in info_dict.get('formats') or [info_dict]:
            width, height = fmt.get('width'), fmt.get('height')
            fmt['short_edge'] = min(width, height) if width and height else None
        return super().process_video_result(info_dict, download=download)

    def process_info(self, info_dict):
        if info_dict.get('extractor_key') == 'NiconicoLive' and info_dict.get('requested_formats'):
            # Let yt-dlp plan one simultaneous FFmpeg download, not sequential live tracks.
            info_dict['protocol'] = '+'.join('m3u8' for _ in info_dict['requested_formats'])
        return super().process_info(info_dict)

    def dl(self, name, info, subtitle=False, test=False):
        if info.get('extractor_key') == 'NiconicoLive' and info.get('requested_formats') and not subtitle and not test:
            # Preserve yt-dlp's Niconico websocket heartbeat while FFmpeg merges the tracks.
            downloader = NiconicoLiveFD(self, self.params)
            for hook in self._progress_hooks:
                downloader.add_progress_hook(hook)
            return downloader.download(name, self._copy_infodict(info))
        return super().dl(name, info, subtitle=subtitle, test=test)


def main(argv=None):
    options = yt_dlp.parse_options(argv)
    try:
        with RestrictedDL(options.ydl_opts) as downloader:
            return downloader.download(options.urls)
    except DownloadError:
        return 1


if __name__ == '__main__':
    sys.exit(main())
