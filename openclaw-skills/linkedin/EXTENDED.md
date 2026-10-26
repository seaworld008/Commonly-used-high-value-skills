# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

### Fetch a Company

```bash
linkedin company fetch <url> [flags] --json -q
```

Optional flags:
- `--employees` – include employees
- `--dms` – include decision makers
- `--posts` – include company posts

Employee filters (require `--employees`):

| Flag | Description |
|------|-------------|
| `--employees-limit` | Max employees to retrieve |
| `--employees-first-name` | Filter by first name |
| `--employees-last-name` | Filter by last name |
| `--employees-position` | Filter by position |
| `--employees-locations` | Comma-separated locations |
| `--employees-industries` | Comma-separated industries |
| `--employees-schools` | Comma-separated school names |
| `--employees-connection-degrees` | Comma-separated connection degrees: `1st`, `2nd`, `3rd+` |

| Flag | Description |
|------|-------------|
| `--dms-limit` | Max decision makers to retrieve (requires `--dms`) |
| `--posts-limit` | Max posts to retrieve (requires `--posts`) |
| `--posts-since` | Posts since ISO timestamp (requires `--posts`) |

```bash
# Basic company info
linkedin company fetch https://www.linkedin.com/company/name --json -q

# With employees filtered by position
linkedin company fetch https://www.linkedin.com/company/name --employees --employees-position "Engineer" --json -q

# With decision makers and posts
linkedin company fetch https://www.linkedin.com/company/name --dms --posts --posts-limit 10 --json -q
```

<a id="section-2"></a>

#### Fetch company

```bash
linkedin navigator company fetch <hashed-url> [flags] --json -q
```

Optional flags:
- `--employees` – include employees
- `--dms` – include decision makers

Employee filters (require `--employees`):

| Flag | Description |
|------|-------------|
| `--employees-limit` | Max employees to retrieve |
| `--employees-first-name` | Filter by first name |
| `--employees-last-name` | Filter by last name |
| `--employees-positions` | Comma-separated positions |
| `--employees-locations` | Comma-separated locations |
| `--employees-industries` | Comma-separated industries |
| `--employees-schools` | Comma-separated school names |
| `--employees-years-of-experience` | Comma-separated experience ranges |
| `--employees-connection-degrees` | Comma-separated connection degrees: `1st`, `2nd`, `3rd+`, `groupMembers` |
| `--dms-limit` | Max decision makers to retrieve (requires `--dms`) |

```bash
linkedin navigator company fetch https://www.linkedin.com/sales/company/97ural --employees --dms --json -q
linkedin navigator company fetch https://www.linkedin.com/sales/company/97ural \
  --employees --employees-positions "Engineer,Designer" --employees-locations "Europe" --json -q
```

<a id="section-3"></a>

### Fetch a Person Profile

```bash
linkedin person fetch <url> [flags] --json -q
```

Optional flags to include additional data:
- `--experience` – work history
- `--education` – education history
- `--skills` – skills list
- `--languages` – languages
- `--posts` – recent posts (with `--posts-limit N`, `--posts-since TIMESTAMP`)
- `--comments` – recent comments (with `--comments-limit N`, `--comments-since TIMESTAMP`)
- `--reactions` – recent reactions (with `--reactions-limit N`, `--reactions-since TIMESTAMP`)

Only request additional data when needed – each flag increases execution time.

```bash
# Basic profile
linkedin person fetch https://www.linkedin.com/in/username --json -q

# With experience and education
linkedin person fetch https://www.linkedin.com/in/username --experience --education --json -q

# With last 5 posts
linkedin person fetch https://www.linkedin.com/in/username --posts --posts-limit 5 --json -q
```

<a id="section-4"></a>

## Output Format

Success:
```json
{"success": true, "data": {"name": "John Doe", "headline": "Engineer"}}
```

Error:
```json
{"success": false, "error": {"type": "personNotFound", "message": "Person not found"}}
```

Exit code 0 means the API call succeeded – always check the `success` field for the action outcome. Non-zero exit codes indicate infrastructure errors:

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success (check `success` field – action may have returned an error like "person not found") |
| 1 | General/unexpected error |
| 2 | Missing or invalid tokens |
| 3 | Subscription/plan required |
| 4 | LinkedIn account issue |
| 5 | Invalid arguments |
| 6 | Rate limited |
| 7 | Network error |
| 8 | Workflow timeout (workflowId returned for recovery) |


### Sales Navigator

Requires a LinkedIn Sales Navigator subscription. Uses hashed URLs for person/company lookups.

#### Fetch person

```bash
linkedin navigator person fetch <hashed-url> --json -q
```

#### Search people

```bash
linkedin navigator person search [flags] --json -q
```

| Flag | Description |
|------|-------------|
| `--term` | Search keyword or phrase |
| `--limit` | Max results |
| `--first-name` | Filter by first name |
| `--last-name` | Filter by last name |
| `--position` | Filter by job position |
| `--locations` | Comma-separated locations |
| `--industries` | Comma-separated industries |
| `--current-companies` | Comma-separated current company names |
| `--previous-companies` | Comma-separated previous company names |
| `--schools` | Comma-separated school names |
| `--years-of-experience` | Comma-separated ranges: `lessThanOne`, `oneToTwo`, `threeToFive`, `sixToTen`, `moreThanTen` |
| `--connection-degrees` | Comma-separated connection degrees: `1st`, `2nd`, `3rd+`, `groupMembers` |

```bash
linkedin navigator person search --term "VP Marketing" --locations "United States" --json -q
linkedin navigator person search --years-of-experience "moreThanTen" --position "CEO" --json -q
```

#### Fetch company

Read [the detailed procedure and examples](EXTENDED.md#section-2) when working on this part of the task.

#### Search companies

```bash
linkedin navigator company search [flags] --json -q
```

| Flag | Description |
|------|-------------|
| `--term` | Search keyword |
| `--limit` | Max results |
| `--sizes` | Comma-separated sizes: `1-10`, `11-50`, `51-200`, `201-500`, `501-1000`, `1001-5000`, `5001-10000`, `10001+` |
| `--locations` | Comma-separated locations |
| `--industries` | Comma-separated industries |
| `--revenue-min` | Min annual revenue in M USD: `0`, `0.5`, `1`, `2.5`, `5`, `10`, `20`, `50`, `100`, `500`, `1000` |
| `--revenue-max` | Max annual revenue in M USD: `0.5`, `1`, `2.5`, `5`, `10`, `20`, `50`, `100`, `500`, `1000`, `1000+` |

```bash
linkedin navigator company search --term "fintech" --sizes "11-50,51-200" --json -q
linkedin navigator company search --revenue-min 10 --revenue-max 100 --locations "United States" --json -q
```

#### Send InMail

```bash
linkedin navigator message send <person-url> '<text>' --subject '<subject>' --json -q
```

Text up to 1900 characters. Subject up to 80 characters.

```bash
linkedin navigator message send https://www.linkedin.com/in/username \
  'Would love to chat about API integrations' --subject 'Partnership Opportunity' --json -q
```

#### Get Sales Navigator conversation

```bash
linkedin navigator message get <person-url> [--since TIMESTAMP] --json -q
```

Prefer `linkedin inbox get --person <url> --type nv` to read Sales Navigator messages; use this only when you need the person's earlier history.


### Statistics

```bash
# Social Selling Index
linkedin stats ssi --json -q

# Performance analytics (profile views, post impressions, search appearances)
linkedin stats performance --json -q

# API usage for a date range
linkedin stats usage --start 2024-01-01T00:00:00Z --end 2024-01-31T00:00:00Z --json -q

# Who viewed your profile
linkedin stats viewers --limit 50 --json -q

# Only views since a moment
linkedin stats viewers --since 2026-08-01T00:00:00Z --json -q
```

Each viewer is either `identified` — carrying `name`, `publicUrl` and `urn` (a member URN, `null`
when LinkedIn does not expose it) — or `anonymous`, carrying only the `description` LinkedIn showed
and a `searchUrl` you can pass to `linkedin person search --url` to look for them. Viewers come
newest first, and `viewedAt` is an estimate derived from the relative age LinkedIn displays.
