---
name: openai-docs
description: 'Use when the user asks how to build with OpenAI products or APIs and needs current official documentation with citations, including Codex, Responses API, Chat Completions, Apps SDK, Agents SDK, Realtime, model capabilities, limits, or migrations; prioritize an available official OpenAI documentation connector and restrict fallback browsing to official OpenAI domains.'
zh_description: "用于查阅和应用 OpenAI 官方文档、API 行为和集成指南。"
version: "1.0.1"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["agent", "ai", "docs", "openai"]'
created_at: "2026-03-04"
updated_at: "2026-08-10"
quality: 3
complexity: "intermediate"
---

# OpenAI Docs

Provide authoritative, current guidance from OpenAI developer docs. Prefer the
official documentation connector exposed by the current client. If no such
connector is available or it returns no meaningful results, fall back to web
search restricted to official OpenAI domains.

## When to Use

Use this skill when the user asks about:

- OpenAI APIs or SDKs
- model capabilities, limits, or migration guidance
- Codex, Responses API, Chat Completions, Realtime, Agents SDK, or Apps SDK
- official OpenAI setup instructions where current docs matter

Do not use this skill when:

- the task is general coding help with no OpenAI product dependency
- the user only wants speculative comparison without needing official guidance

## Usage

Preferred flow:

```text
search official docs
-> fetch exact page or section
-> answer with citation
-> only fall back to official-domain web search if MCP docs fail
```

## Quick start

- Use the connector's documentation search operation to find relevant pages.
- Use its page-fetch operation to retrieve exact sections for accurate
  paraphrases and citations.
- Use its browse/list operation only when no precise query is available.

Example:

```text
1. Search docs for "Responses API tool calling"
2. Fetch the best page
3. Cite the fetched URL in the answer
4. If needed, fetch a narrower anchor section
```

## OpenAI product snapshots

1. Apps SDK: Build ChatGPT apps by providing a web component UI and an MCP server that exposes your app's tools to ChatGPT.
2. Responses API: A unified endpoint designed for stateful, multimodal, tool-using interactions in agentic workflows.
3. Chat Completions API: Generate a model response from a list of messages comprising a conversation.
4. Codex: OpenAI's coding agent for software development that can write, understand, review, and debug code.
5. gpt-oss: Open-weight OpenAI reasoning models (gpt-oss-120b and gpt-oss-20b) released under the Apache 2.0 license.
6. Realtime API: Build low-latency, multimodal experiences including natural speech-to-speech conversations.
7. Agents SDK: A toolkit for building agentic apps where a model can use tools and context, hand off to other agents, stream partial results, and keep a full trace.

## If the documentation connector is missing

Continue with official-domain web search unless the user explicitly asks to
install or configure a connector. Do not invent connector-specific operation
names or pause an otherwise answerable documentation task for installation.

## Workflow

1. Clarify the product scope (Codex, OpenAI API, or ChatGPT Apps SDK) and the task.
2. Search docs with a precise query.
3. Fetch the best page and the specific section needed (use `anchor` when possible).
4. Answer with concise guidance and cite the doc source.
5. Provide code snippets only when the docs support them.

## Quality rules

- Treat OpenAI docs as the source of truth; avoid speculation.
- Keep quotes short and within policy limits; prefer paraphrase with citations.
- If multiple pages differ, call out the difference and cite both.
- If docs do not cover the user’s need, say so and offer next steps.

## Tooling notes

- Always use the available official docs connector before web search for
  OpenAI-related questions.
- If the connector returns no meaningful results, use web search as a fallback.
- When falling back to web search, restrict to official OpenAI domains (developers.openai.com, platform.openai.com) and cite sources.

## Common Pitfalls

- answering from memory when the docs should be checked
- mixing official guidance with uncited third-party blog claims
- using broad web search before trying the docs MCP tools
- giving model or feature guidance without current source attribution
