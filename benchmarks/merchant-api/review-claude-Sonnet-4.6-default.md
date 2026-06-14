# Merchant Integration API — Design Review

## High Severity

### 1. State transition endpoints use inconsistent naming
**Affected:** `POST /orders/{id}/confirmation`, `/rejection`, `/ready`

The transition sub-resources mix noun and verb forms (`/confirmation` vs `/ready`) and imply document creation rather than state change. Client code ends up with three unrelated URLs for what is logically one operation.

**Fix:** Either use a single `PATCH /orders/{id}` with a `status` field plus transition-specific payload, or keep sub-resource POSTs but name them consistently as verbs: `/confirm`, `/reject`, `/mark-ready`.

---

### 2. No idempotency support on mutating endpoints
**Affected:** All three transition POSTs

A merchant POS retrying `confirmOrder` after a timeout receives a `409 Conflict` with no way to determine whether the first attempt succeeded. This is a real operational hazard in unreliable network conditions.

**Fix:** Require an `Idempotency-Key` header on all state-transition POSTs. Cache `(key → response)` server-side for 24 hours and replay the original response on duplicates rather than returning 409.

---

### 3. No push mechanism — polling only
**Affected:** `GET /orders`

Merchants have no way to be notified of new orders except by polling `listOrders`. This introduces latency, unnecessary server load, and brittle client loops — all problematic in a time-sensitive delivery context.

**Fix:** Add a webhook registration endpoint (`POST /merchants/{id}/webhooks`) and emit events for `order.created`, `order.cancelled`, and other merchant-relevant transitions. At minimum, document the polling SLA.

---

### 4. Full catalog replace has no partial-failure or dry-run semantics
**Affected:** `PUT /merchants/{id}/catalog`

If 1 of 500 items fails validation, the entire upload is rejected with a 422 and the existing catalog is unchanged — but the spec doesn't say so. A merchant with a large catalog has no safe way to validate before committing, or to recover from a mid-day failure.

**Fix:** Choose one of: (a) document the all-or-nothing guarantee explicitly; (b) add `?dryRun=true` to validate without applying; or (c) introduce a two-phase publish — `POST /catalog/drafts` → `POST /catalog/drafts/{id}/publish`.

---

## Medium Severity

### 5. Ambiguous 409 conflates idempotent replay with invalid transition
**Affected:** All transition endpoints

A `409` on "already confirmed" (safe to ignore) looks identical to a `409` on "already cancelled" (genuinely unrecoverable). Clients cannot distinguish these without brittle string parsing of the `code` field.

**Fix:** Define distinct `Error.code` values — e.g. `ORDER_ALREADY_IN_STATE` vs `ORDER_TRANSITION_INVALID` — and document the full state machine so clients can pre-validate before calling.

---

### 6. Order state machine is undocumented
**Affected:** `OrderStatus` enum

Seven status values are defined but there is no specification of which transitions are merchant-triggered vs platform-triggered, which are terminal, or which are reversible. The comment "cancelled by platform or customer" is informative but not machine-readable or enforced.

**Fix:** Add an `x-state-machine` extension block, or link to external docs, that enumerates every valid transition and its actor. At minimum, mark terminal states and identify which statuses clients can write.

---

### 7. Page-number pagination is unstable under concurrent writes
**Affected:** `GET /orders`

If a new order is inserted between page 1 and page 2 fetches, items shift between pages — clients see duplicates and miss others. High-volume merchants polling for new orders will hit this regularly.

**Fix:** Add cursor-based pagination. Alternatively, since the `from`/`to` filters are already present, document `from` as a stable continuation cursor and have the response return a `nextFrom` timestamp.

---

### 8. Currency is defined per-item rather than per-merchant
**Affected:** `CatalogItemInput`, `Order`

Nothing prevents a catalog from mixing EUR and GBP items, making the order-level `subtotal` and `currency` ambiguous. There is no constraint enforcing consistency.

**Fix:** Promote `currency` to a merchant- or catalog-level setting and remove it from `CatalogItemInput`. If multi-currency is intentional, document how `subtotal` is computed and add a validation rule.

---

### 9. `lineTotal` creates a dual source of truth
**Affected:** `OrderLine`

`lineTotal` is redundant with `unitPrice × quantity`. If they ever diverge — due to a discount, tax, rounding, or bug — the spec provides no guidance on which field is authoritative.

**Fix:** Either remove `lineTotal` and let clients compute it, or introduce an `adjustments` array to explain any delta and declare `lineTotal` the authoritative figure.

---

### 10. `deleteCatalogItem` has no guard against active order references
**Affected:** `DELETE /catalog/items/{itemId}`

Deleting an item referenced by a `pending` or `confirmed` order leaves those order lines pointing at a non-existent resource. Referential integrity behavior is entirely undefined.

**Fix:** Either block deletion when active orders reference the item (return `409`), or soft-delete by setting `available: false` and defer hard deletion. Either way, document the behavior.

---

## Low Severity

### 11. `markOrderReady` body is not marked `required`
**Affected:** `POST /orders/{id}/ready`

The other two transition endpoints set `required: true` on their request bodies. `markOrderReady` omits this, which causes generated SDK clients to treat the body as fully optional and inconsistent.

**Fix:** Align all transition endpoints — either always `required: true` (with all-optional fields inside) or consistently `required: false`.

---

### 12. `subtotal` scope is undefined
**Affected:** `Order.subtotal`

The field name alone doesn't indicate whether `subtotal` includes taxes, delivery fees, or service charges. This matters for merchant reconciliation and receipt generation.

**Fix:** Add a `pricing` object with explicit `subtotal`, `deliveryFee`, `taxes`, and `total` fields, or at minimum add a `description` that precisely defines what `subtotal` contains.

---

### 13. No `ETag` / optimistic locking on catalog item updates
**Affected:** `PATCH /catalog/items/{itemId}`

Two concurrent PATCH requests for the same item silently last-write-wins. There is no mechanism for a client to detect or prevent a conflicting update.

**Fix:** Return an `ETag` on `GET` and `PATCH` catalog item responses and honour `If-Match` on PATCH, returning `412 Precondition Failed` on conflict.

---

### 14. `CustomerSummary.phone` has no consent or masking policy
**Affected:** `CustomerSummary`

The spec notes phone is provided "only when the merchant needs to contact the customer" but defines no mechanism for requesting it, no consent model, and no indication of whether the number is real or platform-proxied. This is a material GDPR concern in most target markets.

**Fix:** Document whether the number is real or proxied, the conditions under which it is included, and the data-handling obligations placed on merchants who receive it.

---

### 15. No `401` or `403` responses defined anywhere
**Affected:** All endpoints

The API uses bearer JWT authentication but no endpoint documents `401 Unauthorized` (expired/invalid token) or `403 Forbidden` (valid token, wrong merchant). Notably, a merchant accessing another merchant's `merchantId` should receive `403`, not `404`.

**Fix:** Add shared `Unauthorized` and `Forbidden` response components and apply them globally. Document that `merchantId` in the path must match the merchant claim in the JWT.