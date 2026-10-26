#!/usr/bin/env python3
"""Check ffprobe JSON against a Remotion export contract, without running media."""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import re
import sys

MAX_BYTES = 8 * 1024 * 1024


def positive_fraction(value: object, label: str) -> Fraction:
    if isinstance(value, bool) or value is None:
        raise ValueError(f'{label} must be a positive rational number')
    text = str(value)
    if len(text) > 64 or re.fullmatch(r'[0-9]+(?:/[0-9]+|\.[0-9]+)?', text) is None:
        raise ValueError(f'{label} must be a bounded rational number')
    try:
        result = Fraction(text)
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        raise ValueError(f'{label} must be a positive rational number') from error
    if result <= 0:
        raise ValueError(f'{label} must be positive')
    return result


def validate(payload: object, *, width: int, height: int, fps: Fraction, frames: int, audio: str) -> list[str]:
    if width <= 0 or height <= 0 or frames <= 0 or fps <= 0:
        raise ValueError('contract dimensions, fps and frames must be positive')
    if audio not in {'present', 'absent', 'either'}:
        raise ValueError('invalid audio contract')
    if not isinstance(payload, dict) or not isinstance(payload.get('streams'), list):
        raise ValueError('input must contain a streams array')
    streams = payload['streams']
    if any(not isinstance(stream, dict) for stream in streams):
        raise ValueError('every stream must be an object')
    videos = [stream for stream in streams if stream.get('codec_type') == 'video']
    if len(videos) != 1:
        return ['exactly one video stream is required']
    video = videos[0]
    failures = []
    for key, expected in [('width', width), ('height', height)]:
        value = video.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value != expected:
            failures.append(f'{key} does not match contract')
    rate = video.get('avg_frame_rate')
    if rate in {None, '', '0/0', 'N/A'}:
        rate = video.get('r_frame_rate')
    if positive_fraction(rate, 'video frame rate') != fps:
        failures.append('frame rate does not match contract')
    duration = video.get('duration')
    if duration in {None, '', 'N/A'}:
        container = payload.get('format')
        duration = container.get('duration') if isinstance(container, dict) else None
    seconds = positive_fraction(duration, 'video duration')
    if abs(seconds - Fraction(frames, 1) / fps) > Fraction(1, 1) / fps:
        failures.append('duration differs by more than one frame')
    count = video.get('nb_frames')
    if count not in {None, '', 'N/A'}:
        if isinstance(count, bool) or not str(count).isdigit() or int(count) != frames:
            failures.append('frame count does not match contract')
    has_audio = any(stream.get('codec_type') == 'audio' for stream in streams)
    if audio == 'present' and not has_audio:
        failures.append('required audio stream is missing')
    if audio == 'absent' and has_audio:
        failures.append('unexpected audio stream')
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_json', type=Path)
    parser.add_argument('--width', type=int, required=True)
    parser.add_argument('--height', type=int, required=True)
    parser.add_argument('--fps', required=True)
    parser.add_argument('--frames', type=int, required=True)
    parser.add_argument('--audio', choices=['present', 'absent', 'either'], default='either')
    args = parser.parse_args(argv)
    try:
        with args.probe_json.open('rb') as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('probe JSON exceeds 8 MiB')
        payload = json.loads(raw.decode('utf-8'))
        failures = validate(payload, width=args.width, height=args.height,
                            fps=positive_fraction(args.fps, 'contract fps'),
                            frames=args.frames, audio=args.audio)
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as error:
        # Do not reflect arbitrary JSON/metadata or filesystem error contents.
        print(json.dumps({'ok': False, 'error': type(error).__name__}), file=sys.stderr)
        return 1
    print(json.dumps({'ok': not failures, 'failures': failures}))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
