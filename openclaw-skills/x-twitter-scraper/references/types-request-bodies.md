> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: request bodies

```typescript

interface CreateMonitorRequest {
  username: string;
  eventTypes: EventType[];
}

interface UpdateMonitorRequest {
  eventTypes?: EventType[];
  isActive?: boolean;
}

interface CreateKeywordMonitorRequest {
  query: string;
  eventTypes: KeywordEventType[];
}

interface UpdateKeywordMonitorRequest {
  eventTypes?: KeywordEventType[];
  isActive?: boolean;
}

interface CreateWebhookRequest {
  url: string;
  eventTypes: EventType[];
}

interface UpdateWebhookRequest {
  url?: string;
  eventTypes?: EventType[];
  isActive?: boolean;
}

interface CreateApiKeyRequest {
  name?: string;
}

```
