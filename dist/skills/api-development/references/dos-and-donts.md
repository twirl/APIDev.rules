## Naming and Signatures

- Do not apply rules mechanically. Follow a rule only when its reason improves the API for this case.

- Make operation signatures explicit about behavior, side effects, cost, inputs, and outcomes.

Bad:

```ts
// The name does not disclose the time range or computational cost.
orders.getStats();
```

Better:

```ts
// The verb and parameters make the cost and scope explicit.
orders.calculateAggregatedStats({
  from: "2026-01-01",
  to: "2026-01-31",
  group_by: "day"
});
```

- Make modifying operations visibly modifying; do not hide state changes behind property assignment, `get*` names, or read-only verbs.

Bad:

```ts
// Assignment syntax hides a state-changing operation.
order.canceled = true;

// A get* method should not rotate or invalidate credentials.
user.getAccessToken({ rotate: true });
```

Better:

```ts
// Both method names clearly describe state changes.
order.cancel();
user.rotateAccessToken();
```

- Make synchronicity visible in names or through a consistent naming convention.

Bad:

```ts
report.generate(); // Sometimes returns a report, sometimes starts a job.
```

Better:

```ts
// The caller can choose the synchronous or asynchronous path explicitly.
report.generateSync();
report.createGenerationTask();
```

- Use concrete, unambiguous names. Avoid vague verbs such as `get`, `apply`, or `make` unless the object and result are obvious.

Bad:

```ts
// Returned data and side effects are unclear.
user.get();
order.apply();
```

Better:

```ts
// The object being returned or changed is explicit.
user.getProfile();
order.applyDiscountCode({ code: "SPRING" });
```

- Prefer full descriptive names over abbreviations.

Bad:

```jsonc
{
  // Abbreviation forces readers to guess the meaning.
  "eta": "2026-05-01T12:00:00Z"
}
```

Better:

```jsonc
{
  // Full name is longer but self-explanatory.
  "estimated_delivery_time": "2026-05-01T12:00:00Z"
}
```

- Keep matching operations named and ordered consistently; paired or related operations should behave alike.

Bad:

```ts
// begin/stop are not a natural pair.
begin_transition();
stop_transition();

// Related functions use different argument ordering.
string_position(haystack, needle);
string_replace(needle, replacement, haystack);
```

Better:

```ts
// Paired operations use matching terms.
start_transition();
stop_transition();

// Related functions keep argument order stable.
string_find(haystack, needle);
string_replace(haystack, needle, replacement);
```

- Avoid double negations and Boolean names that require mental inversion.

Bad:

```jsonc
{
  // true means "not archived"; this requires mental inversion.
  "is_not_archived": true,
  // false means "do notify"; another inversion.
  "dont_notify_user": false
}
```

Better:

```jsonc
{
  // The flag is explicitly positive; no negation.
  "is_archived": false,
  // If a negative action is required, invent a better name that is not explicitly a negation.
  "skip_user_notification": false
}
```

Inverting double negations is even more error-prone than using a single negation. Avoid it completely.

Bad:

```ts
// Easy to invert incorrectly: people may use "||" instead of "&&".
if (!order.no_items && !order.no_payment_method) {
  submitOrder();
}
```

Better:

```ts
// Positive flags make the condition obvious.
if (order.has_items && order.has_payment_method) {
  submitOrder();
}
```

Or:

```ts
// Create a synthetic flag that is precomputed for convenience.
if (order.canSubmit()) {
  submitOrder();
}
```

## Types and Values

- Use UTF-8 for all strings unless specifically instructed otherwise.

- Let names imply types: plural names for arrays, state-like names for booleans, and explicit suffixes for identifiers, dates, and units.

Bad:

```jsonc
{
  // Singular name hides that this is an array.
  "recipe": ["latte", "lungo"],
  // "task" does not say which Boolean state is represented.
  "task": true
}
```

Better:

```jsonc
{
  // Plural name signals an array.
  "recipes": ["latte", "lungo"],
  // Boolean name describes the state.
  "is_task_finished": true
}
```

- Specify the exact standard used for ambiguous values such as dates, durations, coordinates, measurements, and currencies.

Bad:

```jsonc
{
  // Ambiguous: month/day or day/month?
  "date": "11/12/2026",
  // Ambiguous: latitude-longitude or longitude-latitude?
  "location": [22.44, -74.22],
  // Ambiguous: seconds, milliseconds, or minutes?
  "duration": 5000
}
```

Better:

```jsonc
{
  // ISO format removes date ambiguity.
  "iso_date": "2026-11-12",
  "coordinates": {
    // Coordinate standard and component names are explicit.
    "standard": "WGS84",
    "latitude": 22.44,
    "longitude": -74.22
  },
  "duration_ms": 5000
}
```

Other acceptable formats: `"duration": "5000ms"`, `"iso_duration": "PT5S"` or `"duration": { "value": 5000, "unit": "ms" }`; `"coordinates_wgs84_latlong": [22.44, -74.22]` or `coordinates: "74.22 S, 22.44 E"`.

- Always include currency codes with money values. Preserve fixed-precision fractional values for money sums and other values that require precise operations with fractional parts. Use decimal types, integers with a fixed multiplier, or strings instead of floating-point values when precision matters.

Bad:

```jsonc
{
  // Currency is missing.
  "price": "19.99"
}
```

Better:

```jsonc
{
  "price": "19.99",
  // Amount is now interpretable.
  "currency_code": "USD"
}
```

Bad:

```jsonc
{
  // Float representation leaked into a money-like value.
  "account_balance": 0.30000000000000004
}
```

Better:

```jsonc
{
  // String preserves decimal precision.
  "account_balance": "0.30",
  "currency_code": "USD"
}
```

Alternative:

```jsonc
{
  // Integer minor units avoid floating-point precision loss.
  "account_balance_minor_units": 30,
  "currency_code": "USD"
}
```

- Avoid implicit type casting and magic values. If absence, reset, deletion, and unchanged state are different concepts, model them explicitly.

Bad:

```javascript
// null is overloaded: absent, reset, remove, or unknown?
user.setSpendingLimit(null);
```

Better:

```javascript
// Either an explicit operation
user.removeSpendingLimit();
// Or an explicit data format
user.modifySpendingLimit({
  operation_type: "remove"
});
```

- Make new optional Boolean fields default to `false` when possible. If the field is absent, clients may not know whether the caller intentionally disabled the option or used an old client.

## Limits and Traffic

- Declare technical restrictions for every field: length, range, size, format, and allowed values.

- Return machine-readable validation errors that identify the violated boundary.

Bad:

```jsonc
{
  // Human text is hard to handle programmatically.
  "message": "Invalid display name"
}
```

Better:

```jsonc
{
  // Client code can branch on reason and field.
  "reason": "field_too_long",
  "field": "display_name",
  "max_length": 80
}
```

- Limit every request that can process or return an unbounded amount of data.

Bad:

```http
# No limit: response size can grow without bound.
GET /v1/orders
```

Better:

```http
# Limit and cursor bound the response and support traversal.
GET /v1/orders?limit=100&cursor=eyJwYWdlIjoyfQ
```

- Provide filtering, pagination, or query refinement when a consumer may need more data than one request can safely return.

- Split heavyweight data from lightweight metadata when it needs different loading, caching, or quota behavior.

Bad:

```jsonc
{
  "id": "recipe:latte",
  "name": "Latte",
  "description": "Espresso with steamed milk",
  // Heavy data is embedded in every metadata response.
  "image_base64": "<large binary payload>"
}
```

Better:

```jsonc
{
  "id": "recipe:latte",
  "name": "Latte",
  "description": "Espresso with steamed milk",
  // Heavy data can be loaded and cached separately.
  "image_url": "https://cdn.example.com/recipes/latte.png"
}
```

## Errors and Recovery

- Do not return an error when an empty result is a valid result.

Bad:

```http
POST /v1/offers/search?longitude=…&latitude=…

# No offers is not a client mistake.
HTTP/1.1 404 Not Found
{
  "localized_message": "No offers nearby"
}
```

Better:

```http
POST /v1/offers/search?longitude=…&latitude=…

# Empty result is a successful search result.
HTTP/1.1 200 OK
{
  "results": []
}
```

- Avoid ambiguity with optional arrays. If an array filter is optional but an empty array has no useful meaning, require at least one element when the array is present.

Bad:

```yaml
SearchRequest:
  type: object
  properties:
    recipe_ids:
      type: array
      description: Optional recipe filter.
      items:
        type: string
```

This creates ambiguity about whether `recipe_ids: []` must be ignored (treated as equivalent to absent `recipe_ids`) or return an empty response.

Better:

```yaml
SearchRequest:
  type: object
  properties:
    recipe_ids:
      type: array
      description: Optional recipe filter. Omit to search all recipes.
      minItems: 1
      items:
        type: string
```

This keeps `{}` as "no recipe filter" and rejects `{ "recipe_ids": [] }` instead of making servers and clients guess what it means.

- Validate inputs early and report all useful validation problems when possible.

Bad:

```jsonc
{
  // Too generic and reports only one field.
  "reason": "invalid_request",
  "field": "email"
}
```

Better:

```jsonc
{
  // Client can fix all known validation issues in one pass.
  "reason": "validation_failed",
  "violations": [
    { "field": "email", "reason": "invalid_format" },
    { "field": "display_name", "reason": "field_too_long", "max_length": 80 }
  ]
}
```

- Design errors to help clients decide what to do next: retry, wait, refresh state, fix input, reauthorize, or fail permanently.

Bad:

```jsonc
{
  // Client cannot infer a recovery action.
  "message": "Invalid price"
}
```

Better:

```jsonc
{
  // Client can refresh the offer and retry.
  "reason": "offer_expired",
  "recovery": "fetch_new_offer"
}
```

- Distinguish user-facing localized messages from developer-facing diagnostic details.

Bad:

```jsonc
{
  // For the end user, this is meaningless.
  // They need to know what to do about the error they see.
  "message": "Card token validation failed because processor response code was 54"
}
```

Better (note the `localized_` prefix to distinguish a user-facing string):

```jsonc
{
  // Safe for UI.
  "localized_message": "This card cannot be used. Try another payment method.",
  "details": {
    // Useful for developers and logs.
    "processor_reason": "expired_card",
    "error_message": "Card marked as expired by the payment gateway"
  }
}
```

- Return unresolvable errors before resolvable ones when the client cannot proceed anyway.

- Prioritize the most significant error when multiple problems exist.

## Reliability and Safety

- Describe retry policies, including backoff, retry limits, and which errors are retryable.

Bad:

```jsonc
{
  // Client does not know whether or when to retry.
  "reason": "service_unavailable"
}
```

Better:

```jsonc
{
  // Retry behavior is explicit.
  "reason": "service_unavailable",
  "retryable": true,
  "retry_after_ms": 2000,
  "retry_policy": "exponential_backoff"
}
```

- Make operations idempotent. If natural idempotency is impossible, require explicit idempotency tokens, drafts, revisions, or equivalent safeguards.

- Specify caching policy and resource lifespan, including temporal or contextual validity when relevant.

Bad:

```jsonc
{
  // Price has no validity window or scope.
  "offer_id": "offer:8d9a0c70",
  "price": "19.99",
  "currency_code": "USD"
}
```

Better:

```jsonc
{
  "offer_id": "offer:8d9a0c70",
  "price": "19.99",
  "currency_code": "USD",
  // Client knows when and where the offer is valid.
  "valid_until": "2026-05-01T12:00:00Z",
  "valid_within": {
    "city_id": "city:nyc"
  }
}
```

- Use globally unique external identifiers; do not expose increasing numeric IDs as public identifiers.

Bad:

```jsonc
{
  // Sequential IDs leak business volume and collide across systems.
  "id": 12451
}
```

Better:

```jsonc
{
  // Namespaced globally unique ID is safe to merge and expose.
  "id": "order:8d9a0c70-63f0-46a8-9f2b-6ccf6e9f2ef7"
}
```

- Reserve future restriction paths in the contract, such as rate limits, MFA, captchas, and abuse-prevention errors.

Bad:

```yaml
responses:
  "201":
    # No reserved path for throttling or verification.
    description: Order created
```

Better:

```yaml
responses:
  "201":
    description: Order created
  "429":
    # Clients can prepare for rate limiting before it is enabled.
    description: Too many requests
  "403":
    # Contract leaves room for captcha, MFA, or account checks.
    description: Additional verification required
```

## Security

- Do not invent security protocols; use established standards and current best practices.

- Use TLS 1.2 or newer, preferably TLS 1.3. Never allow downgrading the security level.

- Help consumers avoid security mistakes: sanitize dangerous content where possible, prefer typed input over raw executable strings, and make dangerous bypasses explicit.

Imagine you provide an endpoint for customers to run queries over their data.

Bad:

```jsonc
{
  // Accepting raw executable text invites injection bugs.
  "query": "INSERT INTO customers (name) VALUES ('Robert'); DROP TABLE customers;--')"
}
```

Better:

```jsonc
{
  // Template and values can be escaped by proven tooling.
  "statement": "INSERT INTO customers (name) VALUES (?)",
  "values": ["Robert'); DROP TABLE customers;--"]
}
```

If unsafe bypass is required:

```http
# Dangerous behavior must be explicit at the call site.
X-Dangerously-Allow-Raw-Value: true
```

- Do not provide bulk access to sensitive data unless protected by strict limits, rate controls, and appropriate authentication.

Bad:

```http
# Bulk sensitive export maximizes breach impact.
GET /v1/users/export-all
```

Better:

```http
# Export is bounded, auditable, and task-based.
POST /v1/users/export-tasks
{
  "fields": ["id", "email"],
  "limit": 1000,
  "reason": "compliance_export"
}
```

- Separate API families that require different security controls.

- Accept language parameters even before localization is implemented.

Bad:

```http
# No way for clients to request language-specific content.
GET /v1/offers
```

Better:

```http
# Header can be honored later without changing the API.
GET /v1/offers
Accept-Language: en-US
```

- Treat language, jurisdiction, residence, and current location as distinct inputs when formatting or legal behavior depends on them.

Bad:

```jsonc
{
  // Locale alone cannot determine legal rules, units, or currency.
  "locale": "en-US"
}
```

Better:

```jsonc
{
  // Separate inputs let the API handle formatting and legal behavior:
  // language for text, location for units, calendars, holidays, and law.
  "language": "en",
  "user_location": "US"
}
```
