> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: download media

```typescript

type NonEmptyTweetIds = [string, ...string[]];

type DownloadMediaRequest =
  | { tweetInput: string; tweetId?: never; tweetUrl?: never; tweetIds?: never }
  | { tweetInput?: never; tweetId: string; tweetUrl?: never; tweetIds?: never }
  | { tweetInput?: never; tweetId?: never; tweetUrl: string; tweetIds?: never }
  | { tweetInput?: never; tweetId?: never; tweetUrl?: never; tweetIds: NonEmptyTweetIds };

// Validate tweetIds.length <= 50 at runtime.

interface DownloadMediaSingleResponse {
  tweetId: string;      // Resolved tweet ID
  galleryUrl: string;   // Gallery page URL. Treat it as sensitive.
  cacheHit: boolean;    // True when the cache served the result without usage.
}

interface DownloadMediaBulkResponse {
  galleryUrl: string;   // Combined gallery page URL
  totalTweets: number;  // Number of tweets processed
  totalMedia: number;   // Total media items downloaded
}

```

Check gallery visibility before sharing its URL. Restrict recipients and set a
retention period. Prefer authenticated or expiring links when supported. Delete
the gallery after use when supported.
