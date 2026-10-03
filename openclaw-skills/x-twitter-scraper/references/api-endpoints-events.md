> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `645ccfbad23f258ed9efb24de1ead641f15938e1`. Preserved from `98260596503409589f727b839e5bd3e2cff910e1` under the recorded license. Use the canonical skill and current references for new work.

# Xquik REST API endpoints: events

## List events

Events can contain private monitor data. Show the exact monitor or keyword
monitor, event type filters, page size, cursor, destination, and retention.
Require explicit approval for that scope before reading a page.

```http
GET /events
```

Use these query parameters:

| Parameter | Type | Description |
|-------|------|-------------|
| `monitorId` | string | Filter by monitor ID |
| `keywordMonitorId` | string | Filter by keyword monitor ID |
| `eventType` | string | Filter by event type |
| `limit` | number | Results per page from 1-100; defaults to 50 |
| `cursor` | string | Previous `nextCursor` |

The API returns:
```json
{
  "events": [
    {
      "id": "9010",
      "type": "tweet.new",
      "monitorId": "7",
      "monitorType": "account",
      "username": "elonmusk",
      "occurredAt": "2026-02-24T16:45:00.000Z",
      "data": {
        "id": "1893556789012345678",
        "text": "Hello world",
        "author": {
          "id": "44196397",
          "userName": "elonmusk",
          "name": "Elon Musk"
        },
        "createdAt": "2026-02-24T16:45:00.000Z"
      }
    }
  ],
  "hasMore": true,
  "nextCursor": "MjAyNi0wMi0yNFQxNjozMDowMC4wMDBa..."
}
```

Account events set `monitorType` to `account`. They include `monitorId` and
`username`. They omit `keywordMonitorId` and `query`.

Keyword events set `monitorType` to `keyword`. They include `monitorId`,
`keywordMonitorId`, and `query`. Both ID fields contain the keyword monitor ID.
Keyword events omit `username`.

## Get event

Show the event ID, monitor or account scope, destination, and retention. Require
explicit approval before retrieving the event. Require separate approval before
another workflow forwards private event data.

```http
GET /events/{id}
```

Returns 1 event. Detailed events may include `xEventId`, the source X event ID.

---
