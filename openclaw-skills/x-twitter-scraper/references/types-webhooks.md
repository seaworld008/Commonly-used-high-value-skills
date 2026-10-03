> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: webhooks

```typescript

interface WebhookCreated {
  id: string;
  url: string;
  eventTypes: EventType[];
  secret: string;
  createdAt: string;
}

interface Webhook {
  id: string;
  url: string;
  eventTypes: EventType[];
  isActive: boolean;
  consecutiveFailures: number;
  deliveryStatus: "active" | "paused" | "needs_attention";
  failureHardCap: number;
  createdAt: string;
}

interface Delivery {
  id: string;
  streamEventId: string;
  status: "pending" | "delivered" | "failed" | "exhausted";
  attempts: number;
  lastStatusCode?: number;
  lastError?: string;
  createdAt: string;
  deliveredAt?: string;
}

interface ProductionWebhookPayload {
  schemaVersion: 1;
  streamEventId: string;
  deliveryId: string;
  eventType: EventType;
  username?: string;
  query?: string;
  occurredAt: string;
  data: Record<string, unknown>;
}

interface WebhookTestPayload {
  eventType: "webhook.test";
  data: { message: string };
  timestamp: string;
}

type WebhookPayload = ProductionWebhookPayload | WebhookTestPayload;

```
