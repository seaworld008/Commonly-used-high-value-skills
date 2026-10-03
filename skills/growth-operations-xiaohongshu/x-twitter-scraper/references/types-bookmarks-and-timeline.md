> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: bookmarks & timeline

```typescript

interface BookmarksResponse {
  tweets: Tweet[];
  has_next_page: boolean;
  next_cursor?: string;
}

interface BookmarkFolder {
  id: string;
  name: string;
}

interface BookmarkFoldersResponse {
  folders: BookmarkFolder[];
}

interface NotificationsResponse {
  notifications: Notification[];
  has_next_page: boolean;
  next_cursor?: string;
}

interface TimelineResponse {
  tweets: Tweet[];
  has_next_page: boolean;
  next_cursor?: string;
}

interface DmHistoryResponse {
  messages: DmMessage[];
  has_next_page: boolean;
  next_cursor?: string;
}

interface DmMessage {
  id: string;
  text: string;
  senderId: string;
  createdAt: string;
  media?: TweetMediaItem[];
}

```
