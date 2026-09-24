"""Download Niconico, YouTube, or Bilibili videos and optionally process them with FFmpeg."""

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from nico_urls import default_referer, http_url, page_url


class DownloadError(Exception):
    """An expected download or media-processing failure."""


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("url", type=page_url, help="Niconico page, YouTube video/Shorts/live, or Bilibili video URL")
    result.add_argument("--output-dir", type=Path, default=Path.home() / "Downloads" / "nico")
    result.add_argument("--quality", choices=["1080", "720", "480", "best"], default="1080",
                        help="Maximum advertised shorter edge; default: 1080 (no upscaling)")
    auth = result.add_mutually_exclusive_group()
    auth.add_argument("--cookies", type=Path, help="Netscape-format cookies file")
    auth.add_argument("--cookies-from-browser", choices=["brave", "chrome", "chromium", "edge", "firefox", "safari"])
    result.add_argument("--referer", type=http_url, help="Allowed-site Referer override (default: selected service)")
    result.add_argument("--user-agent", help="Optional User-Agent matching your browser session")
    mode = result.add_mutually_exclusive_group()
    mode.add_argument("--clean", action="store_true", help="Remux into MKV, dropping copied metadata and chapters")
    mode.add_argument("--reencode", action="store_true", help="Re-encode H.264/AAC MP4 and drop copied metadata/chapters")
    result.add_argument("--crf", type=int, choices=range(0, 52), default=18, metavar="0..51")
    return result


def run(command: list[str], stage: str, *, capture: bool = False) -> str:
    # Isolate the whole downloader/FFmpeg tree so cancellation cannot leave it running.
    windows = os.name == 'nt'
    process = subprocess.Popen(command, encoding="utf-8", errors="replace",
                               stdout=subprocess.PIPE if capture else None,
                               stderr=subprocess.PIPE if capture else None,
                               start_new_session=not windows,
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if windows else 0)
    try:
        stdout, _ = process.communicate()
    except KeyboardInterrupt:
        if windows:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        finally:
            if not windows:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait()
        raise
    if process.returncode:
        # Do not include command arguments: they can contain signed URLs or cookies.
        raise DownloadError(f"{stage} failed (exit {process.returncode}). Original files are preserved.")
    return stdout or ""


def inspect_media(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise DownloadError("Media file is missing or empty.")
    try:
        info = json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                               "-show_chapters", "-of", "json", str(path)], "Media inspection", capture=True))
        duration = float(info["format"]["duration"])
        has_video = any(stream["codec_type"] == "video" for stream in info["streams"])
    except (ValueError, KeyError, TypeError) as error:
        raise DownloadError("Could not validate media duration and streams.") from error
    if not math.isfinite(duration) or duration <= 0 or not has_video:
        raise DownloadError("Expected a finite video with a positive duration.")
    return info


def download(args: argparse.Namespace, folder: Path) -> list[Path]:
    manifest = folder / "download-path.json"
    selection = "bv*+ba/b"
    if args.quality != "best":
        selection = f"bv*[short_edge<=?{args.quality}]+ba/b[short_edge<=?{args.quality}]"
    playlist = "--no-playlist" if urlsplit(args.url).hostname == 'www.youtube.com' else "--yes-playlist"
    command = [sys.executable, "-m", "nico_backend", "--ignore-config", playlist, "--abort-on-error",
               "--abort-on-unavailable-fragments", "--retries", "5", "--fragment-retries", "5",
               "--socket-timeout", "30", "--no-overwrites", "--referer", args.referer or default_referer(args.url),
               "--format", selection, "--merge-output-format", "mkv",
               "--output", str(folder / "%(extractor_key)s-%(id)s" / "source.%(ext)s"),
               "--print-to-file", "after_move:%(filepath)j", str(manifest)]
    if args.cookies:
        command.extend(["--cookies", str(args.cookies.expanduser().resolve())])
    if args.cookies_from_browser:
        command.extend(["--cookies-from-browser", args.cookies_from_browser])
    if args.user_agent:
        command.extend(["--user-agent", args.user_agent])
    run([*command, "--", args.url], "Download")
    try:
        paths = manifest.read_text(encoding="utf-8").splitlines()
        if not paths:
            raise ValueError("Empty collection")
        sources = list(dict.fromkeys(Path(json.loads(line)).resolve() for line in paths))
        if any(source.parent.parent != folder.resolve() for source in sources):
            raise ValueError("Unexpected output location")
    except (OSError, ValueError, TypeError) as error:
        raise DownloadError("Download did not produce valid output paths.") from error
    for source in sources:
        inspect_media(source)
    manifest.unlink()
    return sources


def process_media(source: Path, *, reencode: bool, crf: int = 18) -> Path:
    before = inspect_media(source)
    destination = source.parent / ("reencoded.mp4" if reencode else "cleaned.mkv")
    partial = destination.with_name(f"{destination.stem}.partial{destination.suffix}")
    if destination.exists() or partial.exists():
        raise DownloadError("Processed output already exists; refusing to overwrite it.")
    command = ["ffmpeg", "-hide_banner", "-nostdin", "-n", "-i", str(source),
               "-map", "0:v:0", "-map", "0:a?", "-map_metadata", "-1",
               "-map_metadata:s", "-1", "-map_chapters", "-1"]
    if reencode:
        command.extend(["-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart"])
    else:
        command.extend(["-c", "copy"])
    run([*command, str(partial)], "FFmpeg processing")
    after = inspect_media(partial)
    duration = float(before["format"]["duration"])
    if abs(float(after["format"]["duration"]) - duration) > max(2.0, duration * 0.01):
        raise DownloadError("Processed duration differs from the original. Both files are preserved.")
    before_audio = sum(stream["codec_type"] == "audio" for stream in before["streams"])
    after_audio = sum(stream["codec_type"] == "audio" for stream in after["streams"])
    if before_audio != after_audio:
        raise DownloadError("Processed audio stream count differs. Both files are preserved.")
    run(["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-i", str(partial),
         "-map", "0:v", "-map", "0:a?", "-f", "null", "-"], "Full decode validation", capture=True)
    partial.rename(destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    folder = None
    try:
        for executable in ("ffmpeg", "ffprobe"):
            if not shutil.which(executable):
                raise DownloadError(f"Install {executable} and make it available on PATH.")
        if urlsplit(args.url).hostname == 'www.youtube.com' and not shutil.which('deno'):
            raise DownloadError('YouTube requires Deno on PATH for JavaScript challenges. Install Deno, then retry.')
        if args.cookies and not args.cookies.expanduser().is_file():
            raise DownloadError("Cookies file does not exist.")
        root = args.output_dir.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        folder = Path(tempfile.mkdtemp(prefix="nico-", dir=root))
        print(f"Download folder: {folder}", flush=True)
        sources = download(args, folder)
        for source in sources:
            output = source
            if args.clean or args.reencode:
                print("Processing media. Metadata cleanup does not guarantee anonymity.", flush=True)
                output = process_media(source, reencode=args.reencode, crf=args.crf)
                print(f"Original preserved: {source}")
            print(f"Saved: {output}")
        return 0
    except (DownloadError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        if folder:
            print(f"Retained files: {folder}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"\nCancelled. Existing files are preserved{f' in {folder}' if folder else ''}.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
