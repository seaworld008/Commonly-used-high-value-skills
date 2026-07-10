---
name: firebase-security-rules-auditor
description: 'Audit Firebase Security Rules for Firestore and Cloud Storage. Use when reviewing rules diffs, hardening Firebase apps, validating generated rules, checking emulator tests, or investigating authorization, data validation, privilege escalation, and resource abuse risks in Firebase projects.'
zh_description: "审计 Firestore 与 Cloud Storage 安全规则，检查授权、字段校验、权限提升、资源滥用和模拟器测试覆盖。"
version: "1.0.1"
author: seaworld008
source: github:firebase/agent-skills
source_url: "https://github.com/firebase/agent-skills/tree/main/skills/firebase-security-rules-auditor"
license: Apache-2.0
tags: '[firebase, firestore, cloud-storage, security-rules, authorization, appsec]'
created_at: "2026-07-06"
updated_at: "2026-07-10"
quality: 4
complexity: advanced
---

# Overview

This skill acts as an auditor for Firebase Security Rules, evaluating them
against a rigorous set of criteria to ensure they are secure, robust, and
correctly implemented.

# Scoring Criteria

## Assessment: Security Validator (Red Team Edition)

You are a Senior Security Auditor and Penetration Tester specializing in
Firestore. Your goal is to find "the hole in the wall." Do not assume a rule is
secure because it looks complex; instead, actively try to find a sequence of
operations to bypass it.

### Mandatory Audit Checklist:

1. **The Update Bypass:** Compare 'create' and 'update' rules. Can a user create
   a valid document and then 'update' it into an invalid or malicious state
   (e.g., changing their role, bypassing size limits, or corrupting data types)?
1. **Authority Source:** Does the security rely on user-provided data
   (request.resource.data) for sensitive fields like 'role', 'isAdmin', or
   'ownerId'? Carefully consider the source for that authority.
1. **Business Logic vs. Rules:** Does the rule set actually support the app's
   purpose? (e.g., In a collaboration app, can collaborators actually read the
   data? If not, the rules are "broken" or will force insecure workarounds).
1. **Storage Abuse:** Are there string length or array size limits? If not,
   label it as a "Resource Exhaustion/DoS" risk.
1. **Type Safety:** Are fields checked with 'is string', 'is int', or 'is
   timestamp'?
1. **Field-Level vs. Identity-Level Security:** Be careful with rules that use
   \`hasOnly()\` or \`diff()\`. While these restrict *which* fields can be
   updated, they do NOT restrict *who* can update them unless an ownership check
   (e.g., \`resource.data.uid == request.auth.uid\`) is also present. If a rule
   allows any authenticated user to update fields on another user's document
   without a corresponding ownership check, it is a data integrity
   vulnerability.

### Admin Bootstrapping & Privileges:

The admin bootstrapping process is limited in this app. If the rules use a
single hardcoded admin email (e.g., checking request.auth.token.email ==
'admin@example.com'), this should NOT count against the score as long as:

- email_verified is also checked (request.auth.token.email_verified == true).
- It is implemented in a way that does not allow additional admins to add
  themselves or leave an escalation risk open.

### Scoring Criteria (1-5):

- **1 (Critical):** Unauthorized data access (leaks), privilege escalation, or
  total validation bypass.
- **2 (Major):** Broken business logic, self-assigned roles, bypass of controls.
- **3 (Moderate):** PII exposure (e.g., public emails), Inconsistent validation
  (create vs update) on critical fields
- **4 (Minor):** Problems that result in self-data corruption like update
  bypasses that only impact the user's own data, lack of size limits, missing
  minor type checks or over-permissive read access on non-sensitive fields.
- **5 (Secure):** Comprehensive validation, strict ownership, and role-based
  access via secure ACLs.

Return your assessment in JSON format using the following structure: { "score":
1-5, "summary": "overall assessment", "findings": \[ { "check": "checklist
item", "severity": "critical|major|moderate|minor", "issue": "description",
"recommendation": "fix" } \] }
<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## Local Curation Supplement

The upstream assessment and scoring guidance above is preserved unchanged. This
repository-maintained supplement extends it to the Firebase surfaces and test
evidence expected from a production security review.

## Trigger / When to Use

- A pull request changes `firestore.rules`, `storage.rules`, `firebase.json`, or
  Firebase emulator tests.
- An app adds generated rules or changes its collections, storage paths, custom
  claims, membership model, or tenant boundaries.
- A team is investigating permission errors, cross-user access, public data
  exposure, unsafe uploads, or unexpected query failures.
- A reviewer needs evidence that intended access succeeds and attacker access
  fails before deploying rules.

## Core Capabilities

1. Map Firestore collections, Cloud Storage paths, client operations, and Admin
   SDK bypasses to explicit trust boundaries.
2. Test authorization independently for anonymous users, owners, non-owners,
   collaborators, tenant members, and administrators.
3. Compare `create`, `update`, `delete`, `get`, `list`, and query behavior rather
   than treating broad `read` or `write` grants as one operation.
4. Check immutable identity fields, field allowlists, types, enums, timestamps,
   and resource-size limits without confusing validation with authorization.
5. Turn each material finding into an emulator test, emphasizing denied paths
   and privilege-escalation attempts.

## Firestore Operation and Access Matrix

Inventory the rules and the client calls that exercise them before assigning a
score. Record any server or Admin SDK path separately because those calls bypass
Security Rules.

| Actor | Expected private-data access | Primary attack to test |
|---|---|---|
| unauthenticated | none unless explicitly public | direct get, list, create, upload |
| authenticated owner | own scoped records and files | forged path or mutable owner ID |
| authenticated non-owner | no other user's private data | guessed document and storage paths |
| member/collaborator | only authorized team or tenant | changed team ID or stale membership |
| admin/moderator | narrowly defined privileged actions | self-assigned role or editable ACL |

Check Firestore operations independently:

| Operation | Review question |
|---|---|
| `get` | Can an actor read a known document ID outside their scope? |
| `list` | Can the proposed query return any document the actor may not read? |
| `create` | Are ownership, required fields, types, values, and sizes validated? |
| `update` | Are trusted fields immutable and all post-update invariants rechecked? |
| `delete` | Can a non-owner, departed member, or lower role destroy data? |

When product requirements are incomplete, state a least-privilege assumption in
the report instead of silently granting access.

## Create, Update, Field, and Query Checks

### Authorization and create/update parity

- Require `request.auth != null` before private access.
- Derive authority from a path parameter, trusted existing document, protected
  membership record, or custom claim. Never rely only on user-controlled
  `request.resource.data.role`, `isAdmin`, `ownerId`, or `tenantId`.
- Apply the same schema and size invariants to the resulting document on both
  create and update.
- Preserve `uid`, `ownerId`, `tenantId`, `role`, and `createdAt` unless a
  separately authorized transition explicitly permits a change.
- Check identity as well as changed fields: `diff().affectedKeys().hasOnly(...)`
  limits what changed, not who may change it.

```javascript
function isOwner(userId) {
  return request.auth != null && request.auth.uid == userId;
}

function validProfile(data) {
  return data.keys().hasOnly([
      "uid", "displayName", "role", "createdAt", "updatedAt"
    ])
    && data.uid is string
    && data.displayName is string
    && data.displayName.size() <= 80
    && data.role == "member"
    && data.createdAt is timestamp
    && data.updatedAt is timestamp;
}

match /users/{userId} {
  allow create: if isOwner(userId)
    && request.resource.data.uid == userId
    && validProfile(request.resource.data);

  allow update: if isOwner(userId)
    && request.resource.data.uid == resource.data.uid
    && request.resource.data.role == resource.data.role
    && request.resource.data.createdAt == resource.data.createdAt
    && validProfile(request.resource.data);
}
```

### Field and query safety

- Use `keys().hasOnly(...)` and `keys().hasAll(...)` for allowed and required
  fields, then validate types, enum values, string/list sizes, and timestamps.
- Review every `get()` and `exists()` dependency. A membership or role document
  is not trustworthy if the same user can create or modify it.
- Remember that rules are not filters. A list or collection-group query must be
  provably safe for every possible result.
- Compare actual client queries with rule constraints, including owner or tenant
  `where` clauses. If listing is unnecessary, use an explicit denial:

```javascript
allow get: if isOwner(userId);
allow list: if false;
```

## Cloud Storage Review

Audit Storage rules separately even when Firestore stores file metadata. Both
sides must enforce the same ownership or tenant model.

```javascript
match /users/{userId}/uploads/{fileName} {
  allow read: if request.auth != null && request.auth.uid == userId;
  allow write: if request.auth != null
    && request.auth.uid == userId
    && request.resource.size < 5 * 1024 * 1024
    && request.resource.contentType.matches('image/.*');
}
```

Verify path ownership, private versus public reads, overwrite and deletion
rules, file-size caps, content-type checks, and validated metadata. Treat file
extensions and client-supplied metadata as untrusted, and test guessed paths for
another user or tenant.

## Emulator Negative Tests

Use `@firebase/rules-unit-testing` for both allowed behavior and attacker paths.
Seed fixtures with rules disabled, then perform the tested operation through an
authenticated or unauthenticated client context.

```javascript
import fs from "node:fs";
import {
  assertFails,
  initializeTestEnvironment,
} from "@firebase/rules-unit-testing";
import { doc, setDoc, updateDoc } from "firebase/firestore";

test("non-owner cannot update another user's profile", async () => {
  const env = await initializeTestEnvironment({
    projectId: "demo-security-rules",
    firestore: { rules: fs.readFileSync("firestore.rules", "utf8") },
  });

  try {
    await env.withSecurityRulesDisabled(async (context) => {
      await setDoc(doc(context.firestore(), "users/alice"), {
        uid: "alice",
        displayName: "Alice",
        role: "member",
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    });

    const bobDb = env.authenticatedContext("bob").firestore();
    await assertFails(updateDoc(doc(bobDb, "users/alice"), {
      displayName: "Compromised",
    }));
  } finally {
    await env.cleanup();
  }
});
```

At minimum, add negative cases for unauthenticated private access, non-owner
get/list/update/delete, role escalation, owner or tenant mutation, invalid
types, oversized strings/lists/files, unsafe content types, and cross-tenant
membership. Pair them with positive tests for every intended owner, member, or
public access path.

## Severity and Report

| Severity | Typical impact |
|---|---|
| Critical | private-data disclosure, privilege escalation, cross-tenant access, admin bypass |
| High | write/delete of another user's data, mutable owner/role, sensitive public list |
| Medium | important type or size validation gap, create/update mismatch, weak Storage metadata check |
| Low | low-impact overexposure, minor resource cap omission, incomplete test evidence |

Raise severity for PII, billing data, messages, invite tokens, credentials,
precise location, or child-safety data. Report exact rule evidence, exploit
preconditions, impact, a least-privilege remediation, and the emulator test that
would prove the fix:

```json
{
  "score": 2,
  "summary": "Authentication is required, but cross-user updates are allowed.",
  "findings": [
    {
      "severity": "high",
      "rule": "match /users/{userId}: allow update",
      "issue": "The rule does not require request.auth.uid == userId.",
      "impact": "Any signed-in user can modify another user's profile.",
      "recommendation": "Require owner identity and preserve uid, role, and createdAt.",
      "test": "Assert that bob cannot update users/alice in the emulator."
    }
  ]
}
```

## Boundaries

- Do not claim rules are secure without the data model, real client queries,
  Cloud Storage paths, and executable negative-test evidence.
- Do not weaken rules merely to make a client query pass; revise the query or
  data model while preserving least privilege.
- Do not treat Security Rules as server-side validation for privileged backend
  operations, and remember that the Admin SDK bypasses them.
- Do not recommend public access unless the product explicitly requires it and
  the exposed fields or files are safe for every internet user.
- Do not deploy or modify production Firebase state during an audit without
  explicit authorization.
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
