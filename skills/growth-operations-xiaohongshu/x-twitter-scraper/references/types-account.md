> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: account

```typescript

interface Account {
  plan: "active" | "inactive";
  monitorsAllowed: number;
  monitorsUsed: number;
  monitorBilling: {
    activeDailyEstimate: string;
    activeHourlyBurn: string;
    creditsPerActiveMonitorDay: string;
    creditsPerActiveMonitorHour: string;
    eventsIncluded: boolean;
    instantCheckIntervalSeconds: number;
    unlimitedSlots: boolean;
  };
  creditInfo?: {
    balance: string;
    lifetimePurchased: string;
    lifetimeUsed: string;
    autoTopupEnabled: boolean;
    autoTopupAmountDollars: number;
    autoTopupThreshold: string;
  };
  xUsername?: string;
}

```
