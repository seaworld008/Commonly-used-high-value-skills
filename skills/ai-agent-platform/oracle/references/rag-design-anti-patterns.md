Purpose: Use this file when you are choosing a RAG architecture, defining retrieval quality gates, or auditing RAG anti-patterns.

## Contents
- Architecture taxonomy
- Hybrid Search default
- Chunking and index choices
- RAG anti-patterns
- Evaluation model
- Oracle gates

# RAG Design And Anti-Patterns

## Architecture Taxonomy

| Architecture | Best for | Complexity |
|--------------|----------|------------|
| Vanilla RAG | simple FAQ and Q&A | Low |
| Hybrid RAG | production default | Medium |
| Self-RAG | high factuality with self-checks | Medium |
| Corrective RAG | reliability-critical retrieval recovery | Medium |
| GraphRAG | multi-hop reasoning and global summaries | High |
| Agentic RAG | dynamic multi-step retrieval | High |
| Multi-Agent RAG | enterprise multi-domain knowledge | Very high |

Decision flow:
- simple single-corpus Q&A -> Hybrid RAG
- multi-hop reasoning or global summarization -> GraphRAG
- dynamic strategy adaptation -> Agentic RAG
- self-correction and factuality priority -> Self-RAG or Corrective RAG

## Hybrid Search Default

Production default:
1. query expansion or rewrite
2. dense vector search
3. BM25 keyword search
4. reciprocal-rank fusion
5. cross-encoder reranking
6. top `5-8` chunks for context assembly
7. LLM generation

Single highest-ROI improvement: reranking.

## Chunking And Index Choices

| Strategy | Best for | Size guide |
|----------|----------|------------|
| Fixed-size | general docs | `500-1000` tokens, `50-100` overlap |
| Semantic | long docs with topic shifts | variable by boundary |
| Paragraph | structured docs | `200-500` tokens |
| AST-based | source code | function / class level |
| Hierarchical | complex docs | parent summary + child chunks |

Rules:
- avoid naive fixed `512`-token splitting without heading preservation;
- preserve document structure for semantic chunking;
- separate indexes by domain when content differs materially.

### Embedding And Vector DB Selection

- cost-sensitive simple queries -> `text-embedding-3-small`
- long documents -> `voyage-3`
- multilingual -> `Cohere embed-v3` or `BGE-M3`
- highest quality -> `text-embedding-3-large`
- self-hosted -> `BGE-M3`

- `<10k` docs or prototype -> `ChromaDB`
- existing PostgreSQL -> `pgvector`
- managed production -> `Pinecone`
- self-hosted production -> `Qdrant` or `Weaviate`
- Hybrid Search native fit -> `Weaviate`

## RAG Anti-Patterns

| ID | Anti-pattern | Symptom | Fix |
|----|--------------|---------|-----|
| `RP-01` | retrieval as afterthought | RAG bolted onto a PoC | design retrieval as first-class system with SLOs |
| `RP-02` | naive fixed chunking | blind splits | semantic chunking with heading preservation |
| `RP-03` | monolithic index | all content in one store | split by domain |
| `RP-04` | prompt-heavy, query-light | query pipeline ignored | add rewrite, intent classification, clarification |
| `RP-05` | no evaluation framework | no Recall@K / Precision@K | use 3-tier evaluation |
| `RP-06` | knowledge-base chaos | contradictory or outdated docs | versioning and conflict detection |
| `RP-07` | direct live data connection | unsafe live-source dependency | static / periodic / on-demand tiers |
| `RP-08` | no guardrails | unsafe retrieval/use | source whitelisting and output validation |
| `RP-09` | context overload | entire docs in prompt | top `5-8` chunks only |
| `RP-10` | no reranking | raw retrieval order used | add reranker |

## Cascade Failure Model

If retrieval, reranking, generation, and guardrails each run at `95%`:
- end-to-end reliability drops to about `81%`.

Independent gates:
- `Recall@5 >= 0.8`
- `Precision@5 >= 0.7`
- `Faithfulness >= 0.8`
- policy violations `< 1%`

## RAG Evaluation

| Tier | Metrics | Threshold |
|------|---------|-----------|
| Retrieval | `Recall@K`, `Precision@K`, `MRR`, `NDCG` | `Recall@5 >= 0.8`, `Precision@5 >= 0.7` |
| Generation | Faithfulness, relevancy, answer correctness | `Faithfulness >= 0.8` |
| Task | deflection, handle time, CSAT | task-specific |

Anti-patterns:
- regenerated test sets
- retrieval and generation scored as a single unit
- vague “accuracy” without component metrics

## GraphRAG Guidance

Use GraphRAG when:
- the answer needs synthesis across many documents,
- the question requires multi-hop reasoning,
- global themes matter more than passage lookup.

## Oracle Gates

- no Retrieval SLO -> block at `DESIGN`
- fixed-size-only chunking -> require semantic review
- “accuracy” as sole metric -> require 3-tier evaluation
- no reranker -> require ROI analysis
