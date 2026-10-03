> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: radar

```typescript

type RadarSource =
  | "github"
  | "google_trends"
  | "hacker_news"
  | "polymarket"
  | "reddit"
  | "trustmrr"
  | "wikipedia";

type RadarCategory =
  | "general"
  | "tech"
  | "dev"
  | "science"
  | "culture"
  | "politics"
  | "business"
  | "entertainment";

interface RadarItem {
  id: string;
  title: string;
  description?: string;
  url?: string;
  imageUrl?: string;
  source: RadarSource;
  sourceId: string;
  category: RadarCategory;
  region: string;
  language: string;
  score: number;
  metadata: Record<string, unknown>;
  publishedAt: string;
  createdAt: string;
}

interface RadarPage {
  items: RadarItem[];
  hasMore: boolean;
  nextCursor?: string;
}

```
