---
name: api-development
description: API design and implementation guidance. Use when designing a new API, modifying an existing API, writing API contracts or specifications, or asking an agent to implement API endpoints, clients, or SDKs.
---

# API Development

Use this skill to design, modify, or implement APIs with a contract-first, compatibility-aware process.

## Reference Files

Load only the references needed for the task:

- For any non-trivial API design or implementation task, read `references/api-development-framework.md`.
- When modifying an existing API, adding fields, changing behavior, versioning, or evaluating compatibility risk, read `references/backward-compatibility.md`.
- For HTTP, REST, JSON-over-HTTP, URL, status code, header, caching, CORS, or error-format work, read `references/rest-api.md`.
- For SDKs, generated clients, UI libraries, callbacks, events, subscriptions, or client-side recovery behavior, read `references/sdk.md`.
- Before finalizing a public API shape, read `references/dos-and-donts.md` for naming, signatures, and edge-case checks.

## Development Process

1. Clarify the API job before designing.
   Identify the intended users, supported platforms and runtimes, intended frameworks and protocols, authentication and authorization model, compatibility and versioning promise, SDK scope, and naming conventions. For distributed software, clarify whether interaction is request/response, polling, webhook-based, message-based, callback-based, or tied to a specific technology. For UI libraries, clarify the UI stack, framework, and guidelines to follow.

2. Define the user or developer problems the API must solve.
   Do not start from entities or endpoints. State the concrete workflows, consumers, constraints, and success criteria first.

3. Design broad-to-concrete.
   Define the application field, split abstraction levels, isolate responsibility areas, then design final interfaces. Each public entity, operation, event, status, and field must have a clear purpose.

4. Keep abstraction levels adjacent.
   Consumers should work with concepts relevant to their task. Do not expose internal subsystem boundaries, vendor implementation details, or low-level mechanics unless they are part of the product contract.

5. Make operations recoverable.
   Every state-changing operation must be idempotent natively or through an idempotency token, revision, ETag, draft-commit flow, or operation resource. For complex workflows, prefer creating a draft or operation first and committing it through a naturally idempotent step.

6. Design for distributed failure.
   Account for retries, timeouts, network loss, duplicate requests, client crashes, server crashes, partial success, concurrent requests, stale reads, missed callbacks, and partner implementation mistakes.

7. Define errors as recovery instructions.
   For every error path, specify who can act, whether retrying is safe, whether request reformulation can fix the problem, what the user should see, and what the developer should log or handle.

8. Validate from consumer code.
   Write realistic consumer-side pseudocode for the main workflows. Redesign when common tasks require excessive plumbing, hidden state, fragile call order, unclear recovery branches, or knowledge of internals.

9. Run the compatibility and polish pass.
   Check whether the design solves the problems stated earlier, preserves existing observable behavior, leaves room for extension, avoids undocumented public commitments, and follows the applicable dos and don'ts.

## Output Expectations

When producing an API proposal or implementation plan, be concrete:

- State assumptions and unresolved questions.
- Show resources, operations, methods, schemas, events, statuses, errors, and lifecycle rules.
- Describe idempotency, consistency, pagination, async handling, retries, and compatibility implications.
- Explain how clients recover from expected failures.
- Call out breaking changes and safer alternatives.

When implementation is finished, provide a clear machine-readable outcome in the form of a specification.
