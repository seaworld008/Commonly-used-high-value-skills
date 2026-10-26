# Source and Local Validation

The method and original artifacts come from `getsentry/skills` at
`d12f250460ffd961f549dbebf7eeb0cf4afd4c2e`, under Apache-2.0.
Sentry attributes its method to `openai/codex-security` at
`2b74623e0fe2e92b6832e0cea585944ec60495ae`, also verified as Apache-2.0.
The original notices, source inventory, specifications, helper and tests are
retained under `upstream/` as provenance evidence, not as the active entrypoint.

The active `scripts/resolve_security_model.py` is a local hardening of the
Sentry Python implementation. Changes include explicit-ref validation and OID
pinning, special-file and path containment checks, current-file filtering,
historical mode/size checks, and a bounded warning budget. Platform-specific
open flags are used only when available. Historical relative references are
normalized lexically inside the pinned Git tree; root escapes are rejected
and missing historical files never fall back to head. Git path output loses
only its terminating newline, preserving meaningful directory whitespace. Use the active script, not the original
reference snapshot, for local policy checks.

Upstream's 22 tests and local boundary regressions are retained. The regressions
cover empty refs, symlinks/FIFO, deleted tracked files, historical symlink policy,
oversized historical blobs, and warning amplification. Their passing result
does not prove that a policy is correct or a runtime is resistant to every attack.

The `upstream/SOURCES.md` case studies are Sentry's reported observations. They
were not independently rerun here. No security policy was installed into a user
project and no scanner, model, service or production acceptance is implied.
