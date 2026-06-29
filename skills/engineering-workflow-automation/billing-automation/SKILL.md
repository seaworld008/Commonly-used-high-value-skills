---
name: billing-automation
description: 'Build automated billing systems for recurring payments, invoicing, subscription lifecycle, and dunning management. Use when implementing subscription billing, automating invoicing, or managing recurring payment systems.'
zh_description: "用于构建订阅计费、自动开票、续费生命周期和催收管理流程。"
version: "1.0.0"
author: "seaworld008"
source: "github:wshobson/agents"
source_url: "https://github.com/wshobson/agents/blob/main/plugins/payment-processing/skills/billing-automation/SKILL.md"
license: MIT
tags: '["automation", "billing", "workflow"]'
created_at: "2026-05-28"
updated_at: "2026-06-29"
quality: 3
complexity: "intermediate"
---

# Billing Automation

Master automated billing systems including recurring billing, invoice generation, dunning management, proration, and tax calculation.

## When to Use This Skill

- Implementing SaaS subscription billing
- Automating invoice generation and delivery
- Managing failed payment recovery (dunning)
- Calculating prorated charges for plan changes
- Handling sales tax, VAT, and GST
- Processing usage-based billing
- Managing billing cycles and renewals

## Core Concepts

### 1. Billing Cycles

**Common Intervals:**

- Monthly (most common for SaaS)
- Annual (discounted long-term)
- Quarterly
- Weekly
- Custom (usage-based, per-seat)

### 2. Subscription States

```
trial → active → past_due → canceled
              → paused → resumed
```

### 3. Dunning Management

Automated process to recover failed payments through:

- Retry schedules
- Customer notifications
- Grace periods
- Account restrictions

### 4. Proration

Adjusting charges when:

- Upgrading/downgrading mid-cycle
- Adding/removing seats
- Changing billing frequency

## Quick Start

```python
from billing import BillingEngine, Subscription

# Initialize billing engine
billing = BillingEngine()

# Create subscription
subscription = billing.create_subscription(
    customer_id="cus_123",
    plan_id="plan_pro_monthly",
    billing_cycle_anchor=datetime.now(),
    trial_days=14
)

# Process billing cycle
billing.process_billing_cycle(subscription.id)
```

## Detailed patterns and worked examples

Detailed pattern documentation lives in `references/details.md`. Read that file when the navigation tier above is insufficient.

## Implementation Checklist

Before building or changing billing logic, capture:

- Product catalog: plan ids, prices, currency, billing interval, trial rules, and included usage.
- Customer lifecycle: signup, trial conversion, renewal, pause, resume, cancellation, and reactivation.
- Payment failure policy: retry cadence, email/SMS notices, grace period, account restrictions, and final cancellation behavior.
- Proration rules: upgrades, downgrades, seat changes, coupons, taxes, refunds, and invoice credits.
- Ledger model: immutable invoice records, payment attempts, adjustments, and audit metadata.
- Compliance constraints: tax invoices, receipts, PCI boundaries, refund approvals, and data-retention requirements.

## Verification Scenarios

Test billing changes with concrete timelines:

1. Trial user converts to paid plan before trial end.
2. Monthly subscriber upgrades mid-cycle and receives prorated credit.
3. Payment fails three times, enters dunning, then recovers.
4. Annual customer cancels with service continuing through paid period.
5. Seat count changes immediately before renewal.

Record expected invoices, subscription state transitions, customer notifications, and ledger entries for each scenario. Do not ship billing automation with only happy-path tests.

## Risk Controls

Billing changes need stronger safeguards than ordinary workflow automation:

- Use idempotency keys for invoice creation, payment attempts, webhook processing, and retry jobs.
- Store external payment processor ids separately from internal subscription ids.
- Treat webhooks as eventually consistent; never assume event order is guaranteed.
- Make retry jobs safe to run more than once.
- Keep a manual override path for support teams, but log who changed what and why.
- Separate preview calculations from committed ledger writes.
- Add alerts for abnormal retry volume, invoice creation failures, tax calculation errors, and webhook backlog.

## User-facing Summary

When reporting billing automation work, include the business effect:

```text
Changed:
Risk reduced:
Customer impact:
Accounting impact:
Tests run:
Open rollout concern:
```

This helps reviewers evaluate both code correctness and revenue operations risk.
