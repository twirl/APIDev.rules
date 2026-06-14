Design a reusable pure TypeScript (no libs) UI component for displaying and in-place editing some data as JSON.
Functionality: presenting JSON as a tree with collapsible nodes for objects and arrays win an ability
API: constructor (JSON itself + options), methods to selectively collapse and expand individual nodes, handlers for operations with nodes (collapsing, expanding, clicking, double-clicking items), scrolling items into view; an ability to replace values and subtrees programmatically.
Provide the capability to have a custom renderer for leaf nodes. Define what interface it must implement.
Do not write implementation. Create an abstract class with all the signatures and basic documentation.
