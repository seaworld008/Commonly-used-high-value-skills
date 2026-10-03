> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: user activity

```typescript

interface UserTweetsResponse {
  tweets: Tweet[];
  has_next_page: boolean;
  next_cursor?: string;
}

interface UserLikesResponse {
  tweets: Tweet[];
  has_next_page: boolean;
  next_cursor?: string;
}

interface UserMediaResponse {
  tweets: Tweet[];
  has_next_page: boolean;
  next_cursor?: string;
}

interface TweetFavoritersResponse {
  users: UserProfile[];
  has_next_page: boolean;
  next_cursor?: string;
}

interface FollowersYouKnowResponse {
  users: UserProfile[];
  has_next_page: boolean;
  next_cursor?: string;
}

```
