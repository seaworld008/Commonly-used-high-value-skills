# Input Guard

A defensive security skill that scans untrusted external text for embedded prompt injection attacks targeting AI agents. Pure Python with zero external dependencies.

## Features

- **16 detection categories** covering instruction override, role manipulation, system mimicry, jailbreak attempts, data exfiltration, dangerous commands, token smuggling, emotional manipulation, and more
- **LLM-powered scanning** — optional second layer using OpenAI or Anthropic for semantic analysis of evasive attacks
- **Multi-language support** for English, Korean, Japanese, and Chinese patterns
- **4 sensitivity levels**: `low`, `medium` (default), `high`, `paranoid`
- **Multiple output formats**: human-readable, JSON, quiet mode
- **No external dependencies** for pattern scanning — `requests` only needed for `--llm` modes
- **Optional MoltThreats integration** for community threat reporting

## Prerequisites

- **Python 3** — check with `python3 --version`
- **pip** (only needed for LLM scanning) — check with `pip3 --version` or `python3 -m pip --version`

Pattern-based scanning uses only the Python standard library and has **zero external dependencies**. pip is only required if you want to install `requests` for `--llm` modes.

If pip is not installed and you need LLM scanning:
```bash
# Option 1: System package manager (requires sudo)
sudo apt-get install python3-pip        # Debian/Ubuntu
brew install python3                     # macOS (includes pip)

# Option 2: Bootstrap pip without sudo
python3 -m ensurepip --upgrade
```

## Quick Start

```bash
# Inline text
bash scripts/scan.sh "text to check"

# From file
bash scripts/scan.sh --file /tmp/content.txt

# From pipe
echo "content" | bash scripts/scan.sh --stdin

# JSON output
bash scripts/scan.sh --json "text to check"

# High sensitivity
python3 scripts/scan.py --sensitivity high "text to check"

# Pattern + LLM scan (requires OPENAI_API_KEY or ANTHROPIC_API_KEY)
python3 scripts/scan.py --llm "text to check"

# LLM-only analysis
python3 scripts/scan.py --llm-only "text to check"

# Auto-escalate to LLM on MEDIUM+ findings
python3 scripts/scan.py --llm-auto "text to check"

# Send alert via configured OpenClaw channel on MEDIUM+
OPENCLAW_ALERT_CHANNEL=slack python3 scripts/scan.py --alert "text to check"

# Alert only on HIGH/CRITICAL
OPENCLAW_ALERT_CHANNEL=slack python3 scripts/scan.py --alert --alert-threshold HIGH "text to check"
```

## Severity Levels

| Level | Score | Exit Code | Action |
|-------|-------|-----------|--------|
| SAFE | 0 | 0 | Process normally |
| LOW | 1-25 | 0 | Log for awareness |
| MEDIUM | 26-50 | 1 | Stop, alert human |
| HIGH | 51-80 | 1 | Stop, alert human |
| CRITICAL | 81-100 | 1 | Stop, urgent alert |

## When to Use

Run Input Guard **before** processing text from:

- Web pages (fetched content, browser snapshots)
- Social media posts and search results
- Web search results
- Third-party API responses
- Any externally-sourced text

## Workflow

```
Fetch external content → Scan with Input Guard → Check severity
  ├─ SAFE/LOW    → Proceed normally
  └─ MEDIUM+     → Block content, alert human, optionally report
```

## Detection Categories

1. Instruction Override
2. Role Manipulation
3. System Mimicry
4. Jailbreak Attempts
5. Guardrail Bypass
6. Data Exfiltration
7. Dangerous Commands
8. Authority Impersonation
9. Context Hijacking
10. Token Smuggling
11. Safety Bypass
12. Agent Sovereignty Manipulation
13. Call to Action
14. Emotional Manipulation
15. JSON Injection
16. Prompt Extraction

## Project Structure

```
input-guard/
├── SKILL.md                    # Skill documentation
├── INTEGRATION.md              # Integration guide
├── TESTING.md                  # Eval approach and results
├── README.md                   # This file
├── CHANGELOG.md                # Version history
├── taxonomy.json               # Shipped MoltThreats taxonomy (offline LLM scanning)
├── requirements.txt            # Python dependencies (requests)
├── scripts/
│   ├── scan.py                 # Core scanner (Python 3)
│   ├── scan.sh                 # Shell wrapper
│   ├── llm_scanner.py          # LLM-powered analysis module
│   ├── get_taxonomy.py         # Taxonomy loader / refresher
│   └── report-to-molthreats.sh # Community threat reporting
└── evals/
    ├── cases.json              # Test cases (safe, pattern, evasive)
    └── run.py                  # Eval runner
```

## Development

### Setup

```bash
# Clone the skill
cd input-guard

# Install dependencies (only needed for LLM scanning)
pip install -r requirements.txt

# Set up environment variables (create .env in the repo root with your API keys)
```

### Environment Variables

| Variable | Required For | Description |
|----------|-------------|-------------|
| `OPENAI_API_KEY` | LLM scanning | OpenAI API key (uses gpt-4o-mini) |
| `ANTHROPIC_API_KEY` | LLM scanning | Anthropic API key (alternative to OpenAI) |
| `PROMPTINTEL_API_KEY` | Taxonomy refresh, reporting | MoltThreats / PromptIntel API key |
| `OPENCLAW_ALERT_CHANNEL` | Alerts | OpenClaw channel name for alerts |
| `OPENCLAW_ALERT_TO` | Alerts | Optional recipient/target for channels that require one |

Pattern-based scanning requires **no keys** — it works out of the box with Python 3.

### Running Evals

```bash
# Pattern-only tests (fast, no API calls, ~1.5s)
python3 evals/run.py

# Include LLM tests for evasive attack cases (~20s)
python3 evals/run.py --llm

# Verbose output (scores, model info, reasoning)
python3 evals/run.py --llm --verbose

# Filter by category
python3 evals/run.py --category safe
python3 evals/run.py --category pattern
python3 evals/run.py --category evasive --llm

# Run a single test case
python3 evals/run.py --id emerald-box --llm --verbose

# Machine-readable output
python3 evals/run.py --json
```

### Test Categories

| Category | Count | Description |
|----------|-------|-------------|
| `safe` | 3 | Benign content — must score SAFE |
| `pattern` | 17 | Explicit attacks — must be caught by pattern matching |
| `evasive` | 5 | Subtle attacks — patterns expected to miss, LLM should catch |

### Adding Test Cases

Add entries to `evals/cases.json`:

```json
{
  "id": "my-new-test",
  "category": "pattern",
  "description": "What this tests",
  "text": "The text to scan",
  "expected_min_severity": "HIGH",
  "expected_max_severity": "CRITICAL"
}
```

For evasive cases (LLM-required):

```json
{
  "id": "my-evasive-test",
  "category": "evasive",
  "description": "Subtle attack patterns miss",
  "text": "The evasive text",
  "pattern_expected": "SAFE",
  "llm_expected_min_severity": "MEDIUM",
  "llm_expected_max_severity": "CRITICAL"
}
```

## Documentation

- **[SKILL.md](SKILL.md)** — Full skill specification, configuration, and agent integration patterns
- **[INTEGRATION.md](INTEGRATION.md)** — Detailed integration guide with workflow examples
- **[TESTING.md](TESTING.md)** — Eval approach, test categories, and latest results

## Uninstalling

### 1. Remove the AGENTS.md section

During installation, the following section was added to your workspace `AGENTS.md`:

- `## Input Guard — Prompt Injection Scanning`

Delete the entire section (including the workflow, alert format, and MoltThreats reporting subsections).

### 2. Remove the skill directory

```bash
rm -rf skills/input-guard
```

### 3. Clean up environment variables

Remove from your `.env` (if no other skill uses them):
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `PROMPTINTEL_API_KEY`
- `OPENCLAW_ALERT_CHANNEL`
- `OPENCLAW_ALERT_TO`

input-guard does not create any files in the workspace outside its own directory. The `taxonomy.json` file lives inside the skill directory and is removed with it.

## Credits

Inspired by [prompt-guard](https://github.com/seojoonkim) by seojoonkim.

## License

See repository root for license information.
