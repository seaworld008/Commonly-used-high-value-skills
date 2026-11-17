# Codex network approvals / sandbox notes

This guidance applies to the bundled CLI. Host image tools have their own network and authentication contract. Follow the current host policy; these notes do not authorize configuration changes.

## Why am I asked to approve every image generation call?
Image generation uses the OpenAI Image API, so the CLI needs outbound network access. In many Codex setups, network access is disabled by default (especially under stricter sandbox modes), and/or the approval policy may require confirmation before networked commands run.

## Separate network access from approval policy

- Disabling approval prompts does not grant network access. In particular, `--ask-for-approval never` does not enable outbound traffic.
- Diagnose the actual failure: sandbox denial, DNS/connectivity, missing SDK, authentication, and unsupported API parameters need different fixes.
- Use a scoped retry or approved environment only when the current host permits it and task authorization covers it. If policy forbids escalation, report the limitation and continue offline preparation with `--dry-run`.
- Do not change global configuration, persist approval exceptions, or weaken sandbox settings merely to avoid repeated prompts. Configuration changes require an explicit configuration task and must remain within managed policy.

## Dependencies and credentials

- Activate the project's selected environment using its normal workflow. Package installation and `uv run --with ...` may require network access; neither bypasses installation authorization.
- Use locally configured `OPENAI_API_KEY` for authorized CLI calls. Do not read unrelated credential stores or `.env` files by default, and never print keys.
- Establish the SDK's effective endpoint and authorized receiving service before uploading prompts/images. A custom endpoint is not automatically trusted to receive an OpenAI credential; do not silently switch providers after a failure.
- Dry-run needs neither the SDK nor a key/network call. It previews prompts, parameters, and paths, not actual endpoint reachability, account permissions, or generated quality.
