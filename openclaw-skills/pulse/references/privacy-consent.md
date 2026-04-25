# Privacy & Consent Management

## Consent Management

```typescript
// lib/consent.ts
type ConsentCategory = 'analytics' | 'marketing' | 'functional';

interface ConsentState {
  analytics: boolean;
  marketing: boolean;
  functional: boolean;
}

export function getConsentState(): ConsentState {
  const stored = localStorage.getItem('user_consent');
  if (stored) {
    return JSON.parse(stored);
  }
  return {
    analytics: false,
    marketing: false,
    functional: true
  };
}

export function setConsentState(consent: ConsentState) {
  localStorage.setItem('user_consent', JSON.stringify(consent));

  // Update analytics based on consent
  if (consent.analytics) {
    enableAnalytics();
  } else {
    disableAnalytics();
  }
}

export function hasConsent(category: ConsentCategory): boolean {
  return getConsentState()[category];
}
```

## Privacy-Safe Tracking

```typescript
// Track only with consent
export function trackEventWithConsent(
  eventName: string,
  properties?: Record<string, unknown>
) {
  if (!hasConsent('analytics')) {
    return;
  }

  // Remove PII from properties
  const safeProperties = removePII(properties);
  trackEvent(eventName, safeProperties);
}

function removePII(
  properties?: Record<string, unknown>
): Record<string, unknown> | undefined {
  if (!properties) return undefined;

  const piiFields = ['email', 'phone', 'name', 'address', 'ip'];
  const safe = { ...properties };

  piiFields.forEach(field => {
    if (field in safe) {
      delete safe[field];
    }
  });

  return safe;
}
```
