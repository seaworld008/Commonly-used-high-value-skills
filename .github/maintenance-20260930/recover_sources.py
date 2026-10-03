#!/usr/bin/env python3
"""Recover exact source blobs for the interrupted, checksum-bound maintenance."""
import base64
import hashlib
import json
import lzma
import os
from pathlib import Path
import posixpath
import subprocess
import sys

BASE = '85651f151d6cd77dc1f091f830f27296ebaff64a'
DIGEST = 'f0abc8051fd9cfa2e6f4eb48c178d8951ed0e17d5550b03316810a965a7e1a07'
COMMITS = {
    'addyosmani/agent-skills': '2686b620fc1fed2e8f60c704839c766b8594c6b6',
    'cloudflare/security-audit-skill': 'c1c8a8c1471069fb0e188eeaff69b8e8db6564a8',
    'firebase/agent-skills': 'daaf0e1577b2d4ac23cfa9d31f421178ef229735',
    'Graphify-Labs/graphify': '1cd9a36c0c57a661d2d2234bc3207e887e1ba104',
    'ayghri/i-have-adhd': '839872f9d1cd634fed642b4589ce7226199cc15f',
    'prisma/skills': '82b88dd82801e958706f8265c29c910e6f0ebfa4',
    'larksuite/cli': '7beffb086d7fa3c5b843d8affa7c089f49cfc65e',
    'Linked-API/linkedin-skills': 'e46beb9aea0af3896fd49dd7b39cff1061bf8f6d',
    'NousResearch/hermes-agent': 'f42f579cf8bac4918ac9599bece71618afadd846',
    'obra/superpowers': '8ca22dba9a94f28898bbce59f2537ff4d87c747d',
    'microsoft/azure-skills': 'f07c05364353925f7c8b0e474aa95afa291bce54',
    'getsentry/skills': 'd18b7aa8ba878354e5c348310230e652f7690f9c',
    'neondatabase/agent-skills': '80164a28443aca7c82ac1a70aed836950d6c29ea',
    'wshobson/agents': '156b7a5e7a8b93642628a339ee4039c925b34c7f',
    'supabase/agent-skills': '544bfc56c89afe2b87b20017a59b2c6e9502a1fb',
    'Xquik-dev/x-twitter-scraper': '645ccfbad23f258ed9efb24de1ead641f15938e1',
    'simota/agent-skills': 'f425adcb2111ca8c0be88b325888ff61b64dec49',
    'xiaolai/nlpm': '4cf6b70948a2c5201ca50f511d3dd56990bdcb3f',
}

def main():
    transfer = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    packed = base64.b64decode(''.join(p.read_text().strip() for p in sorted(transfer.glob('maintenance.part*.b64'))), validate=True)
    if hashlib.sha256(packed).hexdigest() != DIGEST:
        raise ValueError('Recovery recipe checksum mismatch')
    decoder = lzma.LZMADecompressor(memlimit=256 * 1024 * 1024)
    raw = decoder.decompress(packed, max_length=8 * 1024 * 1024)
    if not decoder.eof or decoder.unused_data:
        raise ValueError('Invalid recovery recipe')
    recipe = json.loads(raw)
    if recipe['base'] != BASE:
        raise ValueError('Unexpected source baseline')
    wanted = {p for p, v in recipe['files'].items() if v[0] == 'upstream'}
    sys.path.insert(0, str(Path.cwd() / 'scripts'))
    from github_artifact_provider import GitHubArtifactProvider
    provider = GitHubArtifactProvider(token=os.environ['GH_TOKEN'])
    resolved = {}
    for mapping in sorted(Path('docs/sources').glob('*.skills.json')):
        original = subprocess.check_output(['git', 'show', BASE + ':' + mapping.as_posix()])
        for entry in json.loads(original).get('skills', []):
            for origin in entry.get('origins', []):
                repo = origin.get('repo')
                commit = COMMITS.get(repo)
                if not commit or origin.get('sync_mode') == 'archived':
                    continue
                tree = provider.tree(repo, commit)
                candidates = {}
                for artifact in origin.get('artifacts', []):
                    source, target = artifact['source'], artifact['target']
                    if artifact.get('type', 'file') == 'file':
                        candidates[target] = source
                    else:
                        prefix = source.rstrip('/') + '/'
                        candidates.update({target.rstrip('/') + '/' + p[len(prefix):]: p for p, item in tree.items() if p.startswith(prefix) and item['type'] == 'blob'})
                if origin['path'].endswith('/SKILL.md'):
                    prefix = posixpath.dirname(origin['path']) + '/'
                    candidates.update({posixpath.dirname(entry['repo_skill']) + '/' + p[len(prefix):]: p for p, item in tree.items() if p.startswith(prefix) and item['type'] == 'blob'})
                for target, source in candidates.items():
                    if target not in wanted:
                        continue
                    item = tree.get(source)
                    if item and item.get('type') == 'blob' and item.get('mode') in ('100644', '100755'):
                        resolved[target] = (repo, source, item)
    if resolved.keys() != wanted:
        raise ValueError('Unresolved immutable sources: ' + repr(sorted(wanted - resolved.keys())))
    def payload(repo, item):
        content = provider.blob(repo, item['sha'])
        blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        if blob != item['sha']:
            raise ValueError('Git blob mismatch')
        return {'git_blob': blob, 'sha256': hashlib.sha256(content).hexdigest(), 'mode': item['mode'], 'base64': base64.b64encode(content).decode()}
    files = []
    for target, (repo, source, item) in sorted(resolved.items()):
        files.append({'target': target, 'source': source, 'current': payload(repo, item)})
    repo = 'mattpocock/skills'
    commit = '6acc160e4e0cd062dbbbd7a1b26ae92855edf07e'
    tree = provider.tree(repo, commit)
    extra = {p: payload(repo, tree[p]) for p in ['LICENSE', 'skills/productivity/grill-me/SKILL.md', 'skills/productivity/grilling/SKILL.md']}
    result = {'entries': [{'origins': [{'files': files}]}], 'extra_sources': {repo: {'commit': commit, 'files': extra}}}
    (out / 'snapshots.json').write_text(json.dumps(result, ensure_ascii=False) + '\n')
    print('Recovered and Git-object-verified', len(files), 'immutable source files.', flush=True)

if __name__ == '__main__':
    main()
