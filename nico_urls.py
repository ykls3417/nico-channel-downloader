"""Accepted video page URLs; media CDN requests are handled by yt-dlp."""

import argparse
import re
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit


VIDEO_HOSTS = {'nicovideo.jp', 'www.nicovideo.jp', 'sp.nicovideo.jp', 'embed.nicovideo.jp'}
LIVE_HOSTS = {'live.nicovideo.jp', 'live2.nicovideo.jp', 'sp.live.nicovideo.jp', 'sp.live2.nicovideo.jp'}
YOUTUBE_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'}
BILIBILI_HOSTS = {'bilibili.com', 'www.bilibili.com', 'm.bilibili.com'}
ALLOWED_HOSTS = VIDEO_HOSTS | LIVE_HOSTS | YOUTUBE_HOSTS | BILIBILI_HOSTS | {'ch.nicovideo.jp', 'nicochannel.jp'}


def http_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        valid = (parts.scheme in {'http', 'https'} and parts.hostname in ALLOWED_HOSTS
                 and parts.username is None and parts.password is None
                 and parts.port in {None, 80 if parts.scheme == 'http' else 443})
    except ValueError:
        valid = False
    if not valid or any(c.isspace() or ord(c) < 32 or c == '\\' for c in value):
        raise argparse.ArgumentTypeError('Use an HTTP(S) URL on an allowed Niconico, YouTube, or Bilibili host, without credentials or custom ports.')
    return value


def page_url(value: str) -> str:
    parts = urlsplit(http_url(value))
    host, path = parts.hostname, parts.path.rstrip('/')
    if host in YOUTUBE_HOSTS:
        query = parse_qs(parts.query, keep_blank_values=True)
        if host == 'youtu.be':
            video_id = path.removeprefix('/')
        elif path == '/watch' and len(query.get('v', [])) == 1:
            video_id = query['v'][0]
        elif re.fullmatch(r'/(?:shorts|live|embed)/[\w-]{11}', path):
            video_id = path.rsplit('/', 1)[1]
        else:
            video_id = ''
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            raise argparse.ArgumentTypeError('Use a YouTube watch, Shorts, live, embed, or youtu.be video URL.')
        # Drop playlist and tracking parameters: these routes always select one video.
        return f'https://www.youtube.com/watch?v={video_id}'
    if host in BILIBILI_HOSTS:
        if not re.fullmatch(r'/video/(?:BV[A-Za-z0-9]{10}|av\d+)', path):
            raise argparse.ArgumentTypeError('Use a Bilibili /video/BV... or /video/av... URL.')
        query = parse_qs(parts.query, keep_blank_values=True)
        part = query.get('p')
        if part is not None and (len(part) != 1 or not re.fullmatch(r'[1-9]\d*', part[0])):
            raise argparse.ArgumentTypeError('Bilibili p must be one positive part number.')
        return urlunsplit(('https', 'www.bilibili.com', path, urlencode({'p': part[0]}) if part else '', ''))
    if host in VIDEO_HOSTS:
        host = 'www.nicovideo.jp'
        pattern = (r'/(?:watch|shorts)/(?:sm|nm|so|ss|nl)?\d+'
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
    if host in YOUTUBE_HOSTS:
        return 'https://www.youtube.com/'
    if host in BILIBILI_HOSTS:
        return 'https://www.bilibili.com/'
    if host == 'nicochannel.jp':
        return 'https://nicochannel.jp/'
    if host in LIVE_HOSTS:
        return 'https://live.nicovideo.jp/'
    return 'https://www.nicovideo.jp/'
