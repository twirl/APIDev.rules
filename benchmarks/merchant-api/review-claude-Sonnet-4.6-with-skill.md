Good, I have everything I need. Here is the full review.

---

## API Review: Merchant Integration API v1.0.0

**Surface reviewed:** OpenAPI 3.1.0 specification for merchant catalog management and order lifecycle. Consumer is a merchant's backend system integrating over HTTPS with JWT auth.

---

### Critical / High Severity

**1. No idempotency on state-changing POST operations**

`confirmOrder`, `rejectOrder`, and `markOrderReady` are all non-idempotent `POST` operations with no idempotency token, ETag, or revision check. A merchant server that times out and retries confirming an order has no way to know whether the first call landed. The result could be a `409 Conflict` (if the server processed it) or a silent double-action (if it didn't). The spec documents no guidance on retry safety for any of these.

Fix: require a client-supplied `Idempotency-Key` header on all three order action endpoints, and document that the server returns the same response for repeated requests with the same key within a defined window (e.g. 24 hours). Alternatively, use ETag/`If-Match` on the order resource.

```yaml
parameters:
  - name: Idempotency-Key
    in: header
    required: true
    schema:
      type: string
      format: uuid
    description: >
      Client-generated UUID. Repeated requests with the same key
      return the cached response without re-executing the action.
      Valid for 24 hours.
```

---

**2. Monetary values use `number / double` — precision loss guaranteed**

`price`, `unitPrice`, `lineTotal`, and `subtotal` are all typed `number, format: double`. IEEE 754 doubles cannot represent most decimal money values exactly. `12.99` becomes `12.989999999999999147...` in many JSON parsers, and accumulated rounding across order lines produces incorrect totals.

Fix: change all money fields to `type: string` with a documented decimal format, or to `type: integer` representing minor currency units (e.g. cents). Add an explicit note in the schema.

```yaml
price:
  type: string
  pattern: '^\d+(\.\d{1,2})?$'
  description: >
    Decimal amount as a string to preserve precision.
    Two decimal places maximum. Example: "12.99"
  example: "12.99"
```

---

**3. `replaceCatalog` (PUT) has no concurrency protection**

`PUT /merchants/{merchantId}/catalog` replaces the entire catalog. If two processes upload simultaneously — a common scenario when merchants run nightly catalog syncs alongside real-time price updates — one silently overwrites the other. There is no ETag, version token, or `If-Match` guard.

Fix: return an `ETag` on `GET /catalog` and `PUT /catalog`, and require `If-Match` on `PUT`. A `412 Precondition Failed` response tells the caller their view is stale.

---

**4. No webhook / push mechanism; polling-only creates serious operational gaps**

The spec has no delivery mechanism for inbound order events. A merchant must poll `GET /merchants/{merchantId}/orders?status=pending` to discover new orders. The spec does not state a polling interval, does not specify whether `pending` orders are guaranteed to remain visible, and does not document any SLA on order acceptance time (typical delivery platforms require a 2–5 minute response window). A missed poll means a missed order.

This is a workflow-level gap, not just a documentation gap. Merchants integrating at scale will build fragile polling loops that are hard to tune without guidance.

Fix: at minimum, document the expected polling frequency, the order visibility window, and the consequences of no response. Ideally, introduce a webhook registration endpoint so the platform pushes `order.created` events, reducing latency and polling load. If webhooks are out of scope now, note it explicitly in the spec and reserve a path (e.g. `/merchants/{merchantId}/webhooks`) to avoid a breaking URL change later.

---

### Medium Severity

**5. `CatalogItemPatch` — ambiguous null vs. absent semantics**

`PATCH` fields are described as "only supplied fields are updated." But the schema does not distinguish between `"available": false` (explicitly set to false), `"available": null` (reset to default?), and the field being absent (unchanged). For `description` and `imageUrl` (both nullable in common practice), a merchant cannot clear a value unless null-means-clear is documented.

Fix: document explicitly whether `null` clears a field or is invalid. If clearing is needed, document it per-field. Consider adopting [JSON Merge Patch (RFC 7396)](https://datatracker.ietf.org/doc/html/rfc7396) semantics explicitly.

---

**6. Order list pagination uses offset/page — not cursor-based**

`GET /orders` accepts `page` and `pageSize`. Offset pagination over a live, mutable dataset (orders are constantly being created, confirmed, and updated) produces skipped or duplicate records when the list changes between pages. A merchant scanning through `pending` orders to process them could miss orders this way.

Fix: replace `page` with an opaque `cursor` token returned in the `pagination` object. The cursor encodes stable traversal position. Keep `pageSize`; drop `page` and `totalPages` (both become meaningless with cursor pagination). If `totalItems` is still needed for UX, make it an optional field that may be omitted or approximate.

```yaml
Pagination:
  type: object
  properties:
    nextCursor:
      type: string
      nullable: true
      description: Opaque token for the next page; null when exhausted
    pageSize:
      type: integer
    totalItems:
      type: integer
      nullable: true
      description: Approximate total; may be omitted on large datasets
```

---

**7. No `401` or `403` responses documented**

Every endpoint specifies `404` and sometimes `409`, but none document `401 Unauthorized` or `403 Forbidden`. All endpoints use JWT bearer auth. Tokens expire. A merchant whose token has lapsed will receive an undocumented status code, which their error handler will likely treat as an unexpected failure rather than a reauth trigger. The spec also gives no guidance on token refresh.

Fix: add `401` and `403` to the shared responses and reference them from every operation. Document what the client should do (reauth vs. check scopes vs. contact support).

---

**8. `OrderRejection.reason = "other"` requires a `note`, but this is not enforced in the schema**

The spec says `note` is "required when reason is `other`," but the schema marks `note` as optional with no conditional validation. Servers will either silently accept invalid rejections or return a runtime error that the spec doesn't document.

Fix: if OpenAPI 3.1's `if/then/else` is supported by your tooling, encode the constraint. Otherwise, document the 422 error body the server returns when `reason=other` and `note` is absent.

```yaml
OrderRejection:
  type: object
  required: [reason]
  properties:
    reason:
      type: string
      enum: [item_unavailable, store_closed, too_busy, order_too_large, other]
    note:
      type: string
  if:
    properties:
      reason:
        const: other
  then:
    required: [reason, note]
```

---

**9. No `429 Too Many Requests` response reserved**

No endpoint documents rate limiting. Any merchant integration will eventually hit a rate limit and have no documented recovery path. The `Retry-After` header behavior is unspecified.

Fix: add `429` to the shared responses and reference it from catalog write operations and order action endpoints at minimum. Document `Retry-After` semantics.

---

**10. `addCatalogItem` returns `201` but no `Location` header**

`POST /merchants/{merchantId}/catalog/items` creates a resource and returns `201 Created` with the created item in the body (including its `itemId`). The `Location` header is absent from the spec. HTTP convention and RFC 9110 both indicate `201` responses should include `Location` pointing to the new resource.

Fix: add the header to the response definition:

```yaml
'201':
  description: Item created
  headers:
    Location:
      schema:
        type: string
        format: uri
      description: URL of the created catalog item
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/CatalogItem'
```

---

### Low Severity / Observations

**11. `preparationTimeMinutes` — unit in name is good, but the field is per-item only**

Preparation time on `CatalogItem` represents a per-item typical duration. Orders with multiple items, or high-volume periods, will differ. When the merchant confirms an order, they provide `estimatedReadyAt` (a timestamp), which is the right signal — but there is no guidance on how the platform uses `preparationTimeMinutes` vs. the confirmed ETA. If the platform auto-suggests an ETA on the confirmation screen based on item prep times, the relationship should be documented to avoid confusion.

**12. `OrderStatus` has `cancelled` but no cancel endpoint**

The spec exposes a `cancelled` status value but provides no endpoint for a merchant to cancel a previously confirmed order. The description says cancellation can happen "by platform or customer," implying it's push-only. This is fine but should be stated explicitly — and there should be a documented mechanism (webhook or polling) for the merchant to detect this transition and stop preparing the order.

**13. `CustomerSummary.phone` has no format constraint**

Phone numbers are notoriously variable internationally. The field is typed `string` with no format, pattern, or note on normalization (E.164 vs. local). Merchant systems that need to display or dial the number will get inconsistent data. Recommend adding `description: "E.164 format, e.g. +15551234567"` and a regex pattern.

**14. `coordinates` object has no documented standard (WGS84 assumed)**

`Address.coordinates` has `lat` and `lng` but no explicit coordinate standard documented. WGS84 is the safe assumption but should be stated.

**15. `CatalogInput` — `replaceCatalog` allows zero items if `minItems: 1` is bypassed**

`CatalogInput.items` has `minItems: 1`, which is correct. However, there is no documented maximum. A malformed upload with 50,000 items has no bounded error path. Document an upper limit and its associated error.

---

### Summary Table

| # | Finding | Severity | Affected Surface |
|---|---------|----------|-----------------|
| 1 | No idempotency on order action POSTs | Critical | `confirmOrder`, `rejectOrder`, `markOrderReady` |
| 2 | Money values use float — precision loss | Critical | `CatalogItem.price`, `OrderLine.*`, `Order.subtotal` |
| 3 | No concurrency guard on catalog replace | High | `replaceCatalog` |
| 4 | No push/webhook; polling gap undocumented | High | Entire order workflow |
| 5 | PATCH null vs. absent semantics undefined | Medium | `updateCatalogItem` |
| 6 | Offset pagination breaks on live order list | Medium | `listOrders` |
| 7 | 401/403 not documented on any endpoint | Medium | All endpoints |
| 8 | `reason=other` note-required rule unenforced | Medium | `rejectOrder` |
| 9 | No 429 / rate-limit path reserved | Medium | Write endpoints |
| 10 | `201` missing `Location` header | Low | `addCatalogItem` |
| 11 | Per-item prep time vs. order ETA relationship unclear | Low | `OrderConfirmation` |
| 12 | `cancelled` status has no merchant-facing endpoint | Low | Order lifecycle |
| 13 | Phone number format undocumented | Low | `CustomerSummary` |
| 14 | Coordinate standard (WGS84) not stated | Low | `Address.coordinates` |
| 15 | No upper bound on catalog item count | Low | `replaceCatalog` |

The two issues most likely to cause production incidents are **#1** (silent double-actions or phantom 409s during network retries) and **#2** (money rounding errors in line totals). Both are worth fixing before any merchant goes live.