> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: monitors

```typescript

interface Monitor {
  id: string;
  username: string;
  xUserId: string;
  eventTypes: EventType[];
  isActive: boolean;
  createdAt: string;
  nextBillingAt: string;
  pausedReason?: "x_user_not_found";
  pausedAt?: string;
}

interface KeywordMonitor {
  id: string;
  query: string;
  eventTypes: KeywordEventType[];
  isActive: boolean;
  createdAt: string;
  nextBillingAt: string;
}

type KeywordEventType =
  | "tweet.new"
  | "tweet.quote"
  | "tweet.reply"
  | "tweet.retweet"
  | "tweet.media"
  | "tweet.link"
  | "tweet.poll"
  | "tweet.mention"
  | "tweet.hashtag"
  | "tweet.longform";

type EventType =
  | KeywordEventType
  | "profile.avatar.changed"
  | "profile.banner.changed"
  | "profile.name.changed"
  | "profile.username.changed"
  | "profile.bio.changed"
  | "profile.location.changed"
  | "profile.url.changed"
  | "profile.verified.changed"
  | "profile.protected.changed"
  | "profile.pinned_tweet.changed"
  | "profile.unavailable.changed";

```

Keyword monitor requests accept only `KeywordEventType`. The shared OpenAPI
event array also serves account monitors and webhooks. It therefore includes
profile events. Never pass a `profile.*` value to a keyword monitor request.
