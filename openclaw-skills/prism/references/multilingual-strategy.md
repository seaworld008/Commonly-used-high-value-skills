# Multilingual Source and Output Review

Use when a notebook's source language differs from the intended audience language.
This is a local curation worksheet, not a claim that every output supports every
language or that a prompt overrides the account's actual output settings.

1. Inventory source languages and preserve the original source files.
2. Record the requested output language, audience and terminology convention.
3. Check the actual product's Output Language setting and the selected feature's
   current language support. Do not infer support from a different output type.
4. Preserve proper names, identifiers, code and quoted terminology where a
   translation would change their meaning. Use a small approved bilingual glossary
   as source material when terminology consistency matters.
5. Ask for a short sample before generating a long artifact when terminology or
   mixed-language source quality is uncertain. Reuse prior approved terminology.
6. Compare sampled claims to the original sources, not only to a translated
   intermediate summary. Label uncertain translations and missing evidence.

Example instruction to adapt to the notebook's actual controls:

```text
Audience language: Simplified Chinese.
Keep API names and quoted identifiers in their original form.
Explain the selected sources, cite their support, and distinguish translated
terminology from the original wording. Do not fill a source gap with translation.
```

Acceptance: the actual output uses the requested language, essential terms remain
consistent, quotations retain meaning, and sampled claims have source support.
Check audio pronunciation and captions separately when those outputs are used.

Official reference, checked 2026-10-26:
[Change output language](https://support.google.com/gemininotebook/answer/16261963?hl=en).
Use the UI or integration actually available; this worksheet defines no extra CLI.
