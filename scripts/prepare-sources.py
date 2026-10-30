# SPDX-License-Identifier: GPL-2.0-or-later
"""Reconstruct pinned source checkouts without USB access or recovery binaries."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args, check=True):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True,
                            text=True, encoding='utf-8', errors='replace')
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def ensure_repo(path, url, revision, check=False):
    if not (path/'.git').exists():
        if check:
            raise RuntimeError(f'Missing source checkout: {path}')
        if path.exists() and any(path.iterdir()):
            raise RuntimeError(f'Preserve this non-repository directory before retrying: {path}')
        path.mkdir(parents=True, exist_ok=True)
        git(path, 'init', '--quiet')
        git(path, 'config', 'core.autocrlf', 'false')
        git(path, 'remote', 'add', 'origin', url)
        git(path, 'fetch', '--depth=1', 'origin', revision)
        git(path, 'checkout', '--quiet', '--detach', 'FETCH_HEAD')
    actual = git(path, 'rev-parse', 'HEAD').stdout.strip()
    if actual != revision:
        raise RuntimeError(f'Source revision mismatch: {path}: {actual}; expected {revision}')


def apply_patch(repo, patch, check=False):
    if git(repo, 'apply', '--reverse', '--check', str(patch), check=False).returncode == 0:
        return
    forward = git(repo, 'apply', '--check', str(patch), check=False)
    if check or forward.returncode:
        raise RuntimeError(f'Patch missing or conflicting local edits: {patch}')
    git(repo, 'apply', str(patch))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify offline without changing files')
    args = parser.parse_args()
    lock = json.loads((ROOT/'SOURCE_LOCK.json').read_text(encoding='utf-8'))
    for key, folder in [('board', 'kws-x1-standalone-rs'), ('engine', 'dmc100-doom')]:
        entry = lock[key]
        repo = ROOT/'vendor'/folder
        ensure_repo(repo, entry['url'], entry['revision'], args.check)
        if 'patch' in entry:
            apply_patch(repo, ROOT/entry['patch'], args.check)
    entry = lock['doomgeneric']
    ensure_repo(ROOT/'vendor/dmc100-doom/oracle/src/doomgeneric-repo',
                entry['url'], entry['revision'], args.check)
    command = [sys.executable, str(ROOT/'scripts/stage-port.py')]
    if args.check:
        command.append('--check')
    subprocess.run(command, check=True)
    print('Source preparation verified; no device was accessed')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Error: {error}') from error
