// ─────────────────────────────────────────────────────────────────────────────
// JsonTreeEditor.ts
// Abstract class defining the public API of a pure-TypeScript, zero-dependency
// UI component that displays and in-place edits arbitrary JSON as a tree.
// ─────────────────────────────────────────────────────────────────────────────


// ─── Value types ─────────────────────────────────────────────────────────────

/** Every JSON-legal primitive that can appear at a leaf node. */
export type JsonPrimitive = string | number | boolean | null;

/** The full set of JSON-legal values. */
export type JsonValue = JsonPrimitive | JsonObject | JsonArray;

/** A JSON object node. */
export interface JsonObject {
  [key: string]: JsonValue;
}

/** A JSON array node. */
export type JsonArray = JsonValue[];


// ─── Path ────────────────────────────────────────────────────────────────────

/**
 * An ordered sequence of keys that uniquely identifies any node in the tree.
 * Object keys are represented as strings; array indices as numbers.
 *
 * Examples:
 *   []                  – the root
 *   ["users"]           – root.users
 *   ["users", 0]        – root.users[0]
 *   ["users", 0, "id"]  – root.users[0].id
 */
export type JsonNodePath = ReadonlyArray<string | number>;


// ─── Node descriptor ─────────────────────────────────────────────────────────

/** Structural classification of a tree node. */
export type JsonNodeKind = "object" | "array" | "leaf";

/**
 * A snapshot of a single tree node at the time an event fires or a query
 * is answered.  The object is immutable; mutating it has no effect on the
 * tree.
 */
export interface JsonNodeDescriptor {
  /** Absolute path from the root to this node. */
  readonly path: JsonNodePath;

  /** Structural kind of the node. */
  readonly kind: JsonNodeKind;

  /**
   * The node's current value.
   * - For `"leaf"` nodes this is a `JsonPrimitive`.
   * - For `"object"` and `"array"` nodes this is the full subtree.
   */
  readonly value: JsonValue;

  /**
   * The key (object property name or array index) under which this node is
   * stored in its parent.  `undefined` for the root node.
   */
  readonly key: string | number | undefined;

  /**
   * `true` when the node is an `"object"` or `"array"` and its children are
   * currently rendered in the DOM.  Always `false` for leaf nodes.
   */
  readonly isExpanded: boolean;

  /**
   * Reference to the DOM element that represents this node's row in the tree,
   * or `null` if the node is inside a collapsed ancestor and therefore not
   * currently mounted.
   */
  readonly element: HTMLElement | null;
}


// ─── Edit event ──────────────────────────────────────────────────────────────

/**
 * Delivered to `JsonTreeEditorOptions.onValueChange` after any programmatic
 * or interactive mutation completes.
 */
export interface JsonValueChangeEvent {
  /** Path of the node whose value was replaced. */
  readonly path: JsonNodePath;

  /** The value that was in place before the change. */
  readonly previousValue: JsonValue;

  /** The value that is now stored at `path`. */
  readonly nextValue: JsonValue;
}


// ─── Interaction events ───────────────────────────────────────────────────────

/**
 * Delivered to expansion / collapse handlers whenever a branch node's open
 * state changes.
 */
export interface JsonExpansionEvent {
  readonly path: JsonNodePath;
  /** The node's expansion state *after* the event fires. */
  readonly isExpanded: boolean;
}

/**
 * Delivered to click / double-click handlers on any row in the tree.
 * The underlying DOM event is included so callers can inspect modifiers,
 * call `stopPropagation`, etc.
 */
export interface JsonClickEvent {
  readonly path: JsonNodePath;
  readonly kind: JsonNodeKind;
  readonly domEvent: MouseEvent;
}


// ─── Custom leaf renderer ─────────────────────────────────────────────────────

/**
 * Context object supplied to a custom leaf renderer each time a leaf is
 * painted or repainted.
 */
export interface LeafRenderContext {
  /** Path of the leaf being rendered. */
  readonly path: JsonNodePath;

  /** Current primitive value of the leaf. */
  readonly value: JsonPrimitive;

  /**
   * Call this function to commit an edited value back to the tree.
   * The change will propagate through `onValueChange` just like any
   * programmatic replacement.
   *
   * Throws `JsonTreeEditorError` with code `"invalid_value"` when `newValue`
   * cannot be serialised to JSON.
   */
  readonly commitValue: (newValue: JsonPrimitive) => void;

  /**
   * The container element the renderer must populate.  The renderer owns the
   * full content of this element for as long as the leaf is visible.
   * The component clears and re-invokes `render` whenever the path's value
   * changes externally.
   */
  readonly container: HTMLElement;
}

/**
 * Interface that a custom leaf renderer must implement.
 *
 * A renderer is responsible for two lifecycle phases:
 *
 * 1. **Render** (`render`): populate `context.container` with whatever DOM
 *    elements represent the leaf.  The method is called each time the node
 *    is first mounted or its value is replaced externally.
 *
 * 2. **Destroy** (`destroy`): remove event listeners, cancel timers, and
 *    release any resources held for this leaf.  Called when the node
 *    scrolls out of view inside a virtualised list or its ancestor is
 *    collapsed.
 *
 * Implementations must be stateless with respect to the tree; all state
 * they need is carried in `context`.  One renderer instance may be reused
 * across many nodes simultaneously.
 *
 * @example
 * ```ts
 * class StarRatingRenderer implements LeafNodeRenderer {
 *   render(context: LeafRenderContext): void {
 *     const stars = document.createElement("span");
 *     stars.textContent = "★".repeat(Number(context.value));
 *     stars.addEventListener("click", () => context.commitValue(5));
 *     context.container.appendChild(stars);
 *   }
 *   destroy(context: LeafRenderContext): void {
 *     context.container.innerHTML = "";
 *   }
 * }
 * ```
 */
export interface LeafNodeRenderer {
  /**
   * Populate `context.container` with the visual representation of the leaf.
   * Called on initial mount and on every external value replacement.
   *
   * The method may be synchronous or async.  If async, the container should
   * show a loading state while the promise is pending.
   */
  render(context: LeafRenderContext): void | Promise<void>;

  /**
   * Release all resources (event listeners, timers, sub-components) that were
   * allocated during `render`.  The component guarantees this is called before
   * `context.container` is removed from the DOM.
   */
  destroy(context: LeafRenderContext): void;
}


// ─── Constructor options ──────────────────────────────────────────────────────

/**
 * A predicate that the constructor uses to decide which leaf paths should use
 * the custom renderer instead of the built-in one.
 *
 * Return `true` to hand the node to the custom renderer.
 */
export type LeafRendererPredicate = (descriptor: JsonNodeDescriptor) => boolean;

/**
 * Configuration accepted by the `JsonTreeEditor` constructor.
 *
 * All properties except `container` are optional; the component ships with
 * sensible defaults for everything else.
 */
export interface JsonTreeEditorOptions {
  /**
   * The DOM element into which the component will render its root.
   * Must already be attached to the document.
   */
  container: HTMLElement;

  /**
   * Paths whose branch nodes should begin in the collapsed state.
   * All other branch nodes start expanded.
   * Defaults to `[]` (everything expanded).
   */
  initiallyCollapsedPaths?: JsonNodePath[];

  /**
   * Maximum nesting depth that the component auto-expands on first render.
   * Nodes deeper than this limit start collapsed.
   * `Infinity` expands everything; `0` collapses everything below root.
   * Defaults to `Infinity`.
   */
  autoExpandDepth?: number;

  /**
   * When `true` the tree is read-only: double-click editing is disabled and
   * programmatic `replaceValue` / `replaceSubtree` calls throw.
   * Defaults to `false`.
   */
  readOnly?: boolean;

  /**
   * Custom renderer for leaf nodes.
   * When omitted, the built-in renderer is used for all leaves.
   */
  leafRenderer?: LeafNodeRenderer;

  /**
   * Selects which leaf nodes are handed to `leafRenderer`.
   * Ignored when `leafRenderer` is not provided.
   * Defaults to a predicate that returns `true` for all leaves.
   */
  leafRendererPredicate?: LeafRendererPredicate;

  // ── Event handlers ─────────────────────────────────────────────────────────

  /**
   * Fired after any node's value or subtree is replaced, whether by the user
   * editing a leaf in-place or by a programmatic call to `replaceValue` /
   * `replaceSubtree`.
   */
  onValueChange?: (event: JsonValueChangeEvent) => void;

  /**
   * Fired each time a branch node is expanded or collapsed, whether by user
   * interaction or by a programmatic call to `expand` / `collapse`.
   */
  onExpansionChange?: (event: JsonExpansionEvent) => void;

  /**
   * Fired on a single pointer click on any tree row.
   */
  onClick?: (event: JsonClickEvent) => void;

  /**
   * Fired on a double pointer click on any tree row.
   * The default behaviour (entering inline-edit mode) can be prevented by
   * calling `event.domEvent.preventDefault()`.
   */
  onDoubleClick?: (event: JsonClickEvent) => void;
}


// ─── Error ───────────────────────────────────────────────────────────────────

/** Machine-readable codes for all errors the component can throw. */
export type JsonTreeEditorErrorCode =
  | "path_not_found"       // The supplied path does not exist in the current tree.
  | "invalid_value"        // The supplied value cannot be serialised to JSON.
  | "read_only"            // A mutation was attempted while readOnly is true.
  | "component_destroyed"; // A method was called after destroy() was invoked.

/**
 * All errors thrown by `JsonTreeEditor` are instances of this class.
 * `code` is machine-readable; `message` is for developers only and must
 * not be relied on programmatically.
 */
export class JsonTreeEditorError extends Error {
  constructor(
    public readonly code: JsonTreeEditorErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "JsonTreeEditorError";
  }
}


// ─── Abstract component ───────────────────────────────────────────────────────

/**
 * `JsonTreeEditor` – a reusable, zero-dependency UI component that renders an
 * arbitrary JSON value as a navigable, collapsible tree and supports in-place
 * editing of leaf nodes.
 *
 * ## Responsibilities
 *
 * - **Display**: render objects, arrays, and primitives as indented tree rows
 *   with type-aware syntax colouring.
 * - **Navigation**: collapse and expand branch nodes individually or in bulk.
 * - **Editing**: let users rename leaf values inline via double-click, or allow
 *   callers to replace any value or subtree programmatically.
 * - **Custom rendering**: delegate specific leaf nodes to a caller-supplied
 *   `LeafNodeRenderer` (e.g. colour pickers, date inputs, star ratings).
 * - **Events**: surface user interactions through typed handler callbacks.
 *
 * ## Lifecycle
 *
 * ```
 * new JsonTreeEditor(data, options)   // mount into options.container
 *        │
 *        ├─ expand / collapse / replaceValue / replaceSubtree …
 *        │
 *        └─ destroy()                 // unmount, release all resources
 * ```
 *
 * After `destroy()` is called every other method throws a
 * `JsonTreeEditorError` with code `"component_destroyed"`.
 *
 * ## Error handling
 *
 * All public methods that can fail throw `JsonTreeEditorError`.
 * The `code` property identifies the problem; see `JsonTreeEditorErrorCode`.
 */
export abstract class JsonTreeEditor {

  // ── Constructor ─────────────────────────────────────────────────────────────

  /**
   * Mount the component into `options.container` and render `data`.
   *
   * @param data    The JSON value to display.  The component takes an internal
   *                deep copy; subsequent mutations to this reference have no
   *                effect.
   * @param options Configuration and event handlers.  `options.container`
   *                is required; all other properties are optional.
   *
   * @throws `JsonTreeEditorError("invalid_value")` when `data` contains
   *   non-JSON-serialisable values (e.g. `undefined`, functions, circular
   *   references).
   */
  constructor(data: JsonValue, options: JsonTreeEditorOptions) {
    void data;
    void options;
  }


  // ── Node inspection ─────────────────────────────────────────────────────────

  /**
   * Return a snapshot of the node at `path`.
   *
   * @throws `JsonTreeEditorError("path_not_found")` when `path` does not exist.
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract describeNode(path: JsonNodePath): JsonNodeDescriptor;

  /**
   * Return `true` when a node exists at `path` in the current tree.
   *
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract hasNode(path: JsonNodePath): boolean;


  // ── Expansion control ───────────────────────────────────────────────────────

  /**
   * Expand the branch node at `path`, revealing its children.
   * Has no effect when the node is already expanded.
   * Fires `onExpansionChange` when the state actually changes.
   *
   * @throws `JsonTreeEditorError("path_not_found")` when `path` does not exist.
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract expand(path: JsonNodePath): void;

  /**
   * Collapse the branch node at `path`, hiding its children.
   * Has no effect when the node is already collapsed.
   * Fires `onExpansionChange` when the state actually changes.
   *
   * @throws `JsonTreeEditorError("path_not_found")` when `path` does not exist.
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract collapse(path: JsonNodePath): void;

  /**
   * Recursively expand the branch node at `path` and all of its descendants
   * up to `depthLimit` levels below `path`.
   * `depthLimit` defaults to `Infinity` (fully expand the entire subtree).
   * Fires `onExpansionChange` once per node whose state actually changes.
   *
   * @throws `JsonTreeEditorError("path_not_found")` when `path` does not exist.
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract expandSubtree(path: JsonNodePath, depthLimit?: number): void;

  /**
   * Recursively collapse the branch node at `path` and all of its descendants.
   * Fires `onExpansionChange` once per node whose state actually changes.
   *
   * @throws `JsonTreeEditorError("path_not_found")` when `path` does not exist.
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract collapseSubtree(path: JsonNodePath): void;

  /**
   * Expand every ancestor of `path` that is currently collapsed, ensuring the
   * target node is visible without scrolling.  Does not expand the node at
   * `path` itself.
   * Fires `onExpansionChange` for each ancestor whose state actually changes.
   *
   * @throws `JsonTreeEditorError("path_not_found")` when `path` does not exist.
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract revealNode(path: JsonNodePath): void;


  // ── Programmatic mutation ───────────────────────────────────────────────────

  /**
   * Replace the primitive value at `path` with `newValue`.
   * The node at `path` must be a leaf (`"leaf"` kind); use `replaceSubtree`
   * to swap objects or arrays.
   * Fires `onValueChange` after the replacement is applied.
   *
   * @throws `JsonTreeEditorError("path_not_found")` when `path` does not exist.
   * @throws `JsonTreeEditorError("invalid_value")` when `newValue` cannot be
   *   serialised to JSON, or when the node at `path` is not a leaf.
   * @throws `JsonTreeEditorError("read_only")` when the component is in
   *   read-only mode.
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract replaceValue(path: JsonNodePath, newValue: JsonPrimitive): void;

  /**
   * Replace the value at `path` – which may be a leaf, object, or array – with
   * `newSubtree`.
   * Fires `onValueChange` after the replacement is applied.
   * When `newSubtree` is an object or array, the subtree is deep-copied
   * internally; subsequent mutations to the reference have no effect.
   *
   * @throws `JsonTreeEditorError("path_not_found")` when `path` does not exist.
   * @throws `JsonTreeEditorError("invalid_value")` when `newSubtree` contains
   *   non-JSON-serialisable values.
   * @throws `JsonTreeEditorError("read_only")` when the component is in
   *   read-only mode.
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract replaceSubtree(path: JsonNodePath, newSubtree: JsonValue): void;


  // ── Viewport ────────────────────────────────────────────────────────────────

  /**
   * Scroll the row for `path` into the viewport.  If `path` is inside a
   * collapsed ancestor, all ancestors are expanded first (equivalent to
   * calling `revealNode(path)` automatically).
   *
   * `scrollBehavior` mirrors the `ScrollIntoViewOptions.behavior` DOM option:
   * - `"auto"` (default) – instant or browser-defined smooth scrolling.
   * - `"smooth"` – CSS smooth-scroll animation.
   *
   * Returns a `Promise` that resolves when any required expansion animations
   * and the scroll motion have finished.
   *
   * @throws `JsonTreeEditorError("path_not_found")` when `path` does not exist.
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract scrollNodeIntoView(
    path: JsonNodePath,
    scrollBehavior?: "auto" | "smooth",
  ): Promise<void>;


  // ── Data access ─────────────────────────────────────────────────────────────

  /**
   * Return a deep copy of the entire JSON value currently held by the
   * component, reflecting all edits made since construction.
   *
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract exportJson(): JsonValue;


  // ── Options ─────────────────────────────────────────────────────────────────

  /**
   * Toggle read-only mode at runtime.
   * When switching to `true` any active inline-edit session is cancelled
   * without committing changes.
   *
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract setReadOnly(readOnly: boolean): void;

  /**
   * Replace the active `LeafNodeRenderer` and `LeafRendererPredicate` at
   * runtime.  Pass `null` for `renderer` to restore the built-in renderer for
   * all leaves.  The tree is re-rendered immediately to apply the change.
   *
   * @throws `JsonTreeEditorError("component_destroyed")` after `destroy()`.
   */
  abstract setLeafRenderer(
    renderer: LeafNodeRenderer | null,
    predicate?: LeafRendererPredicate,
  ): void;


  // ── Lifecycle ───────────────────────────────────────────────────────────────

  /**
   * Unmount the component: remove all DOM nodes from `options.container`,
   * call `destroy()` on any active `LeafNodeRenderer`, and release all event
   * listeners.
   *
   * After this call every other method throws
   * `JsonTreeEditorError("component_destroyed")`.
   *
   * Calling `destroy()` more than once is a no-op.
   */
  abstract destroy(): void;
}