Now I have everything I need to produce a thorough, structured review. Here it is:

---

# API Review: `JsonTreeEditor`

**Surface reviewed:** TypeScript abstract class + supporting types for a collapsible, in-place-editable JSON tree UI component.
**Intended users:** Application developers embedding the component into a web UI.
**Transport style:** UI component SDK (DOM-based).
**Baseline:** New design, no prior version; reviewed against the ui-components, SDK, api-review-framework, and dos-and-donts references.

---

## Confirmed Defects

### 1 — `LeafNodeRenderer` lifecycle has no way to signal a failed or async commit `[HIGH]`

`commit` accepts a `JsonPrimitive`, which the spec uses both to confirm a new value _and_ to cancel (by passing back the original value). This is a magic-value pattern: cancellation is indistinguishable from submitting an identical value. Custom renderers that want to signal "user pressed Escape" vs "user pressed Enter on the same text" cannot do so.

```ts
// Current — overloaded meaning
commit(node.value); // "cancel" or "typed the same thing"?

// Better — explicit intent
commit({ status: "commit", value: newValue });
commit({ status: "cancel" });
```

Additionally, `commit` is synchronous-only. A color-picker or date-range renderer may need to `await` a sub-panel. The lifecycle has no async path and no error path.

**Fix:** Replace the `commit` callback with a richer type, or split into `commit(value)` / `cancel()` as two separate callbacks passed to `mount`.

---

### 2 — `beginEdit` and `commitEdit`/`cancelEdit` create an undocumented shared edit-mode lock `[HIGH]`

There is no explicit model for "there is one active edit". The API implies it (only one edit can be in progress at a time), but:

- What happens when `beginEdit("a.b")` is called while `"c.d"` is being edited? Silent cancel? Silent commit? Throw?
- What does `commitEdit()` return? Does the caller know the committed value?
- The edit lock is never named or documented as a shared resource.

Per the UI component reference: _"Name locks after the resource or state being protected, not after the incidental activity."_ This shared resource needs an explicit policy.

**Fix:** Document the conflict policy. Consider returning the committed `JsonValue` (or a result enum) from `commitEdit()`. Expose an `isEditing` property or `activeEditPath: string | null` so callers can inspect state.

---

### 3 — `insertNode` key semantics are overloaded and ambiguous for arrays `[HIGH]`

For arrays, `key` is described as _"the numeric insertion index (as a string, e.g. `"2"`)"_, but:

- Omitting `key` appends. Passing `"2"` inserts at index 2. Passing an index past the end — what happens? Throw? Append? Clamp?
- For objects, omitting `key` is presumably an error, but no `@throws` is listed for it.
- The same parameter means two different things (property name vs insertion index) depending on parent type. This is an implicit type cast.

**Fix:** For arrays, use an optional `insertAt?: number` (numeric, not string). For objects, make `key` a required separate overload or discriminated union:

```ts
insertNode(parentPath: string, value: JsonValue, key: string): void;    // object
insertNode(parentPath: string, value: JsonValue, index?: number): void; // array
// or a single discriminated form:
insertNode(parentPath: string, value: JsonValue, position?: { key: string } | { index?: number }): void;
```

---

### 4 — `onChange` fires on the _parent_ for `removeNode` and `insertNode` but on the _node itself_ for `setValue` — inconsistent and undocumented `[MEDIUM]`

A consumer wiring `onChange` to rebuild a form must know _which_ node changed. The current contract mixes levels: `setValue` fires on the modified node, but `removeNode` / `insertNode` fire on the parent. There is no mention of this distinction in `NodeChangeHandler`.

**Fix:** Document the exact node passed to `onChange` for each mutation method. Consider always firing on the affected node _and_ propagating a secondary event to the parent, or define a richer change event type:

```ts
export type ChangeKind = "set" | "insert" | "remove";

export type NodeChangeHandler = (
    node: Readonly<JsonNode>,
    oldValue: JsonValue,
    kind: ChangeKind,
) => void;
```

---

### 5 — `scrollIntoView` returns `Promise<void>` but callers cannot cancel it `[MEDIUM]`

If `scrollIntoView` is called twice in quick succession (e.g., the user clicks a second node before the first scroll completes), there is no way to cancel the in-flight promise. The component must silently decide which scroll wins, but the contract gives callers no control and no signal.

**Fix:** Return a cancellable handle or accept an `AbortSignal`:

```ts
abstract scrollIntoView(
  path: string,
  options?: ScrollIntoViewOptions & { signal?: AbortSignal }
): Promise<void>;
```

---

### 6 — `setOptions` requires a full options object; partial updates are explicitly unsupported `[MEDIUM]`

This is ergonomically costly and fragile. Callers must cache the original options to change one field without losing others. On a complex component this means callers maintain a redundant shadow copy of internal state.

**Fix:** Accept `Partial<JsonTreeEditorOptions>` and deep-merge with existing options, or document a `resetOptions(options)` / `updateOptions(partial)` split.

---

### 7 — `collapse` / `expand` / `toggle` are no-ops on leaves but throw no signal `[MEDIUM]`

The methods are documented as no-ops when called on a leaf. Silent no-ops on invalid input hide bugs. A developer who mistypes a path or passes a leaf path to `collapse()` gets no feedback.

**Fix:** Either throw `TypeError` for leaf paths (consistent with `beginEdit` and `removeNode`) or return a boolean indicating whether the operation applied.

---

### 8 — `NodeKind` conflates two structural concepts `[MEDIUM]`

`"object"` and `"array"` are both "branch" nodes, but they have different child models (keyed vs indexed). Many operations (especially `insertNode`) need to distinguish them. Currently, a consumer must check `Array.isArray(node.value)` themselves — the typed `kind` field does not help.

**Fix:** Either make it `"object" | "array" | "leaf"` (already done — but then document that both object and array are "branch" nodes and add a convenience `isBranch` getter or utility), or add a `isBranch` computed property to `JsonNode`.

```ts
readonly isBranch: boolean; // true for object and array
```

---

### 9 — `getVisibleNodes` is unbounded `[LOW]`

For a large document (thousands of nodes), this can return a very large array with no pagination or lazy-iteration option. The component has `pageSize` for rendering, but `getVisibleNodes` bypasses it entirely.

**Fix:** Document that `getVisibleNodes` reflects pagination (only returns nodes that are rendered, not all logically-visible nodes), or add a range parameter.

---

### 10 — `collapsed` is always `false` on leaf nodes but is still a required field `[LOW]`

`JsonNode.collapsed` is documented as _"always `false` for leaf nodes"_. This means it carries no information for leaves. Consumers will write `if (node.kind === 'leaf' && node.collapsed)` branches that are logically dead.

**Fix:** Make `collapsed` only present on branch nodes using a discriminated union:

```ts
export type JsonNode =
    | { kind: "leaf"; collapsed?: never /* other fields */ }
    | { kind: "object" | "array"; collapsed: boolean /* other fields */ };
```

---

## Open Questions

**Q1.** Does `registerLeafRenderer` / `unregisterLeafRenderer` need a priority value, or is registration order sufficient? The spec says "prepends", which means the last registered always wins — this makes it hard for a library to register low-priority fallback renderers.

**Q2.** Is the component thread-safe / reentrant? E.g., can `onChange` call `setValue` on the same component synchronously? There is no documented re-entrancy policy.

**Q3.** `getData()` returns a deep copy every time. For large trees this is expensive. Is there an intentional decision not to offer a `subscribe` or read-only proxy? If so, document the cost.

**Q4.** `path` uses dot-notation with array bracket syntax (`users[0].address`). This format is not uniquely specified (is `users.0` also valid? How are keys containing dots or brackets escaped?). The path grammar needs formal definition or a reference.

**Q5.** `expandToPath` expands _ancestors_ without changing any other nodes. Does it also expand the target node itself if it is a branch?

---

## Naming Issues

`collapseDepthBeyond(depth)` — the word "beyond" is slightly ambiguous. _"Collapses all nodes deeper than `depth`"_ is correct per the docs, but the method name reads as "collapse everything beyond this depth", which could be misread as "collapse from this depth onward" (inclusive). Rename to `collapseBelow(depth)` or `collapseNodesDeeper(thanDepth)` for clarity.

`initialCollapseDepth` — the semantics at `0` (only root visible, everything else collapsed) versus `Infinity` (all expanded) are inverted compared to what "collapse depth" implies. The name feels like it describes "how deep to collapse to", but `0` meaning "collapse everything" is counterintuitive. Consider `initialExpandDepth` with `0` meaning nothing expanded beyond root, which is the natural reading.

---

## Summary

The design is well-structured and covers the common workflows (edit, insert, remove, expand/collapse, custom rendering). The most critical defects are the overloaded `commit` callback in `LeafNodeRenderer`, the undocumented edit-mode lock conflict policy, and the ambiguous `insertNode` key semantics for arrays — each of which would cause real integration bugs. The `setOptions` full-replace requirement and the `onChange` node-level inconsistency are the next highest priority ergonomic fixes. Everything else is lower-severity cleanup.
