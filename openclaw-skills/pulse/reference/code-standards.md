> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `f425adcb2111ca8c0be88b325888ff61b64dec49`. Preserved from `bd5d9cd61c0718c3c093e9cfcce2bd20e9cb4104` under the recorded license. Use the canonical skill and current references for new work.

# Pulse Code Standards

## Good Pulse Code

```typescript
// Clear event naming with typed properties
interface CheckoutStartedEvent {
  cart_value: number;
  item_count: number;
  currency: 'JPY' | 'USD';
}

function trackCheckoutStarted(props: CheckoutStartedEvent) {
  trackEvent('checkout_started', props);
}

// Consent-aware tracking
if (hasConsent('analytics')) {
  trackCheckoutStarted({
    cart_value: cart.total,
    item_count: cart.items.length,
    currency: 'JPY'
  });
}
```

## Bad Pulse Code

```typescript
// Vague event names, untyped properties
trackEvent('click', { data: someObject });

// PII in tracking
trackEvent('signup', { email: user.email, phone: user.phone });

// No consent check
trackEvent('page_view', { path: window.location.href });
```
