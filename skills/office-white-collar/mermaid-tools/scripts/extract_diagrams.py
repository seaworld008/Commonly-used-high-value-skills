#!/usr/bin/env python3
"""
Extract Mermaid diagrams from markdown file and create numbered .mmd files
"""

import argparse
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path


def mermaid_blocks(content):
    """Track Markdown fences, including non-Mermaid example blocks.

    A closing fence uses the same character and at least the opening length.
    Backtick info strings cannot contain backticks. Up to three leading spaces
    are allowed; an unclosed fence extends to EOF, as in Markdown.
    """
    fence = None
    context = []
    body = []
    for line in content.splitlines():
        if fence is None:
            opening = re.match(r"^( {0,3})(`{3,}|~{3,})(.*)$", line)
            if opening:
                indent, marker, info = opening.groups()
                if marker[0] == '`' and '`' in info:
                    context.append(line)
                    continue
                language = info.strip().split()
                fence = (marker, len(indent), bool(language and language[0].lower() == 'mermaid'))
                body = []
            else:
                context.append(line)
        else:
            marker, indent, is_mermaid = fence
            if re.fullmatch(r" {0,3}" + re.escape(marker[0]) + r"{" + str(len(marker)) + r",}[ \t]*", line):
                if is_mermaid:
                    yield context[-20:], '\n'.join(body)
                fence = None
                # Keep context positions bounded without taking names from examples.
                context.append('')
            elif is_mermaid:
                leading = len(line) - len(line.lstrip(' '))
                body.append(line[min(indent, leading):])
    if fence is not None and fence[2]:
        yield context[-20:], '\n'.join(body)


def extract_mermaid_diagrams(markdown_file, output_dir):
    """Extract Mermaid diagrams from markdown file and create numbered .mmd files"""
    
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    matches = list(mermaid_blocks(content))
    
    if not matches:
        print("No Mermaid diagrams found in markdown file")
        return []
    
    # Extract diagram names from context (look backwards for section headers)
    diagrams = []
    for i, (context_lines, match) in enumerate(matches, 1):
        # Look backwards for the most recent section header or meaningful context
        diagram_name = f"diagram-{i:02d}"  # Default fallback
        
        # Priority 1: Look for specific diagram descriptions
        for line in reversed(context_lines):
            line = line.strip().lower()
            if 'system architecture' in line:
                diagram_name = f"{i:02d}-system-architecture"
                break
            elif 'authentication flow' in line:
                diagram_name = f"{i:02d}-authentication-flow"
                break
            elif 'caching architecture' in line or 'multi-layer cache' in line:
                diagram_name = f"{i:02d}-caching-architecture"
                break
            elif 'data flow' in line or 'redshift schema' in line:
                diagram_name = f"{i:02d}-data-flow"
                break
            elif 'api request' in line or 'dashboard metrics endpoints' in line:
                diagram_name = f"{i:02d}-api-request-response"
                break
            elif 'dashboard layout' in line or 'presentation layer' in line:
                diagram_name = f"{i:02d}-dashboard-layout"
                break
            elif 'agency' in line and ('hierarchy' in line or 'filter' in line):
                diagram_name = f"{i:02d}-agency-hierarchy"
                break
        
        # Priority 2: Look for section headers (## or ###)
        if diagram_name.startswith('diagram-'):
            for line in reversed(context_lines):
                line = line.strip()
                if line.startswith('###') or line.startswith('##'):
                    # Extract meaningful part from header
                    header = re.sub(r'^#+\s*\*?\*?', '', line)
                    header = re.sub(r'\*?\*?$', '', header)
                    header = header.strip()
                    
                    # Convert to filename-friendly format
                    name_part = re.sub(r'[^\w\s-]', '', header)
                    name_part = re.sub(r'\s+', '-', name_part.strip())
                    name_part = name_part.lower()[:30]  # Limit length
                    
                    if name_part and name_part != 'detailed-design':
                        diagram_name = f"{i:02d}-{name_part}"
                        break
        
        diagrams.append({
            'number': i,
            'name': diagram_name,
            'content': match.strip()
        })
        
        print(f"Found diagram {i}: {diagram_name}")
    
    # Write .mmd files
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    created_files = []
    for diagram in diagrams:
        mmd_file = output_path / f"{diagram['name']}.mmd"
        with open(mmd_file, 'w', encoding='utf-8') as f:
            f.write(diagram['content'])
        created_files.append(str(mmd_file))
        print(f"Created: {mmd_file}")
    
    return created_files


def publish_pair(source, png, output_dir):
    """Replace one validated pair, restoring originals on publication errors.

    Copy into the destination filesystem before replacing either public path.
    Backups remain available until both replacements succeed. This is rollback
    protection for reported I/O failures, not a crash-atomic two-file rename.
    """
    source, png, output = Path(source), Path(png), Path(output_dir)
    if source.suffix != '.mmd' or png.name != source.with_suffix('.png').name:
        raise ValueError('source and PNG names must describe the same diagram')
    targets = [output / source.name, output / png.name]
    for path in [source, png, *targets]:
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            if path in targets:
                continue
            raise
        if not stat.S_ISREG(mode):
            raise ValueError(f'refusing non-regular publication file: {path}')

    # Destination-local publication copies permit atomic individual replacements
    # even when TMPDIR and the output directory are on different filesystems.
    stage = Path(tempfile.mkdtemp(prefix='.mermaid-publish.', dir=output))
    changed = []
    originals = {}
    preserve = False
    try:
        for index, (new, target) in enumerate(zip([source, png], targets)):
            shutil.copy2(new, stage / f'new-{index}')
            if target.exists():
                backup = stage / f'old-{index}'
                shutil.copy2(target, backup)
                originals[target] = backup
            else:
                originals[target] = None
        for index, target in enumerate(targets):
            os.replace(stage / f'new-{index}', target)
            changed.append(target)
    except BaseException as exc:
        rollback_errors = []
        for target in reversed(changed):
            try:
                backup = originals[target]
                if backup is None:
                    target.unlink()
                else:
                    os.replace(backup, target)
            except OSError as rollback_exc:
                rollback_errors.append(f'{target}: {rollback_exc}')
        if rollback_errors:
            preserve = True
            raise RuntimeError(f'{exc}; rollback incomplete: {rollback_errors}; '
                               f'recovery files retained at {stage}') from exc
        raise
    finally:
        if not preserve:
            try:
                shutil.rmtree(stage)
            except OSError as exc:
                # A cleanup error must not turn a fully published pair into a
                # claimed publication failure, or hide an earlier I/O failure.
                print(f'WARNING: Publication copies could not be removed: {stage}: {exc}', file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown_file")
    parser.add_argument("output_directory")
    parser.add_argument("--manifest", help="write this batch's NUL-separated .mmd filenames")
    parser.add_argument("--publish-png", help="internal: publish input .mmd and this validated PNG as a pair")
    args = parser.parse_args()
    try:
        if args.publish_png:
            publish_pair(args.markdown_file, args.publish_png, args.output_directory)
            sys.exit(0)
        files = extract_mermaid_diagrams(args.markdown_file, args.output_directory)
        if args.manifest:
            Path(args.manifest).write_bytes(b"".join(os.fsencode(Path(f).name) + b"\0" for f in files))
    except Exception as exc:
        action = 'publish diagram pair' if args.publish_png else 'extract diagrams'
        print(f"ERROR: Failed to {action}: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"\nExtracted {len(files)} diagrams successfully")
