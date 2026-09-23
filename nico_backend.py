"""Restricted yt-dlp entry point, including traditional channel pagination."""

import argparse
from html.parser import HTMLParser
import sys
from urllib.parse import parse_qs, urljoin, urlsplit

import yt_dlp
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.extractor.niconico import (
    NiconicoIE, NiconicoLiveIE, NiconicoPlaylistIE, NiconicoSeriesIE, NiconicoUserIE,
)
from yt_dlp.extractor.niconicochannelplus import (
    NiconicoChannelPlusIE, NiconicoChannelPlusChannelVideosIE, NiconicoChannelPlusChannelLivesIE,
)
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
              NiconicoChannelPlusChannelVideosIE, NiconicoChannelPlusChannelLivesIE)


class NiconicoDL(yt_dlp.YoutubeDL):
    def __init__(self, options):
        super().__init__(options, auto_init=False)
        for extractor in EXTRACTORS:
            self.add_info_extractor(extractor())

    def extract_info(self, url, *args, **kwargs):
        # Also validate playlist entries and extractor redirects; no generic fallback.
        try:
            url = page_url(url)
        except argparse.ArgumentTypeError as error:
            raise DownloadError(str(error)) from error
        return super().extract_info(url, *args, **kwargs)


def main(argv=None):
    options = yt_dlp.parse_options(argv)
    try:
        with NiconicoDL(options.ydl_opts) as downloader:
            return downloader.download(options.urls)
    except DownloadError:
        return 1


if __name__ == '__main__':
    sys.exit(main())
