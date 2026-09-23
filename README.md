# Nico Channel Downloader

**Download Niconico videos from your terminal. No Git clone or project setup needed.**

**English** · [繁體中文](https://github.com/ykls3417/nico-channel-downloader/blob/main/README.zh-TW.md) · [日本語](https://github.com/ykls3417/nico-channel-downloader/blob/main/README.ja.md)

Works with regular videos, Shorts, Channel Plus, supported live streams, and video collections. Optional FFmpeg processing can remove copied metadata or create H.264/AAC MP4 files. Originals are always kept. This is an independent, MIT-licensed project.

## 1. Install the requirements

You need **Python 3.10+**, **pipx**, and **FFmpeg / ffprobe**. pipx installs the command in its own environment; FFmpeg is installed separately.

| Your system | Setup |
| --- | --- |
| Ubuntu / Debian | Run `sudo apt install pipx ffmpeg`, then `pipx ensurepath`. |
| macOS with Homebrew | Run `brew install pipx ffmpeg`, then `pipx ensurepath`. |
| Windows | Install [Python](https://www.python.org/downloads/windows/). Run `py -m pip install --user pipx` and `py -m pipx ensurepath`. Install an FFmpeg build from the [FFmpeg download page](https://ffmpeg.org/download.html), and add its `bin` folder to PATH. |

Reopen your terminal after setup. Check that `pipx --version`, `ffmpeg -version`, and `ffprobe -version` work. Re-encoding needs an FFmpeg build with `libx264`. See [pipx installation help](https://pipx.pypa.io/latest/how-to/install-pipx.html) for other systems.

## 2. Install the app

Install the versioned wheel directly from GitHub:

```sh
pipx install https://github.com/ykls3417/nico-channel-downloader/releases/download/v0.3.0/nico_channel_downloader-0.3.0-py3-none-any.whl
nico-dl --help
```

The same package works on Windows, macOS, and Linux. Run `nico-dl` from any folder; you do not need to activate a virtual environment.

**PyPI status:** publishing is prepared but requires the maintainer's PyPI account setup. Until a PyPI release is available, use the GitHub command above. The short command `pipx install nico-channel-downloader` is for after publication.

## 3. Download a video

Replace the URL with the video you want:

```sh
nico-dl "https://www.nicovideo.jp/watch/sm9"
```

Default: download up to the advertised **1080p** resolution into **`~/Downloads/nico`** (`Downloads\nico` under your Windows user folder).

Common examples:

```sh
# Use your signed-in browser for content your account can access.
nico-dl "YOUR_NICONICO_URL" --cookies-from-browser firefox

# Choose the quality and destination.
nico-dl "YOUR_NICONICO_URL" --quality 720 --output-dir "./videos"

# Remove copied metadata and chapters without re-encoding (MKV).
nico-dl "YOUR_NICONICO_URL" --clean

# Re-encode to H.264/AAC MP4 and remove copied metadata/chapters.
nico-dl "YOUR_NICONICO_URL" --reencode --crf 18
```

Use a real supported page URL in place of `YOUR_NICONICO_URL`. Login headers or cookies do not grant access your account does not have.

## Supported URLs

The IDs below illustrate URL shapes; replace them with real IDs.

| Content | URL shape |
| --- | --- |
| Regular / older / channel video | `https://www.nicovideo.jp/watch/sm123` — also `nm123`, `so123`, numeric IDs |
| Shorts | `https://www.nicovideo.jp/shorts/sm123` |
| Niconico Live | `https://live.nicovideo.jp/watch/lv123` — also `/gate/lv123` |
| Channel Plus video / live | `https://nicochannel.jp/CHANNEL/video/smCODE` or `/live/smCODE` |
| Mylist / series | `https://www.nicovideo.jp/mylist/123` or `/series/123` |
| User uploads | `https://www.nicovideo.jp/user/123/video` — user root also accepted |
| Traditional channel collection | `https://ch.nicovideo.jp/CHANNEL/video` — channel root also accepted |
| Channel Plus collections | `https://nicochannel.jp/CHANNEL/videos` or `/lives` |

Collections download all visible entries, following pagination. Each video gets a separate folder. Channel Plus `/lives` lists archived broadcasts.

Input hosts are restricted to `nicovideo.jp`, `www.nicovideo.jp`, `sp.nicovideo.jp`, `embed.nicovideo.jp`, `ch.nicovideo.jp`, `live.nicovideo.jp`, `live2.nicovideo.jp`, `sp.live.nicovideo.jp`, `sp.live2.nicovideo.jp`, and `nicochannel.jp`. Other sites, `nico.ms` short links, custom Channel Plus domains, direct `.m3u8` URLs, and unsupported paths are rejected. Required media CDN/API requests may use other hosts.

## Options at a glance

All options apply to the supported URL types above.

| Option | Meaning |
| --- | --- |
| `--quality 1080` | Maximum advertised height: `1080` (default), `720`, `480`, or `best`. Never upscales; unknown heights are allowed. |
| `--output-dir PATH` | Download location. Default: `~/Downloads/nico`. |
| `--cookies-from-browser NAME` | Use `brave`, `chrome`, `chromium`, `edge`, `firefox`, or `safari` cookies. Availability depends on your OS/browser. |
| `--cookies FILE` | Use a Netscape-format cookie file instead of browser extraction. |
| `--clean` | Remux to MKV, removing copied metadata and chapters. |
| `--reencode` | Convert to H.264/AAC MP4, removing copied metadata and chapters. |
| `--crf 18` | Re-encoding quality, `0`–`51`. Lower usually means higher quality and larger files. Ignored without `--reencode`. |
| `--referer URL` | Override the automatic service Referer with an allowed Niconico URL. |
| `--user-agent TEXT` | Override User-Agent when needed for your session. |
| `-h`, `--help` | Show command help. |

Choose either `--cookies` or `--cookies-from-browser`, and either `--clean` or `--reencode`.

## Your files and important limits

- Each run creates `nico-*/EXTRACTOR-ID/source.*`. Processed files appear beside it as `cleaned.mkv` or `reencoded.mp4`. The source is never deleted.
- Processing checks duration, audio track count, and full decoding before publishing the final output. It keeps the first video track and all audio tracks; subtitles and attachments are omitted.
- A collection stops at the first download error. Processing starts after the whole download succeeds. Earlier source files remain if a later item fails. There is no automatic resume between runs.
- Live recording continues until the broadcast ends or you press Ctrl+C. Processing runs after a completed recording. Partial files may not be playable. Timeshift/archive access depends on the service, yt-dlp, and your account; it is not guaranteed.
- **Metadata cleanup and re-encoding do not guarantee anonymity or remove forensic watermarks.** Encoders may add technical tags, and re-encoding can reduce quality.
- Use content you have permission to download. This app does not remove DRM. Keep cookies and signed URLs private; redact logs before sharing them.

## Update, remove, or troubleshoot

For a new version, copy its wheel URL from [Releases](https://github.com/ykls3417/nico-channel-downloader/releases) and run `pipx install --force "NEW_WHEEL_URL"`. A versioned URL stays on that version. After installing from PyPI, use `pipx upgrade nico-channel-downloader` instead.

```sh
# Update the site extractor independently when a website changes.
pipx runpip nico-channel-downloader install --upgrade "yt-dlp[default]"

# Remove the app (your downloaded videos remain).
pipx uninstall nico-channel-downloader
```

| Problem | Try this |
| --- | --- |
| `nico-dl` is not found | Run `pipx ensurepath`, reopen the terminal, then check `pipx list`. |
| FFmpeg / ffprobe is missing | Install both tools and add their folder to PATH. |
| Login or cookie extraction fails | Check browser login and account access; try `--cookies FILE`. Safari requires macOS. Browser encryption/keyrings can prevent extraction. |
| Unsupported URL | Use a full page URL from the table above. |
| A video or live stream is unavailable | Check it in your browser. Deleted, upcoming, expired, region-restricted, or account-restricted content may be unavailable. |

[Report a problem](https://github.com/ykls3417/nico-channel-downloader/issues) with your OS, Python, yt-dlp and FFmpeg versions, plus redacted error output. For development, testing, and publishing instructions, see [DEVELOPMENT.md](https://github.com/ykls3417/nico-channel-downloader/blob/main/DEVELOPMENT.md).
