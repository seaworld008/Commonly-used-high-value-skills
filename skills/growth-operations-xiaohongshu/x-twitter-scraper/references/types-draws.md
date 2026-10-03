> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: draws

```typescript

interface Draw {
  id: string;
  tweetId: string;
  tweetUrl: string;
  tweetText: string;
  tweetAuthorUsername: string;
  tweetLikeCount: number;
  tweetRetweetCount: number;
  tweetReplyCount: number;
  tweetQuoteCount: number;
  status: "pending" | "running" | "completed" | "failed";
  totalEntries: number;
  validEntries: number;
  createdAt: string;
  drawnAt?: string;
}

interface DrawListItem {
  id: string;
  tweetUrl: string;
  status: "pending" | "running" | "completed" | "failed";
  totalEntries: number;
  validEntries: number;
  createdAt: string;
  drawnAt?: string;
}

interface DrawWinner {
  position: number;
  authorUsername: string;
  tweetId: string;
  isBackup: boolean;
}

interface DrawDetails {
  draw: Draw;
  winners: DrawWinner[];
}

interface DrawList {
  draws: DrawListItem[];
  hasMore: boolean;
  nextCursor?: string;
}

interface CreateDrawRequest {
  tweetUrl: string;
  winnerCount?: number;
  backupCount?: number;
  uniqueAuthorsOnly?: boolean;
  mustRetweet?: boolean;
  mustFollowUsername?: string;
  filterMinFollowers?: number;
  filterAccountAgeDays?: number;
  filterLanguage?: string;
  requiredKeywords?: string[];
  requiredHashtags?: string[];
  requiredMentions?: string[];
}

```
