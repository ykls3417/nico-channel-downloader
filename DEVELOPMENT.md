# Development and releases

User installation: [English](README.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md).

## Work on the code

Requires Python 3.10+, FFmpeg and ffprobe (including the libx264 encoder).

```sh
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Validate the distribution

```sh
python -m pip install build twine pipx
python -m build
python -m twine check --strict dist/*
python tests/check_package.py dist
```

Start with an empty `dist` directory so there is exactly one wheel to test. `build` creates a source archive, then builds the wheel from that archive. The package check installs the wheel into a temporary pipx environment, verifies the installed modules and both CLI entry points, and runs the complete test suite outside the checkout. It does not change your existing pipx apps.

CI builds once and tests that wheel on Windows/macOS with Python 3.12, and Linux with Python 3.10, 3.12 and 3.13. FFmpeg must be present; CI does not silently skip media tests. Local HLS fixtures test actual downloads, four quality choices, cookies/headers, metadata cleanup, all 52 CRF values, output validation and preservation on errors. URL tests cover 27 route examples across Niconico, YouTube and Bilibili, all shared parameters, host restrictions and collection handling. Quality tests use real yt-dlp selection for both portrait and landscape formats, including unknown dimensions. YouTube runtime checks fail before creating output when Deno is missing. Test-only local extractors are not included in the wheel.

These tests do not prove access to paid content, real browser encrypted cookie stores, live broadcasts, or timeshift playback. Public video extraction and traditional-channel pagination have also been checked manually without account credentials.

See [TESTING.md](TESTING.md) for the real-video audit and its limits. Process-tree cancellation is exercised with real child and grandchild processes on each CI platform.

## Architecture

The three existing modules keep their roles: `nico_urls.py` validates and normalizes allowed page URLs, `nico_backend.py` registers only the supported yt-dlp extractors and supplies shorter-edge format metadata, and `nico_dl.py` handles the CLI, download manifest and FFmpeg processing. The `nico-dl` command and package name remain unchanged for existing users. No generic extractor or new service framework is needed.

YouTube requires Deno 2.3.0+ on PATH for manual integration checks. A public YouTube video (`jNQXAC9IVRw`) passed extraction, download, H.264/AAC conversion and full decode validation during the 0.4.0 checks. Bilibili returned HTTP 412 from this environment, so its real download could not be verified. Automated fixtures do not prove current site availability, actual live recording or authenticated access.

## Publish a GitHub release

1. Update `project.version` in `pyproject.toml` and the installation URLs in all three READMEs.
2. Commit the change and wait for Tests to pass.
3. Create a GitHub release with the matching tag, for example `v0.4.0`.
4. The Release workflow checks the tag/version, builds distributions, and runs the five installation/media test jobs. Only after they pass does it attach the wheel, source archive and SHA256 checksums to the release.

The release job can be rerun through Actions → Release → Run workflow. Enter the existing tag. It replaces that release's generated assets; do not move published version tags. PyPI refuses to replace an already-published distribution, so use a new version for package changes.

## Connect PyPI once

Publishing to PyPI is disabled by default until the account owner connects a Trusted Publisher. No API token needs to be committed or pasted into chat.

In [PyPI pending publishers](https://pypi.org/manage/account/publishing/), configure:

| Field | Value |
| --- | --- |
| PyPI project name | `nico-channel-downloader` |
| GitHub owner | `ykls3417` |
| Repository | `nico-channel-downloader` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

Create the repository's GitHub environment named `pypi` and configure a required reviewer. Then run Actions → Release → Run workflow, enter the release tag, and enable **Publish to PyPI**. Approve the environment when prompted. The publish job receives only the tested distributions and uses short-lived OIDC credentials.

After the first successful publication, set repository Actions variable `PYPI_PUBLISHING_ENABLED` to `true` to request PyPI publishing automatically on future GitHub releases. The environment's review still applies. Update all READMEs to make `pipx install nico-channel-downloader` the primary command only after checking the public PyPI package and testing that command.

The publishing workflow is prepared, but this repository alone cannot authorize access to your PyPI account. If the package name is unavailable when registering the publisher, select an available name and update package metadata, installation commands and the package-check script together.

References: [PyPA publishing guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/), [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/), [pipx](https://pipx.pypa.io/).
