---
name: openai-docs
description: 'Use when the user asks how to build with OpenAI products or APIs and needs up-to-date official documentation with citations (for example: Codex, Responses API, Chat Completions, Apps SDK, Agents SDK, Realtime, model capabilities or limits); prioritize OpenAI docs MCP tools and restrict any fallback browsing to official OpenAI domains.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["agent", "ai", "docs", "openai"]'
created_at: "2026-03-04"
updated_at: "2026-03-20"
quality: 3
complexity: "intermediate"
---

# OpenAI Docs

Provide authoritative, current guidance from OpenAI developer docs using the developers.openai.com MCP server. Always prioritize the developer docs MCP tools over web.run for OpenAI-related questions. Only if the MCP server is installed and returns no meaningful results should you fall back to web search.

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

- Use `mcp__openaiDeveloperDocs__search_openai_docs` to find the most relevant doc pages.
- Use `mcp__openaiDeveloperDocs__fetch_openai_doc` to pull exact sections and quote/paraphrase accurately.
- Use `mcp__openaiDeveloperDocs__list_openai_docs` only when you need to browse or discover pages without a clear query.

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

## If MCP server is missing

If MCP tools fail or no OpenAI docs resources are available:

1. Run the install command yourself: `codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp`
2. If it fails due to permissions/sandboxing, immediately retry the same command with escalated permissions and include a 1-sentence justification for approval. Do not ask the user to run it yet.
3. Only if the escalated attempt fails, ask the user to run the install command.
4. Ask the user to restart Codex.
5. Re-run the doc search/fetch after restart.

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

- Always use MCP doc tools before any web search for OpenAI-related questions.
- If the MCP server is installed but returns no meaningful results, then use web search as a fallback.
- When falling back to web search, restrict to official OpenAI domains (developers.openai.com, platform.openai.com) and cite sources.

## Common Pitfalls

- answering from memory when the docs should be checked
- mixing official guidance with uncited third-party blog claims
- using broad web search before trying the docs MCP tools
- giving model or feature guidance without current source attribution
