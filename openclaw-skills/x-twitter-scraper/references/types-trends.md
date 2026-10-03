> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: trends

```typescript

interface Trend {
  name: string;
  description?: string;
  rank?: number;
  query?: string;
  promotedContent?: string | null;
  tweetVolume?: number | null;
  url?: string;
}

interface TrendList {
  trends: Trend[];
  total: number;
  woeid: number;
}

```
