---
name: dependency-auditor
description: 'Audit dependency inventories, verify vulnerability and license evidence, and plan tested upgrades for an existing project.'
zh_description: "梳理依赖清单，核实漏洞与许可证证据，规划可验证的升级。"
version: "1.0.3"
author: "seaworld008"
source: "in-house"
source_url: ""
license: MIT
tags: [auditor, dependency, development, security]
created_at: "2026-03-04"
updated_at: "2026-09-28"
quality: 5
complexity: "intermediate"
---

# Dependency Auditor

## When to Use

Use for dependency security reviews, lockfile changes, upgrade planning,
license evidence collection, or an existing project's dependency inventory.
Use a dedicated performance workflow when the question is actual bundle size.
Do not infer vulnerabilities, latest releases, or legal compliance from names alone.

## Evidence Contract

Keep three distinct outputs: what is installed, what has been checked against
current evidence, and what changes have been tested.
An inventory is not an advisory database or a dependency resolver.
An empty finding list does not prove that a scan ran successfully.
Record the repository revision, lockfiles, runtime, scanner version, and scan date.
State unavailable databases, private registries, excluded workspaces, and parse errors.
Never turn `not_assessed` into `passed` in a report or CI gate.

## Bundled Helpers and Their Limits

### Offline inventory: `scripts/dep_scanner.py`

This helper enumerates selected manifests using simplified parsers.
It performs no registry query, package installation, or vulnerability matching.
Supported inputs include these common forms:

| Ecosystem | Inputs recognized | Important limitation |
|---|---|---|
| Node.js | package.json, package-lock.json, yarn.lock | Not a replacement for the package manager's resolved graph |
| Python | requirements.txt, Poetry-style pyproject.toml, Pipfile.lock, poetry.lock | Dynamic and modern project metadata can need native tooling |
| Go | go.mod | Does not resolve the selected module graph |
| Rust | Cargo.toml, Cargo.lock | Simplified inventory; use Cargo for full resolution |
| Ruby | Gemfile, Gemfile.lock | Does not evaluate arbitrary Ruby declarations |

`go.sum` is not treated as an installed-dependency lockfile.
Java, PHP, .NET, pnpm lockfiles, and arbitrary custom formats need their native tools.
Do not claim those formats were scanned by this helper.
Overlapping manifests may describe the same package or multiple versions.
Preserve the source file and check duplicates against the authoritative lockfile.

```bash
python scripts/dep_scanner.py /path/to/project --format json --output inventory.json
python scripts/dep_scanner.py /path/to/project --quick-scan
```

Run these paths relative to this skill's directory, or use their absolute paths.
The project argument selects the project being inspected, not the skill repository.
`--quick-scan` filters records classified as direct by the simplified parser.
It is not a guarantee that every direct dependency has been found.

The JSON result contains explicit coverage information:

```json
{
  "inventory_status": "best_effort",
  "vulnerability_status": "not_assessed",
  "advisory_source": null,
  "parse_errors": [],
  "vulnerabilities_found": 0
}
```

The zero count remains for compatibility; it is not a security verdict.
Malformed recognized inputs produce `inventory_status: partial` and `parse_errors`.
The CLI exits 2 for a partial inventory.
The legacy `--fail-on-high` option always exits 2 because advisory coverage is absent.
Replace that security gate with a maintained ecosystem scanner.
Exit 1 indicates an execution or input failure; do not suppress it.

### License triage: `scripts/license_checker.py`

This is a heuristic classifier for supplied license metadata and local files.
It is not a legal opinion, an SPDX expression engine, or proof of compliance.
Its policy scores are triage signals, not an authorization to distribute software.
Unknown expressions and uncertain license texts require inspection.
Do not simplify `MIT AND GPL-3.0` to MIT.
Do not relabel the Unlicense or a public-domain declaration as MIT.

```bash
python scripts/license_checker.py /path/to/project --inventory inventory.json --format json
```

Keep declared metadata, actual license text, copyright notices, and package version.
Inspect dual-license choices and exceptions separately before choosing a policy.
A README mentioning a license is weaker evidence than the distributed package's license.
Review the exact artifact that will be shipped, including vendored dependencies.

### Retired simulation: `scripts/upgrade_planner.py`

The old handwritten latest-version catalog and simulated migration estimates
have been retired. They could recommend stale versions as if queried live.
The compatibility entry point remains so existing callers get an explicit result:

```bash
python scripts/upgrade_planner.py inventory.json --format json
```

It returns `version_status: not_assessed` and exits 2.
Historical flags remain accepted, but they do not re-enable simulated analysis.
An empty `available_upgrades` list means no version assessment was performed.
Use the evidence-driven workflow below instead of treating this helper as a gate.

## Workflow

### 1. Establish the actual dependency scope

Read manifests and lockfiles before running commands that may modify them.
Identify workspaces, optional dependencies, extras, build tools, and deployment targets.
Record the package manager and its version from the project, not from memory.
Check the configured registry without printing authentication credentials.
Do not replace a private registry with a public registry merely to obtain a result.
Include runtime constraints such as Node, Python, Java, Rust, and operating system.
Separate runtime dependencies from build-only or test-only dependencies.
A development dependency can still affect the build supply chain.

Example scope note:

```text
Revision: <commit>
Workspace: apps/api
Runtime: <project-supported runtime>
Resolver: <package manager and version>
Lockfile: <path and digest>
Included: runtime + build dependencies
Excluded: optional mobile workspace; reason recorded
```

### 2. Obtain the native resolved inventory

Prefer the ecosystem's resolver output when exact transitive relationships matter.
Use read-only inspection commands and preserve their exit status and stderr.
For npm, inspect the lockfile and `npm ls --all --json` output together.
For Go, inspect the selected module graph rather than every checksum in go.sum.
For Cargo, use metadata or tree output for the intended target and feature selection.
For Python, distinguish declared requirements from the environment actually deployed.
Do not install project dependencies globally just to inspect them.
Any environment creation or dependency resolution should use an isolated workspace.

### 3. Run maintained advisory tooling

Use the tool appropriate to the ecosystem and the available, authorized environment.
Check its official documentation for supported inputs and exit-code meanings.
Do not use the offline inventory helper as a substitute.
Typical tools include npm audit, pip-audit, cargo audit, and ecosystem-specific scanners.
A scanner can contact a registry or advisory service and disclose dependency names.
Confirm that this matches the project's private-package and network policies.
Do not send private package inventories to an unrelated service.

For a configured npm project with a valid lockfile:

```bash
npm audit --json > npm-audit.json
```

Capture the command's nonzero exit code; distinguish findings from tool failure.
Do not run `npm audit fix`, `--force`, or package-manager update commands as a scan.
Those are changes and need the same review and tests as an ordinary dependency update.
For other ecosystems, use the installed scanner's documented lockfile/environment mode.
Record the advisory database refresh time when the tool exposes it.
A timed-out or unreachable advisory source is `unavailable`, not `no vulnerabilities`.

### 4. Verify each actionable finding

Match package identity and ecosystem before comparing versions.
Read the advisory's affected ranges, fixed ranges, withdrawn status, and aliases.
Do not apply one ecosystem's version-ordering rules to another.
Check whether the affected package is present in the deployed dependency graph.
Trace how the package is introduced and whether it is reachable in the application.
A reachable exploit path increases priority; lack of a demonstrated path is not proof of safety.
Distinguish a vulnerable package from an unmaintained-package advisory.
Do not invent CVSS scores, exploit availability, or a remediation version.
Deduplicate aliases while retaining links to the source advisories.

Example finding record:

```json
{
  "package": "<ecosystem/name>",
  "installed_version": "<resolved version>",
  "advisory": "<verified advisory identifier>",
  "source": "<official advisory location>",
  "affected": "<verified range>",
  "fixed": "<verified range or unavailable>",
  "dependency_path": ["application", "parent", "affected package"],
  "reachability": "not yet established",
  "decision": "investigate or upgrade with tests"
}
```

### 5. Collect license evidence

Read license metadata from the exact package version and distributed artifact.
Preserve copyright, NOTICE files, SPDX expressions, and exceptions.
Record missing licenses as unknown, not permissive by default.
Check whether the dependency is linked, vendored, modified, or distributed separately.
Different distribution models can require different reviews.
Escalate ambiguous obligations to the project's responsible reviewer.
Do not make legal conclusions from a numerical helper score.

### 6. Choose a verified upgrade target

Query the project's approved registry and read upstream release notes.
Record the query time and distinguish latest published from latest compatible.
A newer prerelease is not automatically a suitable production target.
A patch version can still change behavior; semantic versioning is not a safety proof.
Check peer dependencies, runtime floors, native addons, and platform support.
Prefer the smallest supported fix that addresses the verified problem.
Do not hold an upgrade merely because it is major when no supported smaller fix exists.
Separate unrelated ecosystem migrations so failures are attributable.

### 7. Apply changes in an isolated branch

Use the project's package manager to update manifests and lockfiles together.
Inspect install scripts and provenance before allowing new code to execute.
Review the lockfile diff for unexpected registries, unrelated packages, and integrity changes.
Preserve project-specific patches and document whether they are still needed.
Do not delete a lockfile to make resolution succeed without understanding the impact.
Run formatting, compilation, unit tests, and relevant integration tests.
Exercise the application path that imports the changed dependency.

### 8. Plan deployment and rollback

Record the old manifest, lockfile, build artifact, and configuration versions.
For database or data-format changes, verify rollback compatibility explicitly.
A package downgrade is not a database rollback strategy.
Define the health metrics and observation window used for rollout acceptance.
Use staging or a canary where the project provides one.
Do not claim production acceptance from static scanning or mocked tests.

## Completion Checklist

- Inventory scope and exclusions are explicit.
- Scanner execution errors are distinct from findings.
- Each vulnerability has a verified package, range, and source.
- Each license conclusion has artifact-level evidence or is marked unresolved.
- Upgrade targets are queried and compatible, not supplied by a mock catalog.
- Manifest and lockfile changes are reviewed together.
- Tests and rollback evidence identify the exact changed revision.
- The report separates fixed, accepted, deferred, and unavailable items.

## Reference Entry Points

- npm audit: https://docs.npmjs.com/cli/commands/npm-audit
- pip-audit: https://pypi.org/project/pip-audit/
- RustSec and cargo audit: https://rustsec.org/
- Go module reference: https://go.dev/ref/mod

Read current tool documentation when executing an audit; this skill does not
embed a security database or promise that any package is presently safe.
