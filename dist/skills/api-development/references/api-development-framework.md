## Questions to Clarify Before Designing the API

- Audience and authorization: who will use the API, on whose behalf it acts, and what authentication and authorization model is required.
- Compatibility and lifecycle: what versioning scheme, backward compatibility promise, deprecation process, migration path, and sunset policy apply.
- Transport and interface style: which protocol or paradigm to use, and which existing style guides, naming rules, error formats, pagination rules, and code conventions must be followed.
- Bidirectional data flow: whether consumers only call the API or must also receive state changes. For server-to-server integrations, clarify whether to use polling, webhooks, or message queues. For client SDKs and user-facing clients, clarify whether to expose events, messages, callbacks, push notifications, duplex connections, or other client-side techniques.
- Contract and documentation: what documentation to generate, in which format, and which clients will use it directly or through code generation.

## Before You Design

- Optimize for developer efficiency. The path from task to correct working code should be short for both happy paths and error paths.
- Prefer established domain conventions and standards. Invent a custom paradigm only when its advantages justify the learning cost.
- Unless explicitly stated otherwise, assume the API will evolve. Leave room for adding functionality and exposing deeper abstraction levels.
- Set data-size restrictions, ideally for every field, unless instructed otherwise. If source code or a database model is available, extract restrictions from it; otherwise, design and document realistic constraints in the API itself.
- When the authorization model is not specified, choose it intentionally: user-like robot accounts for granular access, API-key or certificate-like system authorization for endpoint-level access.
    - Account for robot-account differences: token lifecycle, request volume, parallelism, lack of cookies, inability to solve captchas, and long-running business processes.
    - If the API is for human users, especially with free tiers, leave room for additional checks such as captchas or account verification. Do not enable them unless instructed; only preserve the option in the design, for example with async commit steps instead of synchronous finalization.
    - Avoid mixing user authorization and system authorization without a clear model for scope, delegation, audit, and abuse prevention.

## Design the Contract

- Understand which user or developer problems the API is intended to solve before designing entities or operations.
- Design from broad context to concrete interface: define the application field, separate abstraction levels, isolate responsibility areas, then describe final interfaces.
- Require every API entity to have a brief, clear answer to "what is this needed for?"
- Separate abstraction levels so consumers work only with concepts relevant to their current task.
- Let only adjacent abstraction levels interact; if an API needs to jump across levels, redesign the missing intermediate abstraction.
- Do not expose internal subsystem structure unless it is part of the consumer-facing model.
- Check the design with a data-flow pass: identify what data enters each level, what context that level adds, and what higher-level concept it emits.
- Design every operation to be idempotent, either natively or through an artificial idempotency token.
    - For complex state-changing workflows, prefer a draft-commit scheme: create a draft or operation resource first, then commit it through a naturally idempotent confirmation step.

- Design APIs so clients can recover state and continue after client crashes, server errors, timeouts, network loss, and intermediary failures.
- Expect partners to implement workflows incorrectly; add safeguards so one consumer's mistakes cannot damage other consumers.
- Do not rely on critical operations completing quickly. Long and unpredictable latency is normal in distributed systems.
- If a workflow spans multiple calls requiring significant time or computational effort to complete, provide a way to resume from the current step or safely revert partially staged changes instead of restarting from the beginning.

## Distributed Systems Defaults

### Consistency and Synchronization

- Prefer strongly consistent public interfaces when the system can provide them at acceptable cost. Clarify the conditions if unclear.
- Expect concurrent requests even when the design discourages them, because retries and multi-device usage still happen.
- Unless explicitly stated otherwise, prefer optimistic concurrency control when clients edit shared state: expose resource versions, ETags, precise modification timestamps, or equivalent tokens. Treat version conflicts as normal API behavior and provide clear recovery paths.
- Use explicit API locks only when the consumer can manage lock lifecycle safely and lock granularity prevents cross-consumer harm.
- If strong consistency is not an option, use eventual consistency and mitigate its consequences unless instructed otherwise. Prefer read-your-writes behavior or revision-based consistency checks.
- Do not lower the consistency guarantees of an existing endpoint; that is a compatibility break even if the guarantee was undocumented.

### Asynchronous Operations

- Use asynchronous tasks for operations that take longer than typical request timeouts, have unpredictable duration, need queueing, or reduce collision windows. Infer this from existing implementations when possible; otherwise make a reasonable judgment unless instructed otherwise.
- When asynchronous tasks are implemented, return a stable operation, task, or future resource identifier quickly; let clients retrieve status and result later.
- Avoid endpoints that sometimes return the final result and sometimes return a task link; they force consumers to maintain two branches.
- Provide progress information when it is meaningful and reliable.

### Lists and Pagination

- Never expose responses that can return unbounded arrays, sets, or maps.
- Do not rely on offset pagination for mutable lists when clients need complete and consistent traversal. Do not overcomplicate typical cases where duplicated or missed items are tolerable.
- For immutable lists, offset pagination is acceptable.
- For append-only lists, use stable boundaries such as monotonically ordered identifiers or opaque cursors.
- Keep cursors opaque so the server can change storage and ordering internals without breaking clients.
- Always return enough metadata for convenient traversal, such as cursor, limit, item count, or whether more data may exist.
- For mutable datasets, prefer snapshots or derived immutable event streams over unstable pagination unless instructed otherwise.

### Duplex Interactions

- For public APIs, use polling as the baseline for change discovery because it is simple, spec-friendly, and broadly implementable. For internal APIs, choose a communication framework based on requirements and subject area; treat polling as the simplest, but not the most performant, baseline.
- Add push channels as an optimization or supplement, not as the only way to observe changes, unless explicitly instructed to use them in the first place.
- Use low-frequency polling as a recovery path even when push notifications exist.
- If webhooks or push messages are exposed, define their request and response formats, authentication, retry policy, idempotency, ordering, parallelism, size limits, and delivery guarantees in a formal contract.
- Provide event replay, state retrieval, or reconciliation APIs so partners can recover from missed or incorrectly processed callbacks.
- Use reference-only or batch notifications when payloads are large, frequent, or sequential processing is required.
- Distinguish "message received" from "business event processed" when partners must perform follow-up work.

### Bulk and Partial Changes

- Avoid bulk modifying endpoints when separate requests are practical.
- Prefer decomposed, idempotent, full-replacement sub-endpoints for independently editable parts of a composite resource when traffic and collaboration requirements allow it.
- If a bulk modifying endpoint is necessary, prefer atomic behavior wherever possible.
- If atomicity is impossible, design the partial-success semantics deliberately and document retry behavior.
    - Always return a per-subrequest result or error breakdown for non-atomic bulk operations.
    - Group dependent sub-operations so each group is atomic even if independent groups are processed separately.
    - Ensure nested operations are idempotent, using deterministic internal idempotency tokens when needed.
    - Avoid partial-update formats that rely on magic nulls, empty objects, booleans, array positions, or omitted fields with overloaded meanings. For non-trivial operations, use clear formats with explicit operation types.

- Return the updated representation or enough state for clients to know what changed.
- Do not overcomplicate collaborative editing. Propose full-scale co-editing support only when instructed or when the subject area clearly requires it. For true collaborative editing, model user actions as explicit change operations with known revisions and conflict-resolution rules. Consider CRDTs only when their tradeoffs fit the domain.

## Validation Checklist

After the design is finished, run sanity checks described below. Make changes and repeat if needed.

- Check that the proposed API actually resolves the user or developer problems defined at the start.
- Validate the entity model by writing realistic consumer-side usage scenarios.
- Redesign when common tasks require excessive client-side plumbing.
- Add helper interfaces for known workflows when they reduce boilerplate, prevent common mistakes, or encode domain rules consumers should not reimplement.
- Decompose overloaded interfaces into meaningful groups so consumers can understand and ignore whole parts without scanning long flat field lists. Follow the 5+/-2 rule, keep method nomenclature compact, and use nested namespaces when they prevent bloat.
- Check that all interfaces are idempotent, either natively or through artificial idempotency tokens.
- Check that all error paths are covered and that the error taxonomy clearly tells clients what to do.
