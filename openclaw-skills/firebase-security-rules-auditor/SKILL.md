---
name: firebase-security-rules-auditor
description: 'Audit Firebase Security Rules for Firestore and Cloud Storage. Use when reviewing rules diffs, hardening Firebase apps, validating generated rules, checking emulator tests, or investigating authorization, data validation, privilege escalation, and resource abuse risks in Firebase projects.'
zh_description: "审计 Firestore 与 Cloud Storage 安全规则，检查授权、字段校验、权限提升、资源滥用和模拟器测试覆盖。"
version: "1.0.0"
author: seaworld008
source: github:firebase/agent-skills
source_url: "https://github.com/firebase/agent-skills/tree/main/skills/firebase-security-rules-auditor"
license: Apache-2.0
tags: '[firebase, firestore, cloud-storage, security-rules, authorization, appsec]'
created_at: "2026-07-06"
updated_at: "2026-07-06"
quality: 4
complexity: advanced
---

# Firebase Security Rules Auditor

Review Firebase Security Rules as an application security boundary, not as a
formatting exercise. The goal is to prove whether an attacker can read data,
write invalid state, escalate privileges, corrupt another user's records, or
abuse storage and query costs.

Use this skill for Firestore rules, Cloud Storage rules, emulator test coverage,
generated rules, and pull requests that touch Firebase schemas or client access
patterns.

## Trigger / When to Use

- A PR changes `firestore.rules`, `storage.rules`, `firebase.json`, or Firebase
  emulator tests.
- An AI-generated app adds Firestore or Cloud Storage rules and needs a security
  pass before deployment.
- A team reports permission errors, overly broad reads, or unexpected access
  from another account.
- Rules depend on custom claims, user document roles, group membership, document
  owners, or tenant IDs.
- The app stores user profiles, team data, uploads, invite links, chat messages,
  billing metadata, or admin-only fields.
- The user asks whether Firebase rules are "secure", "production ready", or
  "strict enough".

## Core Capabilities

1. Map the protected data model and trust boundaries.
2. Detect authorization bypasses across users, teams, tenants, and admin roles.
3. Compare create, update, delete, get, list, and query behavior separately.
4. Review field-level validation, immutable fields, type checks, and size caps.
5. Identify rules that trust `request.resource.data` for authority.
6. Check Cloud Storage path ownership, metadata validation, content type, and
   file size controls.
7. Produce emulator test cases that demonstrate each high-risk access path.
8. Rank findings by exploitability and data impact.

## Audit Workflow

### 1. Inventory Firebase Surfaces

Search for Firebase configuration and rules files:

```bash
find . -name 'firestore.rules' -o -name 'storage.rules' -o -name 'firebase.json' -o -name '*.rules'
rg -n "initializeApp|getFirestore|getStorage|collection\\(|doc\\(|ref\\(" .
rg -n "request\\.auth|request\\.resource|resource\\.data|get\\(|exists\\(|allow " .
```

Record:

- Firestore collections and subcollections.
- Cloud Storage bucket paths.
- Client call sites that read, write, upload, or delete.
- Server/admin code paths that bypass rules through Admin SDK.
- Auth model: anonymous, email, custom claims, team membership, multi-tenant
  organization IDs, or public reads.

### 2. Build an Access Matrix

Create a compact matrix before judging the rules:

| Actor | Examples | Expected access |
|---|---|---|
| unauthenticated | signed-out browser, crawler | only public data, if any |
| authenticated owner | user editing own profile | own records and own uploads |
| authenticated non-owner | another user in same app | no private data |
| team member | collaborator with role | scoped team data only |
| admin/moderator | custom claim or trusted ACL | privileged actions only |
| attacker with chosen input | malformed writes, forged owner IDs | denied |

If the product requirements are unclear, infer the safest reasonable model and
state the assumption in the report.

### 3. Review Rule Semantics

Firestore operations are not interchangeable. Check them independently:

- `get`: single-document reads.
- `list`: collection queries and collection group queries.
- `create`: new document validation.
- `update`: mutation of existing documents.
- `delete`: destructive access and ownership constraints.

For every `allow read` or `allow write`, expand it mentally into the exact
operations. A broad `allow read, write` often hides a missing `list` restriction
or an update bypass.

## Firestore Security Checklist

### Authorization

- Require `request.auth != null` before any private read or write.
- Bind ownership to trusted existing state, not user-controlled new data.
- For owner documents, compare against stable paths or immutable fields:

```javascript
function isOwner(userId) {
  return request.auth != null && request.auth.uid == userId;
}

match /users/{userId} {
  allow get: if isOwner(userId);
  allow update: if isOwner(userId)
    && request.resource.data.uid == resource.data.uid
    && request.resource.data.role == resource.data.role;
}
```

- For team or tenant rules, check both identity and membership:

```javascript
function isTeamMember(teamId) {
  return request.auth != null
    && exists(/databases/$(database)/documents/teams/$(teamId)/members/$(request.auth.uid));
}
```

- Treat client-supplied `ownerId`, `teamId`, `role`, `isAdmin`, `tenantId`, and
  `permissions` as untrusted unless they are checked against an existing trusted
  document or custom claim.

### Create vs Update Bypass

Compare validation on `create` and `update`. A common bug is allowing a safe
create and then permitting an update into unsafe state.

High-risk examples:

- User creates `{ role: "member" }`, then updates to `{ role: "admin" }`.
- User creates a valid document, then changes `ownerId`.
- User bypasses type checks by updating only one field.
- User grows arrays or strings after creation to cause resource abuse.

Prefer helper functions for repeated invariants:

```javascript
function hasImmutableIdentity() {
  return request.resource.data.uid == resource.data.uid
    && request.resource.data.ownerId == resource.data.ownerId
    && request.resource.data.createdAt == resource.data.createdAt;
}

function isValidProfile(data) {
  return data.keys().hasOnly(["uid", "displayName", "photoURL", "role", "createdAt", "updatedAt"])
    && data.uid is string
    && data.displayName is string
    && data.displayName.size() <= 80
    && data.role in ["member"]
    && data.createdAt is timestamp
    && data.updatedAt is timestamp;
}
```

### Field-Level Validation

Check that rules validate:

- Allowed fields with `keys().hasOnly(...)`.
- Required fields with `keys().hasAll(...)`.
- Types with `is string`, `is bool`, `is int`, `is number`, `is timestamp`,
  `is list`, or `is map`.
- String and array sizes with `.size()`.
- Enum values with `in [...]`.
- Server timestamps or monotonic timestamps where the app relies on ordering.
- Immutable fields with `request.resource.data.field == resource.data.field`.

Do not accept field allowlists alone as authorization. `diff().affectedKeys()`
and `hasOnly()` restrict what can change, not who can change it.

### Query Safety

Rules are not filters. A query must be provably allowed for every possible
result. Review each list rule against real client queries:

- Does the client include `where("ownerId", "==", uid)` when rules expect owner
  filtering?
- Can a user query another tenant by changing a route param?
- Are collection group queries covered by separate match blocks?
- Are public listings intended, or did `allow read` accidentally include list?

If list access is not needed, separate it from get:

```javascript
allow get: if isOwner(userId);
allow list: if false;
```

### Cross-Document Checks

`get()` and `exists()` are useful but can become expensive or fragile:

- Check that referenced paths cannot be controlled to escape tenant boundaries.
- Confirm membership documents are created by trusted code or strict rules.
- Avoid trusting a role document that the same user can edit.
- Watch for deleted membership edge cases where stale client state still writes.

## Cloud Storage Rules Checklist

Review Storage rules separately from Firestore rules. Storage paths and metadata
often encode authorization.

```javascript
match /users/{userId}/uploads/{fileName} {
  allow read: if request.auth != null && request.auth.uid == userId;
  allow write: if request.auth != null
    && request.auth.uid == userId
    && request.resource.size < 5 * 1024 * 1024
    && request.resource.contentType.matches('image/.*');
}
```

Check:

- Path ownership: user-controlled paths must include a verified `uid`, `teamId`,
  or document ID.
- Read policy: profile images may be public, but private uploads should not be.
- Write policy: content type, size, extension assumptions, and overwrite rules.
- Metadata: do not trust client metadata for authorization without validation.
- Deletion: users should not delete another user's files through guessed paths.
- Pairing with Firestore: if metadata documents point to files, both sides must
  enforce the same ownership model.

## Emulator Test Patterns

Prefer Firebase emulator tests for every material rule. Test both allowed and
denied paths.

```javascript
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
} from "@firebase/rules-unit-testing";
import { doc, getDoc, setDoc, updateDoc } from "firebase/firestore";

test("user cannot update another user's profile", async () => {
  const env = await initializeTestEnvironment({
    projectId: "demo-test",
    firestore: { rules: fs.readFileSync("firestore.rules", "utf8") },
  });

  await env.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), "users/alice"), {
      uid: "alice",
      displayName: "Alice",
      role: "member",
      createdAt: new Date(),
      updatedAt: new Date(),
    });
  });

  const bobDb = env.authenticatedContext("bob").firestore();
  await assertFails(updateDoc(doc(bobDb, "users/alice"), {
    displayName: "Owned",
  }));
});
```

Minimum test set:

- unauthenticated read/write denial for private paths;
- owner allowed get/update for expected fields;
- non-owner denied get/list/update/delete;
- role escalation denied;
- owner ID or tenant ID mutation denied;
- invalid type denied;
- oversize string/list/file denied;
- intended public read allowed, if public access exists.

## Finding Severity

Use this scale:

| Severity | Meaning |
|---|---|
| Critical | Unauthorized private data read, privilege escalation, cross-tenant access, admin bypass |
| High | Write access to another user's data, role or owner mutation, broad public list of sensitive data |
| Medium | Missing type validation on important fields, incomplete create/update parity, weak Storage metadata checks |
| Low | Minor over-permissive public metadata, missing size cap on low-impact fields, unclear tests |

Adjust severity upward when the affected collection contains PII, billing data,
messages, invite tokens, API credentials, location data, or child/user safety
data.

## Report Template

Return concise, evidence-based findings:

```json
{
  "score": 2,
  "summary": "Rules prevent basic unauthenticated access but allow authenticated users to modify other users' profile fields.",
  "findings": [
    {
      "severity": "high",
      "rule": "match /users/{userId} allow update",
      "issue": "The update rule checks request.auth != null but does not require request.auth.uid == userId.",
      "impact": "Any signed-in user can change another user's display name and profile metadata.",
      "recommendation": "Require owner identity and preserve immutable uid, role, and createdAt fields.",
      "test": "Add assertFails(updateDoc(doc(bobDb, 'users/alice'), ...))."
    }
  ]
}
```

## Common Anti-Patterns

- `allow read, write: if request.auth != null` on user, team, or message data.
- Trusting `request.resource.data.ownerId == request.auth.uid` on update without
  checking `resource.data.ownerId`.
- Allowing all authenticated users to list a collection because each document
  also has owner checks.
- Letting users write `role`, `permissions`, `isAdmin`, or `plan` fields.
- Using a user profile document as an admin source when users can edit that
  profile.
- Allowing Storage uploads without size or content-type limits.
- Relying on file extensions for security.
- Assuming Admin SDK behavior is constrained by Security Rules.
- Testing only allowed paths and skipping attacker paths.

## Boundaries

- Do not claim a rule is secure without checking the app's data model and real
  client queries.
- Do not weaken rules to make a failing client query work; change the query or
  data model instead.
- Do not treat Security Rules as a replacement for server-side validation on
  privileged backend operations.
- Do not recommend public read access unless the product explicitly requires
  public data and the data is safe to expose.
- If requirements are ambiguous, choose least privilege and document the
  assumption.
