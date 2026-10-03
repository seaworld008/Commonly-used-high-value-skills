> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik REST API endpoints: API keys

These endpoints require session authentication. They do not accept API keys.

## Manage API keys in the dashboard

API key lifecycle operations stay in the Xquik dashboard. Never request, copy,
display, store, rotate, or revoke an API key through this Skill. Direct the
user to the dashboard account page.

This reference omits API key lifecycle requests and responses. Do not call
those routes from this Skill. Use the dashboard account page.

---
