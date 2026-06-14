## UI Libraries

- Treat UI libraries as SDKs with a larger responsibility area: both application developers and end users interact with them.
- Do not design visual components as thin projections of raw API responses. Ergonomic UI usually combines API data, platform interaction patterns, visual state, and component-specific behavior.
- Before exposing customization, decide which dimensions are customizable: data transformation, business actions, visual style, layout, interaction behavior, and lifecycle hooks.
- Avoid adding customization hooks that force developers to change unrelated code, such as modifying a search function only to change a button icon.
- Define priority rules when component properties can come from multiple sources: defaults, theme, component options, semantic data, parent context, user state, or platform settings.
- Provide a way to inspect computed values when properties are resolved through rules, inheritance, percentages, themes, or responsive calculations.
- Emit change events for computed values when consumers are expected to react to them.

## Component Architecture

- Separate semantic model, presentation data, view components, and action handling when the component is complex or customizable.
- Let high-level components own product-level concepts. Let lower-level components own rendering and local interaction details.
- Do not make sibling components call each other directly when either may be replaced. Route coordination through a parent context, composer, controller, or presenter.
- Use events or explicit state changes for weak coupling, but avoid unstructured event chains that can loop or leak low-level concepts upward.

Example: if there is an ongoing search operation and the user types a new query, the input component should emit a "query changed" event for the parent form to catch and propagate. It should not directly control sibling components, such as stopping pins or enabling buttons.

- Introduce an intermediate abstraction when a high-level component cannot coordinate subcomponents without knowing their implementation details.
- Let the intermediate layer prepare data facets, translate options, manage component-local state, and map low-level user actions to high-level operations.
- If asked, or if the subject area calls for it, use MV\*, presenter, or composer-like patterns to make state flow intentional.
- If deep UI state must be restorable, define a stable semantic model and derive visual state from it where possible.

## Shared Resources and Async Locks

Refer to this set of rules when the UI supports collaborative work or is complex enough to involve background updates, long-running operations, or competing actors.

- Identify shared resources in SDKs explicitly: screen regions, selected objects, local caches, subscriptions, pending operations, files, device capabilities, and user attention.
- Do not model shared-resource conflicts as vague flags such as `isLoading` when the real issue is exclusive access to a resource. Name locks after the resource or state being protected, not after the incidental activity currently using it.

Bad: block offer selection while `isLoading` is true.

Good: require callers to acquire `offerFullView` before replacing the visible offer, and release it when the operation finishes or is cancelled.

- Define conflict policy: ignore the later action, cancel the earlier action, queue work, let higher-priority actors seize the lock, or surface a clear error.

## Validation Checklist

- Are UI customization points coherent, limited, and tied to the right abstraction level?
- Are shared resources and asynchronous conflicts handled with explicit policies?
