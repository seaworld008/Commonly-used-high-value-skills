# Event Schema Design

## Naming Conventions

```
[object]_[action]

Examples:
- user_signed_up
- item_added_to_cart
- checkout_completed
- article_viewed
- subscription_started
```

## Event Structure Template

```typescript
interface AnalyticsEvent {
  // Required
  event_name: string;           // e.g., "checkout_completed"
  timestamp: string;            // ISO 8601 format
  user_id?: string;             // Authenticated user ID
  anonymous_id: string;         // Device/session identifier

  // Context (auto-captured)
  context: {
    page_url: string;
    page_title: string;
    referrer: string;
    user_agent: string;
    locale: string;
    timezone: string;
  };

  // Event-specific properties
  properties: Record<string, unknown>;
}
```

## Common Event Examples

```typescript
// User Signup
{
  event_name: "user_signed_up",
  properties: {
    signup_method: "email" | "google" | "apple",
    referral_source: string,
    plan_type: "free" | "pro" | "enterprise"
  }
}

// Purchase Completed
{
  event_name: "purchase_completed",
  properties: {
    order_id: string,
    total_amount: number,
    currency: "JPY" | "USD",
    item_count: number,
    payment_method: string,
    coupon_code?: string
  }
}

// Feature Used
{
  event_name: "feature_used",
  properties: {
    feature_name: string,
    feature_version: string,
    duration_seconds?: number,
    success: boolean
  }
}

// Content Viewed
{
  event_name: "content_viewed",
  properties: {
    content_id: string,
    content_type: "article" | "video" | "product",
    content_title: string,
    view_duration_seconds: number,
    scroll_depth_percent: number
  }
}
```
