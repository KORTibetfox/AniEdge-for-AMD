"""Acquire pinned runtime assets from GitHub; verify SHA256 before installing.

Only whitelisted executable/model files are extracted, never arbitrary ZIP paths.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(data)
    return result.hexdigest()


def install(asset, check=False):
    expected = asset['files']
    if all((ROOT / name).is_file() and digest(ROOT / name) == sha for name, sha in expected.items()):
        print(asset['id'] + ': verified')
        return
    if check:
        raise RuntimeError(asset['id'] + ': missing or mismatched files; run setup.cmd')
    cache = ROOT / '.cache'
    cache.mkdir(exist_ok=True)
    archive = cache / asset['cache_name']
    if not archive.is_file() or digest(archive) != asset['sha256']:
        partial = archive.with_suffix('.partial')
        print('Downloading ' + asset['id'] + ' ...', flush=True)
        request = urllib.request.Request(asset['url'], headers={'User-Agent': 'AniEdge-for-AMD/0.1'})
        try:
            with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as target:
                shutil.copyfileobj(response, target, length=1024 * 1024)
            if digest(partial) != asset['sha256']:
                raise RuntimeError(asset['id'] + ': download SHA256 mismatch')
            partial.replace(archive)
        finally:
            partial.unlink(missing_ok=True)
    with zipfile.ZipFile(archive) as package:
        for name, sha in expected.items():
            candidates = [entry for entry in package.infolist() if not entry.is_dir() and Path(entry.filename).name == Path(name).name]
            if len(candidates) != 1:
                raise RuntimeError('Missing or ambiguous asset: ' + name)
            data = package.read(candidates[0])
            if hashlib.sha256(data).hexdigest() != sha:
                raise RuntimeError('Extracted asset SHA256 mismatch: ' + name)
            destination = ROOT / name
            if not destination.resolve().is_relative_to(ROOT):
                raise RuntimeError('Asset target is outside the application folder')
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp = destination.with_suffix(destination.suffix + '.partial')
            temp.write_bytes(data)
            temp.replace(destination)
    print(asset['id'] + ': installed and verified')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for asset in json.loads((ROOT / 'assets-manifest.json').read_text(encoding='utf-8'))['assets']:
        install(asset, args.check)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Asset setup failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
