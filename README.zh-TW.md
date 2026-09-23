# Nico Channel Downloader

**在終端機下載 Niconico 影片，無需複製 Git 儲存庫或自行設定專案。**

[English](https://github.com/ykls3417/nico-channel-downloader/blob/main/README.md) · **繁體中文** · [日本語](https://github.com/ykls3417/nico-channel-downloader/blob/main/README.ja.md)

支援一般影片、Shorts、Channel Plus、可存取的直播及影片清單。可選擇使用 FFmpeg 清除複製的中繼資料，或轉成 H.264/AAC MP4。原始檔案一律保留。本工具是採用 MIT 授權的非官方專案。

## 1. 安裝所需工具

需要 **Python 3.10 以上版本**、**pipx**、**FFmpeg 與 ffprobe**。pipx 會在獨立環境安裝指令；FFmpeg 需另外安裝。

| 作業系統 | 設定方法 |
| --- | --- |
| Ubuntu / Debian | 執行 `sudo apt install pipx ffmpeg`，再執行 `pipx ensurepath`。 |
| macOS（使用 Homebrew） | 執行 `brew install pipx ffmpeg`，再執行 `pipx ensurepath`。 |
| Windows | 安裝 [Python](https://www.python.org/downloads/windows/)，執行 `py -m pip install --user pipx` 及 `py -m pipx ensurepath`。從 [FFmpeg 下載頁面](https://ffmpeg.org/download.html) 取得 Windows 版本，並將其 `bin` 資料夾加入 PATH。 |

完成後重新開啟終端機，確認 `pipx --version`、`ffmpeg -version` 及 `ffprobe -version` 均能執行。重新編碼需要含有 `libx264` 的 FFmpeg。其他系統請參閱 [pipx 安裝說明](https://pipx.pypa.io/latest/how-to/install-pipx.html)。

## 2. 安裝程式

直接從 GitHub 安裝指定版本的套件：

```sh
pipx install https://github.com/ykls3417/nico-channel-downloader/releases/download/v0.3.0/nico_channel_downloader-0.3.0-py3-none-any.whl
nico-dl --help
```

同一套件可用於 Windows、macOS 和 Linux。安裝後可在任何資料夾執行 `nico-dl`，無需啟用虛擬環境。

**PyPI 狀態：**發布流程已準備好，但仍需維護者完成 PyPI 帳戶設定。在 PyPI 版本上架前，請使用上面的 GitHub 指令；`pipx install nico-channel-downloader` 短指令需在上架後才可使用。

## 3. 下載影片

將網址換成你想下載的影片：

```sh
nico-dl "https://www.nicovideo.jp/watch/sm9"
```

預設下載最高標示為 **1080p** 的版本，儲存至 **`~/Downloads/nico`**（Windows 為使用者資料夾內的 `Downloads\nico`）。

常用例子：

```sh
# 使用已登入的瀏覽器，存取帳戶有權觀看的內容。
nico-dl "YOUR_NICONICO_URL" --cookies-from-browser firefox

# 選擇畫質及儲存位置。
nico-dl "YOUR_NICONICO_URL" --quality 720 --output-dir "./videos"

# 不重新編碼，清除複製的中繼資料與章節，輸出 MKV。
nico-dl "YOUR_NICONICO_URL" --clean

# 轉成 H.264/AAC MP4，同時清除複製的中繼資料與章節。
nico-dl "YOUR_NICONICO_URL" --reencode --crf 18
```

請把 `YOUR_NICONICO_URL` 換成支援的實際頁面網址。Cookies 或請求標頭不會讓帳戶取得原本沒有的觀看權限。

## 支援的網址

下列 ID 僅用來說明格式，使用時請換成實際 ID。

| 內容 | 網址格式 |
| --- | --- |
| 一般／舊版／頻道影片 | `https://www.nicovideo.jp/watch/sm123`；也接受 `nm123`、`so123` 及純數字 ID |
| Shorts | `https://www.nicovideo.jp/shorts/sm123` |
| Niconico Live | `https://live.nicovideo.jp/watch/lv123`；也接受 `/gate/lv123` |
| Channel Plus 影片／直播 | `https://nicochannel.jp/CHANNEL/video/smCODE` 或 `/live/smCODE` |
| Mylist／系列 | `https://www.nicovideo.jp/mylist/123` 或 `/series/123` |
| 使用者投稿 | `https://www.nicovideo.jp/user/123/video`；也接受使用者首頁 |
| 傳統頻道影片清單 | `https://ch.nicovideo.jp/CHANNEL/video`；也接受頻道首頁 |
| Channel Plus 清單 | `https://nicochannel.jp/CHANNEL/videos` 或 `/lives` |

清單會逐頁下載所有可見項目，每部影片使用獨立資料夾。Channel Plus 的 `/lives` 列出直播存檔。

輸入網址僅允許 `nicovideo.jp`、`www.nicovideo.jp`、`sp.nicovideo.jp`、`embed.nicovideo.jp`、`ch.nicovideo.jp`、`live.nicovideo.jp`、`live2.nicovideo.jp`、`sp.live.nicovideo.jp`、`sp.live2.nicovideo.jp` 及 `nicochannel.jp`。其他網站、`nico.ms` 短網址、自訂 Channel Plus 網域、直接 `.m3u8` 網址及不支援的路徑均會被拒絕。播放所需的 CDN／API 請求可能使用其他網域。

## 參數速查

以下參數適用於上列支援的網址類型。

| 參數 | 用途 |
| --- | --- |
| `--quality 1080` | 最高標示高度：`1080`（預設）、`720`、`480` 或 `best`。不放大影片；允許高度未知的格式。 |
| `--output-dir PATH` | 儲存位置，預設 `~/Downloads/nico`。 |
| `--cookies-from-browser NAME` | 使用 `brave`、`chrome`、`chromium`、`edge`、`firefox` 或 `safari` 的 Cookies；可用性取決於系統及瀏覽器。 |
| `--cookies FILE` | 改用 Netscape 格式的 Cookie 檔案。 |
| `--clean` | 封裝成 MKV，清除複製的中繼資料與章節。 |
| `--reencode` | 轉成 H.264/AAC MP4，清除複製的中繼資料與章節。 |
| `--crf 18` | 重新編碼品質，範圍 `0`–`51`。數值較低通常畫質較高、檔案較大；只在 `--reencode` 模式生效。 |
| `--referer URL` | 以允許的 Niconico 網址覆寫自動選擇的 Referer。 |
| `--user-agent TEXT` | 有需要時指定符合登入工作階段的 User-Agent。 |
| `-h`、`--help` | 顯示指令說明。 |

`--cookies` 與 `--cookies-from-browser` 只能擇一；`--clean` 與 `--reencode` 也只能擇一。

## 檔案與使用限制

- 每次執行建立 `nico-*/EXTRACTOR-ID/source.*`。處理後的 `cleaned.mkv` 或 `reencoded.mp4` 位於同一資料夾，原始檔不會被刪除。
- 輸出前會檢查時長、音軌數量並完整解碼。保留第一條視訊軌及所有音軌，不保留字幕或附件。
- 清單遇到第一個下載錯誤即停止；全部下載成功後才開始處理。後續項目失敗時，先前下載的原始檔仍會保留。目前不支援不同執行之間自動續傳。
- 直播會錄製至結束或按下 Ctrl+C。完成錄製後才進行處理；中斷留下的部分檔案不保證可播放。時移／存檔是否可下載取決於網站、yt-dlp 及帳戶權限。
- **清除中繼資料或重新編碼不保證匿名，也不保證去除鑑識浮水印。**編碼器可能新增技術標籤，重新編碼也可能降低畫質。
- 僅下載你有權下載的內容。本工具不移除 DRM。請勿公開 Cookies、帶簽章的網址或未遮蔽敏感資料的日誌。

## 更新、移除與疑難排解

從 [Releases](https://github.com/ykls3417/nico-channel-downloader/releases) 複製新版 wheel 網址，再執行 `pipx install --force "NEW_WHEEL_URL"`。指定版本的網址不會自動切換版本。若日後改由 PyPI 安裝，可使用 `pipx upgrade nico-channel-downloader`。

```sh
# 網站改版時，可單獨更新解析工具。
pipx runpip nico-channel-downloader install --upgrade "yt-dlp[default]"

# 移除程式；已下載的影片仍會保留。
pipx uninstall nico-channel-downloader
```

| 問題 | 處理方法 |
| --- | --- |
| 找不到 `nico-dl` | 執行 `pipx ensurepath`，重新開啟終端機，再檢查 `pipx list`。 |
| 找不到 FFmpeg／ffprobe | 安裝兩者並將所在資料夾加入 PATH。 |
| 登入或 Cookies 擷取失敗 | 確認瀏覽器登入及觀看權限，或改用 `--cookies FILE`。Safari 需使用 macOS；系統金鑰圈或瀏覽器加密也可能阻止擷取。 |
| 網址不支援 | 改用上表列出的完整頁面網址。 |
| 影片或直播無法存取 | 先用瀏覽器確認。內容可能已刪除、尚未開始、已過期，或有地區／帳戶限制。 |

[回報問題](https://github.com/ykls3417/nico-channel-downloader/issues) 時，請附上作業系統、Python、yt-dlp、FFmpeg 版本及已遮蔽敏感資訊的錯誤訊息。開發、測試與發布方式見 [DEVELOPMENT.md（英文）](https://github.com/ykls3417/nico-channel-downloader/blob/main/DEVELOPMENT.md)。
