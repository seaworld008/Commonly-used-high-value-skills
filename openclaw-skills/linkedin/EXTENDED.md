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
