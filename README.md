# Nico Channel Downloader

A small Python CLI for downloading individual Nico Channel Plus videos through
[yt-dlp](https://github.com/yt-dlp/yt-dlp), with optional FFmpeg metadata cleanup
and H.264/AAC re-encoding. MIT licensed. This is an independent project.

## Install

Requires Python 3.10+, FFmpeg and ffprobe on your PATH. Re-encoding also requires
an FFmpeg build with the `libx264` encoder.

```bash
git clone https://github.com/ykls3417/nico-channel-downloader.git
cd nico-channel-downloader
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
nico-dl --help
```

On Ubuntu/Debian, install media tools with `sudo apt install ffmpeg`.
On macOS with Homebrew, use `brew install python ffmpeg`.

### Windows (PowerShell)

Install Python 3.10+ and a Windows FFmpeg build linked from the
[FFmpeg download page](https://ffmpeg.org/download.html). Add the folder containing
`ffmpeg.exe` and `ffprobe.exe` to PATH, then reopen PowerShell. Git is optional:
GitHub's **Code → Download ZIP** also provides the project source.

```powershell
git clone https://github.com/ykls3417/nico-channel-downloader.git
cd nico-channel-downloader
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\nico-dl.exe --help
.\.venv\Scripts\nico-dl.exe 'YOUR_VIDEO_URL' --reencode
```

These commands do not require activating PowerShell scripts or changing execution
policy. Python and FFmpeg must be installed on each machine; this version is not
a standalone executable. Copy/clone the source, then create a new virtual environment
on each machine instead of copying `.venv` across operating systems.

### Browser independence

No browser is required for a direct URL that works without cookies. When authentication
is needed, choose the browser you actually use on that machine:

```bash
nico-dl 'YOUR_VIDEO_URL' --cookies-from-browser firefox
nico-dl 'YOUR_VIDEO_URL' --cookies-from-browser chrome
nico-dl 'YOUR_VIDEO_URL' --cookies-from-browser edge
nico-dl 'YOUR_VIDEO_URL' --cookies '/path/to/cookies.txt'
```

Brave, Chromium and Safari are also accepted. Availability depends on the OS and
browser: Safari is a macOS option, and browser cookie extraction can fail because
of locked databases, OS keyrings, or cookie encryption. We delegate extraction to
yt-dlp; accepting a browser option does not guarantee every browser/OS combination.
Use a local authenticated session or a Netscape-format cookie file as appropriate.
See [yt-dlp's cookie guidance](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp).
Do not put cookies in the public repository.

## Use

Replace the example URL with an individual video page or a current `.m3u8` URL:

```bash
# Download without re-encoding (default: up to advertised 1080p).
nico-dl 'https://nicochannel.jp/CHANNEL/video/VIDEO_ID'

# Use your existing authenticated browser session when needed.
nico-dl 'https://nicochannel.jp/CHANNEL/video/VIDEO_ID' --cookies-from-browser brave

# Remove copied metadata and chapters without re-encoding; output is MKV.
nico-dl 'https://example.com/video.m3u8' --clean

# Re-encode to H.264/AAC MP4, also removing copied metadata and chapters.
nico-dl 'https://example.com/video.m3u8' --reencode --crf 18

# Choose another quality cap and download location.
nico-dl 'https://example.com/video.m3u8' --quality 720 --output-dir ./downloads
```

`--cookies PATH` accepts a Netscape-format cookies file instead of browser cookies.
`--referer` defaults to `https://nicochannel.jp/`; `--user-agent` allows a session-specific
override. Headers do not replace authentication. Expired signed URLs need to be
obtained again from your authorized session. Support for video-page login depends
on the installed yt-dlp extractor; cookies alone may not satisfy every login flow.

Each run creates a unique `nico-*` directory inside `~/Downloads/nico` by default.
The downloaded `source.*` is always retained, including after successful processing.
Processed files are named `cleaned.mkv` or `reencoded.mp4`. Conversion writes to a
partial file first, checks duration and audio stream count, and decodes the full
result before promoting it to its final name. This extra decode pass takes time.
Failures and interruptions preserve files and return a nonzero exit status.
There is no automatic cross-run resume yet.

The quality setting caps **advertised** resolution, allows unknown heights, and
never upscales. A direct media playlist may lack resolution metadata; the cap cannot
be guaranteed in that case. `--quality best` removes the cap. Channel lists, batches,
and live recording are outside this initial version's scope. Processing keeps the
first video and all audio tracks; subtitles, attachments and data tracks are omitted.

## What “clean” means

`--clean` and `--reencode` disable copying global/stream metadata and chapters using
[FFmpeg's metadata mapping options](https://ffmpeg.org/ffmpeg.html#Metadata).
The output container and encoders can still generate technical tags.
Re-encoding changes the compressed video/audio and can reduce quality even at CRF 18.

**Neither mode guarantees an untraceable file.** Re-encoding is not a reliable
method to eliminate forensic watermarks or identifiers embedded in picture/audio,
and local processing does not change server-side access records. This project does
not detect or certify the absence of such identifiers. 二次轉碼不等於無痕；清除一般
metadata 並不能保證去除浮水印或帳戶相關指紋。

Use content you have permission to download. The tool relies on yt-dlp's supported
access methods and does not implement DRM removal. Do not commit cookies, media,
or signed URLs. Upstream downloader output may contain URLs: redact logs before
sharing them. Command-line URLs may also be retained by your shell history.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The tests generate tiny media fixtures and serve HLS on localhost; they do not use
a Nico account. They exercise actual downloading, metadata cleanup, re-encoding,
failure preservation, and refusal to overwrite existing output. FFmpeg/ffprobe are
required; integration tests skip when these tools are unavailable. Live Nico Channel
authentication and downloads still need verification with a real authorized URL.

CI runs the same media integration tests on Linux, Windows and macOS, and fails
early if FFmpeg tools are missing. Fixtures use paths containing spaces and Japanese
characters. Linux also tests Python 3.10, 3.12 and 3.13. Check the repository's Actions
results for actual platform verification; a configured matrix is not a passing run.
CI does not test account login or access to your browser's encrypted cookie store.

### Parameter coverage

`tests/test_parameters.py` adds the following checks to the original media tests:

| Parameter | Automated verification |
| --- | --- |
| URL | Invalid inputs, signed query preservation, real local HLS downloads |
| `-h`, `--help` | Successful exit, all options listed, no download |
| `--output-dir` | Default home directory, absolute/relative/tilde paths, spaces, Japanese characters, existing-file error |
| `--quality` | All four choices, actual 480/720/1080/1440-height HLS variants, invalid choice |
| `--cookies` | Real cookie-protected local download, missing/directory/malformed files, authentication-option conflict |
| `--cookies-from-browser` | All six browser names forwarded and accepted by yt-dlp; real extraction from an isolated synthetic Firefox database; simulated extraction errors |
| `--referer` | Header verified on playlists and segments; server denies access when omitted; invalid URL |
| `--user-agent` | Header verified on playlists and segments; server denies access when omitted |
| `--clean` | Real remux, metadata/chapter removal, original preservation, conflicting mode |
| `--reencode` | Real H.264/AAC conversion, full decode validation, original preservation, conflicting mode |
| `--crf` | All integers 0–51 parsed, forwarded and encoded by FFmpeg; CLI boundary values; invalid/out-of-range values |

All value-taking options are tested for missing arguments. CRF only affects
`--reencode`; it has no effect on a plain download or `--clean`.
The synthetic Firefox test never reads your personal browser profile. Real Nico
account access and Chromium/Safari OS-protected cookie extraction remain outside
automated coverage; no live-account compatibility claim is implied by passing CI.

For site extraction fixes, update yt-dlp with `python -m pip install -U yt-dlp`.
Please include Python, yt-dlp and FFmpeg versions with bug reports, and remove
credentials and signed URL query parameters from logs.
