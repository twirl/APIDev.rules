# Backward Compatibility

Use this fragment when designing APIs that should stay resilient to future change, or when modifying an existing API.

## Versioning Policy

- Treat backward compatibility as a central API obligation, not a routine implementation detail, unless specifically instructed otherwise.
- Use semantic versioning to classify API changes: major for incompatible changes, minor for compatible functionality, patch for fixes, unless instructed otherwise.
- Do not break compatibility when an additive or otherwise compatible alternative is available. Provide clear migration instructions if a breaking change is inevitable.

## Compatibility Scope

- Define backward compatibility as preserving the functional correctness of existing consumer code, not necessarily preserving every invisible implementation detail.
- Before modifying an existing API, identify the observable contract: documentation, specification, examples, generated clients, SDK behavior, error behavior, timing, consistency, event order, and known consumer usage.
- Treat undocumented but observable behavior as risky to change when consumers may rely on it.
- Document product logic that client code may depend on: state transitions, event order, consistency guarantees, timing assumptions, status causes, and allowed workflows.
- Keep product behavior backward-compatible too; a technically compatible field addition can still break partners if it changes the business process they modeled.

## Exposing Functionality

- Expose the minimal public surface that solves the consumer problem.
- Avoid gray zones: do not return undocumented fields, rely on private behavior in samples, or hint at unsupported capabilities.
- If fixing a bug would break real consumers, preserve the old behavior until the next major version or introduce a compatibility mode, unless specifically instructed otherwise.

## Designing for Extension

- Prefer extending by abstraction: reinterpret the old interface as a helper or reduced case of a more general interface.
- When adding optional capability, make the old behavior equivalent to the new general behavior with explicit default values.

Existing helper:

```ts
await machine.prepareLungo({
    volume: "80ml",
});
```

Generalized interface:

```ts
await machine.prepare({
    recipe: "lungo",
    volume: "80ml",
    options: {
        contactlessDelivery: false,
    },
});
```

The old helper stays compatible as a reduced case of the generalized interface. Do not change the meaning of the old helper when adding the generalized interface. Make the defaults explicit so consumers can understand how old behavior maps to the new model.

- Consider every entity as an implementation of a more general interface, even when no alternative implementation is planned yet.
- Use builder or helper endpoints only to simplify common workflows over more general underlying concepts.

## Coupling and Contexts

Use this section when the API has several abstraction levels, supports interchangeable implementations, or exposes interfaces for integrators to implement. This is especially relevant for SDKs and multi-actor environments.

- Avoid strong coupling where low-level entities define high-level concepts, or high-level entities prescribe low-level implementation details.
- Let higher-level entities define informational contexts for lower-level entities to interpret.
- Delegate concrete work to the lowest abstraction level that actually owns the capability.
- Prefer weak coupling when low-level implementations are expected to vary: exchange state, events, or context changes instead of requiring every implementation to support every method.

Strong coupling:

```ts
// An integrator plugs their own delivery service
// into the API vendor's order processing engine.
createOrder({
    delivery_service: customDeliveryService,
});
// The custom delivery service must follow the contract.
interface CustomDeliveryService {
    registerOrder(orderAccessor: OrderAccessor);
    getCourierName(orderId);
}
// OrderAccessor is the interface the API vendor gives to the partner
// to provide data and functions the partner might need.
interface OrderAccessor {
    id: OrderId;
    confirmOrder();
    cancelOrder();
}
```

Problem: when a new feature appears, such as contactless robot delivery, the shared interface must grow again. The robot needs to tell the user to collect the order and may require a confirmation code before opening the compartment. If the contract is method-based, this becomes another set of optional methods.

```ts
interface CustomDeliveryService {
  registerOrder(orderAccessor: OrderAccessor);
  optional isRobotDelivery(orderId);
  optional getCourierName(orderId);
  optional getConfirmationCode(orderId);
}
interface OrderAccessor {
  id: OrderId;
  confirmOrder();
  cancelOrder();
  optional notifyUserToPickUp();
}
```

Methods become optional, new optional methods are added, and product logic becomes harder to understand. The more this happens, the less clear it is why each optional field or method exists and how to use it correctly.

Weak coupling:

```ts
interface CustomDeliveryService {
  public registerOrder(orderAccessor)
  // Instead of locking the contract to "courier",
  // use generalized terms from the product domain.
  public getDeliveryCarrierData(order) => DeliveryCarrierData
  public subscribe(order, event, callback)
  // Events might be 'confirm', 'cancel', 'user_needs_to_pick_up', etc.
}
interface OrderAccessor {
  id: OrderId;
  notify(event, data);
}
```

- Keep weak coupling practical. Reverse strong coupling can be acceptable when lower-level implementations need to report to a slower-changing higher-level context. In the example above, providing webhooks for specific events instead of requiring generalized subscription functionality is usually acceptable, though less extensible.

- If an entity has no stable semantics beyond identifying a context, keep its public surface minimal and let related contexts carry the data.

- Note that decoupling does not reduce domain complexity or the number of entities. It keeps interfaces reasonably understandable and partners' code readable as implementations diverge.

## Dependency Isolation

- Do not proxy third-party, partner, hardware, or platform APIs directly as your public API.
- Isolate external dependencies behind your own abstraction layer so their changes, outages, latency, or incompatibilities do not become your consumers' problem.
