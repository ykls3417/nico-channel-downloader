# Real-video audit — 2026-09-24/25

This audit used public content from the current sites on Linux with Python 3.12, yt-dlp 2026.8.19, Deno and FFmpeg. A supported URL is not a guarantee that the site will grant access. No personal browser profiles or account cookies were used.

## Bugs reproduced and fixed in 0.4.1

1. **Real Niconico Shorts were rejected.** `https://www.nicovideo.jp/shorts/ss46441082` failed URL validation in 0.4.0. Accept the actual `ss` prefix and the upstream-supported legacy `nl` prefix. The real Short now downloads successfully.
2. **Niconico live audio was recorded after video.** The default yt-dlp path downloaded the separate live tracks sequentially. The backend now plans a single FFmpeg download and delegates to yt-dlp's Niconico live downloader to retain its websocket heartbeat. The retest produced one file containing both video and audio.
3. **Cancellation could leave a downloader running.** An audio FFmpeg process continued after the original CLI exited. Commands now run in their own process group; cancellation stops the entire tree, allowing a brief graceful shutdown on POSIX before forced cleanup. Windows uses process-tree termination. Original files remain untouched; interrupted files are still not guaranteed playable.
4. **Rejected backend URLs failed silently.** Validation now uses yt-dlp's error reporter, so the reason appears on stderr.

The architecture remains three modules: URL validation, restricted extraction, and CLI/media processing. The live adapter reuses upstream streaming/heartbeat logic. No alternative downloader or browser-impersonation dependency was added: the impersonation experiment did not fix Bilibili's 412 response.

## Real-site results

| Content | Public sample | Result |
| --- | --- | --- |
| YouTube video | [jNQXAC9IVRw](https://www.youtube.com/watch?v=jNQXAC9IVRw) | Full download passed. |
| YouTube Short | [BGQWPY4IigY](https://www.youtube.com/shorts/BGQWPY4IigY) | Full downloads at all four quality settings; cleanup and MP4 conversion passed. |
| YouTube active live | [NASA ISS stream](https://www.youtube.com/live/M3HKLzjvKPc) | Recorded about 40 seconds with video and audio; cancellation returned 130 and retained the recording. |
| YouTube archived live | [qVv6vCqciTM](https://www.youtube.com/live/qVv6vCqciTM) | Metadata/formats extracted; this 74-minute recording was not downloaded in full. |
| Niconico regular | [sm9](https://www.nicovideo.jp/watch/sm9) | Full 320-second download and cleanup passed. |
| Niconico older video | [nm14296458](https://www.nicovideo.jp/watch/nm14296458) | Full 209-second download passed. |
| Niconico legacy channel | [nl1872567](https://www.nicovideo.jp/watch/nl1872567) | Full download passed after accepting the prefix. |
| Niconico Short | [ss46441082](https://www.nicovideo.jp/shorts/ss46441082) | Full 15-second downloads at all four quality settings; cleanup and conversion passed after the fix. |
| Traditional channel video | [so46803052](https://www.nicovideo.jp/watch/so46803052) | Full 30-second download and cleanup passed. |
| Traditional channel collection | [ch2525/video](https://ch.nicovideo.jp/ch2525/video) | First two items downloaded and cleaned in separate folders. |
| User collection | [user/141907929/video](https://www.nicovideo.jp/user/141907929/video) | First two items downloaded and cleaned in separate folders. |
| Mylist | [27411728](https://www.nicovideo.jp/mylist/27411728) | First two entries enumerated; media not downloaded in this audit. |
| Series | [12312](https://www.nicovideo.jp/series/12312) | First two entries enumerated; media not downloaded in this audit. |
| Niconico active live | [lv351173788](https://live.nicovideo.jp/watch/lv351173788) | After the live fix, recorded about 36 seconds with video and audio together; cancellation returned 130. |
| Niconico restricted channel video | [so41370536](https://www.nicovideo.jp/watch/so41370536) | Site required membership; authenticated access not tested. |
| Old Niconico live/timeshift | [lv331050399](https://live.nicovideo.jp/watch/lv331050399) | No usable websocket URL; playback not verified. |
| Channel Plus | [kaorin video](https://nicochannel.jp/kaorin/video/smsDd8EdFLcVZk9yyAhD6H7H), [testman/videos](https://nicochannel.jp/testman/videos), [testman/lives](https://nicochannel.jp/testman/lives) | Blocked by DNS failure for upstream `nfc-api.nicochannel.jp`; a public DNS query also returned NXDOMAIN. |
| Bilibili video / multipart | [BV13x41117TL](https://www.bilibili.com/video/BV13x41117TL), [BV1bK411W797?p=2](https://www.bilibili.com/video/BV1bK411W797?p=2) | HTTP 412. Explicit Referer/User-Agent and an isolated curl-cffi browser-impersonation trial also failed. Real downloads remain unverified. |

Collection media tests inserted yt-dlp's `--playlist-end 2` through a test harness to keep the audit bounded; this is not a new public CLI option. No entire channel or user library was downloaded. Live tests sent an interrupt after 35 seconds of wall time; HLS buffering means the recorded duration differs. Both retained live recordings subsequently passed manual cleanup and H.264/AAC conversion, with both streams preserved and full decode validation. Processing was invoked separately after cancellation. They do not verify natural broadcast completion or long-running stability.

## Parameter coverage

| Parameter | Evidence and limits |
| --- | --- |
| Default settings | Real YouTube download passed. Default/tilde destination handling is also covered by automated CLI tests. |
| `--quality 480/720/1080/best` | Real YouTube and Niconico Shorts downloaded for every choice. Outputs stayed within the selected shorter-edge cap. These samples top out at 720×1280; the 1080 choice correctly falls back. Synthetic HLS tests additionally exercise 1080 and 1440 sources. |
| `--output-dir` | Real downloads used paths containing spaces and Japanese characters. |
| `--clean` | Real ordinary videos, Shorts and collection entries remuxed successfully, with original files retained. |
| `--reencode` | Real Shorts converted to H.264/AAC MP4 and passed full decode validation. |
| `--crf 0/18/51` | Complete real Shorts tested at the boundary/default values. |
| All `--crf 0..51` values | Every value passed conversion and full decoding on a one-second sample cut from downloaded YouTube footage; originals were preserved. Automated tests also cover every value. |
| `--cookies FILE` | Real public downloads accepted a valid empty Netscape cookie file. This tests the file option, not authenticated access. Controlled HLS tests separately enforce an actual synthetic cookie. |
| `--cookies-from-browser` | All six choices are parsed and forwarded in automated tests; Firefox extraction is tested with an isolated synthetic profile. Personal signed-in/encrypted browser stores were not tested. |
| `--referer`, `--user-agent` | Explicit values passed on real YouTube and Niconico Short downloads. Controlled HLS tests verify the headers reach both manifests and media segments. |
| `--help`, invalid/conflicting options | Automated CLI checks; no network or FFmpeg needed for help. |
| Ctrl+C | Real live tests and a child/grandchild regression test verify cancellation and process cleanup. Processing is not automatically started after cancellation. |

Do not interpret these results as proof that every URL, account, browser or paid format works. Live URLs and site policies can change after this audit. All 36 automated tests passed locally after the fixes. The automated suite runs against the installed wheel on Linux, macOS and Windows; real-site checks above were performed on Linux.
