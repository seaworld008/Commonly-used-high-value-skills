# Analytics Platform Integration

## GA4 Implementation

```typescript
// lib/analytics.ts
import { getAnalytics, logEvent, setUserProperties } from 'firebase/analytics';

const analytics = getAnalytics();

// Track event
export function trackEvent(
  eventName: string,
  properties?: Record<string, unknown>
) {
  logEvent(analytics, eventName, properties);
}

// Set user properties
export function setUserTraits(traits: Record<string, unknown>) {
  setUserProperties(analytics, traits);
}

// Track page view
export function trackPageView(pagePath: string, pageTitle: string) {
  logEvent(analytics, 'page_view', {
    page_path: pagePath,
    page_title: pageTitle
  });
}
```

## Amplitude Implementation

```typescript
// lib/analytics.ts
import * as amplitude from '@amplitude/analytics-browser';

amplitude.init(process.env.NEXT_PUBLIC_AMPLITUDE_API_KEY!);

export function trackEvent(
  eventName: string,
  properties?: Record<string, unknown>
) {
  amplitude.track(eventName, properties);
}

export function identifyUser(
  userId: string,
  traits?: Record<string, unknown>
) {
  amplitude.setUserId(userId);
  if (traits) {
    const identify = new amplitude.Identify();
    Object.entries(traits).forEach(([key, value]) => {
      identify.set(key, value as string);
    });
    amplitude.identify(identify);
  }
}

export function trackRevenue(
  productId: string,
  price: number,
  quantity: number
) {
  const revenue = new amplitude.Revenue()
    .setProductId(productId)
    .setPrice(price)
    .setQuantity(quantity);
  amplitude.revenue(revenue);
}
```

## Mixpanel Implementation

```typescript
// lib/analytics.ts
import mixpanel from 'mixpanel-browser';

mixpanel.init(process.env.NEXT_PUBLIC_MIXPANEL_TOKEN!);

export function trackEvent(
  eventName: string,
  properties?: Record<string, unknown>
) {
  mixpanel.track(eventName, properties);
}

export function identifyUser(
  userId: string,
  traits?: Record<string, unknown>
) {
  mixpanel.identify(userId);
  if (traits) {
    mixpanel.people.set(traits);
  }
}

export function trackPageView() {
  mixpanel.track_pageview();
}
```

## React Hook for Analytics

```typescript
// hooks/useAnalytics.ts
import { useCallback, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { trackEvent, trackPageView } from '@/lib/analytics';

export function useAnalytics() {
  const pathname = usePathname();

  // Auto-track page views
  useEffect(() => {
    trackPageView(pathname, document.title);
  }, [pathname]);

  // Track custom events
  const track = useCallback((
    eventName: string,
    properties?: Record<string, unknown>
  ) => {
    trackEvent(eventName, {
      ...properties,
      page_path: pathname
    });
  }, [pathname]);

  return { track };
}

// Usage
function CheckoutButton() {
  const { track } = useAnalytics();

  const handleClick = () => {
    track('checkout_started', { cart_value: 9800 });
    // ... proceed to checkout
  };

  return <button onClick={handleClick}>Checkout</button>;
}
```
