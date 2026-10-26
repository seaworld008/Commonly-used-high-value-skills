---
name: remotion-video
description: 'Use when creating or repairing a Remotion React video, composition, or render whose frame timing and exported media must be validated.'
zh_description: "制作和修复 Remotion 视频，以帧时间线、抽帧检查和媒体元数据验证交付结果。"
version: "1.0.0"
author: seaworld008
source: in-house
source_url: ""
license: MIT
tags: [remotion, react, video, animation, rendering, validation]
created_at: "2026-10-26"
updated_at: "2026-10-26"
quality: 3
complexity: advanced
---

# Remotion Video Workflow

Create a reproducible React video and verify its exported media against the
requested dimensions, frame rate, duration and audio requirements.
This is an original workflow based on public API facts, with a local acceptance
validator. It does not copy the unlicensed Remotion Agent Skills repository.

## When to Use

- Build an explainer, title card, product demo or data animation in Remotion.
- Repair frame timing, clipping, missing media or a failed Remotion export.
- Compare the rendered file with a concrete video delivery specification.

For generic React application UI, use a frontend skill. For diffusion-based
video generation, use the relevant media provider instead of this workflow.

## Establish the Render Contract

Read the existing entry point, compositions, package manager and lockfile.
Reuse the project's installed Remotion packages and matching versions.
Record composition ID, width, height, fps, duration in frames, output codec,
audio requirement, destination and the assets the user has authorized.

```yaml
composition: ReleaseCard
width: 1280
height: 720
fps: 30
duration_in_frames: 90
duration_seconds: 3
audio: absent
output: out/release-card.mp4
```

Use `durationInFrames / fps` to derive seconds. Frames start at zero, so the
last frame of the example is 89. Keep dimensions and duration in the composition
configuration rather than scattering them through animations.

## Implement a Deterministic Timeline

Use `useCurrentFrame()` and `useVideoConfig()` inside the composition.
Drive motion from the frame number; clamp interpolation where the value should
hold before or after a transition. Avoid wall-clock time, unseeded randomness,
network-dependent assets or CSS animation state as the video clock.

The original [TitleCard.tsx](examples/TitleCard.tsx) demonstrates a small bounded
fade. Register it through the existing project's `Composition` and `registerRoot`
entry point. Do not overwrite an existing root file just to use the example.

Resolve assets through the project's supported asset mechanism. Use the current
official media and font APIs for the installed version; wait for asynchronous
assets before capturing a frame. Keep API keys and private URLs out of sources
and exported video. Cloud rendering or paid asset generation needs its own task
authorization and configured destination.

## Preview Before a Full Export

Use the project's package runner and installed CLI. The commands below assume
`npx` resolves the project's Remotion CLI; do not silently fetch a new version.
Adapt the entry point and composition ID from observed project files.

```bash
npx remotion compositions src/index.ts
npx remotion still src/index.ts ReleaseCard out/start.png --frame=0
npx remotion still src/index.ts ReleaseCard out/middle.png --frame=45
npx remotion still src/index.ts ReleaseCard out/end.png --frame=89
```

Inspect text legibility, safe margins, clipping, missing assets, motion state and
aspect ratio. For timed captions or cuts, inspect frames on both sides of the
boundary as well. A successful still command alone does not prove visual quality.

## Render and Validate

```bash
npx remotion render src/index.ts ReleaseCard out/release-card.mp4
npx remotion ffprobe -v error -show_streams -show_format -of json out/release-card.mp4 > out/probe.json
python scripts/validate_media.py out/probe.json --width 1280 --height 720 --fps 30 --frames 90 --audio absent
```

The Python script is relative to this skill's directory; pass an absolute JSON
path when running it from there. An existing `ffprobe` binary can produce the
same JSON. The validator does not install dependencies, execute a media file,
contact a service or modify the input. It rejects malformed or oversized JSON,
missing/ambiguous video streams, wrong dimensions/rate/duration and an audio
presence mismatch. Unknown timing is a failed acceptance check, not a pass.

Play the actual exported video, including cuts and the final frame. When audio
is present, listen for clipping, unwanted silence, missing speech and A/V drift.
The metadata validator cannot judge those properties or the quality of a design.

## Failure Diagnosis

- Missing composition: verify the entry point and registered composition ID.
- Off-by-one cut: inspect the zero-based interval and the boundary stills.
- Missing asset or font: verify local paths, render readiness and actual errors.
- Render crash: reduce concurrency only after inspecting memory and error output.
- Correct metadata but poor output: inspect frames and playback; do not weaken
  the contract to make a failed artifact appear valid.

## Deliverables and Evidence

Provide the source changes, render command, final media path, acceptance result,
preview frames and any unverified playback/audio requirements. Record package
versions and distinguish local export from a cloud deployment.
Do not report a video rendered when only TypeScript or metadata fixtures passed.

## Sources and License Boundary

Use [current API and licensing references](references/official-api.md) when the
installed package version or usage terms matter. This skill's MIT license covers
its original guidance, sample and validator; it does not relicense the Remotion
runtime, third-party assets, fonts or the unlicensed upstream skill collection.
