// ============================================================
//  JsonTreeEditor — Abstract API
//  A reusable, pure-TypeScript component for displaying and
//  in-place editing arbitrary JSON data as a collapsible tree.
// ============================================================

// ─────────────────────────────────────────────
//  Primitive types
// ─────────────────────────────────────────────

/** Every JSON-compatible scalar value. */
export type JsonPrimitive = string | number | boolean | null;

/** Any valid JSON value, including nested structures. */
export type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | { [key: string]: JsonValue };


// ─────────────────────────────────────────────
//  Node model
// ─────────────────────────────────────────────

/** Identifies the structural role of a node in the tree. */
export type NodeKind = "object" | "array" | "leaf";

/**
 * A stable descriptor for a single node inside the tree.
 * Passed to every event handler and renderer so callers never
 * need to keep their own references to internal state.
 */
export interface JsonNode {
  /**
   * Dot-notation path from the root, e.g. `"users[0].address.city"`.
   * The root node itself has path `""`.
   */
  readonly path: string;

  /** Structural role of this node. */
  readonly kind: NodeKind;

  /**
   * The key (object property name or array index as a string)
   * under which this node appears in its parent.
   * `undefined` for the root node.
   */
  readonly key: string | undefined;

  /**
   * Current value held by this node.
   * For branch nodes (object / array) this is the live sub-tree.
   */
  readonly value: JsonValue;

  /** Nesting depth; 0 for the root. */
  readonly depth: number;

  /**
   * Whether this branch node is currently collapsed.
   * Always `false` for leaf nodes.
   */
  readonly collapsed: boolean;
}


// ─────────────────────────────────────────────
//  Event handler types
// ─────────────────────────────────────────────

/** Signature for node interaction callbacks. */
export type NodeEventHandler = (node: Readonly<JsonNode>) => void;

/**
 * Invoked whenever a value or sub-tree has been replaced
 * programmatically or through in-place editing.
 *
 * @param node    - The node whose value changed.
 * @param oldValue - The value that was in place before the change.
 */
export type NodeChangeHandler = (
  node: Readonly<JsonNode>,
  oldValue: JsonValue
) => void;


// ─────────────────────────────────────────────
//  Leaf renderer interface
// ─────────────────────────────────────────────

/**
 * Implement this interface to provide a fully custom renderer
 * for leaf nodes (i.e. nodes whose `kind === "leaf"`).
 *
 * The component calls `mount` once when a leaf is first rendered
 * or recycled into view, then calls `update` on subsequent value
 * changes, and `destroy` when the leaf scrolls out of a virtual
 * viewport or the component is disposed.
 *
 * ### Lifecycle
 * ```
 * mount()  →  update()*  →  destroy()
 * ```
 *
 * ### Editing contract
 * When the user finishes editing inside a custom renderer, call
 * the `commit` function supplied to `mount`.  The component will
 * validate, apply the change, and fire `onChange`.  To cancel,
 * call `commit(node.value)` (pass the unchanged value back).
 *
 * @example
 * ```ts
 * class DateRenderer implements LeafNodeRenderer {
 *   private input: HTMLInputElement = document.createElement("input");
 *
 *   mount(container, node, commit) {
 *     this.input.type = "date";
 *     this.input.value = String(node.value);
 *     this.input.addEventListener("change", () => commit(this.input.value));
 *     container.appendChild(this.input);
 *   }
 *
 *   update(node) { this.input.value = String(node.value); }
 *   destroy()    { this.input.remove(); }
 *
 *   // Only handle string values that look like ISO dates.
 *   canRender(node) {
 *     return typeof node.value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(node.value);
 *   }
 * }
 * ```
 */
export interface LeafNodeRenderer {
  /**
   * Returns `true` when this renderer wants to handle `node`.
   * The component calls `canRender` on each registered renderer
   * in order; the first match wins.  If no renderer matches,
   * the built-in default is used.
   */
  canRender(node: Readonly<JsonNode>): boolean;

  /**
   * Called once to attach DOM content for `node` into `container`.
   *
   * @param container - The host element provided by the component.
   *                    The renderer owns its content; the component
   *                    will never touch children of this element.
   * @param node      - The leaf node to display.
   * @param commit    - Call with the new value to confirm an edit,
   *                    or with the current value to cancel.
   */
  mount(
    container: HTMLElement,
    node: Readonly<JsonNode>,
    commit: (newValue: JsonPrimitive) => void
  ): void;

  /**
   * Called when the same node's value changes without unmounting
   * (e.g. a programmatic `setValue` while the node is visible).
   * Implementations should update their DOM in-place.
   */
  update(node: Readonly<JsonNode>): void;

  /**
   * Called before the renderer's container is removed from the DOM.
   * Clean up event listeners, timers, or other resources here.
   */
  destroy(): void;
}


// ─────────────────────────────────────────────
//  Options
// ─────────────────────────────────────────────

/**
 * Configuration object passed to the `JsonTreeEditor` constructor.
 * All fields are optional; the component provides sensible defaults.
 */
export interface JsonTreeEditorOptions {
  /**
   * CSS class name(s) to add to the root container element.
   * Useful for theming without touching the component's own styles.
   */
  className?: string;

  /**
   * Whether nodes are editable by default.
   * Individual leaf values can be double-clicked to edit.
   * @default true
   */
  editable?: boolean;

  /**
   * Depth at which branch nodes are initially collapsed.
   * `0` = everything collapsed (only root visible);
   * `Infinity` = everything expanded.
   * @default 2
   */
  initialCollapseDepth?: number;

  /**
   * Maximum number of items shown inside an object or array
   * before a "show more" affordance is rendered.
   * `Infinity` disables pagination.
   * @default Infinity
   */
  pageSize?: number;

  /**
   * Custom leaf renderers evaluated in order.
   * The first renderer whose `canRender` returns `true` is used.
   * Falls back to the built-in renderer when no match is found.
   */
  leafRenderers?: LeafNodeRenderer[];

  // ── Event handlers ──────────────────────────────────────────

  /** Fired when a branch node is collapsed. */
  onCollapse?: NodeEventHandler;

  /** Fired when a branch node is expanded. */
  onExpand?: NodeEventHandler;

  /** Fired on a single click on any node row. */
  onClick?: NodeEventHandler;

  /** Fired on a double-click on any node row. */
  onDoubleClick?: NodeEventHandler;

  /**
   * Fired after a value or sub-tree has been successfully changed,
   * whether through in-place editing or a programmatic `setValue`.
   */
  onChange?: NodeChangeHandler;
}


// ─────────────────────────────────────────────
//  Abstract component class
// ─────────────────────────────────────────────

/**
 * `JsonTreeEditor` — Abstract base class.
 *
 * Subclasses are responsible for concrete DOM rendering, event
 * wiring, and internal state management.  Callers interact only
 * through this public API.
 *
 * ### Quick-start
 * ```ts
 * const editor = new ConcreteJsonTreeEditor(
 *   { users: [{ id: 1, active: true }] },
 *   {
 *     initialCollapseDepth: 1,
 *     editable: true,
 *     onChange: (node, old) => console.log("changed", node.path, old, "→", node.value),
 *   }
 * );
 *
 * document.getElementById("panel")!.appendChild(editor.getElement());
 * ```
 */
export abstract class JsonTreeEditor {

  // ── Construction ────────────────────────────────────────────

  /**
   * @param data    - The JSON value to display.  A deep copy is made
   *                  internally so the caller's original object is
   *                  never mutated.
   * @param options - Optional configuration.
   */
  constructor(data: JsonValue, options?: JsonTreeEditorOptions) {
    // Concrete subclass calls super(), then performs its own init.
  }


  // ── DOM integration ─────────────────────────────────────────

  /**
   * Returns the root HTML element of the component.
   * Mount this into any container; the component manages everything inside.
   */
  abstract getElement(): HTMLElement;

  /**
   * Releases all DOM nodes, event listeners, and internal resources.
   * After calling `dispose()` the component must not be used again.
   */
  abstract dispose(): void;


  // ── Data access ─────────────────────────────────────────────

  /**
   * Returns a snapshot of the entire current JSON value.
   * The returned object is a deep copy; mutating it has no effect.
   */
  abstract getData(): JsonValue;

  /**
   * Resolves a dot-notation path and returns the corresponding node
   * descriptor, or `undefined` if the path does not exist.
   *
   * @param path - e.g. `"users[0].address"` or `""` for root.
   */
  abstract getNode(path: string): Readonly<JsonNode> | undefined;

  /**
   * Returns descriptors for all currently visible (non-collapsed) nodes
   * in document order (depth-first, pre-order).
   */
  abstract getVisibleNodes(): ReadonlyArray<Readonly<JsonNode>>;


  // ── Expand / collapse ───────────────────────────────────────

  /**
   * Collapses the branch node at `path`.
   * No-op if the node is already collapsed or is a leaf.
   *
   * @param path - Dot-notation path to the target node.
   */
  abstract collapse(path: string): void;

  /**
   * Expands the branch node at `path`.
   * No-op if the node is already expanded or is a leaf.
   *
   * @param path - Dot-notation path to the target node.
   */
  abstract expand(path: string): void;

  /**
   * Toggles the collapsed/expanded state of the branch node at `path`.
   *
   * @param path - Dot-notation path to the target node.
   */
  abstract toggle(path: string): void;

  /**
   * Collapses all branch nodes in the entire tree.
   */
  abstract collapseAll(): void;

  /**
   * Expands all branch nodes in the entire tree.
   */
  abstract expandAll(): void;

  /**
   * Expands every ancestor of the node at `path` so that the node
   * becomes visible, without changing the state of any other nodes.
   *
   * @param path - Dot-notation path to the node to reveal.
   */
  abstract expandToPath(path: string): void;

  /**
   * Collapses all nodes deeper than `depth`.
   * Nodes at depth ≤ `depth` are unaffected.
   *
   * @param depth - 0-based depth threshold (root is depth 0).
   */
  abstract collapseDepthBeyond(depth: number): void;


  // ── Programmatic value mutation ─────────────────────────────

  /**
   * Replaces the value at `path` with `newValue`.
   *
   * - If `newValue` is an object or array it becomes a new branch node.
   * - If `path` points to an existing branch and `newValue` is a
   *   primitive, the branch is replaced with a leaf.
   * - Fires `onChange` after a successful replacement.
   *
   * @param path     - Dot-notation path to the node to replace.
   * @param newValue - The replacement value; must be JSON-serialisable.
   * @throws {RangeError} if `path` does not exist in the current data.
   */
  abstract setValue(path: string, newValue: JsonValue): void;

  /**
   * Removes the node at `path` from its parent.
   *
   * - For object parents, the key is deleted.
   * - For array parents, the element is spliced out and sibling
   *   paths are updated accordingly.
   * - Fires `onChange` on the parent node after removal.
   *
   * @param path - Dot-notation path to the node to remove.
   * @throws {RangeError}  if `path` does not exist.
   * @throws {TypeError}   if `path` is `""` (the root cannot be removed).
   */
  abstract removeNode(path: string): void;

  /**
   * Inserts `value` into the object or array at `parentPath`.
   *
   * For **object** parents, `key` is required and must not already exist.
   * For **array** parents, `key` is the numeric insertion index
   * (as a string, e.g. `"2"`); elements from that index onward are
   * shifted right.  Omitting `key` appends to the end.
   *
   * Fires `onChange` on the parent node after insertion.
   *
   * @param parentPath - Dot-notation path to the parent node.
   * @param value      - Value to insert; must be JSON-serialisable.
   * @param key        - Property name (object) or index (array).
   * @throws {RangeError} if `parentPath` does not exist or is a leaf.
   * @throws {TypeError}  if `key` conflicts with an existing object key.
   */
  abstract insertNode(parentPath: string, value: JsonValue, key?: string): void;


  // ── View / scroll ───────────────────────────────────────────

  /**
   * Scrolls the node at `path` into the visible viewport of the
   * component, expanding collapsed ancestors as needed.
   *
   * Resolves when the scroll animation (if any) has completed.
   *
   * @param path    - Dot-notation path to the target node.
   * @param options - Standard `ScrollIntoViewOptions` forwarded to
   *                  the underlying DOM call (e.g. `{ behavior: "smooth" }`).
   * @throws {RangeError} if `path` does not exist.
   */
  abstract scrollIntoView(
    path: string,
    options?: ScrollIntoViewOptions
  ): Promise<void>;

  /**
   * Programmatically places the component into edit mode for the
   * leaf node at `path`, as if the user had double-clicked it.
   *
   * Expands ancestors, scrolls the node into view, then activates
   * the in-place editor (built-in or custom renderer).
   *
   * @param path - Dot-notation path to the leaf node to edit.
   * @throws {RangeError} if `path` does not exist.
   * @throws {TypeError}  if the node is not a leaf.
   */
  abstract beginEdit(path: string): void;

  /**
   * Commits the currently active in-place edit (if any).
   * Equivalent to the user pressing Enter / Tab.
   * No-op when no edit is in progress.
   */
  abstract commitEdit(): void;

  /**
   * Cancels the currently active in-place edit (if any).
   * Equivalent to the user pressing Escape.
   * No-op when no edit is in progress.
   */
  abstract cancelEdit(): void;


  // ── Options / renderers ─────────────────────────────────────

  /**
   * Replaces the entire option set and re-renders the tree.
   * Partial updates are not supported; supply a complete options object.
   *
   * @param options - New configuration to apply.
   */
  abstract setOptions(options: JsonTreeEditorOptions): void;

  /**
   * Prepends `renderer` to the leaf-renderer chain so it is evaluated
   * before all previously registered renderers.
   *
   * Triggers a re-render of all visible leaf nodes so that newly
   * matched nodes immediately use the new renderer.
   *
   * @param renderer - A `LeafNodeRenderer` implementation.
   */
  abstract registerLeafRenderer(renderer: LeafNodeRenderer): void;

  /**
   * Removes a previously registered leaf renderer.
   * Affected leaf nodes fall back to the next matching renderer
   * (or the built-in default) and are re-rendered immediately.
   *
   * @param renderer - The exact instance that was passed to
   *                   `registerLeafRenderer`.
   */
  abstract unregisterLeafRenderer(renderer: LeafNodeRenderer): void;
}