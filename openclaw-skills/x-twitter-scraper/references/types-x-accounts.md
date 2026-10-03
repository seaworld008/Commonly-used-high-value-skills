> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik TypeScript types: connected X accounts

```typescript

interface ConnectedXAccount {
  id: string;                 // Unique account ID
  username: string;           // X username
  displayName?: string;       // Display name on X
  isActive: boolean;          // Whether the connection is active
  createdAt: string;          // ISO 8601 timestamp
}

// Users connect X accounts in the Xquik dashboard.
// This Skill never handles X login material.

```
