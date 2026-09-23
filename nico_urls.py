"""Accepted Niconico page URLs; media CDN requests are handled by yt-dlp."""

import argparse
import re
from urllib.parse import urlsplit, urlunsplit


VIDEO_HOSTS = {'nicovideo.jp', 'www.nicovideo.jp', 'sp.nicovideo.jp', 'embed.nicovideo.jp'}
LIVE_HOSTS = {'live.nicovideo.jp', 'live2.nicovideo.jp', 'sp.live.nicovideo.jp', 'sp.live2.nicovideo.jp'}
ALLOWED_HOSTS = VIDEO_HOSTS | LIVE_HOSTS | {'ch.nicovideo.jp', 'nicochannel.jp'}


def http_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        valid = (parts.scheme in {'http', 'https'} and parts.hostname in ALLOWED_HOSTS
                 and parts.username is None and parts.password is None
                 and parts.port in {None, 80 if parts.scheme == 'http' else 443})
    except ValueError:
        valid = False
    if not valid or any(c.isspace() or ord(c) < 32 or c == '\\' for c in value):
        raise argparse.ArgumentTypeError('Use an HTTP(S) URL on an allowed Niconico host, without credentials or custom ports.')
    return value


def page_url(value: str) -> str:
    parts = urlsplit(http_url(value))
    host, path = parts.hostname, parts.path.rstrip('/')
    if host in VIDEO_HOSTS:
        host = 'www.nicovideo.jp'
        pattern = (r'/(?:watch|shorts)/(?:sm|nm|so)?\d+'
                   r'|/(?:user/\d+/)?(?:my/)?mylist/\d+'
                   r'|/(?:user/\d+/)?series/\d+|/user/\d+(?:/video)?')
    elif host in LIVE_HOSTS:
        host = host.removeprefix('sp.')
        pattern = r'/(?:watch|gate)/lv\d+'
    elif host == 'nicochannel.jp':
        pattern = r'/[\w.-]+/(?:video/sm\w+|live/sm\w+|videos|lives)'
    else:
        pattern = r'/[\w-]+(?:/video)?'
        if re.fullmatch(pattern, path) and path.count('/') == 1:
            path += '/video'
    if not re.fullmatch(pattern, path):
        raise argparse.ArgumentTypeError('Unsupported Niconico page. Use a watch, Shorts, live, mylist, series, user-video, or channel video/list URL.')
    return urlunsplit(('https', host, path, parts.query, parts.fragment))


def default_referer(url: str) -> str:
    host = urlsplit(url).hostname
    if host == 'nicochannel.jp':
        return 'https://nicochannel.jp/'
    if host in LIVE_HOSTS:
        return 'https://live.nicovideo.jp/'
    return 'https://www.nicovideo.jp/'
