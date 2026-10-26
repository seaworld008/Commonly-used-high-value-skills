# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

#### Part B - Semantic extraction (parallel subagents)

**Fast path:** If detection found zero docs, papers, and images (code-only corpus), skip Part B entirely and go straight to Part C. AST handles code - there is nothing for semantic subagents to do. **First write an empty semantic file** so Part C's merge has its input (it reads `.graphify_semantic.json` unconditionally; without this a code-only run hits `FileNotFoundError`):

```bash
"$(cat graphify-out/.graphify_python)" -c "
import json
from pathlib import Path
Path('graphify-out/.graphify_semantic.json').write_text(json.dumps({'nodes':[],'edges':[],'hyperedges':[],'input_tokens':0,'output_tokens':0}), encoding='utf-8')
"
```

Use available, permitted subagents for independent extraction chunks when it improves throughput. Otherwise process bounded chunks sequentially and preserve the same extraction and evidence contract.

Before dispatching subagents, print a timing estimate:
- Load `total_words` and file counts from `graphify-out/.graphify_detect.json`
- Estimate agents needed: `ceil(uncached_non_code_files / 22)` (chunk size is 20-25 files, capped at ~6000 total lines)
- Estimate time only from observed throughput for the current host, or report it as unmeasured.
- Report the file count, chosen chunk bounds and any measured throughput evidence.

**Step B0 - Check extraction cache first**

Before dispatching any subagents, check which files already have cached extraction results:

SPEC_PATH below is the **absolute** path of the `references/extraction-spec.md` that ships beside this SKILL.md — the same file Step B2 loads and hands to every subagent. It is the extraction prompt, so cache entries are attributed to it: when a graphify upgrade changes the prompt, entries produced by the old one are re-extracted instead of replayed, and unchanged prompts keep their entries (#1939). Substitute the real path in both Step B0 and Step B3 — pass the same one to each, and do not drop the argument.

```bash
"$(cat graphify-out/.graphify_python)" -c "
import json
from graphify.cache import check_semantic_cache
from pathlib import Path

detect = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding=\"utf-8\"))
# Only content files go to semantic extraction. Code is already covered structurally
# by the AST pass (Part A); flattening every category here makes subagents re-read
# every source file (#1392). Video is transcribed to a document in Step 2.5 first.
all_files = [f for cat in ('document', 'paper', 'image') for f in detect['files'].get(cat, [])]

cached_nodes, cached_edges, cached_hyperedges, uncached = check_semantic_cache(all_files, root='INPUT_PATH', prompt_file='SPEC_PATH')

# Always (re)write the cache file: write hits, else DELETE any leftover from a prior
# run so Part C never merges a stale .graphify_cached.json (#1392).
if cached_nodes or cached_edges or cached_hyperedges:
    Path('graphify-out/.graphify_cached.json').write_text(json.dumps({'nodes': cached_nodes, 'edges': cached_edges, 'hyperedges': cached_hyperedges}, ensure_ascii=False), encoding=\"utf-8\")
else:
    Path('graphify-out/.graphify_cached.json').unlink(missing_ok=True)
Path('graphify-out/.graphify_uncached.txt').write_text('\n'.join(uncached), encoding=\"utf-8\")
# Nothing has been dispatched yet, so any chunk file on disk is a leftover from an
# interrupted run, and Step B3 merges every .graphify_chunk_*.json it finds.
if any(Path('graphify-out').glob('.graphify_chunk_*.json')):
    raise RuntimeError('Existing chunk files require an owned run directory; do not merge stale chunks')
print(f'Cache: {len(all_files)-len(uncached)} files hit, {len(uncached)} files need extraction')
"
```

Only dispatch subagents for files listed in `graphify-out/.graphify_uncached.txt`. If all files are cached, skip Steps B1 and B2 but still run Step B3's commands: its merge is the only Part B step that writes `graphify-out/.graphify_semantic.json`, and Part C reads that file unconditionally. Do not write an empty `.graphify_semantic.json` instead, because that drops every cached node.

**Step B1 - Split into chunks**

Load files from `graphify-out/.graphify_uncached.txt`. Split into chunks bounded by BOTH limits: at most 20-25 files AND at most ~6000 total lines per chunk. A text file longer than 2000 lines gets a chunk to itself - that is past the Read tool's single-call cap, so sharing a chunk with other files guarantees it is only partly read. Each image gets its own chunk (vision needs separate context). When splitting, group files from the same directory together so related artifacts land in the same chunk and cross-file relationships are more likely to be extracted.

Both bounds matter. The line bound is not only about the 2000-line Read cap: a subagent holding 25 files splits its attention across all of them and skims the dense ones, and a 590-line plan can come back with zero nodes that way. Bounding content as well as file count is what keeps a chunk's coverage honest (#2225).

**Step B2 - Collect complete chunk results with the supported host**

Use the host's available, permitted delegation mechanism, or process the bounded
chunks sequentially. Do not install an agent runtime, edit global client config,
or invent tool calls. Associate each response with its trusted chunk number.
Each result must be an object with list-valued nodes and edges; hyperedges may
be absent or a list. Preserve the complete result, including coverage and any
actual host usage evidence, when writing its matching chunk JSON.

If a task fails, returns invalid JSON, or cannot persist its expected result,
stop before B3. Do not merge a partial set, update cache, or continue to Part C.
Retry the affected bounded task using available evidence. An output directory
must belong to this run; never delete another task's chunks or cache.

Subagent prompt template:

See `references/extraction-spec.md` for the compact subagent prompt (rules, node-ID format, confidence rubric, hyperedge and vision rules, JSON schema). Load it only here, only when at least one chunk holds a doc, paper, or image; a pure-code corpus has skipped Part B and never reads it. Pass each agent that prompt verbatim with FILE_LIST, CHUNK_NUM, TOTAL_CHUNKS, and DEEP_MODE substituted, and have it return the JSON inline.

**Step B3 - Collect without mutating the graph or cache**

Wait for all subagents. For each result:
- Check that `graphify-out/.graphify_chunk_NN.json` exists on disk — this is the success signal
- If the file exists and contains valid JSON with `nodes` and `edges`, retain it as a candidate only. Do not call `save_semantic_cache` until every expected chunk passes B3.5.
- If the file is missing, the subagent was likely dispatched as read-only (Explore type) — print a warning: "chunk N missing from disk — subagent may have been read-only. Re-run with general-purpose agent." Do not silently skip.
- If any task fails, has no output, or returns invalid JSON, stop before merge and preserve the previous graph/cache.

Every expected chunk is required. Use the current host's actual tool/permission model; a missing optional subagent role is not a reason to invent that role.

**Step B3.5 - Validate receipts against every expected input**

Run the bundled `scripts/validate_semantic_chunks.py` from this skill directory,
passing absolute paths to the scan root, uncached manifest and this run's output.
Set N to the trusted number of chunks planned in B1 (zero for a cache-only run):

```bash
python scripts/validate_semantic_chunks.py --root INPUT_PATH --manifest /absolute/graphify-out/.graphify_uncached.txt --chunks-dir /absolute/graphify-out --expected-chunks N
```

Stop on any failure before graph/cache mutation. The check rejects missing or
stale chunks, malformed payloads, omitted coverage, insufficient text line counts
and sources outside the authorized root. Empty graph arrays are valid when the
coverage receipt is complete. This validates an agent's attestation against file
lengths; it cannot prove that a model actually read or understood the contents.
Binary media still needs its own page/frame/content acceptance evidence.
After all receipts pass, clear only this run's temporary partial-file marker.
Cache-only runs still execute the cached merge below; they never replace cached nodes
with an empty semantic graph.

Merge all chunk files into `.graphify_semantic_new.json`. When the host exposes actual token usage, record it before merging. Otherwise mark usage unmeasured; placeholder zeros are not measured cost or evidence of free execution. Then run:
```bash
"$(cat graphify-out/.graphify_python)" -c "
import json, glob
from pathlib import Path

chunks = sorted(glob.glob('graphify-out/.graphify_chunk_*.json'))
all_nodes, all_edges, all_hyperedges = [], [], []
total_in, total_out = 0, 0
for c in chunks:
    d = json.loads(Path(c).read_text(encoding=\"utf-8\"))
    all_nodes += d.get('nodes', [])
    all_edges += d.get('edges', [])
    all_hyperedges += d.get('hyperedges', [])
    total_in += d.get('input_tokens', 0)
    total_out += d.get('output_tokens', 0)
Path('graphify-out/.graphify_semantic_new.json').write_text(json.dumps({
    'nodes': all_nodes, 'edges': all_edges, 'hyperedges': all_hyperedges,
    'input_tokens': total_in, 'output_tokens': total_out,
}, indent=2, ensure_ascii=False), encoding=\"utf-8\")
print(f'Merged {len(chunks)} chunks: {total_in:,} in / {total_out:,} out tokens')
"
```

Only after every receipt has passed B3.5 and the merge above succeeds, save new results to cache. On validation failure, leave all previous cache entries unchanged. Pass the same SPEC_PATH as Step B0 — it stamps each entry with the prompt that produced it, and a write under a different prompt than the read lands where the next run won't look (#1939):
```bash
"$(cat graphify-out/.graphify_python)" -c "
import json
from graphify.cache import save_semantic_cache
from pathlib import Path

new = json.loads(Path('graphify-out/.graphify_semantic_new.json').read_text(encoding=\"utf-8\")) if Path('graphify-out/.graphify_semantic_new.json').exists() else {'nodes':[],'edges':[],'hyperedges':[]}
uncached = [line for line in Path('graphify-out/.graphify_uncached.txt').read_text(encoding=\"utf-8\").splitlines() if line]
# A partly-read file is cached with partial: True, which load_cached treats as a MISS,
# so the next --update re-dispatches it instead of serving a truncated extraction forever
# (#2225). Same contract the library path uses for a truncated LLM response (#933/#1950).
partial = [line for line in Path('graphify-out/.graphify_partial.txt').read_text(encoding=\"utf-8\").splitlines() if line] if Path('graphify-out/.graphify_partial.txt').exists() else []
saved = save_semantic_cache(new.get('nodes', []), new.get('edges', []), new.get('hyperedges', []), root='INPUT_PATH', allowed_source_files=uncached, prompt_file='SPEC_PATH', partial_source_files=partial)
note = f' ({len(partial)} left partial for retry)' if partial else ''
print(f'Cached {saved} files' + note)
"
```

Merge cached + new results into `graphify-out/.graphify_semantic.json`:
```bash
"$(cat graphify-out/.graphify_python)" -c "
import json
from pathlib import Path

cached = json.loads(Path('graphify-out/.graphify_cached.json').read_text(encoding=\"utf-8\")) if Path('graphify-out/.graphify_cached.json').exists() else {'nodes':[],'edges':[],'hyperedges':[]}
new = json.loads(Path('graphify-out/.graphify_semantic_new.json').read_text(encoding=\"utf-8\")) if Path('graphify-out/.graphify_semantic_new.json').exists() else {'nodes':[],'edges':[],'hyperedges':[]}

all_nodes = cached['nodes'] + new.get('nodes', [])
all_edges = cached['edges'] + new.get('edges', [])
all_hyperedges = cached.get('hyperedges', []) + new.get('hyperedges', [])
seen = set()
deduped = []
for n in all_nodes:
    if n['id'] not in seen:
        seen.add(n['id'])
        deduped.append(n)

merged = {
    'nodes': deduped,
    'edges': all_edges,
    'hyperedges': all_hyperedges,
    'input_tokens': new.get('input_tokens', 0),
    'output_tokens': new.get('output_tokens', 0),
}
Path('graphify-out/.graphify_semantic.json').write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding=\"utf-8\")
print(f'Extraction complete - {len(deduped)} nodes, {len(all_edges)} edges ({len(cached[\"nodes\"])} from cache, {len(new.get(\"nodes\",[]))} new)')
"
```
Clean up temp files: `rm -f graphify-out/.graphify_cached.json graphify-out/.graphify_uncached.txt graphify-out/.graphify_semantic_new.json`

<a id="section-2"></a>

### Step 9 - Save manifest, update cost tracker, clean up, and report

```bash
"$(cat graphify-out/.graphify_python)" -c "
import json
from pathlib import Path
from datetime import datetime, timezone
from graphify.detect import save_manifest

# Save manifest for --update
detect = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding=\"utf-8\"))
extract = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding=\"utf-8\"))
# In --update mode, 'all_files' carries the full corpus; 'files' is the changed
# subset. Full-rebuild mode populates only 'files', so the fallback handles that.
# root= relativizes the manifest keys to the scan root (same base as the build),
# so the on-disk manifest is portable across clones/machines and a later --update
# matches cached files instead of missing every one (#1417).
#
# Only stamp semantic files (docs/papers/images) that ACTUALLY produced output:
# a detected file whose chunk failed or was omitted must stay unstamped so the
# next --update re-queues it, otherwise it is marked done and its content is lost
# forever (#2015). This mirrors the library extract path exactly
# (cli._stamped_manifest_files + clear_semantic + scan_corpus); do not stamp the
# raw corpus. Code files are always stamped (AST is deterministic); only semantic
# types are gated on output.
from graphify.cli import _stamped_manifest_files
_corpus = detect.get('all_files') or detect['files']
# A file a subagent only partly read DID produce output, so the stamp filter alone would
# keep it - but its node set covers just the head of the file, and stamping it means
# detect_incremental reads it as done and never re-queues it, leaving the truncated graph
# live forever. Name those files so they stay unstamped and are retried next run (#2225).
_pf = Path('graphify-out/.graphify_partial.txt')
_partial = {l.strip() for l in _pf.read_text(encoding=\"utf-8\").splitlines() if l.strip()} if _pf.exists() else set()
_manifest_files = _stamped_manifest_files(_corpus, extract, Path('INPUT_PATH'), partial_source_files=_partial)
# Files dispatched this run (the changed subset) but NOT stamped above still carry
# a stale semantic_hash from a prior run; clear it so detect_incremental re-queues
# them instead of reading them as unchanged (#1948).
_sem_types = ('document', 'paper', 'image')
_dispatched = {f for t, fl in detect['files'].items() if t in _sem_types for f in fl}
_stamped = {f for fl in _manifest_files.values() for f in fl}
_cleared = _dispatched - _stamped
# scan_corpus = the RAW full corpus (not the stamp-filtered subset) so in-root
# files newly excluded since last run are dropped rather than masquerading as
# deletions; untouched files' prior rows are still preserved (#1908).
_scan = {f for fl in _corpus.values() for f in fl}
save_manifest(_manifest_files, root='INPUT_PATH', scan_corpus=_scan, clear_semantic=_cleared or None)

# Update cumulative cost tracker
input_tok = extract.get('input_tokens', 0)
output_tok = extract.get('output_tokens', 0)

cost_path = Path('graphify-out/cost.json')
if cost_path.exists():
    cost = json.loads(cost_path.read_text(encoding=\"utf-8\"))
else:
    cost = {'runs': [], 'total_input_tokens': 0, 'total_output_tokens': 0}

cost['runs'].append({
    'date': datetime.now(timezone.utc).isoformat(),
    'input_tokens': input_tok,
    'output_tokens': output_tok,
    'files': detect.get('total_files', 0),
})
cost['total_input_tokens'] += input_tok
cost['total_output_tokens'] += output_tok
cost_path.write_text(json.dumps(cost, indent=2, ensure_ascii=False), encoding=\"utf-8\")

print(f'This run: {input_tok:,} input tokens, {output_tok:,} output tokens')
print(f'All time: {cost[\"total_input_tokens\"]:,} input, {cost[\"total_output_tokens\"]:,} output ({len(cost[\"runs\"])} runs)')
"
rm -f graphify-out/.graphify_detect.json graphify-out/.graphify_extract.json graphify-out/.graphify_ast.json graphify-out/.graphify_semantic.json graphify-out/.graphify_analysis.json graphify-out/.graphify_partial.txt
find graphify-out -maxdepth 1 -name '.graphify_chunk_*.json' -delete 2>/dev/null
rm -f graphify-out/.needs_update 2>/dev/null || true
```

Replace INPUT_PATH with the actual path (same value used in Steps 4-5) so the manifest is relativized to the scan root.

Tell the user (omit the obsidian line unless --obsidian was given):
```
Graph complete. Outputs in PATH_TO_DIR/graphify-out/

  graph.html            - interactive graph, open in browser
  GRAPH_REPORT.md       - audit report
  graph.json            - raw graph data
  obsidian/             - Obsidian vault (only if --obsidian was given)
```

If graphify saved you time, consider supporting it: https://github.com/sponsors/safishamsi

Replace PATH_TO_DIR with the actual absolute path of the directory that was processed.

If PATH_TO_DIR is inside a git repository, add one line to the report: `graphify-out/` was written into the working tree, so unless the repository already ignores it, it will show in `git status`; the user can add `graphify-out/` to `.gitignore`, or commit only the outputs their team should share (see https://docs.graphify.com/guides/team-workflows).

Then paste these sections from GRAPH_REPORT.md directly into the chat:
- God Nodes
- Surprising Connections
- Suggested Questions

Do NOT paste the full report - just those three sections. Keep it concise.

Then immediately offer to explore. Pick the single most interesting suggested question from the report - the one that crosses the most community boundaries or has the most surprising bridge node - and ask:

> "The most interesting question this graph can answer: **[question]**. Want me to trace it?"

If the user says yes, run `/graphify query "[question]"` on the graph and walk them through the answer using the graph structure - which nodes connect, which community boundaries get crossed, what the path reveals. Keep going as long as they want to explore. Each answer should end with a natural follow-up ("this connects to X - want to go deeper?") so the session feels like navigation, not a one-shot report.

The graph is the map. Your job after the pipeline is to be the guide.

---
