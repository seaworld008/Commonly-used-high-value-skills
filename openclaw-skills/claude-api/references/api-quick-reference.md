# Claude API Feature Quick References

Extracted companion quick references from `SKILL.md` for Anthropic SDK and REST integrations. Read only the section matching your integration task.

## Table of Contents

- [Authentication](#authentication-quick-reference)
- [Thinking & Effort](#thinking--effort-quick-reference)
- [Compaction](#compaction-quick-reference)
- [Prompt Caching](#prompt-caching-quick-reference)
- [Fast Mode](#fast-mode-quick-reference)
- [Task Budgets](#task-budgets-quick-reference)
- [Provider Clients (Bedrock, Foundry, Vertex)](#provider-clients-quick-reference)
- [Context Editing](#context-editing-quick-reference)
- [Mid-Conversation System Messages](#mid-conversation-system-messages-quick-reference)
- [Server Tools](#server-tools-quick-reference)
- [Document & File Input](#document--file-input-quick-reference)
- [Tool Use Patterns](#tool-use-patterns-quick-reference)
- [Other API Surfaces](#other-api-surfaces-quick-reference)
- [Workload Identity Federation](#workload-identity-federation-quick-reference)

---

## Authentication (Quick Reference)

**An unset `ANTHROPIC_API_KEY` does NOT mean there are no credentials.** The SDKs and the `ant` CLI resolve credentials in this order (first match wins): `ANTHROPIC_API_KEY` -> `ANTHROPIC_AUTH_TOKEN` -> the `ANTHROPIC_PROFILE`-selected or active OAuth profile from `ant auth login` -> Workload Identity Federation env vars -> the default profile on disk. A bare `Anthropic()` / `new Anthropic()` / `anthropic.NewClient()` works after `ant auth login` with no env var set.

**When you need to call the API and `ANTHROPIC_API_KEY` is unset, don't ask the user for a key.** First run `ant auth status` - it shows which credential source and profile is active. If it reports an active profile:

- **SDK code or `ant` CLI:** just run it. The zero-arg client constructor and every `ant ...` subcommand pick up the profile automatically - no env var needed.
- **Raw `curl` / HTTP:** get a short-lived token with `ant auth print-credentials --access-token` and send it as `Authorization: Bearer <token>` **plus** the header `anthropic-beta: oauth-2025-04-20` (OAuth tokens go on `Authorization: Bearer`, not `x-api-key:` - converting a curl from an API key is a header change, not a key swap). Always pass `--access-token`; the no-flag form prints JSON, not a bare token.

Only ask the user for a key if `ant auth status` reports no active credential source (or `ant` itself isn't installed). Suggest `ant auth login` as the first option - it stores a profile under `~/.config/anthropic/` that the SDKs read automatically - and an exported `ANTHROPIC_API_KEY` as the alternative.

Full auth details (named profiles, scopes, the API-key-shadows-profile trap, refresh-token expiry): `shared/anthropic-cli.md`.

---

## Thinking & Effort (Quick Reference)

Use adaptive thinking (`thinking: {type: "adaptive"}`) on every current model except Haiku 4.5, which still takes `budget_tokens` (table below) - Claude dynamically decides when and how much to think. Per-model rules:

| Model | Thinking config | Omitting `thinking` | `budget_tokens` | Sampling (`temperature`/`top_p`/`top_k`) | Effort levels |
|---|---|---|---|---|---|
| Fable 5 / Claude Fable 5.1 (and the Mythos counterparts) | `{type: "adaptive"}` or omit; explicit `{type: "disabled"}` returns 400 - omit the param instead (Claude Fable 5.1 / Claude Mythos 5.1 also 400 on forced `tool_choice` `any`/`tool`; Claude Fable 5.1 runs preserved thinking's history-editing check on replayed thinking blocks, Claude Mythos 5.1 does not) | Runs adaptive (thinking is always on) | Removed - `{type: "enabled", budget_tokens: N}` returns 400 | Removed - 400 | `low`/`medium`/`high`/`xhigh`/`max` |
| Claude Opus 5.5 | `{type: "adaptive"}` or omit; `{type: "disabled"}` and `{type: "enabled", budget_tokens}` return 400 at **every** effort level - omit the param and lower effort instead (also 400s on forced `tool_choice` `any`/`tool`, and runs preserved thinking - see `shared/model-migration.md` -> Migrating to Claude Opus 5.5) | Runs **adaptive** | Removed - 400 | Removed - 400 | `low`/`medium`/`high`/`xhigh`/`max` - **default `medium`** (not `high`); per-message effort (beta) supported |
| Claude Opus 5 | `{type: "adaptive"}` or omit; `{type: "disabled"}` accepted **only at effort `high` or below** - 400 at `xhigh`/`max`, and see the disabled-thinking pitfall below | Runs **adaptive** (thinking is on by default - unlike Opus 4.8/4.7) | Removed - 400 | Removed - 400 | `low`-`max` (all five) |
| Opus 4.8 / 4.7 | `{type: "adaptive"}` is the only on-mode; `{type: "disabled"}` accepted | Runs **without** thinking - set `{type: "adaptive"}` explicitly | Removed - 400 | Removed - 400 | `low`/`medium`/`high`/`xhigh`/`max` |
| Claude Sonnet 5.5 | `{type: "adaptive"}` or omit; `{type: "disabled"}` returns 400 - to turn thinking off send `{type: "between_tools"}` (no other field; 400 at `xhigh`/`max`; effort can't change mid-conversation with it) (also 400s on forced `tool_choice` `any`/`tool`, and runs preserved thinking - see `shared/model-migration.md` -> Migrating to Claude Sonnet 5.5) | Runs **adaptive** | Removed - 400 | Non-default values - 400 | `low`/`medium`/`high`/`xhigh`/`max` - default `high`, levels recalibrated from Claude Sonnet 5; per-message effort (beta) supported with thinking on |
| Sonnet 5 | `{type: "adaptive"}` is the only on-mode; `{type: "disabled"}` accepted | Runs adaptive | Removed - 400 | Removed - 400 | `low`/`medium`/`high`/`xhigh`/`max` |
| Claude Haiku 5.5 | `{type: "adaptive"}` or omit; `disabled` only at `high` or below | Runs adaptive (on by default) | Removed - 400 | Non-default values - 400 | `low`-`max`, **default `medium`** |
| Opus 4.6 / Sonnet 4.6 | `{type: "adaptive"}` (recommended; auto-enables interleaved thinking, no beta header) | Set `{type: "adaptive"}` explicitly | Deprecated - do not use in new code; transitional escape hatch only (see below) | Allowed | `low`/`medium`/`high`/`max` (`xhigh` arrived with Opus 4.7) |
| Haiku 4.5; older models (Sonnet 4.5, ...) only if explicitly requested | `{type: "enabled", budget_tokens: N}` | No thinking | Required for thinking; must be less than `max_tokens`, minimum 1024 - errors otherwise | Allowed | `effort` works on Opus 4.5 (`low`/`medium`/`high` only - no `xhigh`/`max`); errors on Sonnet 4.5 / Haiku 4.5 |

Opus 4.8 keeps 4.7's request surface - see `shared/model-migration.md` -> Migrating to Opus 4.8 (and -> Migrating to Opus 4.7 from 4.6 or earlier). With `thinking` disabled, Opus 4.8 may write longer reasoning into the visible response - leave adaptive thinking on, or add a final-answer-only instruction.

- **Effort (GA, no beta header):** `output_config: {effort: "low"|"medium"|"high"|"xhigh"|"max"}` - inside `output_config`, not top-level; default `high` (equivalent to omitting it) on every current model except Claude Opus 5.5 and Claude Haiku 5.5, whose default is `medium` (thinking table above) - set it explicitly there. Controls thinking depth and overall token spend; combine with adaptive thinking for the best cost-quality tradeoffs. `xhigh` (added on Opus 4.7, between `high` and `max`) is the best setting for most coding and agentic use cases on Fable 5 / Opus 4.7/4.8 / Sonnet 5, and the default in Claude Code; effort matters more on those models than on any prior model in their tier - re-tune it when migrating, and run long-horizon/agentic tasks at `high`/`xhigh` with the full task spec given up front. Use a minimum of `high` for intelligence-sensitive work, `max` when correctness matters more than cost, and `low` for subagents or simple tasks - lower effort means fewer and more-consolidated tool calls, less preamble, and terser confirmations (`high` is often the sweet spot balancing quality and token efficiency).
- **Choosing an effort level (cost tuning):** Effort is the first quality-trading lever, after the free wins (caching first) - it trades thoroughness against token spend within one model, and the top of the range earns its cost only on hard problems (raise to `max` only when measurement shows headroom at the level below). Which workloads repay higher effort is a property of the workload: coding and long-horizon agentic work respond strongly; chat, classification, and high-volume or latency-sensitive routes often don't and do well at `low`, with `medium` as the cost-saving step-down where quality holds (the per-level defaults above cover the rest). Measure on a sample of real requests before raising a default, and tune per route rather than globally. Before building a multi-model cost cascade, measure the simpler alternative first - the most capable model at lower effort on the same tasks: lower effort on the newest models often matches or exceeds prior-generation performance at high effort (on Fable 5, lower effort often exceeds `xhigh` on prior models), and one model means one cache namespace (caches are model-scoped, so a cascade forfeits cache reuse across its models; a mid-conversation top-level `effort` change still invalidates the messages cache, though the per-message effort system message avoids that on Claude Fable 5.1 / Claude Mythos 5.1 / Claude Opus 5.5 / Claude Opus 5 / Claude Sonnet 5.5 / Claude Haiku 5.5 (with adaptive thinking) - `shared/prompt-caching.md` § Invalidation hierarchy). Judge cost per completed task, not per request - a cheaper request that needs more turns or retries to finish the job isn't cheaper. For the measured effort/cost tradeoffs by workload and the full lever order, `shared/cost-optimization.md` § 2.6.
- **Thinking display - `"omitted"` by default on Fable 5 / Claude Fable 5.1 / Mythos 5 / Claude Mythos 5.1 / Opus 5.5 / 5 / 4.8 / 4.7 / Sonnet 5 / Claude Sonnet 5.5 / Claude Haiku 5.5:** `display: "summarized"` returns a readable summary of the reasoning; `"omitted"` (the default on all eleven - a silent change from Opus 4.6 and Sonnet 4.6, where it was `"summarized"`) streams `thinking` blocks with empty text. `display` controls visibility only - thinking happens and is billed the same under every setting; the raw chain of thought is never exposed on any model. If you stream reasoning to users, the default looks like a long pause before output - set `thinking: {type: "adaptive", display: "summarized"}` explicitly. (Independent of display, echo thinking blocks back unchanged when continuing on the same model; other models silently ignore them (Claude Fable 5.1 / Claude Mythos 5.1 read them, and Claude Sonnet 5.5 reads Claude Sonnet 5, Opus 4.8, Claude Haiku 5.5 / Haiku 4.5, and earlier models' blocks) - see the migration guide.) On Claude Fable 5.1 / Claude Mythos 5.1 / Claude Fable 5 / Claude Opus 5.5 / Claude Sonnet 5.5, `display: "updates"` (beta `thinking-display-updates-2026-08-18`, every platform) hides reasoning like `"omitted"` but returns the model's between-tool-call progress notes as short `thinking` block summaries - see `shared/model-migration.md` -> Migrating to Claude Fable 5.1 from Claude Fable 5 -> New API features.
- **When the user asks for "extended thinking", a "thinking budget", or `budget_tokens`:** always use Fable 5/5.1, Opus 5.5, 5, 4.8, 4.7, or 4.6 with `thinking: {type: "adaptive"}` - the fixed thinking-token-budget concept is deprecated and adaptive thinking replaces it. Do NOT use `budget_tokens` for new 4.6/4.7/4.8 code and do NOT switch to an older model just because the user mentions it. *Gradual-migration carve-out:* `budget_tokens` is still functional on Opus 4.6 and Sonnet 4.6 only, as a transitional escape hatch for existing code that needs a hard token ceiling before you've tuned `effort` - see `shared/model-migration.md` -> Transitional escape hatch. It is fully removed on Fable 5/5.1, Opus 5.5/5/4.7/4.8, Sonnet 5.5/5, and Haiku 5.5.

---

## Compaction (Quick Reference)

**Beta, Fable 5/5.1, Opus 5.5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5.5, Sonnet 5, Sonnet 4.6, and Claude Haiku 5.5.** For long-running conversations that may exceed the 1M context window, enable server-side compaction. The API automatically summarizes earlier context when it approaches the trigger threshold (default: 150K tokens). Requires beta header `compact-2026-01-12`.

**Critical:** Append `response.content` (not just the text) back to your messages on every turn. Compaction blocks in the response must be preserved - the API uses them to replace the compacted history on the next request. Extracting only the text string and appending that will silently lose the compaction state.

See `{lang}/claude-api/README.md` (Compaction section) for code examples. Full docs via WebFetch in `shared/live-sources.md`.

---

## Prompt Caching (Quick Reference)

**Prefix match.** Any byte change anywhere in the prefix invalidates everything after it. Render order is `tools` -> `system` -> `messages`. Keep stable content first (frozen system prompt, deterministic tool list), put volatile content (timestamps, per-request IDs, varying questions) after the last `cache_control` breakpoint.

**Mid-conversation operator instructions** (Claude Opus 5, Claude Opus 5.5, Claude Opus 4.8, Claude Fable 5, Claude Fable 5.1, Claude Mythos 5, Claude Mythos 5.1, Claude Sonnet 5.5; not Claude Sonnet 5; no beta header): append `{"role": "system", ...}` to `messages[]` instead of editing top-level `system`. Preserves the cached history prefix and is the prompt-injection-safe operator channel. See `shared/prompt-caching.md` § Mid-conversation system messages.

**Top-level auto-caching** (`cache_control: {type: "ephemeral"}` on `messages.create()`) is the simplest option when you don't need fine-grained placement. Max 4 breakpoints per request. Minimum cacheable prefix is model-dependent (512-4096 tokens - see `shared/prompt-caching.md` § API reference) - shorter prefixes silently won't cache.

**Verify with `usage.cache_read_input_tokens`** - if it's zero across repeated requests, a silent invalidator is at work (`datetime.now()` in system prompt, unsorted JSON, varying tool set).

For placement patterns, architectural guidance, and the silent-invalidator audit checklist: read `shared/prompt-caching.md`. Language-specific syntax: `{lang}/claude-api/README.md` (Prompt Caching section).

---

## Fast Mode (Quick Reference)

**Research preview, Claude Opus 5 / Claude Opus 5.5 / Opus 4.8 only** - Claude API and Managed Agents, not Bedrock / Google Cloud / Foundry. Opus 4.7 fast mode has been removed: `speed: "fast"` on 4.7 returns an error. Fast mode on Claude Opus 5 is priced at $10 / $50 per MTok; on Claude Opus 5.5, $8 / $40. Fast mode runs the same model at up to 2.5x higher output tokens per second, at premium pricing. Three things are required on every request: use the **beta** messages endpoint (`client.beta.messages....`), pass the beta flag `fast-mode-2026-02-01`, and set `speed: "fast"` as a top-level request parameter (not a header, not in `extra_body`).

```python
client.beta.messages.create(
    model="claude-opus-5-5", max_tokens=4096,
    speed="fast", betas=["fast-mode-2026-02-01"],
    messages=[...],
)
```

| Language | Beta flag | Speed parameter |
|---|---|---|
| Python | `betas=["fast-mode-2026-02-01"]` | `speed="fast"` |
| TypeScript / Ruby | `betas: ["fast-mode-2026-02-01"]` | `speed: "fast"` |
| Go | `[]anthropic.AnthropicBeta{anthropic.AnthropicBetaFastMode2026_02_01}` | `Speed: anthropic.BetaMessageNewParamsSpeedFast` |
| Java | `.addBeta(AnthropicBeta.FAST_MODE_2026_02_01)` | `.speed(MessageCreateParams.Speed.FAST)` |
| C# | `Betas = ["fast-mode-2026-02-01"]` | `Speed = Speed.Fast` (`Anthropic.Models.Beta.Messages`) |
| PHP | `betas: ['fast-mode-2026-02-01']` | `speed: 'fast'` |
| cURL | `anthropic-beta: fast-mode-2026-02-01` header | `"speed": "fast"` in body |

`response.usage.speed` reports which speed was used. Fast mode has its own rate limit separate from standard Opus; on 429, either retry after the `retry-after` delay or drop `speed` and fall back to standard (note: switching speed invalidates prompt cache). Not available with Batch API, Priority Tier, Claude Platform on AWS, or third-party platforms.

**Priority Tier is not supported on every current model.** It is supported on Claude Fable 5, Opus 4.8, and the older current models, but Claude Opus 5.5, Claude Opus 5, Claude Sonnet 5, Claude Sonnet 5.5, Claude Fable 5.1, Claude Mythos 5.1, Claude Mythos 5, and Mythos Preview are excluded - a Priority Tier request naming one of them fails validation.

---

## Task Budgets (Quick Reference)

**Beta, Claude Opus 5 / Claude Opus 5.5 / Fable 5 / Claude Fable 5.1 (confirm at launch) / Claude Sonnet 5.5 / Claude Haiku 5.5 / Opus 4.8 / 4.7 (not Claude Sonnet 5).** A task budget gives Claude a token ceiling for an agentic loop so it paces itself and finishes gracefully instead of being cut off - distinct from `max_tokens`, which is an enforced per-response ceiling the model is not aware of. Minimum `total`: 20,000. Set `task_budget` inside `output_config` on `client.beta.messages.stream(...)` with beta flag `task-budgets-2026-03-13` - use streaming so the large `max_tokens` doesn't hit HTTP timeouts (full details: `shared/model-migration.md` -> Task Budgets):

```python
with client.beta.messages.stream(
    model="claude-opus-5-5", max_tokens=128000,
    output_config={"effort": "high", "task_budget": {"type": "tokens", "total": 64000}},
    betas=["task-budgets-2026-03-13"],
    messages=[...], tools=[...],
) as stream:
    response = stream.get_final_message()
```

`task_budget` fields: `type` (always `"tokens"`), `total`, and optional `remaining` (defaults to `total`). The server injects a countdown marker Claude sees during generation; the budget counts what Claude generates and the tool results it reads this turn - **not** the full history you resend each request. Not the same thing as **Managed Agents session budgets** - those are hard, dollar-denominated, platform-enforced caps on one CMA session (`shared/managed-agents-core.md` § Session budgets); a task budget is advisory and token-denominated.

**Observing spend:** accumulate `response.usage.output_tokens` (plus the token count of the tool-result blocks you append) across loop iterations if you want to display progress. Leave `remaining` unset in the normal loop - the server tracks the countdown itself, and passing a client-computed `remaining` while also resending full history under-reports the budget. **Only pass `remaining`** when you compact or rewrite history between requests and the server can no longer derive prior spend.

---

## Provider Clients (Quick Reference)

When targeting Claude on a third-party platform, use that platform's dedicated client class - not the first-party `Anthropic()` client with a `base_url` override. After construction the client exposes the same `messages.create` / `.stream` surface as the first-party SDK.

### Amazon Bedrock

Use the **Mantle** client (Messages-API Bedrock endpoint). Bedrock model IDs take an `anthropic.` prefix (e.g. `"anthropic.claude-opus-5-5"`). Region is required.

| Language | Client |
|---|---|
| Python | `from anthropic import AnthropicBedrockMantle` -> `AnthropicBedrockMantle(aws_region="...")` |
| TypeScript | `import { AnthropicBedrockMantle } from "@anthropic-ai/bedrock-sdk"` -> `new AnthropicBedrockMantle({ awsRegion: "..." })` |
| Go | `bedrock.NewMantleClient(ctx, bedrock.MantleClientConfig{ AWSRegion: "..." })` |
| Java | `AnthropicOkHttpClient.builder().backend(BedrockMantleBackend.fromEnv()).build()` (from `com.anthropic.bedrock.backends`) |
| C# | `new AnthropicBedrockMantleClient(new() { AwsRegion = "..." })` (package `Anthropic.Bedrock`) |
| PHP | `use Anthropic\Bedrock\MantleClient;` -> `new MantleClient(awsRegion: '...')` |
| Ruby | `Anthropic::BedrockMantleClient.new(aws_region: "...")` |

`AnthropicBedrock` / `BedrockClient` / `BedrockBackend` (without `Mantle`) are the legacy `bedrock-runtime` InvokeModel path - prefer the Mantle client for new code.

### Microsoft Foundry

| Language | Client |
|---|---|
| Python | `from anthropic import AnthropicFoundry` -> `AnthropicFoundry(api_key=..., resource="...")` |
| TypeScript | `import AnthropicFoundry from "@anthropic-ai/foundry-sdk"` -> `new AnthropicFoundry({ ... })` |
| Java | `AnthropicOkHttpClient.builder().backend(FoundryBackend.fromEnv()).build()` (from `com.anthropic.foundry.backends`) |
| C# | `new AnthropicFoundryClient(new AnthropicFoundryApiKeyCredentials(...))` (package `Anthropic.Foundry`) |
| PHP | `Foundry\Client::withCredentials(...)` |

The Go and Ruby SDKs do not currently support Foundry. For Ruby, use the standard `Anthropic::Client.new(base_url: "<foundry endpoint>")` as a fallback (Entra ID auth is not built in). For Claude Platform on AWS, see `shared/claude-platform-on-aws.md`.

### Google Cloud Vertex AI

Two required constructor args: GCP `project_id` and `region`. Vertex model IDs take **no prefix** - current-generation models (Opus 5.5/5/4.8/4.7/4.6, Sonnet 5.5, Sonnet 5, Sonnet 4.6) use the bare first-party ID (e.g. `"claude-opus-5-5"`); dated-snapshot models use an `@` version separator (e.g. `claude-opus-4-5@20251101`, **not** `claude-opus-4-5-20251101`). Auth is GCP ADC (`gcloud auth application-default login`); no Anthropic API key. `region` can be `"global"` (recommended), a multi-region (`"us"`/`"eu"`), or a specific region. After construction, use the same `messages.create` / `.stream` surface.

| Language | Client |
|---|---|
| Python | `from anthropic import AnthropicVertex` -> `AnthropicVertex(project_id="...", region="...")` (install `"anthropic[vertex]"`) |
| TypeScript | `import { AnthropicVertex } from "@anthropic-ai/vertex-sdk"` -> `new AnthropicVertex({ projectId, region })` |
| Go | `import "github.com/anthropics/anthropic-sdk-go/vertex"` -> `anthropic.NewClient(vertex.WithGoogleAuth(ctx, region, projectID))` |
| Java | `AnthropicOkHttpClient.builder().backend(VertexBackend.builder().region("...").project("...").build()).build()` (from `com.anthropic.vertex.backends`) |
| C# | `new AnthropicClient { Backend = new VertexBackend(projectId, region) }` (package `Anthropic.Vertex`) |
| PHP | `use Anthropic\Vertex;` -> `Vertex\Client::fromEnvironment(location: '...', projectId: '...')` - note `location`, not `region` |
| Ruby | `Anthropic::VertexClient.new(region: "...", project_id: "...")` |

---

## Context Editing (Quick Reference)

**Beta.** Context editing **clears** old tool results or thinking blocks from the conversation before the model sees it; it is **not compaction** (which summarizes). On `client.beta.messages.*` with beta `context-management-2025-06-27`, pass `context_management.edits` with a strategy type:

```python
client.beta.messages.create(
    model="claude-opus-5-5", max_tokens=4096,
    betas=["context-management-2025-06-27"],
    context_management={"edits": [{"type": "clear_tool_uses_20250919"}]},
    tools=[...], messages=[...],
)
```

Strategy types: `clear_tool_uses_20250919` (clears old tool results; optional `clear_tool_inputs: true` also clears the tool_use params) and `clear_thinking_20251015` (clears thinking blocks). Do **not** use `compact_20260112` or beta `compact-2026-01-12` - those are the separate compaction feature.

---

## Mid-Conversation System Messages (Quick Reference)

**Claude Opus 5, Claude Opus 5.5, Claude Opus 4.8, Claude Fable 5, Claude Fable 5.1, Claude Mythos 5, Claude Mythos 5.1, Claude Sonnet 5.5, and Claude Haiku 5.5; not Claude Sonnet 5; no beta header.** Append `{"role": "system", "content": "..."}` to the `messages` array (not the top-level `system` field) to add an operator instruction mid-conversation without invalidating the cached prefix. Use the regular `client.messages.create` - there is no beta. A mid-conversation system message must follow a `user` message (or an `assistant` message ending in server-tool use), and must be either the last entry in `messages` or be followed by an `assistant` turn - it cannot be `messages[0]`. Availability: `shared/platform-availability.md`. See `shared/prompt-caching.md` § Mid-conversation system messages. A beta extension shipped with Claude Fable 5.1: `output_config: {effort: ...}` with `content: []` changes effort from that point on without a cache reset (beta `mid-conversation-output-config-2026-07-01`; Claude Fable 5.1, Claude Mythos 5.1, Claude Opus 5.5, Claude Opus 5, Claude Sonnet 5.5, and Claude Haiku 5.5 with thinking on; Claude API and Google Cloud). An effort-only message (empty `content`) is exempt from the placement rules above - it can sit anywhere in `messages`, including first or between an assistant turn and the next user turn; the rules apply to text and `clear_at` messages. For a per-turn reminder, give the message `clear_at: "next_user_message"` (beta `mid-conversation-system-clear-at-2026-08-21`): it renders for one turn, then stays in the transcript cleared - never delete earlier copies (on Claude Fable 5.1, Claude Opus 5.5, Claude Sonnet 5.5, and Claude Haiku 5.5 deleting one invalidates later thinking blocks); without the beta, a text block after the tool results, earlier copies kept. See `shared/model-migration.md` -> Migrating to Claude Fable 5.1 from Claude Fable 5 -> New API features.

---

## Server Tools (Quick Reference)

Server-side tools run on Anthropic's infrastructure - no client-side execution loop. Declare in `tools`; results arrive as content blocks in the same response. **No beta header** unless noted. **Prefer the latest type variant your model supports.** The `_20260209` web search / web fetch variants below (dynamic filtering) require Opus 5.5/5/4.8/4.7/4.6, Sonnet 5.5, Sonnet 5, or Sonnet 4.6; the basic variants for older models are listed after the table.

| Tool | `type` | `name` | Key optional params | Result block type |
|---|---|---|---|---|
| Web search | `web_search_20260209` | `web_search` | `max_uses`, `allowed_domains`/`blocked_domains`, `user_location` | `web_search_tool_result` -> `.content` is a list of `web_search_result` |
| Web fetch | `web_fetch_20260209` | `web_fetch` | `max_uses`, `allowed_domains`/`blocked_domains`, `citations`, `max_content_tokens` | `web_fetch_tool_result` -> `.content` is a `web_fetch_result` with a `document` block |
| Code execution | `code_execution_20260521` | `code_execution` | none | `bash_code_execution_tool_result` -> `.content.stdout` / `.stderr` / `.return_code` |
| Tool search (regex) | `tool_search_tool_regex_20251119` | `tool_search_tool_regex` | mark other tools `defer_loading: true` | `tool_search_tool_result` |
| Tool search (BM25) | `tool_search_tool_bm25_20251119` | `tool_search_tool_bm25` | mark other tools `defer_loading: true` | `tool_search_tool_result` |

`web_search_20260209` / `web_fetch_20260209` have built-in dynamic filtering - code execution runs under the hood, so do **not** separately declare `code_execution` in `tools` (a second execution environment confuses the model). For models older than Opus 4.6 / Sonnet 4.6, use the basic variants `web_search_20250305` / `web_fetch_20250910` instead; on Vertex AI only basic `web_search_20250305` is available. `code_execution_20260120` (REPL persistence + programmatic tool calling) runs on Opus 4.5+ / Sonnet 4.5+. **Go SDK only**: `code_execution_20260521` lives under `client.Beta.Messages.New` with `Betas: []anthropic.AnthropicBeta{"code-execution-2025-08-25"}` (other languages use plain `client.messages.create`); `code_execution_20260120` uses the non-beta `client.Messages.New` in Go like everywhere else. Web fetch only fetches URLs already present in the conversation. Provider availability varies by tool - see `shared/platform-availability.md`. See `shared/tool-use-concepts.md` for `pause_turn` handling.

## Document & File Input (Quick Reference)

**PDF (base64, no beta):** `{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": <b64 string>}}` in user content, placed before the text block. Base64 string must have no newlines. Limits: 32 MB request, 600 pages (100 for 200k-context models). Java: `ContentBlockParam.ofDocument(DocumentBlockParam... Base64PdfSource.builder().data(...))`.

**Files API (no beta):** upload via `client.files.upload(...)` -> response `id` is the `file_id`. Reference it as `{"type": "document", "source": {"type": "file", "file_id": "..."}}` for PDF/text, or `{"type": "image", ...}` for images - the content-block type must match the file's MIME type. To migrate code off `files-api-2025-04-14`, WebFetch the Files API row in `shared/live-sources.md`. Availability: `shared/platform-availability.md`.

**Citations (no beta):** set `citations: {enabled: true}` on each `document` content block (all or none). Response splits into multiple `text` blocks; cited blocks carry a `citations` array. Each citation has `cited_text`, `document_index`, `document_title`, and a location by `type`: `char_location` (`start_char_index`/`end_char_index`) for plain text, `page_location` (`start_page_number`/`end_page_number`, 1-indexed) for PDF, `content_block_location` for custom content. Incompatible with `output_config.format` (returns a 400).

## Tool Use Patterns (Quick Reference)

**Strict tool use (no beta):** set `strict: true` as a top-level field on the tool definition (alongside `name`/`description`/`input_schema`), **not** on `tool_choice`. Schema must have `additionalProperties: false` + `required`. Guarantees `tool_use.input` validates exactly. Go: `Strict: anthropic.Bool(true)` + `additionalProperties` via `InputSchema.ExtraFields`; Java: `.strict(true)` + `.putAdditionalProperty("additionalProperties", JsonValue.from(false))`.

**Parallel tool use (default on):** one assistant message may contain multiple `tool_use` blocks. Execute them concurrently, then return **all** `tool_result` blocks in a **single** user message - splitting them across multiple messages silently trains Claude to stop making parallel calls. For a failed tool, return `tool_result` with `is_error: true` - don't drop it.

**Tool Runner (SDK beta helper):** drives the tool-call loop for you via `client.beta.messages.*`. Python: `@beta_tool` decorator + `client.beta.messages.tool_runner(...)` -> `runner.until_done()`. TypeScript: `betaZodTool({...})` from `@anthropic-ai/sdk/helpers/beta/zod` + `client.beta.messages.toolRunner(...)` -> `await runner`. Go: `toolrunner.NewBetaToolFromJSONSchema(...)` + `client.Beta.Messages.NewToolRunner(...)` -> `.RunToCompletion(ctx)`. Java requires `.addBeta("structured-outputs-2025-11-13")`. Ruby: `Anthropic::BaseTool` subclass + `client.beta.messages.tool_runner(...)`. PHP: `BetaRunnableTool` + `->toolRunner(...)`. C#: raw JSON-schema tools + `BetaToolRunner` via `client.Beta.Messages.ToolRunner(...)`.

**Programmatic tool calling (no beta header):** Claude calls your custom tool from inside code execution. Add `{"type": "code_execution_20260120", "name": "code_execution"}` **and** set `"allowed_callers": ["code_execution_20260120"]` on your custom tool. Opus 4.5+ / Sonnet 4.5+ (availability: `shared/platform-availability.md`). When responding to a pending programmatic call, the user message must contain **only** `tool_result` blocks (no text). Not compatible with `strict: true`, `disable_parallel_tool_use`, forced `tool_choice`, or MCP tools.

## Other API Surfaces (Quick Reference)

**Message Batches (no beta; availability: `shared/platform-availability.md`):** `client.messages.batches.create(requests=[{custom_id, params}, ...])` -> poll `client.messages.batches.retrieve(id).processing_status` until `"ended"` -> stream `client.messages.batches.results(id)`. Each result has `.custom_id` + `.result.type` (`succeeded`/`errored`/`canceled`/`expired`); on success read `.result.message.content`. Python wraps requests as `Request(custom_id=..., params=MessageCreateParamsNonStreaming(...))`. Results arrive in **any order** - key by `custom_id`, never by position.

**Models API (no beta; availability: `shared/platform-availability.md`):** `client.models.list()` (auto-paginates) and `client.models.retrieve("claude-opus-5-5")`. Each model object has `id`, `display_name`, `created_at`, and - since Mar 2026 - `max_input_tokens` (the context window), `max_tokens` (the output cap), and `capabilities`. There is no `context_window` field.

**Stop details (GA, Opus 4.7+):** `response.stop_details` is populated **only when `stop_reason == "refusal"`** (fields: `type: "refusal"`, `category` - an open set, e.g. `"cyber"`, `"bio"`, `"reasoning_extraction"`, `"frontier_llm"`, or `null`; see the docs for the full list - and `explanation`). It is `null` for every other `stop_reason` (`end_turn`, `max_tokens`, `tool_use`, `pause_turn`, ...) - always guard before reading.

**Admin API (beta, since 2026-08-26):** organization management - members, invites, workspaces and workspace members, API keys, rate limit reports, service accounts, federation issuers/rules, CMEK external keys - under `client.beta.organization` in all seven SDKs and `ant beta:organization` in the CLI. Requires an admin credential: an Admin API key (`sk-ant-admin...`, read from `ANTHROPIC_API_KEY`) or an `org:admin` OAuth token (`ANTHROPIC_AUTH_TOKEN`); regular API keys are rejected. Usage and cost reports and the Claude Enterprise user-management/analytics endpoints are **not** in the SDKs - raw HTTP only. See `shared/admin-api.md`.

**Client config (no beta):** `timeout` default 10 min; **units differ by SDK** - Python/Ruby: seconds; TypeScript: **milliseconds**; Go `option.WithRequestTimeout(time.Duration)`; Java `Duration`; C# `TimeSpan`. TS scales the default up to 60 min for large `max_tokens` on non-streaming requests; Java does so for streaming requests (Java non-streaming scales 30s-10 min). `max_retries`/`maxRetries` default 2 (retries 408/409/429/5xx + connection errors). `base_url` (or `ANTHROPIC_BASE_URL` env). Per-request override: Python `client.with_options(timeout=5.0).messages.create(...)`; TS `client.messages.create({...}, {timeout: 5_000})`; Ruby `request_options: {timeout: 5}`. Timeouts are retried - wall-clock can reach `timeout × (max_retries+1)`.

## Workload Identity Federation (Quick Reference)

**GA, no beta header.** Construct the normal zero-arg client (`Anthropic()` / `new Anthropic()` / `anthropic.NewClient()` / `AnthropicOkHttpClient.fromEnv()`); the SDK auto-detects WIF when **all** of `ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_ORGANIZATION_ID`, `ANTHROPIC_SERVICE_ACCOUNT_ID`, and `ANTHROPIC_IDENTITY_TOKEN_FILE` (or `ANTHROPIC_IDENTITY_TOKEN`) are set, exchanges the JWT at `/v1/oauth/token`, and auto-refreshes. `ANTHROPIC_WORKSPACE_ID` does not gate activation - required only when the federation rule spans multiple workspaces (else 400 `workspace_id_required`), optional for single-workspace rules. `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` (even empty) outrank WIF, and a set `ANTHROPIC_PROFILE` also wins over the federation env vars (a missing named profile is an error, not a fall-through) - unset all three.
