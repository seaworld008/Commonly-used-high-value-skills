# Dictionary Iteration Workflow

The core value of transcript-fixer is building a personalized correction dictionary that improves over time.

## The Core Loop

```
┌─────────────────────────────────────────────────┐
│  1. Fix transcript (manual or Stage 3)          │
│                    ↓                            │
│  2. Identify new ASR errors during fixing       │
│                    ↓                            │
│  3. Review reusable terms; save if authorized    │
│                    ↓                            │
│  4. Next time: Stage 1 auto-corrects these      │
└─────────────────────────────────────────────────┘
```

**Key principle**: Review source meaning and counterexamples first. Persist only confirmed reusable corrections within existing dictionary-maintenance authorization; a one-off correction may return review-only suggestions. Reuse authorized setup without adding a new approval loop.

## Workflow Checklist

Copy this checklist when correcting transcripts:

```
Correction Progress:
- [ ] Run correction: --input file.md --stage 3
- [ ] Review output file for remaining ASR errors
- [ ] Fix errors manually with Edit tool
- [ ] Save confirmed reusable corrections with --add when persistence is in scope
- [ ] Verify with --list that corrections were saved
- [ ] Next time: Stage 1 handles these automatically
```

## Save Corrections Immediately

After source review, save authorized reusable corrections (commands run from the skill root). The following mappings are contextual examples, not universal replacements:

```bash
# Single correction
uv run scripts/fix_transcription.py --add "错误词" "正确词" --domain general

# Multiple corrections - run command for each
uv run scripts/fix_transcription.py --add "片片总" "翩翩总" --domain general
uv run scripts/fix_transcription.py --add "姐弟" "结业" --domain general
uv run scripts/fix_transcription.py --add "自杀性" "自嗨性" --domain general
uv run scripts/fix_transcription.py --add "被看" "被砍" --domain general
uv run scripts/fix_transcription.py --add "单反过" "单访过" --domain general
```

## Verify Dictionary

Always verify corrections were saved:

```bash
# List all corrections in current domain
uv run scripts/fix_transcription.py --list

# Direct database query
sqlite3 ~/.transcript-fixer/corrections.db \
  "SELECT from_text, to_text, domain FROM active_corrections ORDER BY added_at DESC LIMIT 10;"
```

## Domain Selection

Choose the right domain for corrections:

| Domain | Use Case |
|--------|----------|
| `general` | Common ASR errors, names, general vocabulary |
| `embodied_ai` | 具身智能、机器人、AI 相关术语 |
| `finance` | 财务、投资、金融术语 |
| `medical` | 医疗、健康相关术语 |
| `火星加速器` | Custom Chinese domain name (any valid name works) |

```bash
# Domain-specific correction
uv run scripts/fix_transcription.py --add "股价系统" "框架系统" --domain embodied_ai
uv run scripts/fix_transcription.py --add "片片总" "翩翩总" --domain 火星加速器
```

## Common ASR Error Patterns

Build your dictionary with these common patterns:

| Type | Examples |
|------|----------|
| **Homophones** | 赢→营, 减→剪, 被看→被砍, 营业→营的 |
| **Names** | 片片→翩翩, 亮亮→亮哥 |
| **Technical** | 巨升智能→具身智能, 股价→框架 |
| **English** | log→vlog |
| **Broken words** | 姐弟→结业, 单反→单访 |

## When GLM API Fails

Use the failure exit status (normally 1) and current-run output manifest to identify unavailable AI. There is no guaranteed host-specific fallback marker. Stage 2 includes dictionary processing first; pass the original input directly. Outputs are `*_stage1.md` and, only on AI success, `*_stage2.md`. Stage 3 does not generate HTML; explicitly run `scripts/generate_word_diff.py original.md corrected.md output.html`.

Steps:
1. The available host can analyze the supplied text within existing authorization
2. Save manual corrections separately, preserving uncertainty and attribution
3. Save only source-supported reusable corrections when dictionary maintenance is authorized
4. Dictionary corrections work even without AI

## Auto-Learning Feature

Learning and automatic approval are off by default, independently gated. When learning is explicitly enabled, review recurring patterns with their source context and counterexamples. The current CLI review and approval handlers are placeholders; these commands only print "not yet implemented":

```bash
# Check learned patterns
uv run scripts/fix_transcription.py --review-learned

# Approve high-confidence patterns
uv run scripts/fix_transcription.py --approve "错误词" "正确词"
```

Frequency and confidence thresholds are candidate-screening methods, not proof of correctness. Use manual review and authorized `--add` for approved reusable terms. The wrapper reads only explicit process credentials and does not open a browser by default.

## Best Practices

1. **Review before saving**: Confirm meaning, reusability, domain and counterexamples
2. **Be specific**: Use exact phrases, not partial words
3. **Use domains**: Organize corrections by topic for better precision
4. **Verify**: Always run --list to confirm saves
5. **Review suggestions**: Keep a human-reviewed candidate list; do not rely on placeholder CLI approval
