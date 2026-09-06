---
name: rag-architect
description: 'Design or diagnose RAG ingestion, retrieval, permissions, reranking, citations, and evaluation when answers must be grounded in a specialized corpus.'
zh_description: "用于以评测为先设计和诊断生产级 RAG，包括权限、混合检索、重排、引用和监控。"
version: "2.0.1"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["architect", "rag", "retrieval", "evaluation", "search"]'
created_at: "2026-03-04"
updated_at: "2026-09-06"
quality: 5
complexity: "advanced"
---

# RAG Architect

Design from measured retrieval failures, not from a fashionable vector
database or chunk size.

## Start With the Product Contract

Define:

- users and authorization boundary
- answerable and unanswerable question classes
- source corpus, languages, formats, and update rate
- freshness and deletion requirements
- latency, cost, availability, and data-residency constraints
- citation and audit requirements
- acceptable abstention and false-answer rates

Do not build RAG when direct context, structured queries, a conventional search
index, or a deterministic API is simpler and more reliable.

## Build the Evaluation Set First

Create a versioned dataset before tuning:

```json
{
  "id": "policy-017",
  "query": "Can a contractor export customer data?",
  "expected_source_ids": ["policy-access-4.2"],
  "required_facts": ["contractors cannot export", "exception requires DPO approval"],
  "forbidden_claims": ["contractors always have export access"],
  "user_acl": ["policy:employee"],
  "as_of": "2026-07-01",
  "answerable": true
}
```

Include:

- exact lookup, paraphrase, and multi-hop questions
- ambiguous and underspecified queries
- near-duplicate sources with conflicting dates
- permission-denied documents
- no-answer and adversarial cases
- multilingual and noisy-document cases where applicable

Keep a held-out set. Do not tune and report on the same examples.

## Measure the Pipeline in Layers

Evaluate retrieval separately from generation.

### Retrieval

- Recall@k for required sources
- MRR or nDCG when ranking order matters
- permission leakage rate
- stale-source retrieval rate
- duplicate-result rate
- latency by corpus and query class

### Answering

- required-fact coverage
- unsupported-claim rate
- citation precision and citation completeness
- correct abstention rate
- answer consistency across paraphrases
- end-to-end task success

Always inspect failures by slice. One aggregate score can hide catastrophic
permission or freshness failures.

## Ingestion Contract

Preserve provenance:

```text
source_id
document_version
canonical_uri
content_hash
effective_at
expires_at
acl
parser_version
chunker_version
indexed_at
```

Make ingestion idempotent. Support updates and deletions. A deleted or
permission-revoked document must stop appearing without rebuilding unrelated
content.

Reject or quarantine parser failures instead of silently indexing empty or
garbled text.

## Chunking

Select chunking from document structure and evaluation results:

- preserve headings, tables, list boundaries, and parent-child context
- attach stable source and section identifiers
- avoid repeated headers and navigation noise
- keep atomic facts together
- add neighboring or parent context only when it improves held-out recall

Do not choose a universal token count or overlap percentage without evidence.
Record the chunker version so retrieval regressions are reproducible.

## Retrieval Architecture

Start with the simplest baseline:

1. metadata and ACL filtering
2. lexical search
3. dense retrieval
4. reciprocal-rank fusion or another explicit hybrid strategy
5. reranking when the evaluation set proves it adds value

Apply authorization before returning content to the model. Post-filtering an
over-retrieved unauthorized result set is not a sufficient security boundary.

Use query rewriting only when it measurably helps specific query classes.
Preserve the original query for audit and fallback.

## Structured and Multi-Source Data

Route structured questions to databases or APIs rather than embedding every
row. When combining structured and unstructured evidence:

- define source precedence
- normalize entity identifiers
- record timestamps and units
- surface conflicts instead of averaging them away

## Answer Generation

Require the answerer to:

- use only retrieved evidence for corpus-specific claims
- cite the exact source span or stable source identifier
- distinguish source facts from inference
- state when evidence conflicts or is stale
- abstain when evidence does not support the answer

Do not treat a fluent answer as evidence of retrieval quality.

## Failure Diagnosis

Classify every failed example:

| Failure | Typical evidence | Fix layer |
|---|---|---|
| Missing content | source absent from index | ingestion |
| Wrong boundary | fact split or table lost | parsing/chunking |
| Low recall | expected source below k | retrieval |
| Bad ordering | source found but ranked low | fusion/reranking |
| Permission leak | unauthorized source returned | filtering/security |
| Unsupported answer | source present, claim absent | generation |
| Wrong citation | answer true, citation unrelated | citation mapping |
| Stale answer | old version outranks current | freshness/versioning |

Change one layer at a time and rerun the same evaluation slices.

## Production Monitoring

Track:

- ingestion lag and failure rate
- index version and corpus coverage
- p50/p95/p99 retrieval and end-to-end latency
- empty-result, fallback, and abstention rates
- source/citation click-through where appropriate
- permission-denial and suspected leakage events
- quality samples reviewed by humans

Log query, retrieved source identifiers, scores, pipeline versions, and final
citations subject to privacy policy. Avoid storing sensitive raw content when
identifiers and hashes are sufficient.

## Rollout

Use shadow evaluation or canaries for index, embedding, chunker, or reranker
changes. Keep the previous index addressable until rollback is proven.

Block rollout when:

- permission leakage is non-zero
- held-out critical recall regresses
- unsupported-claim rate exceeds the agreed threshold
- deletion or freshness guarantees fail

## Output Contract

Return:

- product and security assumptions
- baseline architecture
- evaluation dataset and metrics
- ingestion and deletion design
- retrieval and ranking design
- citation and abstention policy
- rollout and monitoring plan
- unresolved experiments with decision thresholds

Prefer a measured baseline over an elaborate untested architecture.
