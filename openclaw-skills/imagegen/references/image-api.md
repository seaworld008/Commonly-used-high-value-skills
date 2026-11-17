# Image API quick reference

These are bundled CLI/API controls, not a portable host-tool schema. Verify current official API documentation and the installed SDK for the selected model before live calls; a local dry-run does not establish service support.

## Endpoints
- Generate: `POST /v1/images/generations` (`client.images.generate(...)`)
- Edit: `POST /v1/images/edits` (`client.images.edit(...)`)

## Models
- Default: `gpt-image-1.5`
- Alternatives: `gpt-image-1-mini` (for faster, lower-cost generation)
- The reviewed upstream CLI uses the same default and accepts the `gpt-image-` family prefix, including `gpt-image-1`. A prefix match is not a model availability list or a guarantee that every option works on every model.

## Core parameters (generate + edit)
- `prompt`: text prompt
- `model`: image model
- `n`: number of images (1-10)
- `size`: `1024x1024`, `1536x1024`, `1024x1536`, or `auto`
- `quality`: `low`, `medium`, `high`, or `auto`
- `background`: `transparent`, `opaque`, or `auto` (transparent requires `png`/`webp`)
- `output_format`: `png` (default), `jpeg`, `webp`
- `output_compression`: 0-100 (jpeg/webp only)
- `moderation`: `auto` (default) or `low`

## Edit-specific parameters
- `image`: one or more input images (first image is primary)
- `mask`: optional mask image (same size, alpha channel required)
- `input_fidelity`: optional `low` or `high` (support/default varies by model); the CLI validates those values and omits the parameter when not supplied. Check the selected model's support before using `high` for strict edits.

## Output
- `data[]` list with `b64_json` per image

## Limits & notes
- Input images and masks must be under 50MB.
- The CLI only checks paths and warns about size/non-PNG masks; it does not fully validate mask dimensions, alpha, or decoded images. Inspect edit inputs and outputs separately.
- Use edits endpoint when the user requests changes to an existing image.
- Masking is prompt-guided; exact shapes are not guaranteed.
- Large sizes and high quality increase latency and cost.
- For fast iteration or latency-sensitive runs, start with `quality=low`; raise to `high` for text-heavy or detail-critical outputs.
- Use `input_fidelity=high` for strict edits (identity preservation, layout lock, or precise compositing).
- When supported, high input fidelity can increase input token usage. If an option is unsupported, identify the model/SDK mismatch before retrying; do not silently drop a user-required editing constraint.
