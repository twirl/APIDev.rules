## When to Use (REST) HTTP APIs

- Unless specified otherwise, treat a "REST" or "RESTful" API as a JSON-over-HTTP client-server API that uses HTTP protocol semantics and complies with the HTTP specification.
- Prefer (REST) HTTP APIs when broad platform support, human-readable traffic, proxy/gateway compatibility, standard tooling, and easy debugging matter more than maximum wire efficiency.

## Design Process

- Start from the happy path: draw every HTTP call needed for a normal user or client workflow.
- Interpret each call as an operation applied to a resource, then define the URL and allowed methods for that resource.
- Enumerate errors for each operation and define how the client can restore application state after receiving each error.
- Decide which behavior belongs to HTTP-level metadata: authentication headers, content negotiation, caching, retries, concurrency checks, pagination, rate limits, and error classification.
- Do not use non-trivial HTTP functionality such as range requests, content negotiation, `Vary` headers, or non-standard/custom HTTP methods unless specifically asked. By default, stick to the well-known subset of the specification.
- Reject signatures that are technically "REST-like" but make the client code awkward, ambiguous, or hard to recover after errors.

## HTTP Semantics

- Treat the URL as the address of the resource the operation is applied to. Avoid typical mistakes and remember:
  - Sending `PUT` to a URL means `GET` on that URL, if implemented, must return the representation that was put.
  - Deleting a resource identified by a URL means that resource is no longer available afterwards.
  - `404` on `POST /resource` (as well as `PUT`, `PATCH`, etc.) means the target resource itself does not exist, not whatever the request body encodes.
- Treat `GET` URLs as cache keys. If two `GET` requests can return different resources, they must differ by URL or by an explicitly documented `Vary` header.
- Do not put modifying operations behind `GET`; crawlers, preview generators, caches, and retrying clients may call `GET` without user intent.
- Do not put non-idempotent operations behind `PUT` or `DELETE`.
- Do not rely on request bodies for `GET`, `HEAD`, or `DELETE`; there is no clear semantic meaning for such bodies, and many tools and intermediaries will ignore, drop, or mishandle them.
- Do not return a body with `HEAD` or `204 No Content`.
- Use `POST` for operation-specific processing, server-generated creation, complex searches with request bodies, and actions whose side effects are not naturally idempotent.
- Remember that `POST` is not synonymous with "create". It means "process this representation according to the target resource's semantics."
- Treat `PATCH` as potentially non-idempotent and order-dependent unless the patch format makes idempotency explicit.

## URL Design

- Use path components for strict hierarchy and resource ownership:

```http
GET /v1/partners/{partner_id}/machines/{machine_id}
```

- Use query parameters for non-strict relations, filters, cursors, and operation parameters:

```http
GET /v1/orders?user_id={user_id}&cursor={cursor}
```

- Prefer a new root resource when a hierarchy is uncertain or may become many-to-many later.

```http
GET /v1/orders?user_id={user_id}
```

is usually more resilient than:

```http
GET /v1/users/{user_id}/orders
```

when orders may later be shared, delegated, or owned by organizations.

- Use dedicated operation resources for cross-domain operations instead of forcing an artificial hierarchy.

Avoid forcing one entity to look subordinate to the other when the operation actually depends on both:

```http
POST /v1/machines/{machine_id}/recipes/{recipe_id}/prepare
```

Prefer a dedicated operation resource with explicit parameters. This is more concise, more resilient to change, and easier to discover:

```http
POST /v1/prepare
Content-Type: application/json

{
  "machine_id": "machine:123",
  "recipe_id": "recipe:lungo"
}
```

- Keep URLs concise and readable. Do not contort names only to satisfy a folk rule such as "URLs must contain nouns only" unless explicitly asked otherwise.
- Put the major API version in the path unless the project has an explicit versioning convention.

```http
GET /v1/orders/123
```

- Define a trailing-slash policy and enforce it consistently with redirects or clear errors.
- Choose casing per request component and document transformations:
  - domains, paths, and headers commonly use `kebab-case`;
  - query parameters commonly use `snake_case`, though `camelCase` is acceptable;
  - JSON bodies should use the project's established JSON casing consistently, with `camelCase` or `snake_case` as the default.
- Avoid moving parameters between URL path, query, headers, and body without reconsidering casing, escaping, cache behavior, log readability, and proxy/gateway rules.
- Do not put values that require escaping, contain arbitrary user text, or may include `/`, `?`, `#`, or non-alphanumeric symbols into path components. Put them in query parameters or the body.
- Do not invent a private syntax for arrays or nested objects in query parameters. Use a body-capable method for complex structures, or as a last resort pass a clearly documented encoded JSON value, possibly Base64url-encoded.

## Stateless and Layered Design

- Make every request contain the data needed to process it at the correct abstraction level. Prefer well-defined request parameters with integrity checks over deducing operation parameters implicitly. Instead of:

```
GET /my/orders
Authorization: Bearer <token>
```

with the user ID being deduced from the token, do:

```
GET /v1/orders?user_id=<user_id>
Authorization: Bearer <token>
```

Here, the token is only needed to verify that the caller has access to that user's orders.

- Keep authentication, identification, and authorization conceptually separate:
  - authenticate who is calling;
  - identify which resource the operation targets;
  - authorize whether the caller may act on that resource.
- Design service-to-service APIs so intermediate proxies or gateways can be added or removed without changing downstream interfaces. Encode all required parameters in the operation itself, so proxying, possibly with path modification, is enough to change the service mesh.

## Caching and Concurrency

- Always provide explicit cache directives for `GET` responses. Do not let clients or intermediaries invent cache behavior.

```http
HTTP/1.1 200 OK
Cache-Control: no-store
Content-Type: application/json
```

- Be careful with cacheable error statuses, especially `404`, `405`, `410`, and `414`. If stale absence is harmful, make the caching policy explicit.
- Use `ETag` or `Last-Modified` and conditional requests when clients or gateways can reuse resource snapshots.

```http
GET /v1/orders?user_id={user_id} HTTP/1.1
If-None-Match: "orders-rev-42"
```

```http
HTTP/1.1 304 Not Modified
ETag: "orders-rev-42"
```

or (less reliable):

```http
GET /v1/orders?user_id={user_id} HTTP/1.1
If-Modified-Since: <HTTP Date>
```

```http
HTTP/1.1 304 Not Modified
Last-Modified: <HTTP Date>
```

- Use explicit revisions as query/body parameters, or an `If-Match` check, for operations that depend on a previously observed state.

```http
POST /v1/orders?user_id={user_id} HTTP/1.1
If-Match: "orders-rev-42"
Content-Type: application/json

{ "recipe": "lungo" }
```

## Creation, Updates, and Lifecycle

- Make creation idempotent either through an idempotency token, ETag/revision check, or a draft-commit flow.
- Prefer a draft-commit flow for complex creation, collaborative editing, payment-like operations, or any operation where retrying the final step must be safe.

```http
POST /v1/order-drafts
Content-Type: application/json

{ "recipe": "lungo" }
```

```http
HTTP/1.1 201 Created
Location: /v1/order-drafts/{draft_id}
ETag: "draft-rev-1"
```

```http
PUT /v1/order-drafts/{draft_id}/commit
If-Match: "draft-rev-1"
Content-Type: application/json

{ "status": "confirmed" }
```

- Use `PUT /resource/{id}` creation only when client-generated identifiers are acceptable and collision handling is well-defined.
- For long or filtered lists, expose an enumerator resource with pagination.

```http
GET /v1/orders?user_id={user_id}&cursor={cursor}
```

- For complex searches, prefer `POST` with a request body over an unreadable query string.

```http
POST /v1/orders/search
Content-Type: application/json

{
  "user_id": "user:123",
  "recipes": ["latte", "lungo"],
  "created_after": "2026-01-01T00:00:00Z"
}
```

- For complex updates, prefer small atomic sub-resources or a draft-commit update flow over broad ambiguous `PATCH` documents.

```http
PUT /v1/orders/{order_id}/delivery-address
Content-Type: application/json

{ "line1": "Example street 1" }
```

- Treat physical deletion as rare. In most product APIs, expose archive, cancel, deactivate, or close operations instead of `DELETE`.

```http
PUT /v1/orders/{order_id}/archive
Content-Type: application/json

{ "reason": "user_requested" }
```

## Responses

- Return a JSON object as the response root when the response has a body. Objects are extensible; arrays and primitives are not.

Bad:

```json
[
  { "id": "order:1" }
]
```

Better:

```json
{
  "orders": [
    { "id": "order:1" }
  ],
  "next_cursor": null
}
```

- For successful responses with no meaningful body, use either `{}` with `200 OK` if future extension is likely, or `204 No Content` if an empty body is part of the contract.
- Include common headers explicitly: `Date`, `Content-Type`, `Content-Length`, `Content-Encoding`, `Cache-Control`, `ETag`, `Retry-After`, and `Location` when applicable.
- Use `Location` for newly created resources.

```http
HTTP/1.1 201 Created
Location: /v1/orders/123
Content-Type: application/json

{ "id": "order:123" }
```

## Errors

- Use HTTP status codes to describe the error family, not every business error subtype.
- Use a structured error body and, when useful for logs and gateways, a namespaced error-kind header.

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
X-MyCompanyAPI-Error-Kind: wrong_parameter_value
```

```json
{
  "reason": "wrong_parameter_value",
  "localized_message": "Something is wrong. Contact the developer of the app.",
  "details": {
    "checks_failed": [
      {
        "field": "position.latitude",
        "error_type": "constraint_violation",
        "constraints": { "min": -90, "max": 90 },
        "message": "position.latitude must be between -90 and 90"
      }
    ]
  }
}
```

- Keep the `400` error format general enough to represent unknown `4xx` codes, because clients must treat unknown `4xx` statuses like `400`.
- Use the common status families consistently:
  - `400` or `422` for validation and request-shape errors;
  - `401` for missing or invalid authentication when that is the project's documented convention; note that this is a non-normative but highly popular practice;
  - `403` for authorization failures;
  - `404` for absent resources or when the real cause must not be exposed;
  - `409` for state conflicts and integrity violations;
  - `410` for known permanent removal;
  - `429` for rate limits and quotas;
  - `500` for server failures;
  - `503` or `Retry-After` for temporary unavailability.
- Use `Retry-After` when retrying is expected after a known delay.

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json
```

- For internal APIs, include machine-readable server error subtypes so monitoring can distinguish database timeouts, dependency failures, saturation, and code defects, typically as additional headers.
- Document retry behavior explicitly. Do not assume clients will infer retry safety from status codes or method idempotency.
- Include enough error metadata for the client to decide whether to retry, reformulate the request, ask the user for action, or stop.

## Browser and Gateway Compatibility

- Support `OPTIONS` and CORS if browser access is possible now or later.
- Namespace custom headers with the API or company name; avoid generic names that may collide with standard or intermediary headers.

```http
X-MyCompanyAPI-Error-Kind: wrong_parameter_value
X-MyCompanyAPI-Request-Id: req_123
```

- Protect HTTP APIs against common protocol-level attack classes such as CSRF, SSRF, response splitting, unvalidated redirects, request smuggling, and overly permissive CORS.

## Validation Checklist

- Can every operation be explained as a method applied to a resource?
- Are unsafe operations kept out of `GET`?
- Are `PUT` and `DELETE` truly idempotent?
- Does every non-idempotent or complex operation have an idempotency token, revision check, or draft-commit flow?
- Is every `GET` response explicitly cacheable or non-cacheable?
- Are `Last-Modified` / `If-Modified-Since` or `ETag` / `If-Match` / `If-None-Match` used where stale writes or stale reads matter?
- Can the client recover application state after each documented error?
- Are business error subtypes machine-readable outside the status code?
- Are response roots extensible JSON objects?
- Is the URL nomenclature readable enough for external developers and stable enough for future product changes?
- Can a gateway, proxy, generated SDK, or monitoring tool understand the important metadata without parsing the whole body?
