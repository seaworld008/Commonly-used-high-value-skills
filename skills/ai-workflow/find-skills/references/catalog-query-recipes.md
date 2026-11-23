# Local Catalog Query & Overlap Triage Recipes

Deterministic commands for inspecting `docs/catalog.json`, `docs/sources/portfolio-policy.json`, and canonical `SKILL.md` files before querying external registries.

## 1. Search by Keyword, Tag, or Category in `docs/catalog.json`

```bash
python3 -c "
import json
q = 'postgres'
data = json.load(open('docs/catalog.json', encoding='utf-8'))
hits = [
    s for s in data['skills']
    if q in (s['name'] + ' ' + s.get('description','') + ' ' + ' '.join(s.get('tags',[]))).lower()
]
for s in hits:
    print(f"{s['name']} [{s['category']}] (q={s.get('quality')}) -> {s['path']}")
"
```

## 2. Check Retired Aliases & Canonical Replacements

```bash
python3 -c "
import json
policy = json.load(open('docs/sources/portfolio-policy.json', encoding='utf-8'))
for row in policy.get('retired_skills', []):
    print(f"{row['name']} -> {row.get('replacement') or 'retired'}: {row['reason']}")
"
```

## 3. Overlap & Provenance Verification Checklist

1. **Canonical group check**: if a candidate matches an entry in `canonical_groups[].retired_aliases`, recommend the `canonical` skill instead of installing an alias.
2. **Asset depth check**: inspect `scripts/` and `references/` in the candidate directory — prefer script/reference-backed skills over single-file prompt wrappers.
3. **License & origin check**: verify `LICENSE` / `LICENSE.txt` / `LICENSE.upstream.txt` and commit SHA before recommending installation (`skill-security-auditor`).
