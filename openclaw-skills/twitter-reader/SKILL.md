---
name: twitter-reader
description: 'Fetch Twitter/X post content by URL using jina.ai API to bypass JavaScript restrictions. Use when Claude needs to retrieve tweet content including author, timestamp, post text, images, and thread replies. Supports individual posts or batch fetching from x.com or twitter.com URLs.'
zh_description: "用于通过 URL 抓取 Twitter/X 帖子内容、作者、时间、图片和线程回复。"
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["growth", "marketing", "reader", "twitter"]'
created_at: "2026-03-04"
updated_at: "2026-06-29"
quality: 3
complexity: "intermediate"
---

# Twitter Reader

Fetch Twitter/X post content without needing JavaScript or authentication.

## Prerequisites

You need a Jina API key to use this skill:

1. Visit https://jina.ai/ to sign up (free tier available)
2. Get your API key from the dashboard
3. Set the environment variable:

```bash
export JINA_API_KEY="your_api_key_here"
```

## Quick Start

For a single tweet, use curl directly:

```bash
curl "https://r.jina.ai/https://x.com/USER/status/ID" \
  -H "Authorization: Bearer ${JINA_API_KEY}"
```

For multiple tweets, use the bundled script:

```bash
scripts/fetch_tweets.sh url1 url2 url3
```

## What Gets Returned

- **Title**: Post author and content preview
- **URL Source**: Original tweet link
- **Published Time**: GMT timestamp
- **Markdown Content**: Full post text with media descriptions

## Bundled Scripts

### fetch_tweet.py

Python script for fetching individual tweets.

```bash
python scripts/fetch_tweet.py https://x.com/user/status/123 output.md
```

### fetch_tweets.sh

Bash script for batch fetching multiple tweets.

```bash
scripts/fetch_tweets.sh \
  "https://x.com/user/status/123" \
  "https://x.com/user/status/456"
```

## URL Formats Supported

- `https://x.com/USER/status/ID`
- `https://twitter.com/USER/status/ID`
- `https://x.com/...` (redirects work automatically)

## Environment Variables

- `JINA_API_KEY`: Required. Your Jina.ai API key for accessing the reader API

## Usage Guidelines

Use this skill for retrieval, not for engagement automation. It is appropriate when the user needs to quote, summarize, archive, or analyze X/Twitter content from one or more URLs. It is not appropriate for liking, reposting, following, scraping private content, or bypassing access controls.

## Verification Checklist

Before relying on fetched content:

- Confirm the URL points to a public post and not an account, search page, or deleted status.
- Preserve the original URL in the output for traceability.
- Record the fetch time when posts may change or be deleted.
- Distinguish post text from media descriptions and quoted-post content.
- For threads, keep reply order and author identity clear.
- If Jina returns an error or partial content, report that limitation instead of filling gaps from memory.

## Output Pattern

For analysis tasks, return:

```text
Source URL:
Author:
Published:
Post text:
Media / quoted content:
Notes or caveats:
```

## Batch Analysis Pattern

For multiple URLs, normalize each result before summarizing:

- Keep one record per source URL.
- Deduplicate retweets, quote tweets, and repeated thread fragments.
- Preserve author handles so later claims can be traced.
- Flag missing, deleted, protected, or partially fetched posts.
- Separate factual extraction from sentiment, topic clustering, or growth recommendations.

## Risk Notes

Twitter/X content is volatile. Posts may be edited, deleted, restricted, or regionally unavailable after retrieval. Do not present fetched content as permanent evidence unless the user has asked for archiving and the original URL plus fetch timestamp are retained. Avoid inferring private context from a public post; summarize only the retrieved content and clearly label any interpretation.
