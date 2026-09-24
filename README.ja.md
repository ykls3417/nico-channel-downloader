# Nico Channel Downloader

**ターミナルからニコニコ・YouTube・Bilibili の動画をダウンロード。Git のクローンやプロジェクトの設定は不要です。**

[English](https://github.com/ykls3417/nico-channel-downloader/blob/main/README.md) · [繁體中文](https://github.com/ykls3417/nico-channel-downloader/blob/main/README.zh-TW.md) · **日本語**

ニコニコの動画と一覧、YouTube の動画・ショート・生配信、Bilibili の動画に対応します。FFmpeg によるコピーされたメタデータの削除や、H.264/AAC MP4 への変換も可能です。元のファイルは必ず残します。MIT ライセンスの非公式プロジェクトです。

## 1. 必要なツールをインストール

**Python 3.10 以降**、**pipx**、**FFmpeg / ffprobe** が必要です。pipx は専用の環境にコマンドをインストールします。FFmpeg は別途インストールしてください。

| OS | 設定方法 |
| --- | --- |
| Ubuntu / Debian | `sudo apt install pipx ffmpeg`、続いて `pipx ensurepath` を実行します。 |
| macOS（Homebrew 使用） | `brew install pipx ffmpeg`、続いて `pipx ensurepath` を実行します。 |
| Windows | [Python](https://www.python.org/downloads/windows/) をインストールし、`py -m pip install --user pipx` と `py -m pipx ensurepath` を実行します。[FFmpeg のダウンロードページ](https://ffmpeg.org/download.html) から Windows 版を入手し、その `bin` フォルダーを PATH に追加します。 |

設定後にターミナルを開き直し、`pipx --version`、`ffmpeg -version`、`ffprobe -version` が動作することを確認してください。再エンコードには `libx264` を含む FFmpeg が必要です。その他の環境は [pipx のインストール手順](https://pipx.pypa.io/latest/how-to/install-pipx.html) を参照してください。

**YouTube には [Deno](https://docs.deno.com/runtime/getting_started/installation/) 2.3.0 以降も必要です。** PATH に追加し、`deno --version` を確認してください。Deno は YouTube の JavaScript チャレンジを実行します。解決用スクリプトは `yt-dlp[default]` に含まれます。ニコニコと Bilibili では Deno は不要です。

## 2. アプリをインストール

GitHub からバージョン指定のパッケージを直接インストールします。

```sh
pipx install https://github.com/ykls3417/nico-channel-downloader/releases/download/v0.4.0/nico_channel_downloader-0.4.0-py3-none-any.whl
nico-dl --help
```

同じパッケージを Windows、macOS、Linux で使えます。インストール後は任意のフォルダーで `nico-dl` を実行でき、仮想環境を有効にする操作は不要です。

**PyPI の公開状況：**公開用の仕組みは準備済みですが、管理者による PyPI アカウントの設定が必要です。PyPI で公開されるまでは上の GitHub コマンドを使用してください。`pipx install nico-channel-downloader` という短いコマンドは、公開後に利用できます。

## 3. 動画をダウンロード

URL をダウンロードしたい動画に置き換えます。

```sh
nico-dl "https://www.nicovideo.jp/watch/sm9"
```

初期設定では、解像度の表示が **1080p 以下**の動画を **`~/Downloads/nico`**（Windows ではユーザーフォルダー内の `Downloads\nico`）に保存します。

よく使う例：

```sh
# ログイン済みのブラウザーを使い、アカウントで視聴できるコンテンツにアクセス。
nico-dl "YOUR_VIDEO_URL" --cookies-from-browser firefox

# 画質と保存先を指定。
nico-dl "YOUR_VIDEO_URL" --quality 720 --output-dir "./videos"

# 再エンコードせず、コピーされたメタデータとチャプターを削除して MKV に保存。
nico-dl "YOUR_VIDEO_URL" --clean

# H.264/AAC MP4 に再エンコードし、コピーされたメタデータとチャプターも削除。
nico-dl "YOUR_VIDEO_URL" --reencode --crf 18
```

`YOUR_VIDEO_URL` は対応する実際のページ URL に置き換えてください。Cookie やリクエストヘッダーを指定しても、アカウントが持たない視聴権限は得られません。

## 対応する URL

以下の ID は形式を示す例です。実際の ID に置き換えてください。

| コンテンツ | URL の形式 |
| --- | --- |
| YouTube 動画 | `https://www.youtube.com/watch?v=VIDEO_ID` または `https://youtu.be/VIDEO_ID` |
| YouTube ショート／生配信 | `https://www.youtube.com/shorts/VIDEO_ID` または `/live/VIDEO_ID` |
| Bilibili 動画 | `https://www.bilibili.com/video/BV...` または `/video/av123`。`?p=2` でパートを指定 |
| 通常／旧形式／チャンネル動画 | `https://www.nicovideo.jp/watch/sm123` — `nm123`、`so123`、数字のみの ID にも対応 |
| ショート | `https://www.nicovideo.jp/shorts/sm123` |
| ニコニコ生放送 | `https://live.nicovideo.jp/watch/lv123` — `/gate/lv123` にも対応 |
| チャンネルプラスの動画／生放送 | `https://nicochannel.jp/CHANNEL/video/smCODE` または `/live/smCODE` |
| マイリスト／シリーズ | `https://www.nicovideo.jp/mylist/123` または `/series/123` |
| ユーザーの投稿動画 | `https://www.nicovideo.jp/user/123/video` — ユーザートップにも対応 |
| 従来のチャンネルの動画一覧 | `https://ch.nicovideo.jp/CHANNEL/video` — チャンネルトップにも対応 |
| チャンネルプラスの一覧 | `https://nicochannel.jp/CHANNEL/videos` または `/lives` |

ニコニコの一覧は次のページもたどり、表示される項目をすべてダウンロードします。動画ごとに別のフォルダーに保存します。チャンネルプラスの `/lives` は放送アーカイブの一覧です。

YouTube の URL は常に動画を 1 本だけ選び、再生リスト・追跡・時刻のパラメーターを除去します。録画済み動画は先頭から保存します。Bilibili は `p` を省略すると全パート、指定するとそのパートだけを保存します。

入力できるホストは `nicovideo.jp`、`www.nicovideo.jp`、`sp.nicovideo.jp`、`embed.nicovideo.jp`、`ch.nicovideo.jp`、`live.nicovideo.jp`、`live2.nicovideo.jp`、`sp.live.nicovideo.jp`、`sp.live2.nicovideo.jp`、`nicochannel.jp`、`youtube.com`、`www.youtube.com`、`m.youtube.com`、`youtu.be`、`bilibili.com`、`www.bilibili.com`、`m.bilibili.com` に限定しています。他のサイト、`nico.ms` と `b23.tv` の短縮 URL、YouTube のチャンネル／再生リスト、Bilibili の生配信／番組／`bilibili.tv`、独自ドメインのチャンネルプラス、直接の `.m3u8` URL、未対応のパスは拒否します。再生に必要な CDN／API への通信には、別のホストを使用する場合があります。

## オプション一覧

以下のオプションは、上記の対応 URL で共通して使えます。

| オプション | 内容 |
| --- | --- |
| `--quality 1080` | 表示上の短辺の上限。`1080`（初期値）、`720`、`480`、`best`。拡大処理はしません。サイズが不明な形式も許可します。1920×1080 と 1080×1920 はどちらも `1080` に収まります。 |
| `--output-dir PATH` | 保存先。初期値は `~/Downloads/nico`。 |
| `--cookies-from-browser NAME` | `brave`、`chrome`、`chromium`、`edge`、`firefox`、`safari` の Cookie を使用。利用可否は OS とブラウザーによります。 |
| `--cookies FILE` | Netscape 形式の Cookie ファイルを使用。 |
| `--clean` | コピーされたメタデータとチャプターを削除し、MKV に再多重化。 |
| `--reencode` | コピーされたメタデータとチャプターを削除し、H.264/AAC MP4 に変換。 |
| `--crf 18` | 再エンコードの品質。範囲は `0`～`51`。通常、小さいほど高画質・大容量。`--reencode` 使用時のみ有効。 |
| `--referer URL` | 自動設定される Referer を、許可されたサイトの URL で上書き。 |
| `--user-agent TEXT` | 必要に応じてセッションに合う User-Agent を指定。 |
| `-h`、`--help` | コマンドのヘルプを表示。 |

`--cookies` と `--cookies-from-browser`、`--clean` と `--reencode` は、それぞれ同時に指定できません。

## 保存ファイルと制限

- 実行ごとに `nico-*/EXTRACTOR-ID/source.*` を作成します。処理後の `cleaned.mkv` または `reencoded.mp4` は同じフォルダーに保存し、元のファイルは削除しません。
- 出力の確定前に、長さ・音声トラック数・全体のデコードを検証します。最初の映像トラックとすべての音声トラックを残し、字幕や添付ファイルは含めません。
- 一覧のダウンロードは最初のエラーで停止します。処理は全件のダウンロード成功後に始まります。途中で失敗しても、それまでの元ファイルは残ります。別の実行からの自動再開には未対応です。
- YouTube の生配信は現在の位置から録画します。先頭からの録画や配信開始待ちのオプションはありません。利用可能なアーカイブは通常の動画として保存します。
- 生放送は終了するか Ctrl+C を押すまで録画します。処理は録画完了後に行います。中断したファイルの再生は保証できません。タイムシフト／アーカイブの利用可否は、サイト・yt-dlp・アカウントの権限によります。
- **メタデータの削除や再エンコードは、匿名性や識別用ウォーターマークの除去を保証しません。**エンコーダーが技術情報を追加する場合があり、再エンコードで画質が低下することもあります。
- ダウンロードする権限があるコンテンツだけを利用してください。DRM の解除機能はありません。Cookie、署名付き URL、機密情報を含むログを公開しないでください。

## 更新・削除・トラブルシューティング

[Releases](https://github.com/ykls3417/nico-channel-downloader/releases) から新しい wheel の URL をコピーし、`pipx install --force "NEW_WHEEL_URL"` を実行します。バージョン指定の URL は自動的に新バージョンへ切り替わりません。PyPI からインストールした場合は `pipx upgrade nico-channel-downloader` を使用できます。

```sh
# サイトの変更に対応するため、抽出ツールだけを更新。
pipx runpip nico-channel-downloader install --upgrade "yt-dlp[default]"

# アプリを削除。ダウンロード済みの動画は残ります。
pipx uninstall nico-channel-downloader
```

| 問題 | 対処方法 |
| --- | --- |
| `nico-dl` が見つからない | `pipx ensurepath` を実行し、ターミナルを開き直して `pipx list` を確認。 |
| FFmpeg／ffprobe が見つからない | 両方をインストールし、配置したフォルダーを PATH に追加。 |
| YouTube で Deno が必要と表示される | Deno 2.3.0 以降を PATH に追加し、ターミナルを開き直す。 |
| YouTube がログインや PO token を要求する | yt-dlp を更新し、アカウントが必要な場合のみ Cookie を使用。一部の形式には外部の [PO token プロバイダー](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) が必要です。この CLI はプロバイダーの設定や token の指定に対応しないため、取得できない場合があります。 |
| Bilibili の画質が指定より低い | 画質はログイン・会員資格・地域・動画によります。`--quality` は上限であり、形式を解放するものではありません。 |
| ログインや Cookie の抽出に失敗する | ブラウザーのログイン状態と視聴権限を確認し、必要なら `--cookies FILE` を使用。Safari は macOS 専用です。ブラウザーの暗号化や OS のキーリングにより抽出できない場合があります。 |
| URL が未対応と表示される | 上の表にある完全なページ URL を使用。 |
| 動画や生放送にアクセスできない | まずブラウザーで確認。削除済み、開始前、期限切れ、地域制限、アカウント制限などが考えられます。 |

[問題を報告](https://github.com/ykls3417/nico-channel-downloader/issues) する際は、OS、Python、yt-dlp、FFmpeg のバージョンと、機密情報を伏せたエラー出力を添えてください。開発・テスト・公開の手順は [DEVELOPMENT.md（英語）](https://github.com/ykls3417/nico-channel-downloader/blob/main/DEVELOPMENT.md) を参照してください。
