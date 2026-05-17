## When to Build SDKs

- Treat an SDK as a native client library that gives developers a high-level interface to an underlying API.
- Build an SDK when client developers would otherwise repeat non-trivial protocol, state, retry, callback, or recovery logic in every integration.
- Do not treat an auto-generated client as a complete SDK for a complex API. Generated clients are useful for type mapping, serialization, naming conventions, and request wrappers; high-level SDKs must also encode product workflows and recovery rules.
- Prefer an SDK when the API requires client-side storage of authorization tokens, idempotency keys, draft identifiers, cursors, consistency tokens, subscriptions, or other cross-request state.

## SDK Responsibilities

- Follow the target platform's naming, error handling, packaging, async, cancellation, logging, and lifecycle conventions.
- Convert wire-level formats into idiomatic platform objects and types. Do not expose JSON quirks, raw identifiers, or transport naming when native concepts are clearer.

For example, expose a timestamp as `Date`, `Instant`, or the platform's equivalent, not as an unparsed JSON string, unless preserving the raw value is required.

- Represent relationships as references or lazy objects where that reduces repeated lookup code.

For example, let an `Offer` expose list of related `Product` object instead of forcing every app to map `offer.product_ids` to a separately fetched product list.

- Initialize related entities when that is part of the developer's task, but make network, cache, and latency behavior explicit enough to reason about.
- Implement documented retry policy for safe requests. Respect server retry hints such as `Retry-After`, use backoff, and never retry unsafe operations unless idempotency is guaranteed.
- Manage client-side state that is easy to misuse: tokens, draft operation IDs, idempotency keys, last-seen revisions, subscription cursors, cache entries, and local locks.
- Turn low-level API errors into SDK-level recovery behavior when the recovery is part of the normal workflow. For example, renew an expired offer or refresh a stale consistency token instead of forcing every app to repeat the same branch. Expose business errors only when the application developer must make a product decision.
- Provide raw access to underlying APIs only when necessary or explicitly instructed.

## Generated Clients

- If code generation is available, use it for mechanical translation: request methods, response models, enum/type definitions, serialization, deserialization, and platform naming.
- Keep generated and handwritten layers separated so regeneration does not overwrite product-specific logic.

## Workflow Design

- Design SDK methods around developer tasks, not endpoint inventory.
- Keep the happy path short, but also make error and recovery paths explicit.
- Hide transport-level callback mechanics behind object-level events, observers, streams, or platform-native subscription mechanisms.

For example, prefer `order.on("stateChange", handler)` to requiring each app to subscribe to a global event stream and filter by `order_id`.

- Prevent missed updates around "list then subscribe" workflows. The SDK must reconcile state changes that happen between initial retrieval and subscription activation.

For example, if the app calls `getOngoingOrders()` and then subscribes to order changes, the SDK must not lose an order update that arrives between those two operations.

- Provide replay, reconciliation, or state refresh helpers for missed, duplicated, reordered, or delayed events. Prefer resumable workflows for long-running operations: expose operation objects, status retrieval, continuation, cancellation, and cleanup methods.
- If polling is required, encapsulate schedule, backoff, cancellation, and server-load safeguards in the SDK.
- Make asynchronous operations cancellable when the platform supports it.

## Versioning and Compatibility

- Keep SDK and server API versioning aligned, but do not expose server version complexity unless consumers need it.
- Use the SDK to isolate consumers from compatible server changes and, when feasible, from server major-version migrations.
- Do not change undocumented observable SDK behavior casually. Existing apps may rely on it even if the documentation did not promise it.
- Document consistency, ordering, retry, cache, callback, and threading guarantees at the SDK level.

## Validation Checklist

- Can the developer complete the main workflow without knowing low-level protocol details?
- Are retries, idempotency, token storage, consistency tokens, and recovery behavior handled by the SDK where appropriate?
- Are subscriptions safe against missed, duplicated, and reordered events?
- Are generated and handwritten layers clearly separated?
- Is SDK-specific behavior well documented, and is its backward compatibility policy explicit?
- Can consumers debug and reconcile SDK behavior without bypassing the SDK entirely?
