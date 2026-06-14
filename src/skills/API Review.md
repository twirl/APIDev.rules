---
name: api-review
description: API review guidance. Use when reviewing an API proposal, specification, endpoint change, SDK interface, generated client surface, event contract, documentation, or compatibility-impacting API modification; use to find design defects, compatibility risks, unclear contracts, recovery gaps, REST/HTTP mistakes, SDK ergonomics issues, or unsafe API behavior.
---

# API Review

Use this skill to review API designs and changes. Do not redesign from scratch unless the requested review scope requires it. Focus on concrete defects, compatibility risks, unclear contracts, and practical fixes.

## Reference Files

Load only the references needed for the review:

- For every non-trivial API review, read `references/api-review-framework.md`.
- For HTTP, REST, JSON-over-HTTP, URL, status code, header, caching, CORS, or error-format reviews, read `references/rest-api.md`.
- For SDKs, generated clients, UI libraries, callbacks, events, subscriptions, or client-side recovery behavior, read `references/sdk.md`.
- For UI component API reviews, read `references/ui-components.md`.
- Before finalizing findings, read `references/dos-and-donts.md` for naming, signatures, type/value clarity, limits, traffic, security, and edge-case checks.

## Review Process

1. Establish the review baseline.
   Identify the reviewed surface, intended users, integration scenarios, A&A model, transport style, local conventions, versioning policy, compatibility promise, and known consumer usage.

2. Check problem fit.
   Verify that the API solves the user or developer problem it claims to solve. Flag designs driven by internal entities, database tables, subsystem boundaries, or implementation convenience instead of consumer workflows.

3. Check contract shape.
   Review abstraction levels, responsibility boundaries, public entities, fields, methods, events, statuses, examples, and documented behavior. Treat exposed behavior as a product commitment.

4. Check compatibility.
   Identify observable behavior from docs, specs, examples, generated clients, SDK behavior, errors, timing, consistency, event order, and real usage. Classify changes by consumer impact, not implementation size.

5. Check distributed behavior.
   Review idempotency, retries, draft-commit or operation-resource needs, consistency, pagination, async handling, duplex callbacks, bulk operations, partial success, and recovery after failures.

6. Check errors and recovery.
   Verify that errors tell clients whether to retry, wait, refresh state, fix input, reauthorize, ask the user, or fail permanently.

7. Apply transport-specific checks.
   Use the HTTP/REST, SDK, or UI component references only when relevant.

8. Produce findings.
   Lead with findings ordered by severity and consumer impact. For each finding, state the problem, why it matters, the affected contract surface, and the smallest practical fix.

## Output Expectations

- Separate confirmed defects from open questions and assumptions.
- Call out compatibility breaks explicitly.
- Prefer concrete alternatives over abstract objections.
- Show corrected operations, schemas, events, or SDK signatures when useful.
- If no material issues are found, say so and note remaining test, generator, compatibility, or operational risks.
