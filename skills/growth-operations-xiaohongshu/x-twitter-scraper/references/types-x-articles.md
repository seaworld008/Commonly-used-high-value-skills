> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: X Articles

```typescript
interface ArticleResponse {
  article: {
    title?: string;
    previewText?: string;
    coverImageUrl?: string;
    bodyText?: string;
    contents?: Array<{
      type?: string;
      text?: string;
      url?: string;
      previewUrl?: string;
      width?: number;
      height?: number;
      inlineStyleRanges?: Array<{
        offset?: number;
        length?: number;
        style?: string;
      }>;
    }>;
    createdAt?: string;
    likeCount?: number;
    replyCount?: number;
    quoteCount?: number;
    viewCount?: number;
  };
  author?: {
    id: string;
    username: string;
    name: string;
    profilePicture?: string;
  };
}
```
