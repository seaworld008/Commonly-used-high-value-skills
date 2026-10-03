#!/usr/bin/env python3
"""Stream-verify release archives against the checked-out Git commit, without extraction."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile


def verify_archive(archive: Path, prefix: str, expected: dict, required: set[str]) -> int:
    seen: set[str] = set()
    with tarfile.open(archive, 'r|gz') as bundle:
        for member in bundle:
            if not member.name.startswith(prefix):
                raise ValueError(f'Unexpected archive prefix: {member.name}')
            name = member.name[len(prefix):].rstrip('/')
            parts = PurePosixPath(name)
            if parts.is_absolute() or '..' in parts.parts or '\\' in name:
                raise ValueError(f'Unsafe archive path: {member.name}')
            if member.isdir():
                continue
            if not member.isfile() or name not in expected or name in seen:
                raise ValueError(f'Unexpected, duplicate, or non-regular member: {name}')
            item = expected[name]
            if member.size != item['size']:
                raise ValueError(f'Size mismatch: {name}')
            data = bundle.extractfile(member)
            if data is None or hashlib.file_digest(data, 'sha256').hexdigest() != item['sha256']:
                raise ValueError(f'Content mismatch: {name}')
            if bool(member.mode & 0o111) != (item['mode'] == '100755'):
                raise ValueError(f'Executable mode mismatch: {name}')
            seen.add(name)
    missing = required - seen
    if missing:
        raise ValueError(f'Missing required archive members: {sorted(missing)}')
    return len(seen)


def expected_files() -> dict:
    result = {}
    raw = subprocess.check_output(['git', 'ls-tree', '-rz', 'HEAD'])
    for record in raw.split(b'\0'):
        if not record:
            continue
        meta, path = record.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        name = path.decode()
        if mode not in {'100644', '100755'} or kind != 'blob':
            raise ValueError(f'Unsupported Git object: {name}')
        data = Path(name).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if actual != blob:
            raise ValueError(f'Working copy differs from the release commit: {name}')
        result[name] = {'mode': mode, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--tag', default='v3.2.0')
    parser.add_argument('--write-manifest', action='store_true')
    args = parser.parse_args()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if head != args.sha or args.tag != 'v3.2.0':
        raise ValueError('Unexpected release commit or tag')
    expected = expected_files()
    if any(p.startswith('.github/maintenance-20260930/') for p in expected):
        raise ValueError('Temporary transfer files must not ship')
    package = json.loads(Path('package.json').read_text())
    if package['version'] != args.tag[1:]:
        raise ValueError('Release and package version mismatch')
    canonical = [p for p in expected if p.startswith('skills/') and p.count('/') == 3 and p.endswith('/SKILL.md')]
    if len(canonical) != 287:
        raise ValueError('Unexpected canonical skill count')
    # npm intentionally omits ignore-control metadata, never runtime dependencies.
    omitted = sorted(p for p in expected if p.startswith('skills/') and Path(p).name in {'.gitignore', '.npmignore'})
    required_npm = {p for p in expected if p.startswith(('skills/', 'bin/'))} - set(omitted)
    required_npm.update({'package.json', 'LICENSE', 'README.md', 'README.en.md', 'docs/releases/v3.2.0.json'})
    specs = [
        (f'high-value-skills-{args.tag}.tar.gz', f'high-value-skills-{args.tag}/', set(expected)),
        (f'common-high-value-skills-{package["version"]}.tgz', 'package/', required_npm),
    ]
    assets = []
    for filename, prefix, required in specs:
        path = args.directory / filename
        count = verify_archive(path, prefix, expected, required)
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        assets.append({'file': filename, 'sha256': digest, 'bytes': path.stat().st_size, 'verified_files': count})
    manifest = {'tag': args.tag, 'commit': head, 'canonical_skills': len(canonical), 'package_version': package['version'],
                'assets': assets, 'npm_omitted_ignore_metadata': omitted,
                'checks': ['every member is tracked, regular and content-exact', 'all required runtime files included', 'Git executable modes preserved'],
                'boundaries': 'No real-model, live SaaS, database, production, or client-global-installation acceptance.'}
    manifest_path = args.directory / 'release-manifest.json'
    if args.write_manifest:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    elif json.loads(manifest_path.read_text()) != manifest:
        raise ValueError('Downloaded manifest does not match independent archive verification')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
