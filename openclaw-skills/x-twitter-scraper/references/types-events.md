> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: events

```typescript

interface XquikEventBase {
  id: string;
  type: EventType;
  // Account monitor ID or keyword monitor ID, based on monitorType.
  monitorId: string;
  occurredAt: string;
  data: Record<string, unknown>;
}

type XquikEvent = XquikEventBase & (
  | {
      monitorType: "account";
      username: string;
      query?: never;
      keywordMonitorId?: never;
    }
  | {
      monitorType: "keyword";
      username?: never;
      query: string;
      keywordMonitorId: string;
    }
);

type XquikEventDetail = XquikEvent & {
  xEventId?: string;
};

interface EventList {
  events: XquikEvent[];
  hasMore: boolean;
  nextCursor?: string;
}

```
