# Official Remotion API References

Checked 2026-10-26. Read the documentation matching the project's installed
version rather than assuming every example applies to older projects.

| Question | Official reference |
|---|---|
| Composition dimensions, frame duration and fps | https://www.remotion.dev/docs/composition |
| Zero-based current frame | https://www.remotion.dev/docs/use-current-frame |
| Composition configuration in React | https://www.remotion.dev/docs/use-video-config |
| Numeric interpolation and extrapolation | https://www.remotion.dev/docs/interpolate |
| CLI video/audio export | https://www.remotion.dev/docs/cli/render |
| CLI still export | https://www.remotion.dev/docs/cli/still |
| CLI media metadata | https://www.remotion.dev/docs/cli/ffprobe |
| Product usage terms and licensing | https://www.remotion.dev/docs/license |

The CLI export interface accepts an entry point, composition ID and output path.
Project configuration may also supply defaults. Prefer explicit values in a
repeatable acceptance record, and inspect the installed CLI help for options.

## Original Acceptance Validator

`scripts/validate_media.py` consumes ffprobe JSON. Exit 0 means the supplied
metadata meets the requested contract; exit 1 means a mismatch or invalid input.
It uses exact rational frame rates and a one-frame duration tolerance for container
rounding. A passing fixture does not establish that a real file was rendered.

The validator checks one video stream, positive width/height, average frame rate
(or a usable nominal rate when average is absent), finite duration, an optional
frame count, and the requested audio presence. It does not decode video, check
subtitles, detect black frames, measure loudness or confirm A/V synchronization.

## Provenance Decision

The `remotion-dev/skills` repository was a high-signal discovery candidate, but no
explicit permissive license was found at the reviewed repository root. No text,
scripts, rule files or skill routers from that collection were copied here.
This independently authored workflow uses public API facts and original code.
