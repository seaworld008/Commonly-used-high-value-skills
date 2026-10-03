> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik REST API endpoints: connected X accounts

Manage connected X accounts for confirmed write actions.

Users connect and re-authenticate X accounts in the Xquik dashboard. This Skill never handles X login material. Direct users to the dashboard account page to connect or refresh an account.

Never request passwords, cookies, 2FA codes, or verification codes.

The OpenAPI spec includes dashboard-owned account connection routes:

```http
POST /x/accounts
GET /x/account-connection-attempts/{id}
POST /x/account-connection-challenges/{id}/submit
POST /x/accounts/{id}/reauth
POST /x/accounts/bulk-retry
```

Do not call these routes from this Skill. This list keeps the Skill docs aligned with the documented API and marks the dashboard-only boundary.

## List X accounts

```http
GET /x/accounts
```

Returns all connected X accounts as `{ accounts: [{ id, username, displayName, isActive, createdAt }] }`.

This is a private read. This endpoint returns the complete connected-account list.
Show that full scope and list identities only after explicit approval.

## Get X account

```http
GET /x/accounts/{id}
```

Returns `{ id, username, displayName, isActive, createdAt }`.

This is a private read. Show the account ID. Retrieve its metadata only after
explicit approval for that exact read.

## Disconnect X account

Use the delete method on `/x/accounts/{id}`.

Permanently removes the account from Xquik. Returns `{ success: true }`. Before calling, confirm with the user.

This action is destructive. Show the exact account and lost access before
disconnecting it. Obtain explicit approval immediately before the call.

---
