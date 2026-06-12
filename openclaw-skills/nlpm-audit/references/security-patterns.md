# NL Artifact Security Patterns

Use this reference when an NL artifact repository contains executable surfaces:
hooks, scripts, MCP configs, package install scripts, or commands that pass user
input into tools.

## Execution Context First

Classify a match before assigning severity.

| File context | Can execute? | Handling |
|---|---|---|
| `*.sh`, `*.py`, `*.js`, `*.ts` scripts | yes | scan fully |
| hook config and referenced hook scripts | yes | scan fully |
| `.mcp.json` and MCP launcher config | yes | scan fully |
| package manifests with install scripts | yes | scan install paths |
| markdown docs and SKILL.md | usually no | cap at Low unless executed by a hook/script |

Markdown examples are usually documentation, not executable code. A `curl | sh`
snippet in a README is not the same risk as a hook script running `curl | sh` on
every tool call.

## Critical Patterns

Block or escalate:

- `curl ... | sh`, `wget ... | bash`, or download-then-execute;
- `eval "$USER_INPUT"` or equivalent string-to-shell execution;
- reverse shell patterns such as `/dev/tcp/`;
- base64 decode piped to shell/interpreter;
- SSH key or token exfiltration;
- hardcoded private credentials.

## High Patterns

Investigate before publish:

- `subprocess.run(..., shell=True)` with untrusted input;
- `os.system(...)`;
- dynamic `require()` / `import()` from variables;
- `new Function(...)` or `eval(...)` in executable JavaScript;
- writing executable files outside the repository;
- `sudo` or PATH/profile modification;
- runtime dependency install from unpinned remote sources.

## MCP And Hook Risks

Check MCP configs for:

- remote servers outside known domains;
- missing auth on remote servers;
- broad filesystem or shell capability;
- wildcard permissions.

Check hooks for:

- scripts that do not exist;
- broad event matchers that run on every tool call;
- scripts that modify files or send network requests;
- fail-closed behavior without a security rationale;
- user prompt or file content passed to shell without escaping.

## False-Positive Filters

Drop or downgrade findings when the pattern is:

- inside markdown code fences;
- inside shell comments;
- inside help/usage output;
- inside test fixtures or object literals that are not locally executed;
- an analytics or browser publishable key, such as GA measurement IDs, Sentry
  browser DSNs, Stripe `pk_` publishable keys, or PostHog `phc_` project keys.

Never drop:

- AWS keys;
- GitHub tokens;
- OpenAI/Anthropic API keys;
- database URLs with credentials;
- private keys;
- Stripe `sk_` secret keys;
- server-side credentials in backend paths.

## Security Report Pattern

```markdown
## Security Scan

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |

### Findings
| Severity | File | Evidence | Why executable | Fix |
|---|---|---|---|---|
```

If any Critical or High finding survives context filtering, do not recommend
publishing until it is fixed or explicitly accepted by the maintainer.
