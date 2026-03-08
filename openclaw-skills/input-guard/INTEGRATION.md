# Input Guard + MoltThreats Integration

Complete workflow for detecting and optionally reporting prompt injection attacks.

## Workflow Overview

```
External Content
      ↓
   Fetch
      ↓
  Scan (input-guard)
      ↓
  MEDIUM/HIGH/CRITICAL?
      ↓
  Block Content
      ↓
  Channel Alert to Human
      ↓
  "Report to MoltThreats?"
      ↓
Human replies "yes"
      ↓
  Submit to MoltThreats API
      ↓
  Community Protection
```

## Example: Web Article Scan

### 1. Fetch Content

```bash
ARTICLE_URL="https://suspicious-site.com/article"
CONTENT=$(curl -s "$ARTICLE_URL")
```

### 2. Scan with Input Guard

```bash
SCAN_OUTPUT=$(python3 skills/input-guard/scripts/scan.py --quiet "$CONTENT")
SEVERITY=$(echo "$SCAN_OUTPUT" | awk '{print $1}')
SCORE=$(echo "$SCAN_OUTPUT" | awk '{print $2}')
```

### 3. Check Severity

```bash
if [[ "$SEVERITY" == "MEDIUM" || "$SEVERITY" == "HIGH" || "$SEVERITY" == "CRITICAL" ]]; then
    # STOP processing - send alert
    echo "⚠️ Threat detected: $SEVERITY (score: $SCORE)"
fi
```

### 4. Agent Sends Channel Alert

```
🛡️ Input Guard Alert: HIGH
Source: https://suspicious-site.com/article
Finding: Prompt injection detected - SYSTEM_INSTRUCTION pattern followed by role override
Action: Content blocked, skipping this source.

Report to MoltThreats? Reply "yes" to share this threat with the community.
```

### 5. Human Replies "yes"

Agent runs:

```bash
bash skills/input-guard/scripts/report-to-molthreats.sh \
  "HIGH" \
  "https://suspicious-site.com/article" \
  "Prompt injection detected - SYSTEM_INSTRUCTION pattern followed by role override"
```

### 6. Report Submitted

```
🔒 Reporting to MoltThreats...

Title: Prompt injection detected - SYSTEM_INSTRUCTION pattern followed by role overrid
Category: prompt
Severity: high
Source: https://suspicious-site.com/article

✅ Report submitted to MoltThreats
Report ID: 0b5291de-9970-4e91-81f7-6efdf0c159cc
```

## Severity Mapping

| Input Guard | MoltThreats | Action |
|-------------|-------------|--------|
| CRITICAL | critical | Alert + offer report |
| HIGH | high | Alert + offer report |
| MEDIUM | medium | Alert + offer report |
| LOW | - | Log only (no alert) |
| SAFE | - | Proceed normally |

## Agent Implementation

```python
# After fetching external content
scan_result = scan_with_input_guard(content)

if scan_result.severity in ["MEDIUM", "HIGH", "CRITICAL"]:
    # Block content
    blocked = True

    # Send channel alert
    send_channel_alert(f"""🛡️ Input Guard Alert: {scan_result.severity}
Source: {source_url}
Finding: {scan_result.findings}
Action: Content blocked, skipping this source.

Report to MoltThreats? Reply "yes" to share this threat with the community.
""")

    # Wait for the human to decide on reporting
    # If "yes" → run report-to-molthreats.sh
```

## Benefits

1. **Immediate Protection** - Content blocked before processing
2. **Human Decision** - The human controls what gets reported publicly
3. **Community Defense** - Shared threats protect other agents
4. **No False Positives Shared** - Only confirmed threats reported
5. **Full Context** - Reports include source URL and detection details

## Rate Limits

- **Input Guard**: No limits (local scanning)
- **MoltThreats Reports**: 5/hour, 20/day
- **Channel Alerts**: No limits

Choose reporting wisely for high-confidence detections.
