"""Install a wheel with pipx, then test the installed package outside the checkout."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    wheel, = Path(sys.argv[1]).resolve().glob('*.whl')
    tests = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='nico-package-') as directory:
        root = Path(directory).resolve()
        env = dict(os.environ, PIPX_HOME=str(root / 'pipx'), PIPX_BIN_DIR=str(root / 'bin'),
                   PIPX_MAN_DIR=str(root / 'man'), PYTHONUTF8='1')
        env.pop('PYTHONPATH', None)
        subprocess.run([sys.executable, '-m', 'pipx', 'install', '--python', sys.executable, str(wheel)],
                       cwd=root, env=env, check=True)
        windows = sys.platform == 'win32'
        python = root / 'pipx/venvs/nico-channel-downloader' / ('Scripts/python.exe' if windows else 'bin/python')
        cli = root / 'bin' / ('nico-dl.exe' if windows else 'nico-dl')
        subprocess.run([str(cli), '--help'], cwd=root, env=env, check=True)
        subprocess.run([str(python), '-c',
                        'import pathlib, sys, nico_dl, nico_backend, nico_urls; '
                        'assert all(pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path(sys.prefix).resolve()) '
                        'for m in (nico_dl, nico_backend, nico_urls))'], cwd=root, env=env, check=True)
        subprocess.run([str(python), '-m', 'nico_backend', '--help'], cwd=root, env=env, check=True)
        subprocess.run([str(python), '-m', 'unittest', 'discover', '-s', str(tests), '-v'],
                       cwd=root, env=env, check=True)
    print('Wheel installation, CLI entry points, and installed-package tests passed.')


if __name__ == '__main__':
    main()
