Use this fragment when the task is to review an API proposal, specification, implementation plan, endpoint change, SDK interface, or compatibility-impacting modification. It replaces the general development and backward-compatibility framework for review tasks.

## Review Setup

- Identify what is being reviewed: a new API, a change to an existing API, an SDK, generated client surface, HTTP endpoint, event contract, documentation, or implementation.
- Establish the review baseline before judging the design:
    - intended users and integration scenarios;
    - authentication and authorization model;
    - transport, interface style, and local conventions;
    - versioning, compatibility, deprecation, migration, and sunset policy;
    - existing documentation, examples, generated clients, SDK behavior, and known consumer usage;
    - whether consumers only call the API or must also receive state changes through polling, webhooks, messages, callbacks, subscriptions, or duplex channels.
- If the API is existing or the change may affect existing consumers, treat compatibility risk as part of the review even when the user did not explicitly ask for it.
- Do not redesign the whole API unless the requested review scope requires it. Focus on concrete defects, risks, unclear contracts, and safer alternatives.

## Problem Fit

- Check whether the API solves the user or developer problems it claims to solve.
- Flag designs that start from internal entities, database tables, subsystem boundaries, or implementation convenience instead of consumer workflows.
- Check that each public entity, field, method, event, status, and error has a clear purpose.
- Validate the design by writing or mentally executing realistic consumer-side usage scenarios. Common workflows should not require excessive client-side plumbing, fragile call order, hidden state, or knowledge of internals.
- Check that helper interfaces encode real common workflows, reduce mistakes, or hide domain rules consumers should not reimplement.

## Contract Shape

- Check that abstraction levels are separated and adjacent. Consumers should work with concepts relevant to their task, not internal subsystem structure.
- Flag interfaces that jump across abstraction levels without an intermediate concept.
- Check data flow through the contract: what data enters each level, what context the level adds, and what higher-level concept it emits.
- Flag overloaded interfaces with long flat field lists, unrelated method groups, or unclear namespaces.
- Flag undocumented returned fields, private behavior shown in samples, or hints at unsupported capabilities.

## Compatibility Review

- Define backward compatibility as preserving the functional correctness of existing consumer code, not preserving every invisible implementation detail.
- Identify the observable contract: documentation, specification, examples, generated clients, SDK behavior, error behavior, timing, consistency, event order, status causes, allowed workflows, and known consumer usage.
- Treat undocumented but observable behavior as risky to change when consumers may rely on it.
- Classify the change by consumer impact, not implementation size:
    - patch for fixes that preserve behavior;
    - minor for compatible additions;
    - major for incompatible behavior, schema, workflow, or guarantee changes.
- Flag backward-incompatible changes that could be implemented without breaking the contract.
- Flag technically compatible changes that still alter product behavior, state transitions, event order, timing assumptions, or business workflows, including bug fixes that might break existing customers.
- Check generated-code compatibility when the contract is consumed through OpenAPI, protobuf, TypeScript types, or another generator. Avoid controversial specification constructs unless the relevant generators are tested.
- Check all fields have limits (such as size of arrays, length of strings, etc.) explicitly stated.

## Extension and Coupling

- Check whether the design leaves room for likely future functionality without exposing "just in case" surface area.
- Check whether extensions follow generalization logic: old helpers should become reduced cases of more general interfaces with explicit defaults, not isolated legacy artifacts.
- Check that third-party, partner, hardware, or platform APIs are isolated behind the vendor's own abstraction instead of being proxied directly as the public contract.

## Distributed Systems Review

- Check that every state-changing operation is idempotent natively or through an idempotency token, revision, ETag, draft-commit flow, operation resource, or equivalent safeguard.
- Check recovery after client crashes, server errors, timeouts, network loss, intermediary failures, missed callbacks, duplicate requests, and partial success.
- Check that long or unpredictable operations are asynchronous and return a stable task, operation, or future resource.
- Check consistency guarantees: strong consistency when practical, optimistic concurrency for shared editable state, and explicit mitigation for eventual consistency.
- Flag lowered consistency guarantees as compatibility breaks, even if the previous consistency level was undocumented.
- Check list responses for bounds, pagination, cursor opacity, mutable-list behavior, and enough traversal metadata.
- Check duplex or callback-style integrations for authentication, retry policy, idempotency, ordering, parallelism, size limits, delivery guarantees, replay, reconciliation, and state retrieval.
- Check bulk and partial-change endpoints for atomicity, partial-success semantics, per-item errors, retry behavior, and overloaded null/empty/omitted-field meanings.

## Error and Recovery Review

- Check that errors tell clients what to do next: retry, wait, refresh state, fix input, reauthorize, ask the user, or fail permanently.
- Flag generic errors that hide recoverability, user action, or developer diagnostics.
- If errors are intended to be visible to end users, check that they have meaningful messages that help users recover.
- Check that validation errors are machine-readable and identify violated fields, constraints, and allowed values.
- Check that clients can recover application state after each documented error.

## Transport-Specific Checks

- For HTTP or REST-like APIs, apply `rest-api.md` for URL design, method semantics, status codes, headers, caching, CORS, and structured errors.
- For SDKs or generated clients, apply `sdk.md` for native platform conventions, generated/handwritten layer separation, client-side state, subscriptions, retries, and recovery behavior.
- For UI component APIs, apply `ui-components.md` if the reviewed surface is a user-interface library.
- Before finalizing findings, apply `dos-and-donts.md` for naming, signatures, type/value clarity, limits, traffic, security, and edge-case checks.

## Review Output

- Lead with findings ordered by severity and consumer impact.
- For each finding, state the problem, why it matters, the affected contract surface, and the smallest practical fix.
- Separate confirmed defects from open questions and assumptions.
- Call out compatibility breaks explicitly.
- Prefer concrete alternatives over abstract objections. Show corrected operations, schemas, events, or SDK signatures when useful.
- If no material issues are found, say so and note any remaining test, generator, compatibility, or operational risks.
